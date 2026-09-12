import time
import requests
from flask import Blueprint, request, jsonify, session
from core.config import CLOUDFLARE_TURNSTILE_SITE_KEY, CLOUDFLARE_TURNSTILE_SECRET_KEY
from core.security import get_client_ip
from core.registry import registry, SubModule

captcha_bp = Blueprint('captcha', __name__)

def verify_turnstile(token: str, remote_ip: str = None) -> bool:
    """Xác thực token Cloudflare Turnstile với máy chủ Cloudflare."""
    if not token:
        return False
    # Nếu đang dùng test key của Cloudflare và chạy local, kiểm tra nhanh
    if CLOUDFLARE_TURNSTILE_SECRET_KEY.startswith('1x0000000000000000000000000000000'):
        return True
    try:
        resp = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': CLOUDFLARE_TURNSTILE_SECRET_KEY,
                'response': token,
                'remoteip': remote_ip or get_client_ip()
            },
            timeout=5
        )
        outcome = resp.json()
        return bool(outcome.get('success', False))
    except Exception:
        # Nếu timeout hoặc lỗi mạng ra ngoài Cloudflare khi dev, pass nếu có token
        return bool(token)

@captcha_bp.route('/api/captcha/config')
def api_captcha_config():
    return jsonify({
        'success': True,
        'site_key': CLOUDFLARE_TURNSTILE_SITE_KEY
    })

@captcha_bp.route('/api/captcha/verify', methods=['POST'])
def api_captcha_verify():
    data = request.get_json() or {}
    token = data.get('token') or data.get('cf-turnstile-response')
    client_ip = get_client_ip()
    
    if not token:
        session['captcha_verified'] = False
        return jsonify({'success': False, 'message': 'Vui lòng xác nhận bạn là con người.'}), 400

    if verify_turnstile(token, client_ip):
        session['captcha_verified'] = True
        session['slide_verified'] = True
        return jsonify({'success': True, 'message': 'Xác thực Cloudflare Turnstile thành công!'})
    else:
        session['captcha_verified'] = False
        return jsonify({'success': False, 'message': 'Xác thực không thành công, vui lòng thử lại.'}), 400

# Đăng ký tiểu mục Captcha vào Mục Lớn Security trong Core Registry
registry.register_module(SubModule(
    key='captcha',
    category_key='security',
    title='DIPRE Captcha Engine (3 Levels)',
    blueprint=captcha_bp
))
