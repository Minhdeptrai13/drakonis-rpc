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
import io
import math
from functools import wraps
from datetime import datetime, timezone
from typing import Optional, List, Dict, Union, Any
from PIL import Image, ImageDraw, ImageFilter
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
KNOWN_ASSET_ICONS = {
    'vscode': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg',
    'python': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg',
    'git': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/git/git-original.svg',
    'docker': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg',
    'js': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg',
    'ts': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg',
    'jsx': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg',
    'tsx': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg',
    'html': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/html5/html5-original.svg',
    'css': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/css3/css3-original.svg',
    'c': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/c/c-original.svg',
    'cpp': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/cplusplus/cplusplus-original.svg',
    'csharp': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/csharp/csharp-original.svg',
    'java': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg',
    'rust': 'https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/rust/rust-original.svg',
    'go': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/go/go-original.svg'
}
LOG_BUFFER = []
MAX_LOG_ENTRIES = 120

QUEST_LOG_BUFFER = []
QUEST_LOG_LOCK = threading.Lock()
MAX_QUEST_LOG_ENTRIES = 200

def log_event(message: str, level: str='info'):
    timestamp = time.strftime('%H:%M:%S')
    entry = {'time': timestamp, 'message': str(message), 'level': level}
    LOG_BUFFER.append(entry)
    if len(LOG_BUFFER) > MAX_LOG_ENTRIES:
        LOG_BUFFER.pop(0)
    print(f'[{timestamp}] [{level.upper()}] {message}')

def quest_log(message: str, level: str = 'info'):
    """Push log entry into QUEST_LOG_BUFFER for realtime terminal display"""
    timestamp = time.strftime('%H:%M:%S')
    entry = {'time': timestamp, 'message': str(message), 'level': level}
    with QUEST_LOG_LOCK:
        QUEST_LOG_BUFFER.append(entry)
        if len(QUEST_LOG_BUFFER) > MAX_QUEST_LOG_ENTRIES:
            QUEST_LOG_BUFFER.pop(0)
    print(f'[QUEST][{timestamp}] [{level.upper()}] {message}')

log_event('Hệ thống Discord RPC Master v2.2 đã sẵn sàng hoạt động.', 'info')

# ==============================================================================
# DIPRE CYBER SHIELD: MULTI-LAYER ANTI-DDOS & BRUTE-FORCE PROTECTION
# ==============================================================================
IP_REQUEST_HISTORY: Dict[str, List[float]] = {}
IP_FAILED_ATTEMPTS: Dict[str, List[float]] = {}
IP_BLACKLIST: Dict[str, float] = {}  # ip -> ban_until timestamp
SECURITY_LOCK = threading.Lock()

RATE_LIMIT_GLOBAL = 100        # max requests per 10s window
RATE_LIMIT_SENSITIVE = 20      # max requests per 10s window for auth/captcha
MAX_FAILED_ATTEMPTS = 6        # max failed logins/captchas before jail
JAIL_DURATION_SECONDS = 180    # 3 minutes temporary jail

def get_client_ip() -> str:
    """Trích xuất IP thực tế của client (hỗ trợ reverse proxy Render / Cloudflare)"""
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

def is_ip_jailed(ip: str) -> bool:
    now = time.time()
    with SECURITY_LOCK:
        if ip in IP_BLACKLIST:
            if now < IP_BLACKLIST[ip]:
                return True
            else:
                del IP_BLACKLIST[ip]
    return False

def record_failed_attempt(ip: str):
    now = time.time()
    with SECURITY_LOCK:
        history = IP_FAILED_ATTEMPTS.get(ip, [])
        history = [t for t in history if now - t < 120]  # giữ trong 2 phút
        history.append(now)
        IP_FAILED_ATTEMPTS[ip] = history
        if len(history) >= MAX_FAILED_ATTEMPTS:
            IP_BLACKLIST[ip] = now + JAIL_DURATION_SECONDS
            log_event(f"🚨 [DIPRE Shield] IP {ip} bị tạm khóa {JAIL_DURATION_SECONDS}s do thất bại liên tiếp {len(history)} lần!", "warning")

def clear_failed_attempts(ip: str):
    with SECURITY_LOCK:
        if ip in IP_FAILED_ATTEMPTS:
            del IP_FAILED_ATTEMPTS[ip]

