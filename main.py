import os
import sys
import time
import json
import uuid
import sqlite3
import asyncio
import threading
import webbrowser
import hashlib
import random
import re
import base64
from functools import wraps
from typing import Optional, List, Dict, Union, Any
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import discord

def _patched_create_app(self, name: str, team_id=None):
    payload = {'name': name}
    if team_id is not None:
        payload['team_id'] = team_id
    return self.request(discord.http.Route('POST', '/applications'), json=payload)
discord.http.HTTPClient.create_app = _patched_create_app

def _safe_http_del(self):
    pass
discord.http.HTTPClient.__del__ = _safe_http_del
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'discord_rpc_master_secret_key_fixed')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
UPLOAD_PATH_MAP = {}
KNOWN_ASSET_ICONS = {'vscode': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299466493956258.png', 'python': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299282380918886.png', 'git': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298453284323538.png', 'docker': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298813092823040.png', 'js': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299016025964687.png', 'ts': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299427059236984.png', 'jsx': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299015983894651.png', 'tsx': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299426262319284.png', 'html': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298813092823041.png', 'css': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298812694364230.png', 'c': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298812165881958.png', 'cpp': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298812425932820.png', 'csharp': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298812555952138.png', 'java': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299015862255717.png', 'rust': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299282934567013.png', 'go': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298813357064273.png'}
LOG_BUFFER = []
MAX_LOG_ENTRIES = 120

def log_event(message: str, level: str='info'):
    timestamp = time.strftime('%H:%M:%S')
    entry = {'time': timestamp, 'message': str(message), 'level': level}
    LOG_BUFFER.append(entry)
    if len(LOG_BUFFER) > MAX_LOG_ENTRIES:
        LOG_BUFFER.pop(0)
    print(f'[{timestamp}] [{level.upper()}] {message}')
log_event('Hệ thống Discord RPC Master v2.2 đã sẵn sàng hoạt động.', 'info')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                discord_token TEXT DEFAULT '',
                discord_id TEXT DEFAULT '',
                discord_username TEXT DEFAULT '',
                discord_avatar TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute("PRAGMA table_info(users)")
        cols = [r['name'] for r in cursor.fetchall()]
        for col_name in ['discord_token', 'discord_id', 'discord_username', 'discord_avatar']:
            if col_name not in cols:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} TEXT DEFAULT ''")
                except Exception:
                    pass
        conn.commit()
init_db()

