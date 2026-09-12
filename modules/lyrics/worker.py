import os
import re
import time
import threading
import requests

from core.logger import quest_log
from modules.quest.helpers import make_discord_headers

class DiscordLyricWorker:
    def __init__(self):
        self.active_threads = {}
        self.stop_events = {}
        self.lock = threading.Lock()

    def update_lyric(self, token: str, text: str, emoji: str = '🎵') -> tuple[bool, str]:
        if not token or not text:
            return False, 'Thiếu token hoặc nội dung'
        try:
            headers = make_discord_headers(token)
            payload = {
                'custom_status': {
                    'text': str(text)[:128],
                    'emoji_name': emoji,
                    'emoji_id': None
                }
            }
            res = requests.patch('https://discord.com/api/v9/users/@me/settings', headers=headers, json=payload, timeout=6)
            if res.status_code == 200:
                return True, 'Đã cập nhật trạng thái suy nghĩ'
            return False, f'Discord trả về lỗi mã {res.status_code}'
        except Exception as e:
            return False, str(e)

    def clear_lyric(self, token: str) -> tuple[bool, str]:
        if not token:
            return False, 'Thiếu token'
        try:
            headers = make_discord_headers(token)
            payload = {'custom_status': None}
            res = requests.patch('https://discord.com/api/v9/users/@me/settings', headers=headers, json=payload, timeout=6)
            if res.status_code == 200:
                return True, 'Đã xóa trạng thái suy nghĩ'
            return False, f'Discord trả về lỗi mã {res.status_code}'
        except Exception as e:
            return False, str(e)

    def fetch_nct_lyrics(self, keyword: str) -> tuple[bool, str, list]:
        """Lấy lời bài hát đồng bộ từ LRCLIB / NhacCuaTui cho bài hát bất kỳ"""
        try:
            # 1. Tìm kiếm trên LRCLIB (hỗ trợ hàng triệu bài hát quốc tế & V-Pop có timestamp chuẩn)
            url = f"https://lrclib.net/api/search?q={requests.utils.quote(keyword)}"
            headers = {"User-Agent": "DIPRE-Discord/1.0"}
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                tracks = r.json()
                for track in tracks:
                    synced = track.get("syncedLyrics")
                    if synced:
                        parsed = self.parse_lrc(synced)
                        if parsed:
                            name = f"{track.get('trackName', keyword)} - {track.get('artistName', '')}".strip(" -")
                            return True, name, parsed

            # 2. Fallback tìm kiếm NCT
            search_url = f"https://www.nhaccuatui.com/tim-kiem/bai-hat.html?q={requests.utils.quote(keyword)}"
            r2 = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
            if r2.status_code == 200:
                m = re.search(r'href="(https://www\.nhaccuatui\.com/bai-hat/[^"]+\.html)" title="([^"]+)"', r2.text)
                if m:
                    song_title = m.group(2)
                    r3 = requests.get(f"https://lrclib.net/api/search?q={requests.utils.quote(song_title)}", headers=headers, timeout=5)
                    if r3.status_code == 200:
                        for tr in r3.json():
                            if tr.get("syncedLyrics"):
                                return True, song_title, self.parse_lrc(tr["syncedLyrics"])

            return False, 'Không tìm thấy lời bài hát đồng bộ', []
        except Exception as e:
            return False, f'Lỗi lấy lyric: {e}', []

    def parse_lrc(self, lrc_content: str) -> list:
        lines = []
        for line in lrc_content.splitlines():
            matches = re.findall(r'\[(\d{2}):(\d{2}(?:\.\d+)?)\]', line)
            if matches:
                text = re.sub(r'\[\d{2}:\d{2}(?:\.\d+)?\]', '', line).strip()
                if text:
                    for m in matches:
                        sec = int(m[0]) * 60 + float(m[1])
                        lines.append((sec, text))
        lines.sort(key=lambda x: x[0])
        return lines

    def start_lyric_stream(self, user_id: int, token: str, lyrics: list, emoji: str = '🎵'):
        self.stop_lyric_stream(user_id)
        stop_event = threading.Event()

        def _worker():
            start_time = time.time()
            idx = 0
            total = len(lyrics)
            quest_log(f"Bắt đầu phát lyric đồng bộ ({total} câu)...", "info")

            while not stop_event.is_set() and idx < total:
                elapsed = time.time() - start_time
                target_sec, text = lyrics[idx]

                if elapsed >= target_sec:
                    self.update_lyric(token, text, emoji)
                    quest_log(f"[Lyric] {text}", "info")
                    idx += 1
                time.sleep(0.3)

            if not stop_event.is_set():
                time.sleep(3)
                self.clear_lyric(token)

        th = threading.Thread(target=_worker, daemon=True)
        with self.lock:
            self.active_threads[user_id] = th
            self.stop_events[user_id] = stop_event
        th.start()

    def stop_lyric_stream(self, user_id: int):
        with self.lock:
            if user_id in self.stop_events:
                self.stop_events[user_id].set()
                del self.stop_events[user_id]
            if user_id in self.active_threads:
                del self.active_threads[user_id]

    def stop_all(self):
        with self.lock:
            for ev in self.stop_events.values():
                ev.set()
            self.stop_events.clear()
            self.active_threads.clear()

lyric_worker = DiscordLyricWorker()