@app.before_request
def dipre_security_firewall():
    """Lớp chắn bảo mật Anti-DDoS & Kiểm tra tính toàn vẹn của Session trước mỗi request"""
    ip = get_client_ip()
    now = time.time()

    # 1. Kiểm tra danh sách tạm giam (Jail)
    if is_ip_jailed(ip):
        ban_remain = int(IP_BLACKLIST.get(ip, now) - now)
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'DIPRE_SHIELD_BLOCKED',
                'message': f'IP của bạn bị tạm khóa do nghi vấn spam/brute-force. Thử lại sau {ban_remain}s.'
            }), 429
        return f"""
        <html><body style="background:#0b0e17;color:#f43f5e;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
        <div style="text-align:center;padding:2rem;background:#111214;border:1px solid #f43f5e;border-radius:16px;box-shadow:0 0 30px rgba(244,63,94,0.3);">
            <h1>🚨 DIPRE CYBER SHIELD</h1>
            <p>Hệ thống phát hiện hoạt động bất thường từ địa chỉ IP của bạn.</p>
            <p>Tạm khóa yêu cầu trong: <b>{ban_remain} giây</b></p>
        </div>
        </body></html>
        """, 429

    # 2. In-Memory Sliding Window Rate Limiter
    is_sensitive = request.path in ['/login', '/register'] or request.path.startswith('/api/captcha')
    limit = RATE_LIMIT_SENSITIVE if is_sensitive else RATE_LIMIT_GLOBAL

    with SECURITY_LOCK:
        history = IP_REQUEST_HISTORY.get(ip, [])
        history = [t for t in history if now - t < 10.0]
        if len(history) >= limit:
            return jsonify({
                'success': False,
                'error': 'RATE_LIMIT_EXCEEDED',
                'message': 'Thao tác quá dồn dập. Vui lòng chậm lại!'
            }), 429
        history.append(now)
        IP_REQUEST_HISTORY[ip] = history

    # 3. KIỂM TRA TÍNH TOÀN VẸN CỦA TÀI KHOẢN TRONG DATABASE
    # Giải quyết triệt để lỗi khi xóa DB hoặc deploy lại Render làm mất dữ liệu:
    if 'user_id' in session:
        user_exists = False
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, username, discord_token FROM users WHERE id = ?', (session['user_id'],))
                u = cursor.fetchone()
                if u:
                    user_exists = True
        except Exception:
            user_exists = False

        if not user_exists:
            # Dữ liệu tài khoản trong DB đã không còn (do xóa database.db hoặc render reset)
            # Ngay lập tức xóa sạch session mồ côi
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'session_expired': True,
                    'message': 'Cơ sở dữ liệu đã được làm mới. Vui lòng đăng nhập lại.'
                }), 401
            elif request.path not in ['/login', '/register', '/static/']:
                flash('Cơ sở dữ liệu đã được cập nhật hoặc phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'warning')
                return redirect(url_for('login'))

@app.after_request
def dipre_security_headers(response):
    """Gắn các Security Headers chuẩn OWASP chống XSS, Clickjacking, MIME sniffing"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    # Kích hoạt WAL mode để tối ưu hiệu năng ghi đọc, không bị lock database trên Render
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
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
        for col_name in ['discord_token', 'discord_id', 'discord_username', 'discord_avatar', 'config']:
            if col_name not in cols:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} TEXT DEFAULT ''")
                except Exception:
                    pass
        conn.commit()
init_db()


def generate_turnstile_captcha():
    """Cấp 1: Captcha một chạm thông minh phong cách Cloudflare Turnstile"""
    challenge_token = hashlib.sha256(f"{uuid.uuid4()}-{time.time()}-DIPRE".encode()).hexdigest()[:32]
    session['turnstile_token'] = challenge_token
    session['turnstile_issued_at'] = time.time()
    session['captcha_level'] = 1
    session['captcha_verified'] = False
    return {
        'level': 1,
        'type': 'turnstile',
        'challenge': challenge_token,
        'title': 'Xác thực một chạm bảo mật DIPRE Shield',
        'prompt': 'Tôi là con người'
    }

def generate_slide_captcha():
    """Cấp 2: Captcha trượt TikTok-style mảnh ghép puzzle khuyết"""
    width, height = 320, 160
    piece_w, piece_h = 46, 46

    bg_img = None
    try:
        urls = [
            'https://picsum.photos/320/160?random=' + str(random.randint(1, 9999)),
            'https://picsum.photos/320/160'
        ]
        url = random.choice(urls)
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            bg_img = Image.open(io.BytesIO(res.content)).convert('RGBA')
            if bg_img.size != (width, height):
                bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
    except Exception:
        bg_img = None

    if bg_img is None:
        bg_img = Image.new('RGBA', (width, height), (10, 12, 20, 255))
        draw = ImageDraw.Draw(bg_img)
        for y in range(height):
            r = int(12 + (30 - 12) * (y / height))
            g = int(15 + (20 - 15) * (y / height))
            b = int(28 + (65 - 28) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        for i in range(0, width, 24):
            draw.line([(i, 0), (i, height)], fill=(99, 102, 241, 35), width=1)
        for j in range(0, height, 20):
            draw.line([(0, j), (width, j)], fill=(6, 182, 212, 35), width=1)
        for _ in range(7):
            cx = random.randint(30, width - 30)
            cy = random.randint(20, height - 20)
            rad = random.randint(20, 40)
            draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(147, 51, 234, 90), width=2)
            draw.text((cx - 15, cy - 8), "DIPRE", fill=(56, 189, 248, 140))

    target_x = random.randint(85, width - piece_w - 20)
    target_y = random.randint(15, height - piece_h - 15)

    session['slide_target_x'] = target_x
    session['slide_target_y'] = target_y
    session['captcha_level'] = 2
    session['captcha_verified'] = False
    session['slide_verified'] = False

    mask = Image.new('L', (piece_w, piece_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, piece_w - 1, piece_h - 1], radius=8, fill=255)

    crop = bg_img.crop((target_x, target_y, target_x + piece_w, target_y + piece_h))
    piece_img = Image.new('RGBA', (piece_w, piece_h), (0, 0, 0, 0))
    piece_img.paste(crop, (0, 0), mask)

    p_draw = ImageDraw.Draw(piece_img)
    p_draw.rounded_rectangle([0, 0, piece_w - 1, piece_h - 1], radius=8, outline=(129, 140, 248, 255), width=2)

    hole = Image.new('RGBA', (piece_w, piece_h), (0, 0, 0, 220))
    bg_img.paste(hole, (target_x, target_y), mask)
    bg_draw = ImageDraw.Draw(bg_img)
    bg_draw.rounded_rectangle([target_x, target_y, target_x + piece_w - 1, target_y + piece_h - 1], radius=8, outline=(255, 255, 255, 190), width=2)

    bg_buffer = io.BytesIO()
    bg_img.convert('RGB').save(bg_buffer, format='JPEG', quality=88)
    bg_base64 = base64.b64encode(bg_buffer.getvalue()).decode('utf-8')

    piece_buffer = io.BytesIO()
    piece_img.save(piece_buffer, format='PNG')
    piece_base64 = base64.b64encode(piece_buffer.getvalue()).decode('utf-8')

    return {
        'level': 2,
        'type': 'slide',
        'bg_image': f"data:image/jpeg;base64,{bg_base64}",
        'piece_image': f"data:image/png;base64,{piece_base64}",
        'target_y': target_y,
        'piece_width': piece_w,
        'piece_height': piece_h,
        'bg_width': width,
        'bg_height': height,
        'prompt': 'Kéo thanh trượt để khớp mảnh ghép puzzle'
    }

def generate_circle_rotation_captcha():
    """Cấp 3: Captcha xoay vòng tròn đồng tâm khớp hình phong cách TikTok / Arkose Labs"""
    size = 260
    center = size // 2
    inner_radius = 70
    outer_radius = 120

    base_img = None
    try:
        url = 'https://picsum.photos/260/260?random=' + str(random.randint(1000, 9999))
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            base_img = Image.open(io.BytesIO(res.content)).convert('RGBA')
            if base_img.size != (size, size):
                base_img = base_img.resize((size, size), Image.Resampling.LANCZOS)
    except Exception:
        base_img = None

    if base_img is None:
        base_img = Image.new('RGBA', (size, size), (8, 10, 18, 255))
        draw = ImageDraw.Draw(base_img)
        for r in range(outer_radius, 20, -15):
            col = (int(90 + 160 * (r / outer_radius)), int(40 + 80 * (r / outer_radius)), 245, 255)
            draw.ellipse([center - r, center - r, center + r, center + r], outline=col, width=3)
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            rad = math.radians(angle)
            x2 = center + int(outer_radius * math.cos(rad))
            y2 = center + int(outer_radius * math.sin(rad))
            draw.line([(center, center), (x2, y2)], fill=(56, 189, 248, 220), width=4)
        draw.regular_polygon((center, center, 42), 6, fill=(147, 51, 234, 210), outline=(255, 255, 255, 255))
        draw.text((center - 25, center - 8), "DIPRE", fill=(255, 255, 255, 255))

    # Góc xoay bí mật: từ 45 độ đến 315 độ
    secret_angle = random.choice([50, 75, 90, 120, 145, 180, 210, 240, 270, 295])
    session['rotate_target_angle'] = secret_angle
    session['captcha_level'] = 3
    session['captcha_verified'] = False

    inner_mask = Image.new('L', (size, size), 0)
    m_draw = ImageDraw.Draw(inner_mask)
    m_draw.ellipse([center - inner_radius, center - inner_radius, center + inner_radius, center + inner_radius], fill=255)

    inner_crop = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    inner_crop.paste(base_img, (0, 0), inner_mask)

    # Xoay vòng tròn nhỏ theo góc ban đầu
    initial_rotated_inner = inner_crop.rotate(secret_angle, resample=Image.Resampling.BICUBIC, center=(center, center))

    outer_img = base_img.copy()
    o_draw = ImageDraw.Draw(outer_img)
    o_draw.ellipse([center - inner_radius, center - inner_radius, center + inner_radius, center + inner_radius], outline=(147, 51, 234, 255), width=3)
    o_draw.ellipse([center - outer_radius, center - outer_radius, center + outer_radius, center + outer_radius], outline=(6, 182, 212, 255), width=2)

    outer_mask = Image.eval(inner_mask, lambda a: 255 - a)
    outer_final = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    outer_final.paste(outer_img, (0, 0), outer_mask)

    buf_outer = io.BytesIO()
    outer_final.save(buf_outer, format='PNG')
    outer_b64 = base64.b64encode(buf_outer.getvalue()).decode('utf-8')

    buf_inner = io.BytesIO()
    initial_rotated_inner.save(buf_inner, format='PNG')
    inner_b64 = base64.b64encode(buf_inner.getvalue()).decode('utf-8')

    return {
        'level': 3,
        'type': 'rotate',
        'outer_image': f"data:image/png;base64,{outer_b64}",
        'inner_image': f"data:image/png;base64,{inner_b64}",
        'initial_angle': secret_angle,
        'size': size,
        'inner_radius': inner_radius,
        'prompt': 'Xoay vòng tròn đồng tâm sao cho hình ảnh khớp hoàn toàn'
    }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'session_expired': True, 'message': 'Vui lòng đăng nhập để tiếp tục.'}), 401
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

        # NẾU LÀ ẢNH NHỎ VÀ NGƯỜI DÙNG KHÔNG NHẬP HOẶC ĐÃ GỠ -> TRẢ VỀ NONE HẲN (KHÔNG HIỆN ẢNH NHỎ TRÊN DISCORD)
        if prefix == 's' and not img_val:
            return None

        if lower_val in ('', 'bot', 'app', 'bot_avatar', 'app_icon', 'developer_portal', 'portal', 'default'):
            if prefix == 's':
                return None
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
        if app and prefix == 'l':
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
        return None

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

def normalize_rpc_config(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    out = dict(data)
    
    # Map snake_case to camelCase
    if 'name' in data and not data.get('activityName'):
        out['activityName'] = data['name']
    if 'activity_name' in data and not data.get('activityName'):
        out['activityName'] = data['activity_name']
    if not out.get('activityName'):
        out['activityName'] = 'Visual Studio Code'
        
    if 'activity_type' in data and not data.get('activityType'):
        out['activityType'] = data['activity_type']
    if 'stream_url' in data and not data.get('streamUrl'):
        out['streamUrl'] = data['stream_url']
    if 'large_image' in data and not data.get('largeImage'):
        out['largeImage'] = data['large_image']
    if 'small_image' in data and not data.get('smallImage'):
        out['smallImage'] = data['small_image']
    if 'large_text' in data and not data.get('largeText'):
        out['largeText'] = data['large_text']
    if 'small_text' in data and not data.get('smallText'):
        out['smallText'] = data['small_text']
    if 'app_id' in data and not data.get('appId'):
        out['appId'] = data['app_id']
    if 'use_timestamp' in data and not data.get('hasTimestamp'):
        out['hasTimestamp'] = bool(data['use_timestamp'])
        
    # Buttons
    buttons = data.get('buttons', [])
    if isinstance(buttons, list) and len(buttons) > 0:
        if len(buttons) >= 1 and isinstance(buttons[0], dict):
            out['btn1Label'] = buttons[0].get('label', '')
            out['btn1Url'] = buttons[0].get('url', '')
        if len(buttons) >= 2 and isinstance(buttons[1], dict):
            out['btn2Label'] = buttons[1].get('label', '')
            out['btn2Url'] = buttons[1].get('url', '')
            
    return out


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
    """Tái sử dụng TCP session giữ kết nối liên tục, chống bị Discord đóng kết nối bất thường"""
    sess = requests.Session()
    sess.headers.update(make_discord_headers(token))
    return sess

from datetime import datetime, timezone

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
        """Vòng lặp tự phát hiện, tự nhận và hoàn thành toàn bộ quest — DIPRE Engine cho Minh"""
        quest_log("══════════════════════════════════════════════════", "info")
        quest_log("🌸 KHỞI ĐỘNG CHẾ ĐỘ AUTO QUEST COMPLETER — MINH", "success")
        quest_log("Tự động quét Discord, cày dứt điểm quest đã nhận & nhận 1 cày 1 an toàn!", "info")
        quest_log("══════════════════════════════════════════════════", "info")

        completed_ids = set()
        failed_enrollment_ids = set()
        cycle = 0

        while not self.stop_flag.is_set():
            cycle += 1
            quest_log(f"─── Quét nhiệm vụ lần #{cycle} (Minh) ───", "info")
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

                # BƯỚC 1: Cày dứt điểm các quest ĐÃ ĐƯỢC NHẬN mà CHƯA HOÀN THÀNH
                actionable_enrolled = [
                    (q, p) for q, p in zip(raw_quests, parsed_list)
                    if p['completable'] and p['enrolled'] and not p['completed'] and p['id'] not in completed_ids
                ]

                # BƯỚC 2: Nếu không còn quest nào đã nhận cần cày -> nhận từng quest một có giãn cách
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
            # Log mỗi 10% thay đổi để tránh spam
            if pct // 10 != last_log_pct // 10:
                last_log_pct = pct
                bar_filled = int(pct / 5)
                bar = '█' * bar_filled + '░' * (20 - bar_filled)
                quest_log(f'[{bar}] {pct}% ({int(seconds_done)}s / {target_seconds}s)', 'info')

        # Final terminal call
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

import xml.etree.ElementTree as ET

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

lyric_worker = DiscordLyricWorker()

@app.route('/api/captcha')
def api_captcha():
    requested_level = request.args.get('level', type=int)
    if not requested_level:
        requested_level = session.get('captcha_level', 1)

    if requested_level == 1:
        data = generate_turnstile_captcha()
    elif requested_level == 3:
        data = generate_circle_rotation_captcha()
    else:
        data = generate_slide_captcha()

    return jsonify({
        'success': True,
        'captcha': data
    })

@app.route('/api/captcha/verify', methods=['POST'])
def api_captcha_verify():
    data = request.get_json() or {}
    level = data.get('level')
    if not level:
        level = session.get('captcha_level', 1)

    try:
        level = int(level)
        if level == 1:
            token = data.get('token')
            expected = session.get('turnstile_token')
            issued_at = session.get('turnstile_issued_at', 0)
            # Chống bot click tức thì dưới 400ms
            if not token or token != expected or (time.time() - issued_at) < 0.4:
                session['captcha_verified'] = False
                return jsonify({'success': False, 'message': 'Xác thực không hợp lệ hoặc thao tác quá nhanh, hãy thử lại'}), 400
            session['captcha_verified'] = True
            session['slide_verified'] = True
            return jsonify({'success': True, 'level': 1, 'message': 'Xác thực DIPRE Shield một chạm thành công!'})

        elif level == 3:
            user_angle = data.get('angle')
            target_angle = session.get('rotate_target_angle')
            if user_angle is None or target_angle is None:
                return jsonify({'success': False, 'message': 'Thiếu góc xoay xác thực'}), 400
            user_angle = float(user_angle)
            target_angle = float(target_angle)
            # Tính sai số góc xoay (chu kỳ 360 độ)
            diff = abs((user_angle - target_angle + 180) % 360 - 180)
            if diff <= 9.0:
                session['captcha_verified'] = True
                session['slide_verified'] = True
                return jsonify({'success': True, 'level': 3, 'message': 'Hình ảnh đã khớp hoàn hảo! Xác thực thành công!'})
            else:
                session['captcha_verified'] = False
                return jsonify({'success': False, 'diff': round(diff, 1), 'message': f'Hình ảnh chưa khớp (lệch ~{int(diff)}°), vui lòng xoay chuẩn hơn!'}), 400

        else: # level 2: slide puzzle
            slide_x = data.get('x')
            target_x = session.get('slide_target_x')
            if slide_x is None or target_x is None:
                return jsonify({'success': False, 'message': 'Thiếu dữ liệu kéo trượt'}), 400
            slide_x = float(slide_x)
            if abs(slide_x - target_x) <= 8:
                session['captcha_verified'] = True
                session['slide_verified'] = True
                return jsonify({'success': True, 'level': 2, 'message': 'Khối ghép chuẩn xác! Xác thực thành công!'})
            else:
                session['captcha_verified'] = False
                return jsonify({'success': False, 'message': 'Khối ghép chưa đúng vị trí, hãy thử lại!'}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

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
        if not session.get('captcha_verified', False) and not session.get('slide_verified', False):
            flash('Vui lòng hoàn thành xác thực bảo mật trước khi đăng nhập.', 'error')
            return redirect(url_for('login'))
        session['captcha_verified'] = False
        session['slide_verified'] = False

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
            clear_failed_attempts(get_client_ip())
            session['user_id'] = user['id']
            session['username'] = user['username']
            if user['discord_token']:
                session['discord_token'] = user['discord_token']
                session['discord_username'] = user['discord_username']
                session['discord_avatar'] = user['discord_avatar']
            flash(f'Chào mừng trở lại, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            record_failed_attempt(get_client_ip())
            flash('Tên đăng nhập hoặc mật khẩu không chính xác.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    if not session.get('slide_verified', False) and not session.get('captcha_verified', False):
        flash('Vui lòng hoàn thành xác thực bảo mật trước khi đăng ký.', 'error')
        return redirect(url_for('login'))
    session['slide_verified'] = False
    session['captcha_verified'] = False

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
            clear_failed_attempts(get_client_ip())
        flash('Tạo tài khoản thành công! Hãy đăng nhập ngay bây giờ.', 'success')
    except sqlite3.IntegrityError:
        record_failed_attempt(get_client_ip())
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
            'username': d_username,
            'avatar': d_avatar,
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
    
    quests = []
    if token:
        try:
            headers = make_discord_headers(token)
            res = requests.get('https://discord.com/api/v9/quests/@me', headers=headers, timeout=10)
            if res.status_code == 200:
                raw = res.json()
                raw_quests = []
                if isinstance(raw, dict):
                    raw_quests = raw.get('quests', [])
                elif isinstance(raw, list):
                    raw_quests = raw
                for q in raw_quests:
                    quests.append(parse_discord_quest_item(q))
        except Exception as e:
            log_event(f'Lỗi tải Quests Discord từ API: {e}', 'warn')

    runner = get_user_quest_runner(user_id)
    return jsonify({
        'success': True,
        'quests': quests,
        'worker_status': runner.get_status()
    })

@app.route('/api/quests/enroll_all', methods=['POST'])
@login_required
def api_quests_enroll_all():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')
    if not token:
        return jsonify({'success': False, 'message': 'Vui lòng liên kết Discord Token trước!'}), 400

    runner = get_user_quest_runner(user_id)
    count = 0
    try:
        headers = make_discord_headers(token)
        res = requests.get('https://discord.com/api/v9/quests/@me', headers=headers, timeout=8)
        if res.status_code == 200:
            raw = res.json()
            raw_quests = raw.get('quests', []) if isinstance(raw, dict) else raw
            for q in raw_quests:
                p = parse_discord_quest_item(q)
                if not p['completable']:
                    continue
                if not p['enrolled'] and not p['completed']:
                    if runner.enroll(token, p['id']):
                        count += 1
                        time.sleep(1.5)
        log_event(f'Đã tự động nhận {count} nhiệm vụ Discord mới!', 'success')
        return jsonify({'success': True, 'count': count, 'message': f'Đã nhận thành công {count} nhiệm vụ mới!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi nhận nhiệm vụ: {str(e)}'}), 500

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
    runner = get_user_quest_runner(user_id)

    # Chế độ tự động hoàn toàn (Auto Completer)
    if data.get('auto', False) or data.get('quest_id') == 'auto':
        runner.start_auto(token)
        return jsonify({'success': True, 'message': 'Đã khởi động chế độ Tự Động Quét & Cày Tất Cả Nhiệm Vụ!'})

    quest_id = data.get('quest_id', 'quest_discord_desktop')
    quest_name = data.get('quest_name', 'Nhiệm Vụ Discord')
    task_type = data.get('task_type', 'PLAY_ON_DESKTOP')
    target_seconds = int(data.get('target_seconds', 45))

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

@app.route('/api/quests/logs', methods=['GET', 'DELETE'])
@login_required
def api_quests_logs():
    global QUEST_LOG_BUFFER
    if request.method == 'DELETE':
        with QUEST_LOG_LOCK:
            QUEST_LOG_BUFFER.clear()
        quest_log('Đã xóa nhật ký Quest Console.', 'info')
        return jsonify({'success': True, 'message': 'Đã xóa nhật ký'})
    with QUEST_LOG_LOCK:
        logs_copy = list(QUEST_LOG_BUFFER)
    return jsonify({'success': True, 'logs': logs_copy})

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

@app.route('/api/lyrics/search', methods=['GET'])
@login_required
def api_lyrics_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'success': False, 'message': 'Vui lòng nhập tên bài hát'}), 400
    try:
        url = f"https://lrclib.net/api/search?q={requests.utils.quote(q)}"
        r = requests.get(url, headers={"User-Agent": "DIPRE-Discord/1.0"}, timeout=6)
        results = []
        if r.status_code == 200:
            tracks = r.json()
            # Giới hạn đúng 10 bài hát
            selected_tracks = tracks[:10]
            
            # Lấy cover art từ iTunes Search API cho nhanh và nét
            for t in selected_tracks:
                track_name = t.get('trackName') or ''
                artist_name = t.get('artistName') or ''
                cover_url = ''
                try:
                    itunes_url = f"https://itunes.apple.com/search?term={requests.utils.quote(track_name + ' ' + artist_name)}&entity=song&limit=1"
                    ir = requests.get(itunes_url, timeout=3)
                    if ir.status_code == 200:
                        ires = ir.json().get('results', [])
                        if ires:
                            # Lấy ảnh 300x300 hoặc 600x600 nét căng
                            raw_art = ires[0].get('artworkUrl100', '')
                            cover_url = raw_art.replace('100x100bb', '400x400bb')
                except Exception:
                    cover_url = ''

                if not cover_url:
                    # Fallback ảnh nhạc gradient xịn
                    cover_url = 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=400&auto=format&fit=crop&q=80'

                results.append({
                    'id': t.get('id'),
                    'name': track_name,
                    'artist': artist_name,
                    'album': t.get('albumName') or '',
                    'duration': t.get('duration') or 0,
                    'cover': cover_url,
                    'has_synced': bool(t.get('syncedLyrics'))
                })
            return jsonify({'success': True, 'tracks': results})
        return jsonify({'success': True, 'tracks': []})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/lyrics/song', methods=['GET'])
@login_required
def api_lyrics_song():
    q = request.args.get('q', '').strip()
    song_id = request.args.get('id')
    try:
        if song_id:
            url = f"https://lrclib.net/api/get/{song_id}"
            r = requests.get(url, headers={"User-Agent": "DIPRE-Discord/1.0"}, timeout=6)
            if r.status_code == 200:
                t = r.json()
                synced = t.get('syncedLyrics') or ''
                parsed = lyric_worker.parse_lrc(synced)
                return jsonify({
                    'success': True,
                    'track': {
                        'name': t.get('trackName'),
                        'artist': t.get('artistName'),
                        'duration': t.get('duration'),
                        'lyrics': [{'t': p[0], 'l': p[1]} for p in parsed]
                    }
                })
        elif q:
            ok, name, parsed = lyric_worker.fetch_nct_lyrics(q)
            if ok:
                return jsonify({
                    'success': True,
                    'track': {
                        'name': name,
                        'lyrics': [{'t': p[0], 'l': p[1]} for p in parsed]
                    }
                })
        return jsonify({'success': False, 'message': 'Không tìm thấy bài hát hoặc lời bài hát'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
    
    # Tìm kiếm theo tên bài hát và tự phát đồng bộ theo thời gian bài hát
    song_name = data.get('song', '').strip()
    emoji = data.get('emoji', '🎵').strip()
    if song_name:
        ok, title, lyrics = lyric_worker.fetch_nct_lyrics(song_name)
        if not ok:
            return jsonify({'success': False, 'message': title}), 400
        lyric_worker.start_lyric_stream(user_id, token, lyrics, emoji=emoji)
        return jsonify({'success': True, 'message': f'Đang phát: {title} ({len(lyrics)} câu)'})

    # Cập nhật một câu status tùy chỉnh (hỗ trợ cả 'status' và 'text')
    text = (data.get('text') or data.get('status') or '').strip()
    if text:
        ok, msg = lyric_worker.update_lyric(token, text, emoji=emoji)
        return jsonify({'success': ok, 'message': msg})
    return jsonify({'success': False, 'message': 'Nội dung câu hát trống'}), 400

@app.route('/api/lyrics/clear', methods=['POST'])
@login_required
def api_lyrics_clear():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')

    lyric_worker.stop_lyric_stream(user_id)
    if not token:
        return jsonify({'success': False, 'message': 'Tài khoản chưa liên kết Discord Token!'}), 400

    ok, msg = lyric_worker.clear_lyric(token)
    return jsonify({'success': ok, 'message': msg})

ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg', 'flac', 'webm'}
_STT_MODEL = None
_STT_MODEL_LOCK = threading.Lock()

def _get_stt_model():
    """Lazy-load faster-whisper model (chi tai 1 lan, dung chung cho ca app)."""
    global _STT_MODEL
    with _STT_MODEL_LOCK:
        if _STT_MODEL is None:
            from faster_whisper import WhisperModel
            model_size = os.environ.get('STT_MODEL_SIZE', 'base')
            _STT_MODEL = WhisperModel(model_size, device='cpu', compute_type='int8')
        return _STT_MODEL

def _format_lrc_timestamp(seconds: float) -> str:
    seconds = max(0, seconds)
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f'[{m:02d}:{s:02d}]'

@app.route('/api/lyrics/transcribe', methods=['POST'])
@login_required
def api_lyrics_transcribe():
    """Nhan file am thanh, dung faster-whisper de tu dong nhan dien loi bai hat -> LRC."""
    if 'audio' not in request.files:
        return jsonify({'success': False, 'message': 'Không tìm thấy file âm thanh'}), 400
    file = request.files['audio']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'Chưa chọn file âm thanh nào'}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify({'success': False, 'message': 'Định dạng không hỗ trợ (mp3, wav, m4a, ogg, flac)'}), 400

    tmp_name = f'{uuid.uuid4().hex}.{ext}'
    tmp_path = os.path.join(UPLOAD_FOLDER, tmp_name)
    file.save(tmp_path)
    try:
        try:
            model = _get_stt_model()
        except ImportError:
            return jsonify({
                'success': False,
                'message': 'Chưa cài thư viện nhận diện giọng nói. Chạy: pip install faster-whisper'
            }), 500

        segments, _info = model.transcribe(tmp_path, task='transcribe', vad_filter=True)
        lines = []
        count = 0
        for seg in segments:
            text = (seg.text or '').strip()
            if not text:
                continue
            lines.append(f'{_format_lrc_timestamp(seg.start)} {text}')
            count += 1

        if not lines:
            return jsonify({'success': False, 'message': 'Không nhận diện được lời bài hát nào từ file này.'}), 200

        lrc_text = '\n'.join(lines)
        quest_log(f'🎤 STT: đã tạo {count} dòng lời từ file {file.filename}', 'info')
        return jsonify({'success': True, 'lrc': lrc_text, 'segments': count})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi khi nhận diện: {e}'}), 500
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

@app.route('/api/status', methods=['GET'])
@login_required
def api_status():
    return jsonify(rpc_worker.get_status_data())

@app.route('/api/start', methods=['POST'])
@login_required
def api_start():
    raw_data = request.get_json() or {}
    data = normalize_rpc_config(raw_data)
    token = data.get('token', '').strip()
    if not token:
        user_id = session.get('user_id')
        if user_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                if row and row['discord_token']:
                    token = row['discord_token']
        if not token and 'discord_token' in session:
            token = session['discord_token']
    if not token:
        return (jsonify({'success': False, 'message': 'Chưa có token. Vui lòng liên kết Discord Token tại mục Quản Lý Tài Khoản trước!'}), 400)
    data['token'] = token
    activity_name = data.get('activityName', '').strip()
    if not activity_name:
        data['activityName'] = 'Visual Studio Code'
    rpc_worker.start(data)
    log_event(f'Khởi động Discord RPC: {data["activityName"]}', 'success')
    return jsonify({'success': True, 'message': 'Đã gửi lệnh kết nối tới Discord Gateway'})

@app.route('/api/update', methods=['POST'])
@login_required
def api_update():
    raw_data = request.get_json() or {}
    data = normalize_rpc_config(raw_data)
    token = data.get('token', '').strip()
    if not token:
        user_id = session.get('user_id')
        if user_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                if row and row['discord_token']:
                    token = row['discord_token']
        if not token and 'discord_token' in session:
            token = session['discord_token']
    if token:
        data['token'] = token
    activity_name = data.get('activityName', '').strip()
    if not activity_name:
        data['activityName'] = 'Visual Studio Code'
    try:
        rpc_worker.update_presence(data)
        log_event(f'Cập nhật Discord RPC: {data["activityName"]}', 'info')
        return jsonify({'success': True, 'message': 'Đã cập nhật trạng thái Discord thành công!'})
    except Exception as e:
        return (jsonify({'success': False, 'message': f'Lỗi khi cập nhật: {str(e)}'}), 500)

@app.route('/api/save_config', methods=['POST'])
@login_required
def api_save_config():
    user_id = session['user_id']
    data = request.get_json() or {}
    cfg = normalize_rpc_config(data)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET config = ? WHERE id = ?', (json.dumps(cfg), user_id))
        conn.commit()
    log_event('Đã lưu cấu hình RPC thành công', 'success')
    return jsonify({'success': True, 'message': 'Đã lưu cấu hình thành công!'})

@app.route('/api/get_config', methods=['GET'])
@login_required
def api_get_config():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT config FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    cfg_raw = (row['config'] if row and row['config'] else '')
    if cfg_raw:
        try:
            return jsonify({'success': True, 'config': json.loads(cfg_raw)})
        except Exception:
            pass
    return jsonify({'success': True, 'config': None})

@app.route('/api/stop', methods=['POST'])
@login_required
def api_stop():
    rpc_worker.stop()
    return jsonify({'success': True, 'message': 'Đã dừng Discord RPC'})

@app.route('/bot_avatar')
def serve_bot_avatar():
    return redirect('https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg')

@app.route('/api/portal_app_info', methods=['GET', 'POST'])
@login_required
def api_portal_app_info():
    token = ''
    if request.is_json:
        data = request.get_json() or {}
        token = data.get('token', '').strip()
    if not token:
        token = request.args.get('token', '').strip()
    if not token:
        user_id = session.get('user_id')
        if user_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                if row and row['discord_token']:
                    token = row['discord_token']
    if not token and 'discord_token' in session:
        token = session['discord_token']
    if not token and rpc_worker and rpc_worker.current_config:
        token = rpc_worker.current_config.get('token', '').strip()
    if not token:
        return (jsonify({'success': True, 'apps': [], 'message': 'Chưa liên kết Discord Token tại mục Tài Khoản'}), 200)
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