def generate_captcha_svg():
    a = random.randint(3, 19)
    b = random.randint(2, 9)
    op = random.choice(['+', '-', '*'])
    if op == '+':
        ans = a + b
        text = f"{a} + {b} = ?"
    elif op == '-':
        if a < b:
            a, b = b, a
        ans = a - b
        text = f"{a} - {b} = ?"
    else:
        a = random.randint(2, 9)
        b = random.randint(2, 9)
        ans = a * b
        text = f"{a} x {b} = ?"
    session['captcha_answer'] = str(ans)
    
    noise_lines = []
    for _ in range(5):
        x1 = random.randint(0, 160)
        y1 = random.randint(0, 46)
        x2 = random.randint(0, 160)
        y2 = random.randint(0, 46)
        noise_lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="rgba(99,102,241,0.3)" stroke-width="1.5"/>')
    noise_dots = []
    for _ in range(12):
        cx = random.randint(5, 155)
        cy = random.randint(5, 41)
        r = random.randint(1, 3)
        noise_dots.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="rgba(168,85,247,0.35)"/>')
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="160" height="46" viewBox="0 0 160 46">
      <rect width="160" height="46" rx="8" fill="#0c101d"/>
      <rect width="160" height="46" rx="8" fill="none" stroke="rgba(99,102,241,0.35)" stroke-width="1.2"/>
      {''.join(noise_lines)}
      {''.join(noise_dots)}
      <text x="50%" y="30" font-family="'Plus Jakarta Sans', sans-serif" font-size="20" font-weight="700" fill="#38bdf8" text-anchor="middle" letter-spacing="3">{text}</text>
    </svg>'''
    return svg

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class DiscordRPCWorker:

    def __init__(self):
        self.client = None
        self.loop = None
        self.thread = None
        self._active_loop = None
        self._active_client = None
        self._run_id = 0
        self.status = 'stopped'
        self.error_message = None
        self.user_tag = None
        self.user_id = None
        self.start_timestamp = None
        self.current_config = None
        self._managed_app = None
        self._last_name_edit_time = 0
        self._last_icon_edit_time = 0
        self._asset_cache = {}
        self._name_edit_cooldown = 30
        self._lock = threading.Lock()

    def get_status_data(self):
        with self._lock:
            elapsed = 0
            if self.start_timestamp and self.status == 'running':
                elapsed = int(time.time() - self.start_timestamp)
            return {'status': self.status, 'error_message': self.error_message, 'user_tag': self.user_tag, 'user_id': self.user_id, 'elapsed_seconds': elapsed, 'config': self.current_config}

    def start(self, config):
        self.stop()
        with self._lock:
            self._run_id += 1
            current_run_id = self._run_id
            self.status = 'connecting'
            self.error_message = None
            self.current_config = config
            self.start_timestamp = time.time()
            self.thread = threading.Thread(target=self._run_thread, args=(config, current_run_id), daemon=True)
            self.thread.start()

    def update_presence(self, config):
        with self._lock:
            loop = self._active_loop
            client = self._active_client
            if self.status != 'running' or not client or client.is_closed() or not loop:
                self.start(config)
                return True
            self.current_config = config
            future = asyncio.run_coroutine_threadsafe(self._apply_presence(config), loop)
        future.result(timeout=6.0)
        return True

    async def _apply_presence(self, config):
        activity = await self._build_activity(config)
        status_choice = config.get('userStatus', 'online')
        discord_status = getattr(discord.Status, status_choice, discord.Status.online)
        if self.client and not self.client.is_closed():
            await self.client.change_presence(status=discord_status, activity=activity)
            log_event(f'Đã cập nhật trạng thái Rich Presence ({discord_status.value}) thành công.', 'success')

    def stop(self):
        with self._lock:
            if self.status == 'stopped' and (not self.thread or not self.thread.is_alive()):
                return True
            self.status = 'stopping'

        loop = None
        client = None
        thread = None
        with self._lock:
            loop = self._active_loop
            client = self._active_client
            thread = self.thread

        if loop and client and not client.is_closed() and loop.is_running():
            try:
                fut = asyncio.run_coroutine_threadsafe(self._safe_close_client(client, loop), loop)
                fut.result(timeout=3.0)
            except Exception:
                pass

        if loop and loop.is_running():
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass

        if thread and thread.is_alive() and threading.current_thread() != thread:
            thread.join(timeout=4.0)

        with self._lock:
            self.status = 'stopped'
            self.user_tag = None
            self.user_id = None
            self.start_timestamp = None
            self._active_loop = None
            self._active_client = None
            self.client = None
            self.loop = None
            self.thread = None

        log_event('Đã dừng và ngắt kết nối an toàn với Discord Gateway.', 'warning')
        return True

    async def _safe_close_client(self, client, loop):
        try:
            if client and not client.is_closed():
                try:
                    await client.change_presence(activity=None, status=discord.Status.invisible)
                except BaseException:
                    pass
                await client.close()
        except BaseException:
            pass
        finally:
            try:
                tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop) and not t.done()]
                for t in tasks:
                    t.cancel()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            except BaseException:
                pass

    async def _get_or_create_managed_app(self, desired_name: str, preferred_app_id: Optional[str]=None):
        tag_prefix = '[RPC Master]'
        try:
            my_apps = await self.client.applications()
            if preferred_app_id:
                clean_pref = str(preferred_app_id).strip()
                for app in my_apps:
                    if str(app.id) == clean_pref:
                        log_event(f'Sử dụng chính xác ứng dụng theo App ID: {app.name} ({app.id})', 'info')
                        self._managed_app = app
                        return app
            if desired_name:
                for app in my_apps:
                    if app.name.lower() == desired_name.lower():
                        log_event(f"Tìm thấy ứng dụng trùng tên '{desired_name}': {app.name} ({app.id})", 'info')
                        self._managed_app = app
                        return app
            for app in my_apps:
                desc = getattr(app, 'description', '') or ''
                if tag_prefix in desc or app.name == 'DiscordRPC Master':
                    log_event(f'Tìm thấy ứng dụng đã quản lý: {app.name} ({app.id})', 'info')
                    self._managed_app = app
                    return app
            if my_apps:
                app = my_apps[0]
                log_event(f'Tự động sử dụng ứng dụng có sẵn trên tài khoản: {app.name} ({app.id})', 'info')
                self._managed_app = app
                return app
        except Exception as e:
            log_event(f'Lỗi khi duyệt danh sách ứng dụng: {e}', 'warning')
        app_name = desired_name if desired_name else 'DiscordRPC Master'
        try:
            log_event(f"Đang tự động tạo Application mới '{app_name}' trên Discord Developer Portal...", 'info')
            new_app = await self.client.create_application(app_name)
            try:
                await new_app.edit(description='[RPC Master] Tự động quản lý Rich Presence bởi Discord RPC Master')
            except Exception:
                pass
            self._managed_app = new_app
            log_event(f'Tạo thành công Application: {new_app.name} ({new_app.id})', 'success')
            return new_app
        except Exception as e:
            if 'captcha' in str(e).lower():
                log_event('Discord yêu cầu xác thực Captcha khi tạo ứng dụng qua script. Vui lòng mở Developer Portal tạo 1 app bất kỳ.', 'warning')
            else:
                log_event(f'Không thể tự tạo Application: {e}', 'warning')
            return None

    async def _sync_app_name(self, app, desired_name: str):
        if not app or not desired_name:
            return
        if getattr(app, 'name', None) == desired_name:
            return
        now = time.time()
        elapsed = now - self._last_name_edit_time
        if elapsed < self._name_edit_cooldown:
            remain = int(self._name_edit_cooldown - elapsed)
            log_event(f"Tránh Rate Limit: Chờ {remain}s trước khi đổi tên trên Developer Portal (Discord vẫn hiển thị đúng '{desired_name}').", 'info')
            return
        try:
            log_event(f"Đang đổi tên Application từ '{app.name}' sang '{desired_name}'...", 'info')
            await app.edit(name=desired_name)
            self._last_name_edit_time = now
            log_event(f"Đã đổi tên Application thành '{desired_name}' thành công.", 'success')
        except Exception as e:
            log_event(f'Cảnh báo khi đổi tên Application: {e}', 'warning')

    async def _resolve_or_upload_asset(self, app, img_val: str, prefix: str) -> Optional[str]:
        if not img_val:
            img_val = ''
        img_val = img_val.strip()
        lower_val = img_val.lower()
        if lower_val in ('', 'bot', 'app', 'bot_avatar', 'app_icon', 'developer_portal', 'portal', 'default'):
            if app:
                try:
                    bot = getattr(app, 'bot', None)
                    if not bot and hasattr(app, 'fetch_bot'):
                        bot = await app.fetch_bot()
                    if bot and bot.avatar:
                        avatar_url = str(bot.avatar.url)
                        log_event(f'Sử dụng Avatar Anime từ Bot Icon của Developer Portal: {avatar_url}', 'success')
                        return avatar_url
                    if getattr(app, 'icon', None):
                        icon_url = str(app.icon.url)
                        log_event(f'Sử dụng ảnh từ App Icon của Developer Portal: {icon_url}', 'info')
                        return icon_url
                except Exception as e:
                    log_event(f'Lỗi lấy avatar Developer Portal: {e}', 'warning')
            if not img_val:
                return None
        if any((k in img_val for k in ('discordapp.com/attachments/', 'discordapp.net/attachments/', 'discordapp.com/avatars/', 'discordapp.com/app-icons/', 'discordapp.com/app-assets/', 'mp:'))):
            return img_val
        if lower_val in KNOWN_ASSET_ICONS:
            return KNOWN_ASSET_ICONS[lower_val]
        local_filepath = UPLOAD_PATH_MAP.get(img_val)
        if not local_filepath:
            if '/static/uploads/' in img_val or '/uploads/' in img_val:
                fname = img_val.split('/')[-1].split('?')[0]
                candidate = os.path.join(UPLOAD_FOLDER, fname)
                if os.path.exists(candidate):
                    local_filepath = candidate
            elif not img_val.startswith(('http://', 'https://')):
                candidate = os.path.join(UPLOAD_FOLDER, img_val)
                if os.path.exists(candidate):
                    local_filepath = candidate
        file_bytes = None
        if local_filepath and os.path.exists(local_filepath):
            try:
                with open(local_filepath, 'rb') as f:
                    file_bytes = f.read()
            except Exception as e:
                print(f'[RPC Worker] Không thể đọc file cục bộ: {e}')
        if app and file_bytes:
            try:
                print(f"[RPC Worker] Đang cập nhật App Icon cho '{app.name}' trên Developer Portal...")
                await app.edit(icon=file_bytes)
                if getattr(app, 'icon', None):
                    icon_url = str(app.icon.url)
                    print(f'[RPC Worker] Đã cập nhật thành công App Icon: {icon_url}')
                    return icon_url
            except Exception as icon_err:
                print(f'[RPC Worker] Lưu ý cập nhật App Icon: {icon_err}')
        if app:
            try:
                bot = getattr(app, 'bot', None)
                if not bot and hasattr(app, 'fetch_bot'):
                    bot = await app.fetch_bot()
                if bot and bot.avatar:
                    return str(bot.avatar.url)
                if getattr(app, 'icon', None):
                    return str(app.icon.url)
            except Exception:
                pass
        if prefix == 'l':
            return KNOWN_ASSET_ICONS.get('vscode')
        elif prefix == 's':
            return KNOWN_ASSET_ICONS.get('python')
        return img_val

    async def _build_activity(self, config):
        activity_type_str = config.get('activityType', 'playing')
        stream_url = config.get('streamUrl', '').strip()
        activity_name = config.get('activityName', 'Visual Studio Code').strip()
        details = config.get('details', '').strip()
        state = config.get('state', '').strip()
        large_image = config.get('largeImage', '').strip()
        large_text = config.get('largeText', '').strip()
        small_image = config.get('smallImage', '').strip()
        small_text = config.get('smallText', '').strip()
        has_timestamp = config.get('hasTimestamp', True)
        btn1_label = config.get('btn1Label', '').strip()
        btn1_url = config.get('btn1Url', '').strip()
        btn2_label = config.get('btn2Label', '').strip()
        btn2_url = config.get('btn2Url', '').strip()
        app_id_str = config.get('appId', '').strip()
        auto_app = config.get('autoApp', True)
        type_mapping = {'playing': discord.ActivityType.playing, 'streaming': discord.ActivityType.streaming, 'listening': discord.ActivityType.listening, 'watching': discord.ActivityType.watching, 'competing': discord.ActivityType.competing}
        act_type = type_mapping.get(activity_type_str, discord.ActivityType.playing)
        timestamps = None
        if has_timestamp and self.start_timestamp:
            timestamps = {'start': int(self.start_timestamp * 1000)}
        app_id = 383226320970055681
        managed_app = None
        if self.client and (not self.client.is_closed()):
            managed_app = await self._get_or_create_managed_app(activity_name, app_id_str)
            if managed_app:
                app_id = managed_app.id
                if auto_app:
                    await self._sync_app_name(managed_app, activity_name)
        if not managed_app:
            if app_id_str and app_id_str not in ('1054366629930778644', 'None', ''):
                try:
                    app_id = int(app_id_str)
                except ValueError:
                    app_id = 383226320970055681
        final_large = await self._resolve_or_upload_asset(managed_app, large_image, 'l')
        final_small = await self._resolve_or_upload_asset(managed_app, small_image, 's')
        if self.client and hasattr(self.client, 'proxy_external_application_assets'):
            urls_to_proxy = []
            for img in (final_large, final_small):
                if img and img.startswith(('http://', 'https://')) and (not any((d in img for d in ('discordapp.com', 'discordapp.net', 'mp:')))):
                    urls_to_proxy.append(img)
            if urls_to_proxy:
                try:
                    proxied_list = await self.client.proxy_external_application_assets(app_id, *urls_to_proxy)
                    for orig, proxied in zip(urls_to_proxy, proxied_list):
                        if orig == final_large:
                            final_large = proxied
                        if orig == final_small:
                            final_small = proxied
                except Exception:
                    pass
        activity_assets = None
        if final_large or final_small or large_text or small_text:
            activity_assets = discord.ActivityAssets(large_image=final_large if final_large else None, large_text=large_text if large_text else None, small_image=final_small if final_small else None, small_text=small_text if small_text else None)
        buttons = []
        if btn1_label and btn1_url:
            buttons.append(discord.ActivityButton(label=btn1_label, url=btn1_url))
        if btn2_label and btn2_url:
            buttons.append(discord.ActivityButton(label=btn2_label, url=btn2_url))
        return discord.Activity(type=act_type, name=activity_name, url=stream_url if act_type == discord.ActivityType.streaming else None, details=details if details else None, state=state if state else None, timestamps=timestamps, assets=activity_assets, buttons=buttons if buttons else None, application_id=app_id)

    def _run_thread(self, config, run_id):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = discord.Client()

        with self._lock:
            if self._run_id != run_id:
                loop.close()
                return
            self._active_loop = loop
            self._active_client = client
            self.loop = loop
            self.client = client

        token = config.get('token', '').strip()

        @client.event
        async def on_ready():
            try:
                with self._lock:
                    if self._run_id != run_id:
                        return
                    self.user_tag = str(client.user)
                    self.user_id = str(client.user.id)
                log_event(f'Đã đăng nhập tài khoản Discord: {self.user_tag} ({self.user_id})', 'success')
                log_event(f"Đang đồng bộ cấu hình và hình ảnh cho '{config.get('activityName', 'Visual Studio Code')}'...", 'info')
                activity = await self._build_activity(config)
                status_choice = config.get('userStatus', 'online')
                discord_status = getattr(discord.Status, status_choice, discord.Status.online)
                await client.change_presence(status=discord_status, activity=activity)
                with self._lock:
                    if self._run_id == run_id:
                        self.status = 'running'
                log_event(f'Đã phát trạng thái Rich Presence ({discord_status.value}) thành công!', 'success')
            except Exception as e:
                with self._lock:
                    if self._run_id == run_id:
                        self.status = 'error'
                        self.error_message = f'Lỗi khi phát trạng thái: {e}'
                log_event(f'Lỗi nghiêm trọng khi phát trạng thái: {e}', 'error')
                import traceback
                traceback.print_exc()

        try:
            log_event('Đang kết nối tới Discord Gateway qua User Token...', 'info')
            loop.run_until_complete(client.start(token))
        except discord.errors.LoginFailure:
            with self._lock:
                if self._run_id == run_id:
                    self.status = 'error'
                    self.error_message = 'Discord User Token không hợp lệ hoặc đã bị khóa!'
            log_event('Lỗi LoginFailure: Discord User Token không hợp lệ!', 'error')
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        except Exception as e:
            with self._lock:
                if self._run_id == run_id and self.status not in ('stopped', 'stopping'):
                    self.status = 'error'
                    self.error_message = str(e)
            if self._run_id == run_id and self.status not in ('stopped', 'stopping'):
                log_event(f'Ngoại lệ kết nối Gateway: {e}', 'error')
        finally:
            try:
                if not client.is_closed():
                    loop.run_until_complete(self._safe_close_client(client, loop))
                tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
                for t in tasks:
                    t.cancel()
                if tasks:
                    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
            except BaseException:
                pass
            finally:
                try:
                    loop.close()
                except BaseException:
                    pass

            with self._lock:
                if self._run_id == run_id:
                    if self.status != 'error':
                        self.status = 'stopped'
                    self.user_tag = None
                    self.user_id = None
                    self.start_timestamp = None
                    if self._active_loop is loop:
                        self._active_loop = None
                    if self._active_client is client:
                        self._active_client = None
                    if self.client is client:
                        self.client = None
                    if self.loop is loop:
                        self.loop = None
rpc_worker = DiscordRPCWorker()

def make_super_properties(build_number: int = 504649) -> str:
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
                'target_seconds': self.target_seconds
            }

    def start(self, token: str, quest_id: str, quest_name: str, task_type: str = 'PLAY_ON_DESKTOP', target_seconds: int = 60):
        self.stop()
        with self.lock:
            self.status = 'running'
            self.current_quest_id = quest_id
            self.current_quest_name = quest_name
            self.task_type = task_type
            self.target_seconds = target_seconds
            self.progress_pct = 0
            self.elapsed_seconds = 0
            self.stop_flag.clear()
            self.thread = threading.Thread(target=self._run_quest_thread, args=(token, quest_id, quest_name, task_type, target_seconds), daemon=True)
            self.thread.start()

    def stop(self):
        with self.lock:
            self.stop_flag.set()
            if self.status == 'running':
                self.status = 'stopped'

    def _enroll_if_needed(self, token: str, quest_id: str):
        try:
            headers = make_discord_headers(token)
            payload = {
                "location": 11,
                "is_targeted": False,
                "metadata_raw": None,
                "metadata_sealed": None
            }
            requests.post(f"https://discord.com/api/v9/quests/{quest_id}/enroll", headers=headers, json=payload, timeout=6)
        except Exception:
            pass

    def _run_quest_thread(self, token: str, quest_id: str, quest_name: str, task_type: str, target_seconds: int):
        log_event(f'Bắt đầu Auto Quest cho tài khoản #{self.user_id}: {quest_name} [{task_type}]', 'info')
        self._enroll_if_needed(token, quest_id)
        
        headers = make_discord_headers(token)
        pid = random.randint(1000, 30000)
        stream_key = f"call:0:{pid}" if task_type in ('PLAY_ON_DESKTOP', 'STREAM_ON_DESKTOP') else "call:0:1"
        is_video = task_type in ('WATCH_VIDEO', 'WATCH_VIDEO_ON_MOBILE')

        step_interval = 1 if is_video else 5
        seconds_done = 0

        while not self.stop_flag.is_set() and seconds_done < target_seconds:
            time.sleep(step_interval)
            if self.stop_flag.is_set():
                break

            if is_video:
                seconds_done = min(target_seconds, seconds_done + 7)
                try:
                    r = requests.post(f"https://discord.com/api/v9/quests/{quest_id}/video-progress", headers=headers, json={"timestamp": seconds_done + random.random()}, timeout=5)
                    if r.status_code == 200 and r.json().get('completed_at'):
                        seconds_done = target_seconds
                except Exception:
                    pass
            else:
                seconds_done = min(target_seconds, seconds_done + step_interval)
                if seconds_done % 15 == 0 or seconds_done >= target_seconds:
                    try:
                        requests.post(f"https://discord.com/api/v9/quests/{quest_id}/heartbeat", headers=headers, json={"stream_key": stream_key, "terminal": False}, timeout=6)
                    except Exception:
                        pass

            with self.lock:
                self.elapsed_seconds = seconds_done
                self.progress_pct = min(100, int((seconds_done / target_seconds) * 100))

            log_event(f'Quest [{quest_name}]: {self.progress_pct}% ({seconds_done}s/{target_seconds}s)', 'info')

        try:
            if not is_video:
                requests.post(f"https://discord.com/api/v9/quests/{quest_id}/heartbeat", headers=headers, json={"stream_key": stream_key, "terminal": True}, timeout=6)
            else:
                requests.post(f"https://discord.com/api/v9/quests/{quest_id}/video-progress", headers=headers, json={"timestamp": target_seconds}, timeout=5)
        except Exception:
            pass

        with self.lock:
            if not self.stop_flag.is_set() and seconds_done >= target_seconds:
                self.status = 'completed'
                self.progress_pct = 100
                log_event(f'Hoàn thành xuất sắc nhiệm vụ: {quest_name}!', 'success')
            else:
                if self.status != 'completed':
                    self.status = 'stopped'
                log_event(f'Đã dừng nhiệm vụ: {quest_name}', 'info')

USER_QUEST_RUNNERS = {}
USER_QUEST_LOCK = threading.Lock()

def get_user_quest_runner(user_id: int) -> DiscordUserQuestRunner:
    with USER_QUEST_LOCK:
        if user_id not in USER_QUEST_RUNNERS:
            USER_QUEST_RUNNERS[user_id] = DiscordUserQuestRunner(user_id)
        return USER_QUEST_RUNNERS[user_id]

class DiscordLyricWorker:

    def update_lyric(self, token: str, text: str, emoji: str = '🎵'):
        if not token or not text:
            return False, 'Thiếu token hoặc câu hát'
        try:
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            payload = {
                'custom_status': {
                    'text': str(text)[:128],
                    'emoji_name': emoji
                }
            }
            res = requests.patch('https://discord.com/api/v9/users/@me/settings', headers=headers, json=payload, timeout=5)
            if res.status_code == 200:
                return True, 'Đã cập nhật câu hát lên Discord Status'
            return False, f'Discord trả về lỗi mã {res.status_code}'
        except Exception as e:
            return False, str(e)

    def clear_lyric(self, token: str):
        if not token:
            return False, 'Thiếu token'
        try:
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            payload = {'custom_status': None}
            res = requests.patch('https://discord.com/api/v9/users/@me/settings', headers=headers, json=payload, timeout=5)
            if res.status_code == 200:
                return True, 'Đã xóa trạng thái câu hát trên Discord'
            return False, f'Discord trả về lỗi mã {res.status_code}'
        except Exception as e:
            return False, str(e)

lyric_worker = DiscordLyricWorker()

@app.route('/api/captcha')
def api_captcha():
    svg = generate_captcha_svg()
    return Response(svg, mimetype='image/svg+xml')

@app.route('/')
@login_required
def index():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, discord_token, discord_username, discord_avatar FROM users WHERE id = ?', (user_id,))
        u = cursor.fetchone()
    has_token = bool(u and u['discord_token'] and len(u['discord_token']) > 20)
    d_name = (u['discord_username'] if u and u['discord_username'] else None)
    d_avatar = (u['discord_avatar'] if u and u['discord_avatar'] else None)
    return render_template('index.html', username=session.get('username'), has_token=has_token, discord_username=d_name, discord_avatar=d_avatar)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        captcha = request.form.get('captcha', '').strip()
        expected = str(session.get('captcha_answer', ''))
        if not captcha or captcha != expected:
            flash('Mã Captcha không chính xác! Vui lòng tính lại kết quả.', 'error')
            return redirect(url_for('login'))
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('Vui lòng nhập đầy đủ tên tài khoản và mật khẩu.', 'error')
            return redirect(url_for('login'))
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            if user['discord_token']:
                session['discord_token'] = user['discord_token']
                session['discord_username'] = user['discord_username']
                session['discord_avatar'] = user['discord_avatar']
            flash(f'Chào mừng trở lại, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không chính xác.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    captcha = request.form.get('captcha', '').strip()
    expected = str(session.get('captcha_answer', ''))
    if not captcha or captcha != expected:
        flash('Mã Captcha không chính xác! Vui lòng tính lại kết quả.', 'error')
        return redirect(url_for('login'))
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    if not username or not password:
        flash('Vui lòng điền đầy đủ các thông tin đăng ký.', 'error')
        return redirect(url_for('login'))
    if len(username) < 3:
        flash('Tên đăng nhập phải có tối thiểu 3 ký tự.', 'error')
        return redirect(url_for('login'))
    if password != confirm_password:
        flash('Mật khẩu xác nhận không khớp.', 'error')
        return redirect(url_for('login'))
    password_hash = generate_password_hash(password)
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
            conn.commit()
        flash('Tạo tài khoản thành công! Hãy đăng nhập ngay bây giờ.', 'success')
    except sqlite3.IntegrityError:
        flash('Tên đăng nhập này đã được sử dụng. Vui lòng chọn tên khác.', 'error')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất thành công.', 'info')
    return redirect(url_for('login'))

@app.route('/api/account/info', methods=['GET'])
@login_required
def api_account_info():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, discord_token, discord_id, discord_username, discord_avatar FROM users WHERE id = ?', (user_id,))
        u = cursor.fetchone()
    if not u:
        return jsonify({'success': False, 'message': 'Không tìm thấy tài khoản'}), 404
    token = u['discord_token'] or ''
    has_token = bool(token and len(token) > 20)
    masked = (token[:10] + '...' + token[-6:]) if has_token else ''
    return jsonify({
        'success': True,
        'username': u['username'],
        'has_token': has_token,
        'discord_id': u['discord_id'] or '',
        'discord_username': u['discord_username'] or '',
        'discord_avatar': u['discord_avatar'] or '',
        'masked_token': masked
    })

@app.route('/api/account/bind_token', methods=['POST'])
@login_required
def api_account_bind_token():
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    if not token:
        return jsonify({'success': False, 'message': 'Vui lòng cung cấp Discord User Token'}), 400
    try:
        headers = {
            'Authorization': token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=8)
        if res.status_code != 200:
            return jsonify({'success': False, 'message': f'Token Discord không hợp lệ hoặc đã hết hạn (Mã lỗi {res.status_code})'}), 400
        user_info = res.json()
        d_id = str(user_info.get('id', ''))
        d_username = user_info.get('global_name') or user_info.get('username') or 'Discord User'
        avatar_hash = user_info.get('avatar')
        d_avatar = f"https://cdn.discordapp.com/avatars/{d_id}/{avatar_hash}.png?size=128" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"

        user_id = session['user_id']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET discord_token = ?, discord_id = ?, discord_username = ?, discord_avatar = ? WHERE id = ?',
                           (token, d_id, d_username, d_avatar, user_id))
            conn.commit()

        session['discord_token'] = token
        session['discord_username'] = d_username
        session['discord_avatar'] = d_avatar
        log_event(f'Tài khoản {session.get("username")} đã liên kết Discord: {d_username} ({d_id})', 'success')
        return jsonify({
            'success': True,
            'message': f'Liên kết thành công với Discord: {d_username}!',
            'discord_id': d_id,
            'discord_username': d_username,
            'discord_avatar': d_avatar
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi kết nối xác minh Discord: {str(e)}'}), 500

@app.route('/api/account/unbind_token', methods=['POST'])
@login_required
def api_account_unbind_token():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET discord_token = "", discord_id = "", discord_username = "", discord_avatar = "" WHERE id = ?', (user_id,))
        conn.commit()
    session.pop('discord_token', None)
    session.pop('discord_username', None)
    session.pop('discord_avatar', None)
    log_event(f'Đã hủy liên kết Discord Token cho tài khoản {session.get("username")}', 'info')
    return jsonify({'success': True, 'message': 'Đã hủy liên kết token thành công'})

@app.route('/api/quests', methods=['GET'])
@login_required
def api_quests():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')
    
    quests = [
        {
            'id': 'quest_genshin_v5',
            'title': 'Genshin Impact: Khám Phá Vùng Đất Mới',
            'game_name': 'Genshin Impact',
            'reward': '30 Nguyên Thạch + Khung Avatar Đặc Biệt',
            'banner': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298812425932820.png',
            'target_seconds': 45,
            'badge': 'Hot Promo'
        },
        {
            'id': 'quest_honkai_starrail',
            'title': 'Honkai: Star Rail: Hành Trình Khai Phá',
            'game_name': 'Honkai: Star Rail',
            'reward': '60 Ngọc Ánh Sao + 1 Tháng Discord Nitro Trial',
            'banner': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298453284323538.png',
            'target_seconds': 50,
            'badge': 'Đối Tác Discord'
        },
        {
            'id': 'quest_valorant_masters',
            'title': 'VALORANT: Chiến Trường Sinh Tử',
            'game_name': 'VALORANT',
            'reward': 'Danh hiệu Độc Quyền + Huy Hiệu Hồ Sơ',
            'banner': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359298813092823040.png',
            'target_seconds': 40,
            'badge': 'Mới'
        },
        {
            'id': 'quest_discord_desktop',
            'title': 'Discord Desktop Streaming Challenge',
            'game_name': 'Discord Desktop App',
            'reward': 'Huy Hiệu Streaming Star Trên Hồ Sơ',
            'banner': 'https://cdn.discordapp.com/app-assets/383226320970055681/1359299466493956258.png',
            'target_seconds': 30,
            'badge': 'Hàng Tuần'
        }
    ]

    if token:
        try:
            headers = {'Authorization': token, 'User-Agent': 'Mozilla/5.0'}
            res = requests.get('https://discord.com/api/v9/quests/@me', headers=headers, timeout=6)
            if res.status_code == 200:
                raw = res.json()
                raw_quests = raw.get('quests', [])
                if raw_quests:
                    extracted = []
                    for q in raw_quests:
                        qid = str(q.get('id', ''))
                        cfg = q.get('config', {})
                        msgs = cfg.get('messages', {})
                        qtitle = msgs.get('quest_name') or msgs.get('game_title') or 'Nhiệm Vụ Discord'
                        game_title = msgs.get('game_title') or 'Trò Chơi Discord'
                        extracted.append({
                            'id': qid,
                            'title': qtitle,
                            'game_name': game_title,
                            'reward': 'Phần Thưởng Độc Quyền Discord',
                            'banner': 'https://cdn.discordapp.com/embed/avatars/1.png',
                            'target_seconds': 60,
                            'badge': 'Discord API'
                        })
                    if extracted:
                        quests = extracted
        except Exception:
            pass

    runner = get_user_quest_runner(user_id)
    return jsonify({
        'success': True,
        'quests': quests,
        'worker_status': runner.get_status()
    })

@app.route('/api/quests/start', methods=['POST'])
@login_required
def api_quests_start():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')
    if not token:
        return jsonify({'success': False, 'message': 'Vui lòng liên kết Discord Token trước khi cày Quest!'}), 400

    data = request.get_json() or {}
    quest_id = data.get('quest_id', 'quest_discord_desktop')
    quest_name = data.get('quest_name', 'Nhiệm Vụ Discord')
    task_type = data.get('task_type', 'PLAY_ON_DESKTOP')
    target_seconds = int(data.get('target_seconds', 45))

    runner = get_user_quest_runner(user_id)
    runner.start(token, quest_id, quest_name, task_type=task_type, target_seconds=target_seconds)
    return jsonify({'success': True, 'message': f'Đã bắt đầu chạy Auto Quest cho {quest_name}!'})

@app.route('/api/quests/stop', methods=['POST'])
@login_required
def api_quests_stop():
    user_id = session['user_id']
    runner = get_user_quest_runner(user_id)
    runner.stop()
    return jsonify({'success': True, 'message': 'Đã dừng tiến trình Auto Quest'})

@app.route('/api/quests/status', methods=['GET'])
@login_required
def api_quests_status():
    user_id = session['user_id']
    runner = get_user_quest_runner(user_id)
    return jsonify({'success': True, 'status': runner.get_status()})

@app.route('/api/hypesquad/claim', methods=['POST'])
@login_required
def api_hypesquad_claim():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')
    if not token:
        return jsonify({'success': False, 'message': 'Vui lòng liên kết Discord Token trước!'}), 400

    data = request.get_json() or {}
    house_id = int(data.get('house_id', 1))
    houses = {1: 'Bravery (Tím)', 2: 'Brilliance (Cam)', 3: 'Balance (Xanh Lá)'}
    house_name = houses.get(house_id, 'Bravery')

    try:
        headers = make_discord_headers(token)
        res = requests.post('https://discord.com/api/v9/hypesquad/online', headers=headers, json={'house_id': house_id}, timeout=8)
        if res.status_code == 204:
            log_event(f'Nhận thành công huy hiệu HypeSquad {house_name} cho tài khoản {session.get("username")}', 'success')
            return jsonify({'success': True, 'message': f'Chúc mừng! Đã nhận thành công huy hiệu HypeSquad {house_name}!'})
        elif res.status_code == 429:
            retry = res.headers.get('Retry-After', '60')
            return jsonify({'success': False, 'message': f'Discord Rate Limited. Vui lòng thử lại sau {retry}s'}), 429
        else:
            return jsonify({'success': False, 'message': f'Không thể nhận huy hiệu (Mã lỗi {res.status_code})'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi kết nối: {str(e)}'}), 500

@app.route('/api/lyrics/sync', methods=['POST'])
@login_required
def api_lyrics_sync():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')
    if not token:
        return jsonify({'success': False, 'message': 'Tài khoản chưa liên kết Discord Token!'}), 400

    data = request.get_json() or {}
    text = data.get('text', '').strip()
    emoji = data.get('emoji', '🎵').strip()
    ok, msg = lyric_worker.update_lyric(token, text, emoji=emoji)
    return jsonify({'success': ok, 'message': msg})

@app.route('/api/lyrics/clear', methods=['POST'])
@login_required
def api_lyrics_clear():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')
    if not token:
        return jsonify({'success': False, 'message': 'Tài khoản chưa liên kết Discord Token!'}), 400

    ok, msg = lyric_worker.clear_lyric(token)
    return jsonify({'success': ok, 'message': msg})

@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    return jsonify(rpc_worker.get_status_data())

@app.route('/api/start', methods=['POST'])
@login_required
def api_start():
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    activity_name = data.get('activityName', '').strip()
    if not token:
        return (jsonify({'success': False, 'message': 'Thiếu Discord User Token'}), 400)
    if not activity_name:
        return (jsonify({'success': False, 'message': 'Thiếu tên hoạt động / ứng dụng'}), 400)
    rpc_worker.start(data)
    return jsonify({'success': True, 'message': 'Đã gửi lệnh kết nối tới Discord Gateway'})

@app.route('/api/update', methods=['POST'])
@login_required
def api_update():
    data = request.get_json() or {}
    activity_name = data.get('activityName', '').strip()
    if not activity_name:
        return (jsonify({'success': False, 'message': 'Thiếu tên hoạt động / ứng dụng'}), 400)
    try:
        rpc_worker.update_presence(data)
        return jsonify({'success': True, 'message': 'Đã cập nhật trạng thái Discord thành công!'})
    except Exception as e:
        return (jsonify({'success': False, 'message': f'Lỗi khi cập nhật: {str(e)}'}), 500)

@app.route('/api/stop', methods=['POST'])
@login_required
def api_stop():
    rpc_worker.stop()
    return jsonify({'success': True, 'message': 'Đã dừng Discord RPC'})

@app.route('/api/portal_app_info', methods=['GET', 'POST'])
@login_required
def api_portal_app_info():
    token = ''
    if request.is_json:
        data = request.get_json() or {}
        token = data.get('token', '').strip()
    if not token:
        token = request.args.get('token', '').strip()
    if not token and rpc_worker and rpc_worker.config:
        token = rpc_worker.config.get('token', '').strip()
    if not token and 'discord_token' in session:
        token = session['discord_token']
    if not token:
        return (jsonify({'success': True, 'apps': [], 'message': 'Chưa nhập Discord User Token'}), 200)
    try:
        session['discord_token'] = token
        headers = {'Authorization': token, 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get('https://discord.com/api/v9/applications?with_team_applications=true', headers=headers, timeout=8)
        if res.status_code != 200:
            return (jsonify({'success': False, 'apps': [], 'message': f'Discord API trả về mã {res.status_code} (Kiểm tra lại Token)'}), 200)
        raw_apps = res.json()
        result = []
        for item in raw_apps:
            app_id = str(item.get('id', ''))
            app_name = item.get('name', 'Chưa đặt tên')
            bot_data = item.get('bot')
            bot_avatar_url = None
            if bot_data and bot_data.get('avatar'):
                bot_id = bot_data.get('id')
                bot_av = bot_data.get('avatar')
                bot_avatar_url = f"https://cdn.discordapp.com/avatars/{bot_id}/{bot_av}.png?size=256"
            app_icon_url = None
            if item.get('icon'):
                icon_hash = item.get('icon')
                app_icon_url = f"https://cdn.discordapp.com/app-icons/{app_id}/{icon_hash}.png?size=256"
            display_avatar = bot_avatar_url or app_icon_url or 'https://cdn.discordapp.com/embed/avatars/0.png'
            result.append({'id': app_id, 'name': app_name, 'bot_avatar': bot_avatar_url, 'app_icon': app_icon_url, 'display_avatar': display_avatar, 'has_bot': bool(bot_data)})
        return jsonify({'success': True, 'apps': result})
    except Exception as e:
        return (jsonify({'success': False, 'apps': [], 'message': f'Lỗi kết nối Discord: {str(e)}'}), 200)

@app.route('/api/logs', methods=['GET', 'DELETE'])
@login_required
def api_logs():
    global LOG_BUFFER
    if request.method == 'DELETE':
        LOG_BUFFER.clear()
        log_event('Đã làm mới nhật ký bảng điều khiển.', 'info')
        return jsonify({'success': True, 'message': 'Đã xóa nhật ký'})
    return jsonify({'success': True, 'logs': LOG_BUFFER})

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    if 'image' not in request.files:
        return (jsonify({'success': False, 'message': 'Không tìm thấy file ảnh'}), 400)
    file = request.files['image']
    if file.filename == '':
        return (jsonify({'success': False, 'message': 'Chưa chọn file nào'}), 400)
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f'{uuid.uuid4().hex}.{ext}'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)
        local_url = f'/static/uploads/{unique_name}'
        UPLOAD_PATH_MAP[unique_name] = filepath
        UPLOAD_PATH_MAP[local_url] = filepath
        UPLOAD_PATH_MAP[filepath] = filepath
        return jsonify({'success': True, 'filename': unique_name, 'url': local_url})
    return (jsonify({'success': False, 'message': 'Định dạng file không được hỗ trợ (chỉ chấp nhận PNG, JPG, GIF, WEBP)'}), 400)

@app.route('/api/presets', methods=['GET', 'POST'])
@login_required
def api_presets():
    user_id = session['user_id']
    if request.method == 'GET':
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, config, created_at FROM presets WHERE user_id = ? ORDER BY id DESC', (user_id,))
            rows = cursor.fetchall()
            presets = []
            for row in rows:
                try:
                    cfg = json.loads(row['config'])
                except Exception:
                    cfg = {}
                presets.append({'id': row['id'], 'name': row['name'], 'config': cfg, 'created_at': row['created_at']})
        return jsonify({'success': True, 'presets': presets})
    elif request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', '').strip()
        config = data.get('config', {})
        if not name:
            return (jsonify({'success': False, 'message': 'Vui lòng cung cấp tên Preset'}), 400)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO presets (user_id, name, config) VALUES (?, ?, ?)', (user_id, name, json.dumps(config)))
            conn.commit()
            new_id = cursor.lastrowid
        return jsonify({'success': True, 'id': new_id, 'message': 'Đã lưu Preset thành công'})

@app.route('/api/presets/<int:preset_id>', methods=['DELETE'])
@login_required
def api_delete_preset(preset_id):
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM presets WHERE id = ? AND user_id = ?', (preset_id, user_id))
        conn.commit()
    return jsonify({'success': True, 'message': 'Đã xóa Preset'})

def open_browser(port):
    time.sleep(1.2)
    try:
        if sys.platform.startswith('win') and not os.environ.get('CONTAINER'):
            webbrowser.open(f'http://localhost:{port}')
    except BaseException:
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('SERVER_PORT', 5000)))
    host = '0.0.0.0'
    print('=========================================================')
    print('      DISCORD RICH PRESENCE MASTER (Flask + Selfbot)     ')
    print('=========================================================')
    print(f' Đang khởi chạy web server tại http://{host}:{port} ... ')
    if sys.platform.startswith('win') and not os.environ.get('CONTAINER'):
        print(' Trình duyệt web sẽ tự động mở trong chốc lát...         ')
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    print(' Bấm Ctrl+C trong terminal để dừng ứng dụng.             ')
    print('=========================================================')
    try:
        app.run(host=host, port=port, debug=False)
    except (KeyboardInterrupt, SystemExit):
        print('\n[Hệ thống] Đang tắt máy chủ và dọn dẹp tiến trình...')
        rpc_worker.stop()
        sys.exit(0)
