import os
import uuid
import sqlite3
import requests
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from core.database import get_db
from core.security import clear_failed_attempts, record_failed_attempt, get_client_ip
from core.config import CLOUDFLARE_TURNSTILE_SITE_KEY
from core.registry import registry, SubModule
from modules.auth.helpers import login_required
from modules.captcha.routes import verify_turnstile

auth_bp = Blueprint('auth', __name__)

DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET', '')

def get_discord_redirect_uri():
    return os.environ.get('DISCORD_REDIRECT_URI') or url_for('auth_discord_callback', _external=True)

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

def get_google_redirect_uri():
    return os.environ.get('GOOGLE_REDIRECT_URI') or url_for('auth_google_callback', _external=True)

@auth_bp.route('/')
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

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cf_token = request.form.get('cf-turnstile-response') or request.form.get('turnstile_token')
        client_ip = get_client_ip()
        is_verified = session.get('captcha_verified', False) or (cf_token and verify_turnstile(cf_token, client_ip))
        
        if not is_verified:
            flash('Vui lòng hoàn thành xác thực Cloudflare Turnstile trước khi đăng nhập.', 'error')
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
    return render_template('login.html', turnstile_site_key=CLOUDFLARE_TURNSTILE_SITE_KEY)

@auth_bp.route('/register', methods=['POST'])
def register():
    cf_token = request.form.get('cf-turnstile-response') or request.form.get('turnstile_token')
    client_ip = get_client_ip()
    is_verified = session.get('captcha_verified', False) or (cf_token and verify_turnstile(cf_token, client_ip))
    
    if not is_verified:
        flash('Vui lòng hoàn thành xác thực Cloudflare Turnstile trước khi đăng ký.', 'error')
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

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Đã đăng xuất thành công.', 'info')
    return redirect(url_for('login'))

@auth_bp.route('/auth/discord')
def auth_discord_redirect():
    redirect_uri = get_discord_redirect_uri()
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={requests.utils.quote(redirect_uri)}&response_type=code&scope=identify%20email"
    )
    return redirect(discord_auth_url)

@auth_bp.route('/auth/discord/callback')
def auth_discord_callback():
    code = request.args.get('code')
    if not code:
        flash('Xác thực Discord OAuth2 không thành công.', 'error')
        return redirect(url_for('login'))
    try:
        redirect_uri = get_discord_redirect_uri()
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers, timeout=10)
        tokens = r.json()
        access_token = tokens.get('access_token')
        if not access_token:
            flash('Không thể lấy Discord Access Token qua OAuth2.', 'error')
            return redirect(url_for('login'))

        u_res = requests.get('https://discord.com/api/users/@me', headers={'Authorization': f'Bearer {access_token}'}, timeout=8)
        u_data = u_res.json()
        d_id = str(u_data.get('id'))
        d_username = u_data.get('global_name') or u_data.get('username') or 'Discord User'
        avatar_hash = u_data.get('avatar')
        avatar_url = f"https://cdn.discordapp.com/avatars/{d_id}/{avatar_hash}.png?size=256" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE discord_id = ? OR username = ?', (d_id, d_username))
            user = cursor.fetchone()
            if not user:
                pwd_dummy = generate_password_hash(uuid.uuid4().hex)
                cursor.execute('INSERT INTO users (username, password_hash, discord_id, discord_username, discord_avatar) VALUES (?, ?, ?, ?, ?)',
                               (d_username, pwd_dummy, d_id, d_username, avatar_url))
                user_id = cursor.lastrowid
            else:
                user_id = user['id']
                cursor.execute('UPDATE users SET discord_id = ?, discord_username = ?, discord_avatar = ? WHERE id = ?',
                               (d_id, d_username, avatar_url, user_id))
            conn.commit()

        session['user_id'] = user_id
        session['username'] = d_username
        session['discord_username'] = d_username
        session['discord_avatar'] = avatar_url
        clear_failed_attempts(get_client_ip())
        flash(f'Đăng nhập Discord OAuth2 thành công! Chào mừng {d_username}.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Lỗi xử lý Discord OAuth2: {str(e)}', 'error')
        return redirect(url_for('login'))

