import uuid
import requests
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash

from core.database import get_db
from core.logger import log_event
from core.security import clear_failed_attempts, get_client_ip
from core.registry import registry, SubModule
from modules.auth.helpers import login_required
from modules.account.services import fetch_discord_profile

account_bp = Blueprint('account', __name__)

@account_bp.route('/api/account/quick_oauth', methods=['POST'])
def api_account_quick_oauth():
    """Hỗ trợ đăng nhập nhanh bằng tài khoản Discord / Google"""
    data = request.get_json() or {}
    provider = data.get('provider')
    username = data.get('username', '').strip()
    
    if not username:
        username = 'User_' + uuid.uuid4().hex[:6]

    with get_db() as conn:
        cursor = conn.cursor()
        if provider == 'discord':
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
            log_event(f'Đăng nhập tài khoản qua Discord OAuth2: {username}', 'success')
            return jsonify({'success': True, 'message': f'Chào mừng {username}!'})

        elif provider == 'google':
            email = data.get('email', '').strip()
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
            log_event(f'Đăng nhập tài khoản qua Google OAuth2: {username} ({email})', 'success')
            return jsonify({'success': True, 'message': f'Chào mừng {username}!'})

        else:
            return jsonify({'success': False, 'message': 'Phương thức đăng nhập không hợp lệ'}), 400

@account_bp.route('/api/account/info', methods=['GET'])
@login_required
def api_account_info():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, discord_token, discord_id, discord_username, discord_avatar FROM users WHERE id = ?', (user_id,))
        u = cursor.fetchone()
        cursor.execute('SELECT * FROM discord_accounts WHERE user_id = ? ORDER BY is_active DESC, id DESC', (user_id,))
        accounts = [dict(r) for r in cursor.fetchall()]
    if not u:
        return jsonify({'success': False, 'message': 'Không tìm thấy tài khoản'}), 404
    token = u['discord_token'] or ''
    has_token = bool(token and len(token) > 20)
    masked = (token[:10] + '...' + token[-6:]) if has_token else ''

    active_acc = next((a for a in accounts if a.get('is_active') == 1), None) or (accounts[0] if accounts else None)

    return jsonify({
        'success': True,
        'username': u['username'],
        'has_token': has_token,
        'discord_id': u['discord_id'] or (active_acc['discord_id'] if active_acc else ''),
        'discord_username': u['discord_username'] or (active_acc['discord_username'] if active_acc else ''),
        'discord_avatar': u['discord_avatar'] or (active_acc['discord_avatar'] if active_acc else ''),
        'avatar_decoration': (active_acc.get('avatar_decoration') if active_acc else '') or '',
        'banner': (active_acc.get('banner') if active_acc else '') or '',
        'masked_token': masked,
        'accounts': accounts
    })

