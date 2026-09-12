import time
import random
import threading
import requests
from datetime import datetime
from typing import Union

from core.logger import quest_log, log_event
from modules.quest.helpers import (
    make_discord_headers,
    get_quest_name,
    _quest_get,
    parse_discord_quest_item
)

class DiscordUserQuestRunner:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.status = 'idle'
        self.current_quest_id = None
        self.current_quest_name = None
        self.task_type = 'PLAY_ON_DESKTOP'
        self.progress_pct = 0
        self.target_seconds = 60
        self.elapsed_seconds = 0
        self.is_auto_mode = False
        self.thread = None
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()

    def get_status(self):
        with self.lock:
            return {
                'status': self.status,
                'quest_id': self.current_quest_id,
                'quest_name': self.current_quest_name,
                'task_type': self.task_type,
                'progress_pct': self.progress_pct,
                'elapsed_seconds': self.elapsed_seconds,
                'target_seconds': self.target_seconds,
                'is_auto_mode': self.is_auto_mode
            }

    def start_auto(self, token: str):
        self.stop()
        with self.lock:
            self.status = 'running'
            self.is_auto_mode = True
            self.current_quest_id = None
            self.current_quest_name = "Tự Động Quét & Hoàn Thành Quest"
            self.progress_pct = 0
            self.elapsed_seconds = 0
            self.target_seconds = 100
            self.stop_flag.clear()
            self.thread = threading.Thread(
                target=self._run_auto_quest_loop,
                args=(token,),
                daemon=True
            )
            self.thread.start()

    def start(self, token: str, quest_id: str, quest_name: str, task_type: str = 'PLAY_ON_DESKTOP', target_seconds: int = 60):
        self.stop()
        with self.lock:
            self.status = 'running'
            self.is_auto_mode = False
            self.current_quest_id = quest_id
            self.current_quest_name = quest_name
            self.task_type = task_type
            self.target_seconds = max(10, int(target_seconds))
            self.progress_pct = 0
            self.elapsed_seconds = 0
            self.stop_flag.clear()
            self.thread = threading.Thread(
                target=self._run_quest_thread,
                args=(token, quest_id, quest_name, task_type, self.target_seconds),
                daemon=True
            )
            self.thread.start()

    def stop(self):
        with self.lock:
            self.stop_flag.set()
            if self.status == 'running':
                self.status = 'stopped'

    def enroll(self, token: str, quest: Union[dict, str]) -> bool:
        qid = quest["id"] if isinstance(quest, dict) else str(quest)
        name = get_quest_name(quest) if isinstance(quest, dict) else f"Quest #{qid}"
        raw_meta = quest.get("traffic_metadata_raw") if isinstance(quest, dict) else None
        sealed_meta = quest.get("traffic_metadata_sealed") if isinstance(quest, dict) else None

        headers = make_discord_headers(token)
        payload = {
            "location": 11,
            "is_targeted": False,
            "metadata_raw": None,
            "metadata_sealed": None,
            "traffic_metadata_raw": raw_meta,
            "traffic_metadata_sealed": sealed_meta
        }
        try:
            res = requests.post(f"https://discord.com/api/v9/quests/{qid}/enroll", headers=headers, json=payload, timeout=10)
            if res.status_code in (200, 201, 204):
                quest_log(f"Đã nhận thành công: {name}", "success")
                return True
            if res.status_code == 429:
                wait = res.json().get("retry_after", 5)
                quest_log(f"[RATE LIMIT] Discord tạm khóa nhận quest ({wait:.0f}s) - Bỏ qua để cày quest có sẵn", "warning")
                return False
            quest_log(f"Enroll '{name}' thất bại (HTTP {res.status_code})", "warning")
            return False
        except Exception as e:
            quest_log(f"Lỗi enroll '{name}': {e}", "error")
            return False

    def _fetch_quests(self, token: str) -> list:
        try:
            headers = make_discord_headers(token)
            r = requests.get("https://discord.com/api/v9/quests/@me", headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    return data.get("quests", [])
                elif isinstance(data, list):
                    return data
            elif r.status_code == 429:
                wait = r.json().get("retry_after", 5) + 1
                time.sleep(wait)
                return self._fetch_quests(token)
        except Exception as e:
            quest_log(f"Lỗi khi tải danh sách quest: {e}", "error")
        return []

    def _complete_video(self, token: str, qid: str, name: str, seconds_needed: int, seconds_done: float, enrolled_ts: float):
        headers = make_discord_headers(token)
        speed = 7
        interval = 1
        max_future = 10
        quest_log(f"[VIDEO] {name} ({int(seconds_done)}/{seconds_needed}s)", "info")

        while not self.stop_flag.is_set() and seconds_done < seconds_needed:
            max_allowed = (time.time() - enrolled_ts) + max_future
            diff = max_allowed - seconds_done
            timestamp = seconds_done + speed

            if diff >= speed:
                try:
                    payload = {"timestamp": min(seconds_needed, timestamp + random.random())}
                    r = requests.post(f"https://discord.com/api/v9/quests/{qid}/video-progress", headers=headers, json=payload, timeout=8)
                    if r.status_code == 200:
                        body = r.json()
                        if body.get("completed_at"):
                            quest_log(f"Hoàn thành video: {name}", "success")
                            with self.lock:
                                self.progress_pct = 100
                                self.elapsed_seconds = seconds_needed
                            return
                        seconds_done = min(seconds_needed, timestamp)
                        with self.lock:
                            self.elapsed_seconds = int(seconds_done)
                            self.progress_pct = min(100, int((seconds_done / seconds_needed) * 100))
                        quest_log(f"  [{name}] {int(seconds_done)}/{seconds_needed}s (Video)", "info")
                    elif r.status_code == 429:
                        retry_after = r.json().get("retry_after", 5) + 1
                        time.sleep(retry_after)
                        continue
                except Exception as e:
                    quest_log(f"  Lỗi video: {e}", "error")

            if timestamp >= seconds_needed:
                break
            time.sleep(interval)

        try:
            requests.post(f"https://discord.com/api/v9/quests/{qid}/video-progress", headers=headers, json={"timestamp": seconds_needed}, timeout=5)
        except Exception:
            pass
        quest_log(f"Hoàn thành video: {name}", "success")

    def _complete_heartbeat(self, token: str, qid: str, name: str, task_type: str, seconds_needed: int, seconds_done: float):
        headers = make_discord_headers(token)
        remaining = max(0, seconds_needed - seconds_done)
        quest_log(f"[{task_type}] {name} (~{int(remaining // 60)} phút còn lại)", "info")
        pid = random.randint(1000, 30000)

        while not self.stop_flag.is_set() and seconds_done < seconds_needed:
            try:
                r = requests.post(
                    f"https://discord.com/api/v9/quests/{qid}/heartbeat",
                    headers=headers,
                    json={"stream_key": f"call:0:{pid}", "terminal": False},
                    timeout=10
                )
                if r.status_code == 200:
                    body = r.json()
                    progress_data = body.get("progress", {})
                    if progress_data and task_type in progress_data:
                        seconds_done = progress_data[task_type].get("value", seconds_done + 20)
                    else:
                        seconds_done += 20
                    with self.lock:
                        self.elapsed_seconds = int(seconds_done)
                        self.progress_pct = min(100, int((seconds_done / seconds_needed) * 100))
                    quest_log(f"  [{name}] {int(seconds_done)}/{seconds_needed}s [{self.progress_pct}%]", "info")
                    if body.get("completed_at") or seconds_done >= seconds_needed:
                        quest_log(f"Hoàn thành: {name}", "success")
                        return
                elif r.status_code == 429:
                    retry_after = r.json().get("retry_after", 10) + 1
                    time.sleep(retry_after)
                    continue
            except Exception as e:
                quest_log(f"  Lỗi heartbeat: {e}", "error")

            for _ in range(20):
                if self.stop_flag.is_set():
                    break
                time.sleep(1)

        try:
            requests.post(f"https://discord.com/api/v9/quests/{qid}/heartbeat", headers=headers, json={"stream_key": f"call:0:{pid}", "terminal": True}, timeout=6)
        except Exception:
            pass
        quest_log(f"Hoàn thành: {name}", "success")

    def _complete_activity(self, token: str, qid: str, name: str, seconds_needed: int, seconds_done: float):
        headers = make_discord_headers(token)
        remaining = max(0, seconds_needed - seconds_done)
        quest_log(f"[ACTIVITY] {name} (~{int(remaining // 60)} phút còn lại)", "info")
        stream_key = "call:0:1"

        while not self.stop_flag.is_set() and seconds_done < seconds_needed:
            try:
                r = requests.post(
                    f"https://discord.com/api/v9/quests/{qid}/heartbeat",
                    headers=headers,
                    json={"stream_key": stream_key, "terminal": False},
                    timeout=10
                )
                if r.status_code == 200:
                    body = r.json()
                    progress_data = body.get("progress", {})
                    if progress_data and "PLAY_ACTIVITY" in progress_data:
                        seconds_done = progress_data["PLAY_ACTIVITY"].get("value", seconds_done + 20)
                    else:
                        seconds_done += 20
                    with self.lock:
                        self.elapsed_seconds = int(seconds_done)
                        self.progress_pct = min(100, int((seconds_done / seconds_needed) * 100))
                    quest_log(f"  [{name}] {int(seconds_done)}/{seconds_needed}s [{self.progress_pct}%]", "info")
                    if body.get("completed_at") or seconds_done >= seconds_needed:
                        quest_log(f"Hoàn thành: {name}", "success")
                        return
                elif r.status_code == 429:
                    retry_after = r.json().get("retry_after", 10) + 1
                    time.sleep(retry_after)
                    continue
            except Exception as e:
                quest_log(f"  Lỗi activity: {e}", "error")

            for _ in range(20):
                if self.stop_flag.is_set():
                    break
                time.sleep(1)

        try:
            requests.post(f"https://discord.com/api/v9/quests/{qid}/heartbeat", headers=headers, json={"stream_key": stream_key, "terminal": True}, timeout=6)
        except Exception:
            pass
        quest_log(f"Hoàn thành: {name}", "success")

    def _run_auto_quest_loop(self, token: str):
        quest_log("══════════════════════════════════════════════════", "info")
        quest_log("🌸 KHỞI ĐỘNG CHẾ ĐỘ AUTO QUEST COMPLETER", "success")
        quest_log("Tự động quét Discord, cày dứt điểm quest đã nhận & nhận 1 cày 1 an toàn!", "info")
        quest_log("══════════════════════════════════════════════════", "info")

        completed_ids = set()
        failed_enrollment_ids = set()
        cycle = 0

        while not self.stop_flag.is_set():
            cycle += 1
            quest_log(f"─── Quét nhiệm vụ lần #{cycle} ───", "info")
            raw_quests = self._fetch_quests(token)
            total = len(raw_quests)

            if not raw_quests:
                quest_log("Không tìm thấy nhiệm vụ nào từ Discord.", "warning")
            else:
                parsed_list = [parse_discord_quest_item(q) for q in raw_quests]
                valid_quests = [q for q in parsed_list if q['completable']]
                enrolled_count = sum(1 for q in valid_quests if q['enrolled'])
                completed_count = sum(1 for q in valid_quests if q['completed'])

                quest_log(f"Discord có: {total} quest ({len(valid_quests)} hỗ trợ) | Đã nhận: {enrolled_count} | Đã xong: {completed_count}", "info")

                actionable_enrolled = [
                    (q, p) for q, p in zip(raw_quests, parsed_list)
                    if p['completable'] and p['enrolled'] and not p['completed'] and p['id'] not in completed_ids
                ]

                if not actionable_enrolled:
                    unenrolled = [
                        (q, p) for q, p in zip(raw_quests, parsed_list)
                        if p['completable'] and not p['enrolled'] and not p['completed']
                        and p['id'] not in completed_ids and p['id'] not in failed_enrollment_ids
                    ]
                    for q, p in unenrolled:
                        if self.stop_flag.is_set():
                            break
                        qid = p['id']
                        name = p['title']
                        quest_log(f"Đang nhận quest: {name} [id={qid}]...", "info")
                        success = self.enroll(token, qid)
                        if success:
                            quest_log(f"  -> Đã nhận thành công: {name}", "success")
                            p['enrolled'] = True
                            actionable_enrolled.append((q, p))
                            time.sleep(3)
                            break
                        else:
                            failed_enrollment_ids.add(qid)
                            quest_log(f"  -> Bỏ qua quest {name} (chống dính rate limit Discord)", "warning")
                            time.sleep(2)

                if not actionable_enrolled:
                    quest_log("Không có nhiệm vụ nào đủ điều kiện cần cày lúc này.", "info")
                else:
                    for q, p in actionable_enrolled:
                        if self.stop_flag.is_set():
                            break
                        qid = p['id']
                        name = p['title']
                        task_type = p['task_type']
                        seconds_needed = p['target_seconds']
                        seconds_done = p['seconds_done']

                        with self.lock:
                            self.current_quest_id = qid
                            self.current_quest_name = name
                            self.task_type = task_type
                            self.target_seconds = seconds_needed
                            self.elapsed_seconds = int(seconds_done)
                            self.progress_pct = p['progress_pct']

                        quest_log(f"━━━ Bắt đầu cày: {name} [{task_type}] ━━━", "success")

                        us = _quest_get(q, "userStatus", "user_status") or {}
                        enrolled_at_str = _quest_get(us, "enrolledAt", "enrolled_at")
                        enrolled_ts = time.time()
                        if enrolled_at_str:
                            try:
                                enrolled_ts = datetime.fromisoformat(enrolled_at_str.replace("Z", "+00:00")).timestamp()
                            except Exception:
                                pass

                        if task_type in ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE"):
                            self._complete_video(token, qid, name, seconds_needed, seconds_done, enrolled_ts)
                        elif task_type in ("PLAY_ON_DESKTOP", "STREAM_ON_DESKTOP"):
                            self._complete_heartbeat(token, qid, name, task_type, seconds_needed, seconds_done)
                        elif task_type == "PLAY_ACTIVITY":
                            self._complete_activity(token, qid, name, seconds_needed, seconds_done)

                        completed_ids.add(qid)
                        time.sleep(2)

            quest_log("Chờ 45s để quét lại đợt nhiệm vụ tiếp theo...", "info")
            for _ in range(45):
                if self.stop_flag.is_set():
                    break
                time.sleep(1)

        with self.lock:
            self.status = 'stopped'
            quest_log("⛔ Đã dừng Auto Quest Completer.", "warning")

    def _run_quest_thread(self, token: str, quest_id: str, quest_name: str, task_type: str, target_seconds: int):
        quest_log(f'╔══ BẮT ĐẦU AUTO QUEST ══╗', 'info')
        quest_log(f'► Nhiệm vụ: {quest_name}', 'info')
        quest_log(f'► Quest ID: {quest_id}', 'info')
        quest_log(f'► Loại task: {task_type}', 'info')
        quest_log(f'► Thời gian cần: {target_seconds}s', 'info')
        quest_log(f'► Đang đăng ký tham gia quest...', 'info')
        log_event(f'Bắt đầu Auto Quest cho user #{self.user_id}: {quest_name} [{task_type}] - Cần {target_seconds}s', 'info')

        enrolled = self.enroll(token, quest_id)
        if enrolled:
            quest_log(f'✅ Đăng ký quest thành công!', 'success')
        else:
            quest_log(f'⚠ Đăng ký quest thất bại (có thể đã đăng ký rồi, tiếp tục...)', 'warning')

        headers = make_discord_headers(token)

        is_video = task_type in ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE")
        is_activity = task_type == "PLAY_ACTIVITY"

        pid = random.randint(1000, 30000)
        stream_key = "call:0:1" if is_activity else f"call:0:{pid}"

        if is_video:
            quest_log(f'► Chế độ: VIDEO PROGRESS (gửi timestamp mỗi 1s)', 'info')
        else:
            quest_log(f'► Chế độ: HEARTBEAT (gửi heartbeat mỗi 5s, pid={pid})', 'info')

        step_interval = 1 if is_video else 5
        seconds_done = 0
        last_log_pct = -1
        quest_log(f'═══ BẮT ĐẦU TIẾN TRÌNH CÀY ═══', 'info')

        while not self.stop_flag.is_set() and seconds_done < target_seconds:
            time.sleep(step_interval)
            if self.stop_flag.is_set():
                break

            if is_video:
                seconds_done = min(target_seconds, seconds_done + 7)
                try:
                    payload_ts = min(target_seconds, seconds_done + random.random())
                    r = requests.post(
                        f"https://discord.com/api/v9/quests/{quest_id}/video-progress",
                        headers=headers,
                        json={"timestamp": payload_ts},
                        timeout=5
                    )
                    if r.status_code == 200:
                        b = r.json()
                        if b.get("completed_at"):
                            seconds_done = target_seconds
                            quest_log(f'✅ Discord xác nhận hoàn thành video!', 'success')
                        else:
                            quest_log(f'📹 Video progress: {payload_ts:.1f}s → HTTP {r.status_code}', 'info')
                    elif r.status_code == 429:
                        wait = r.json().get("retry_after", 3)
                        quest_log(f'⏳ Rate limited! Chờ {wait}s...', 'warning')
                        time.sleep(wait)
                        continue
                    else:
                        quest_log(f'⚠ Video progress lỗi HTTP {r.status_code}: {r.text[:80]}', 'warning')
                except Exception as e:
                    quest_log(f'✗ Lỗi gửi video progress: {e}', 'error')
            else:
                seconds_done = min(target_seconds, seconds_done + step_interval)
                if seconds_done % 15 == 0 or seconds_done >= target_seconds:
                    try:
                        r = requests.post(
                            f"https://discord.com/api/v9/quests/{quest_id}/heartbeat",
                            headers=headers,
                            json={"stream_key": stream_key, "terminal": False},
                            timeout=6
                        )
                        if r.status_code == 200:
                            b = r.json()
                            if b.get("completed_at"):
                                seconds_done = target_seconds
                                quest_log(f'✅ Discord xác nhận hoàn thành heartbeat!', 'success')
                            else:
                                quest_log(f'💓 Heartbeat OK: {seconds_done}s/{target_seconds}s → HTTP {r.status_code}', 'info')
                        elif r.status_code == 429:
                            wait = r.json().get("retry_after", 5)
                            quest_log(f'⏳ Rate limited! Chờ {wait}s...', 'warning')
                            time.sleep(wait)
                            continue
                        else:
                            quest_log(f'⚠ Heartbeat lỗi HTTP {r.status_code}: {r.text[:80]}', 'warning')
                    except Exception as e:
                        quest_log(f'✗ Lỗi gửi heartbeat: {e}', 'error')

            with self.lock:
                self.elapsed_seconds = seconds_done
                self.progress_pct = min(100, int((seconds_done / target_seconds) * 100))

            pct = self.progress_pct
            if pct // 10 != last_log_pct // 10:
                last_log_pct = pct
                bar_filled = int(pct / 5)
                bar = '█' * bar_filled + '░' * (20 - bar_filled)
                quest_log(f'[{bar}] {pct}% ({int(seconds_done)}s / {target_seconds}s)', 'info')

        quest_log(f'═══ GỬI TÍN HIỆU HOÀN THÀNH CUỐI ═══', 'info')
        try:
            if is_video:
                r = requests.post(
                    f"https://discord.com/api/v9/quests/{quest_id}/video-progress",
                    headers=headers,
                    json={"timestamp": target_seconds},
                    timeout=5
                )
                quest_log(f'📹 Final video-progress → HTTP {r.status_code}', 'info')
            else:
                r = requests.post(
                    f"https://discord.com/api/v9/quests/{quest_id}/heartbeat",
                    headers=headers,
                    json={"stream_key": stream_key, "terminal": True},
                    timeout=6
                )
                quest_log(f'💓 Final heartbeat (terminal=True) → HTTP {r.status_code}', 'info')
        except Exception as e:
            quest_log(f'✗ Lỗi gửi tín hiệu cuối: {e}', 'error')

        with self.lock:
            if not self.stop_flag.is_set() and seconds_done >= target_seconds:
                self.status = 'completed'
                self.progress_pct = 100
                quest_log(f'╚══ ✅ HOÀN THÀNH! {quest_name} ══╝', 'success')
                quest_log(f'► Vào Discord để nhận phần thưởng!', 'success')
                log_event(f'✅ Hoàn thành xuất sắc nhiệm vụ Discord: {quest_name}!', 'success')
            else:
                if self.status != 'completed':
                    self.status = 'stopped'
                quest_log(f'╚══ ⛔ ĐÃ DỪNG: {quest_name} ══╝', 'warning')
                log_event(f'Đã dừng nhiệm vụ Discord: {quest_name}', 'info')

USER_QUEST_RUNNERS = {}
USER_QUEST_LOCK = threading.Lock()

def get_user_quest_runner(user_id: int) -> DiscordUserQuestRunner:
    with USER_QUEST_LOCK:
        if user_id not in USER_QUEST_RUNNERS:
            USER_QUEST_RUNNERS[user_id] = DiscordUserQuestRunner(user_id)
        return USER_QUEST_RUNNERS[user_id]

def stop_all_quest_runners():
    with USER_QUEST_LOCK:
        for r in USER_QUEST_RUNNERS.values():
            try:
                r.stop()
            except Exception:
                pass
