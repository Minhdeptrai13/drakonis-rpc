import time
import requests
from flask import Blueprint, request, jsonify, session

from core.database import get_db
from core.logger import log_event, quest_log, QUEST_LOG_BUFFER, QUEST_LOG_LOCK
from core.registry import registry, SubModule
from modules.auth.helpers import login_required
from modules.quest.helpers import make_discord_headers, parse_discord_quest_item
from modules.quest.runner import get_user_quest_runner, stop_all_quest_runners

quest_bp = Blueprint('quest', __name__)

@quest_bp.route('/api/quests', methods=['GET'])
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

@quest_bp.route('/api/quests/enroll_all', methods=['POST'])
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

@quest_bp.route('/api/quests/start', methods=['POST'])
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

@quest_bp.route('/api/quests/stop', methods=['POST'])
@login_required
def api_quests_stop():
    user_id = session['user_id']
    runner = get_user_quest_runner(user_id)
    runner.stop()
    return jsonify({'success': True, 'message': 'Đã dừng tiến trình Auto Quest'})

@quest_bp.route('/api/quests/status', methods=['GET'])
@login_required
def api_quests_status():
    user_id = session['user_id']
    runner = get_user_quest_runner(user_id)
    return jsonify({'success': True, 'status': runner.get_status()})

@quest_bp.route('/api/quests/logs', methods=['GET', 'DELETE'])
@login_required
def api_quests_logs():
    if request.method == 'DELETE':
        with QUEST_LOG_LOCK:
            QUEST_LOG_BUFFER.clear()
        quest_log('Đã xóa nhật ký Quest Console.', 'info')
        return jsonify({'success': True, 'message': 'Đã xóa nhật ký'})
    with QUEST_LOG_LOCK:
        logs_copy = list(QUEST_LOG_BUFFER)
    return jsonify({'success': True, 'logs': logs_copy})

@quest_bp.route('/api/hypesquad/claim', methods=['POST'])
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

# Đăng ký tiểu mục Auto Quest vào Mục Lớn Quest trong Core Registry
registry.register_module(SubModule(
    key='auto_quest',
    category_key='quest',
    title='Discord Auto Quest Runner & HypeSquad claimer',
    blueprint=quest_bp,
    cleanup_handler=stop_all_quest_runners
))