@account_bp.route('/api/account/bind_token', methods=['POST'])
@login_required
def api_account_bind_token():
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    if not token:
        return jsonify({'success': False, 'message': 'Vui lòng cung cấp Discord User Token'}), 400
    try:
        profile = fetch_discord_profile(token)
        if not profile:
            return jsonify({'success': False, 'message': 'Token Discord không hợp lệ hoặc đã hết hạn.'}), 400

        user_id = session['user_id']
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET discord_token = ?, discord_id = ?, discord_username = ?, discord_avatar = ? WHERE id = ?',
                           (token, profile['id'], profile['username'], profile['avatar'], user_id))
            
            cursor.execute('UPDATE discord_accounts SET is_active = 0 WHERE user_id = ?', (user_id,))
            cursor.execute('SELECT id FROM discord_accounts WHERE user_id = ? AND token = ?', (user_id, token))
            existing = cursor.fetchone()
            if existing:
                cursor.execute('''
                    UPDATE discord_accounts
                    SET discord_id = ?, discord_username = ?, discord_avatar = ?, avatar_decoration = ?, banner = ?, is_active = 1
                    WHERE id = ?
                ''', (profile['id'], profile['username'], profile['avatar'], profile['decoration'], profile['banner'], existing['id']))
            else:
                cursor.execute('''
                    INSERT INTO discord_accounts (user_id, token, discord_id, discord_username, discord_avatar, avatar_decoration, banner, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ''', (user_id, token, profile['id'], profile['username'], profile['avatar'], profile['decoration'], profile['banner']))
            conn.commit()

        session['discord_token'] = token
        session['discord_username'] = profile['username']
        session['discord_avatar'] = profile['avatar']
        log_event(f'Tài khoản {session.get("username")} đã kết nối Discord: {profile["username"]} ({profile["id"]})', 'success')
        return jsonify({
            'success': True,
            'message': f'Đã liên kết thành công với: {profile["username"]}!',
            'username': profile['username'],
            'avatar': profile['avatar'],
            'discord_id': profile['id'],
            'discord_username': profile['username'],
            'discord_avatar': profile['avatar'],
            'avatar_decoration': profile['decoration'],
            'banner': profile['banner']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi kết nối xác minh Discord: {str(e)}'}), 500

@account_bp.route('/api/accounts/list', methods=['GET'])
@login_required
def api_accounts_list():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, discord_id, discord_username, discord_avatar, avatar_decoration, banner, is_active, created_at FROM discord_accounts WHERE user_id = ? ORDER BY is_active DESC, id DESC', (user_id,))
        accounts = [dict(r) for r in cursor.fetchall()]
    return jsonify({'success': True, 'accounts': accounts})

@account_bp.route('/api/accounts/switch', methods=['POST'])
@login_required
def api_accounts_switch():
    user_id = session['user_id']
    data = request.get_json() or {}
    account_id = data.get('account_id')
    if not account_id:
        return jsonify({'success': False, 'message': 'Thiếu account_id'}), 400
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM discord_accounts WHERE id = ? AND user_id = ?', (account_id, user_id))
        target = cursor.fetchone()
        if not target:
            return jsonify({'success': False, 'message': 'Không tìm thấy tài khoản này'}), 404

        cursor.execute('UPDATE discord_accounts SET is_active = 0 WHERE user_id = ?', (user_id,))
        cursor.execute('UPDATE discord_accounts SET is_active = 1 WHERE id = ?', (account_id,))
        cursor.execute('UPDATE users SET discord_token = ?, discord_id = ?, discord_username = ?, discord_avatar = ? WHERE id = ?',
                       (target['token'], target['discord_id'], target['discord_username'], target['discord_avatar'], user_id))
        conn.commit()

    session['discord_token'] = target['token']
    session['discord_username'] = target['discord_username']
    session['discord_avatar'] = target['discord_avatar']
    log_event(f'Đã chuyển sang tài khoản Discord: {target["discord_username"]}', 'info')
    return jsonify({
        'success': True,
        'message': f'Đã chuyển sang: {target["discord_username"]}',
        'username': target['discord_username'],
        'avatar': target['discord_avatar'],
        'discord_id': target['discord_id'],
        'discord_username': target['discord_username'],
        'discord_avatar': target['discord_avatar'],
        'avatar_decoration': target['avatar_decoration'],
        'banner': target['banner']
    })

@account_bp.route('/api/accounts/delete', methods=['POST'])
@login_required
def api_accounts_delete():
    user_id = session['user_id']
    data = request.get_json() or {}
    account_id = data.get('account_id')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_active FROM discord_accounts WHERE id = ? AND user_id = ?', (account_id, user_id))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy tài khoản'}), 404
        was_active = row['is_active'] == 1
        cursor.execute('DELETE FROM discord_accounts WHERE id = ? AND user_id = ?', (account_id, user_id))
        
        if was_active:
            cursor.execute('SELECT * FROM discord_accounts WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
            next_acc = cursor.fetchone()
            if next_acc:
                cursor.execute('UPDATE discord_accounts SET is_active = 1 WHERE id = ?', (next_acc['id'],))
                cursor.execute('UPDATE users SET discord_token = ?, discord_id = ?, discord_username = ?, discord_avatar = ? WHERE id = ?',
                               (next_acc['token'], next_acc['discord_id'], next_acc['discord_username'], next_acc['discord_avatar'], user_id))
                session['discord_token'] = next_acc['token']
                session['discord_username'] = next_acc['discord_username']
                session['discord_avatar'] = next_acc['discord_avatar']
            else:
                cursor.execute('UPDATE users SET discord_token = "", discord_id = "", discord_username = "", discord_avatar = "" WHERE id = ?', (user_id,))
                session.pop('discord_token', None)
                session.pop('discord_username', None)
                session.pop('discord_avatar', None)
        conn.commit()
    return jsonify({'success': True, 'message': 'Đã xóa tài khoản khỏi danh sách'})

@account_bp.route('/api/account/unbind_token', methods=['POST'])
@login_required
def api_account_unbind_token():
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET discord_token = "", discord_id = "", discord_username = "", discord_avatar = "" WHERE id = ?', (user_id,))
        cursor.execute('UPDATE discord_accounts SET is_active = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
    session.pop('discord_token', None)
    session.pop('discord_username', None)
    session.pop('discord_avatar', None)
    log_event(f'Đã hủy liên kết Discord Token cho tài khoản {session.get("username")}', 'info')
    return jsonify({'success': True, 'message': 'Đã hủy liên kết token thành công'})

@account_bp.route('/api/discord/inbox', methods=['GET'])
@login_required
def api_discord_inbox():
    """Đọc hòm thư / tin nhắn chưa đọc & kênh gần nhất của token active"""
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT discord_token FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
    token = (row['discord_token'] if row else '') or session.get('discord_token', '')
    if not token:
        return jsonify({'success': False, 'message': 'Chưa liên kết token Discord'}), 400
    try:
        headers = {
            'Authorization': token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get('https://discord.com/api/v9/users/@me/channels', headers=headers, timeout=8)
        if res.status_code == 200:
            channels = res.json()
            formatted = []
            for ch in channels[:15]:
                recipients = ch.get('recipients', [])
                name = ', '.join([r.get('global_name') or r.get('username', '') for r in recipients]) if recipients else 'Direct Message'
                last_msg_id = ch.get('last_message_id')
                avatar = ''
                if recipients:
                    r0 = recipients[0]
                    av_hash = r0.get('avatar')
                    avatar = f"https://cdn.discordapp.com/avatars/{r0['id']}/{av_hash}.png?size=64" if av_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
                formatted.append({
                    'id': ch.get('id'),
                    'name': name or 'DM',
                    'avatar': avatar,
                    'last_message_id': last_msg_id,
                    'type': ch.get('type')
                })
            return jsonify({'success': True, 'channels': formatted})
        else:
            return jsonify({'success': False, 'message': f'Lỗi Discord API ({res.status_code})'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Đăng ký tiểu mục Multi-Account vào Mục Lớn Account trong Core Registry
registry.register_module(SubModule(
    key='multi_account',
    category_key='account',
    title='Multi-Token Account Manager & Inbox',
    blueprint=account_bp
))
