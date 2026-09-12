import time
import threading
from typing import Dict, List
from flask import Flask, request, jsonify, session, redirect, url_for, flash
from core.logger import log_event
from core.database import get_db

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

def init_security(app: Flask):
    """Gắn middleware bảo mật firewall và security headers vào Flask app"""

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
                session.clear()
                if request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'session_expired': True,
                        'message': 'Cơ sở dữ liệu đã được làm mới. Vui lòng đăng nhập lại.'
                    }), 401
                elif request.path not in ['/login', '/register', '/static/']:
                    flash('Cơ sở dữ liệu đã được cập nhật hoặc phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'warning')
                    return redirect(url_for('auth.login'))

    @app.after_request
    def dipre_security_headers(response):
        """Gắn các Security Headers chuẩn OWASP chống XSS, Clickjacking, MIME sniffing"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