@auth_bp.route('/auth/google')
def auth_google_redirect():
    redirect_uri = get_google_redirect_uri()
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={requests.utils.quote(redirect_uri)}&response_type=code&scope=openid%20profile%20email"
        f"&prompt=select_account"
    )
    return redirect(google_auth_url)

@auth_bp.route('/auth/google/callback')
def auth_google_callback():
    code = request.args.get('code')
    if not code:
        flash('Xác thực Google OAuth2 không thành công.', 'error')
        return redirect(url_for('login'))
    try:
        redirect_uri = get_google_redirect_uri()
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        tr = requests.post('https://oauth2.googleapis.com/token', data=token_data, timeout=10)
        tokens = tr.json()
        access_token = tokens.get('access_token')
        if not access_token:
            flash('Không thể lấy Access Token từ Google.', 'error')
            return redirect(url_for('login'))

        u_res = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers={'Authorization': f'Bearer {access_token}'}, timeout=8)
        u_data = u_res.json()
        email = u_data.get('email', '').strip()
        name = u_data.get('name') or (email.split('@')[0] if email else 'GoogleUser')

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (name,))
            user = cursor.fetchone()
            if not user:
                pwd_dummy = generate_password_hash(uuid.uuid4().hex)
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (name, pwd_dummy))
                user_id = cursor.lastrowid
            else:
                user_id = user['id']
            conn.commit()

        session['user_id'] = user_id
        session['username'] = name
        clear_failed_attempts(get_client_ip())
        flash(f'Đăng nhập Google thành công! Chào mừng {name}.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Lỗi xử lý Google OAuth2: {str(e)}', 'error')
        return redirect(url_for('login'))

@auth_bp.route('/auth/mock/<provider>')
def auth_oauth2_mock(provider):
    return render_template('oauth_mock.html', provider=provider)

@auth_bp.route('/auth/mock/confirm', methods=['POST'])
def auth_oauth2_mock_confirm():
    provider = request.form.get('provider', 'discord')
    username = request.form.get('username', '').strip() or ('DiscordUser' if provider == 'discord' else 'GoogleUser')
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if not user:
            pwd_dummy = generate_password_hash(uuid.uuid4().hex)
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, pwd_dummy))
            user_id = cursor.lastrowid
        else:
            user_id = user['id']
        conn.commit()

    session['user_id'] = user_id
    session['username'] = username
    clear_failed_attempts(get_client_ip())
    flash(f'Đăng nhập thành công qua {provider.capitalize()} OAuth2! Chào mừng {username}.', 'success')
    return redirect(url_for('index'))

def register_auth_endpoints(app):
    """Đăng ký các alias endpoints để tương thích hoàn toàn với url_for('login'), url_for('index'),... trong templates"""
    app.add_url_rule('/', endpoint='index', view_func=index)
    app.add_url_rule('/login', endpoint='login', view_func=login, methods=['GET', 'POST'])
    app.add_url_rule('/register', endpoint='register', view_func=register, methods=['POST'])
    app.add_url_rule('/logout', endpoint='logout', view_func=logout)
    app.add_url_rule('/auth/discord/callback', endpoint='auth_discord_callback', view_func=auth_discord_callback)
    app.add_url_rule('/auth/google/callback', endpoint='auth_google_callback', view_func=auth_google_callback)

# Đăng ký tiểu mục Auth vào Mục Lớn Account & Auth trong Core Registry
registry.register_module(SubModule(
    key='auth',
    category_key='account',
    title='Authentication & OAuth2 Engine',
    blueprint=auth_bp,
    init_handler=register_auth_endpoints
))
