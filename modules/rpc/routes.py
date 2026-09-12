import os
import re
import json
import uuid
import requests
from flask import Blueprint, request, jsonify, session, redirect

from core.config import UPLOAD_FOLDER, UPLOAD_PATH_MAP
from core.database import get_db
from core.logger import log_event, LOG_BUFFER
from core.registry import registry, SubModule
from modules.auth.helpers import login_required
from modules.rpc.helpers import allowed_file, normalize_rpc_config
from modules.rpc.worker import rpc_worker

rpc_bp = Blueprint('rpc', __name__)

@rpc_bp.route('/api/youtube/meta', methods=['GET'])
@login_required
def api_youtube_meta():
    """Trích xuất ID, Thumbnail và Title của video YouTube từ link"""
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'message': 'Thiếu tham số url'}), 400
    video_id = None
    m = re.search(r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})', url)
    if m:
        video_id = m.group(1)
    if not video_id:
        return jsonify({'success': False, 'message': 'Không nhận diện được ID video YouTube'}), 400

    thumb = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    title = f"YouTube Video ({video_id})"
    try:
        r = requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json", timeout=5)
        if r.status_code == 200:
            title = r.json().get('title', title)
    except Exception:
        pass

    return jsonify({
        'success': True,
        'video_id': video_id,
        'title': title,
        'thumbnail': thumb,
        'watch_url': f"https://www.youtube.com/watch?v={video_id}"
    })

@rpc_bp.route('/api/status', methods=['GET'])
@login_required
def api_status():
    return jsonify(rpc_worker.get_status_data())

@rpc_bp.route('/api/start', methods=['POST'])
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

@rpc_bp.route('/api/update', methods=['POST'])
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

@rpc_bp.route('/api/save_config', methods=['POST'])
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

@rpc_bp.route('/api/get_config', methods=['GET'])
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

@rpc_bp.route('/api/stop', methods=['POST'])
@login_required
def api_stop():
    rpc_worker.stop()
    return jsonify({'success': True, 'message': 'Đã dừng Discord RPC'})

@rpc_bp.route('/bot_avatar')
def serve_bot_avatar():
    return redirect('https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vscode/vscode-original.svg')

@rpc_bp.route('/api/portal_app_info', methods=['GET', 'POST'])
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

@rpc_bp.route('/api/logs', methods=['GET', 'DELETE'])
@login_required
def api_logs():
    if request.method == 'DELETE':
        LOG_BUFFER.clear()
        log_event('Đã làm mới nhật ký bảng điều khiển.', 'info')
        return jsonify({'success': True, 'message': 'Đã xóa nhật ký'})
    return jsonify({'success': True, 'logs': LOG_BUFFER})

@rpc_bp.route('/api/upload', methods=['POST'])
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
        filepath = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(filepath)
        local_url = f'/static/uploads/{unique_name}'
        UPLOAD_PATH_MAP[unique_name] = filepath
        UPLOAD_PATH_MAP[local_url] = filepath
        UPLOAD_PATH_MAP[filepath] = filepath
        return jsonify({'success': True, 'filename': unique_name, 'url': local_url})
    return (jsonify({'success': False, 'message': 'Định dạng file không được hỗ trợ (chỉ chấp nhận PNG, JPG, GIF, WEBP)'}), 400)

@rpc_bp.route('/api/presets', methods=['GET', 'POST'])
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

@rpc_bp.route('/api/presets/<int:preset_id>', methods=['DELETE'])
@login_required
def api_delete_preset(preset_id):
    user_id = session['user_id']
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM presets WHERE id = ? AND user_id = ?', (preset_id, user_id))
        conn.commit()
    return jsonify({'success': True, 'message': 'Đã xóa Preset'})

# Đăng ký tiểu mục RPC vào Mục Lớn RPC trong Core Registry
registry.register_module(SubModule(
    key='rich_presence',
    category_key='rpc',
    title='Discord Rich Presence Master Engine',
    blueprint=rpc_bp,
    worker=rpc_worker,
    cleanup_handler=lambda: rpc_worker.stop()
))
