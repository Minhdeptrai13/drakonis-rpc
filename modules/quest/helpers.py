import time
import json
import base64
import requests
import re
from datetime import datetime, timezone

_DISCORD_BUILD_NUMBER = None
_DISCORD_BUILD_NUMBER_TIME = 0

def fetch_latest_build_number() -> int:
    global _DISCORD_BUILD_NUMBER, _DISCORD_BUILD_NUMBER_TIME
    FALLBACK = 504649
    now = time.time()
    if _DISCORD_BUILD_NUMBER and (now - _DISCORD_BUILD_NUMBER_TIME) < 86400:
        return _DISCORD_BUILD_NUMBER
    try:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        r = requests.get("https://discord.com/app", headers={"User-Agent": ua}, timeout=6)
        if r.status_code == 200:
            scripts = re.findall(r'/assets/([a-f0-9]+)\.js', r.text)
            if not scripts:
                scripts_alt = re.findall(r'src="(/assets/[^"]+\.js)"', r.text)
                scripts = [s.split('/')[-1].replace('.js', '') for s in scripts_alt]
            for asset_hash in scripts[-5:]:
                try:
                    ar = requests.get(f"https://discord.com/assets/{asset_hash}.js", headers={"User-Agent": ua}, timeout=6)
                    m = re.search(r'buildNumber["\s:]+["\s]*(\d{5,7})', ar.text)
                    if m:
                        _DISCORD_BUILD_NUMBER = int(m.group(1))
                        _DISCORD_BUILD_NUMBER_TIME = now
                        return _DISCORD_BUILD_NUMBER
                except Exception:
                    continue
    except Exception:
        pass
    return _DISCORD_BUILD_NUMBER or FALLBACK

def make_super_properties(build_number: int = None) -> str:
    if not build_number:
        build_number = fetch_latest_build_number()
    obj = {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": "1.0.9175",
        "os_version": "10.0.26100",
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": "en-US",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36",
        "browser_version": "32.2.7",
        "client_build_number": build_number,
        "native_build_number": 59498,
        "client_event_source": None
    }
    return base64.b64encode(json.dumps(obj).encode()).decode()

def make_discord_headers(token: str) -> dict:
    return {
        "Authorization": token,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9175 Chrome/128.0.6613.186 Electron/32.2.7 Safari/537.36",
        "X-Super-Properties": make_super_properties(),
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Ho_Chi_Minh",
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/channels/@me"
    }

def create_discord_session(token: str) -> requests.Session:
    sess = requests.Session()
    sess.headers.update(make_discord_headers(token))
    return sess

SUPPORTED_QUEST_TASKS = [
    "WATCH_VIDEO",
    "PLAY_ON_DESKTOP",
    "STREAM_ON_DESKTOP",
    "PLAY_ACTIVITY",
    "WATCH_VIDEO_ON_MOBILE",
]

def _quest_get(d, *keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            return d[k]
    return None

def get_task_config(quest: dict) -> dict:
    cfg = quest.get("config", {})
    return _quest_get(cfg, "taskConfig", "task_config", "taskConfigV2", "task_config_v2") or {}

def get_quest_name(quest: dict) -> str:
    cfg = quest.get("config", {})
    msgs = cfg.get("messages", {})
    name = _quest_get(msgs, "questName", "quest_name")
    if name:
        return name.strip()
    game = _quest_get(msgs, "gameTitle", "game_title")
    if game:
        return game.strip()
    app_name = cfg.get("application", {}).get("name")
    if app_name:
        return app_name.strip()
    return f"Quest #{quest.get('id', '?')}"

def is_completable(quest: dict) -> bool:
    expires = _quest_get(quest.get("config", {}), "expiresAt", "expires_at")
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if exp_dt <= datetime.now(timezone.utc):
                return False
        except Exception:
            pass
    tc = get_task_config(quest)
    tasks = tc.get("tasks", {})
    return any(tasks.get(t) is not None for t in SUPPORTED_QUEST_TASKS)

def is_enrolled(quest: dict) -> bool:
    us = _quest_get(quest, "userStatus", "user_status") or {}
    return bool(_quest_get(us, "enrolledAt", "enrolled_at"))

def is_completed(quest: dict) -> bool:
    us = _quest_get(quest, "userStatus", "user_status") or {}
    return bool(_quest_get(us, "completedAt", "completed_at"))

def get_task_type(quest: dict) -> str:
    tc = get_task_config(quest)
    tasks = tc.get("tasks", {})
    for t in SUPPORTED_QUEST_TASKS:
        if tasks.get(t) is not None:
            return t
    return "UNSUPPORTED"

def get_seconds_needed(quest: dict) -> int:
    tc = get_task_config(quest)
    ttype = get_task_type(quest)
    if not tc or ttype == "UNSUPPORTED":
        return 0
    return tc.get("tasks", {}).get(ttype, {}).get("target", 0)

def get_seconds_done(quest: dict) -> float:
    ttype = get_task_type(quest)
    if ttype == "UNSUPPORTED":
        return 0.0
    us = _quest_get(quest, "userStatus", "user_status") or {}
    prog = us.get("progress", {})
    if isinstance(prog, dict) and ttype in prog:
        return float(prog[ttype].get("value", 0))
    return float(prog.get("value", 0)) if isinstance(prog, dict) else 0.0

def parse_discord_quest_item(q: dict) -> dict:
    qid = str(q.get("id", ""))
    cfg = q.get("config", {})
    name = get_quest_name(q)
    task_type = get_task_type(q)
    target_seconds = get_seconds_needed(q)
    seconds_done = get_seconds_done(q)
    enrolled = is_enrolled(q)
    completed = is_completed(q)
    completable = is_completable(q)

    pct = 0
    if target_seconds > 0:
        pct = min(100, int((seconds_done / target_seconds) * 100))
    if completed:
        pct = 100

    assets = cfg.get("assets", {})
    banner_url = assets.get("hero") or assets.get("banner") or assets.get("quest_bar_hero")
    if not banner_url:
        banner_url = "https://cdn.discordapp.com/embed/avatars/0.png"
    elif not banner_url.startswith("http"):
        banner_url = f"https://cdn.discordapp.com/assets/{qid}/{banner_url}.png"

    rewards_config = cfg.get("rewards_config", {}) or cfg.get("rewardsConfig", {})
    rewards_list = rewards_config.get("rewards", [])
    reward_name = "Phần Thưởng Độc Quyền Discord"
    if rewards_list and isinstance(rewards_list[0], dict):
        reward_name = rewards_list[0].get("name") or rewards_list[0].get("description") or reward_name

    return {
        "id": qid,
        "title": name,
        "name": name,
        "game_name": name,
        "app_name": name,
        "task_type": task_type,
        "type": task_type,
        "target_seconds": int(target_seconds),
        "seconds_done": float(seconds_done),
        "progress_pct": pct,
        "enrolled": enrolled,
        "completed": completed,
        "completable": completable,
        "banner": banner_url,
        "banner_url": banner_url,
        "reward": reward_name,
        "rewards_text": reward_name,
        "badge": "Discord Quest"
    }
