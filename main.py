import os
import sys
import time
import threading
import webbrowser
from flask import Flask

# 1. Nạp Core Framework & Cấu hình
from core.config import (
    BASE_DIR,
    UPLOAD_FOLDER,
    SECRET_KEY
)
from core.database import init_db
from core.security import init_security
from core.logger import log_event

# 2. Nạp Modules chức năng (tự động đăng ký vào Core Registry)
from modules import registry

def create_app() -> Flask:
    """Application Factory: Khởi tạo và liên kết các thành phần hệ thống"""
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Khởi tạo cơ sở dữ liệu SQLite & tự động migration
    init_db()

    # Kích hoạt tường lửa bảo mật DIPRE Cyber Shield & Anti-DDoS
    init_security(app)

    # Nạp toàn bộ các Blueprint và route từ Core Registry
    registry.bind_to_app(app)

    # Hỗ trợ Reverse Proxy (Render, Cloudflare, Nginx) để nhận diện đúng HTTPS
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    except Exception:
        pass

    log_event('Hệ thống Discord RPC Master (Modular Architecture) đã sẵn sàng hoạt động.', 'info')
    return app

app = create_app()

def open_browser(port: int):
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
    print('      DISCORD RICH PRESENCE MASTER (Modular Engine)      ')
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
        registry.shutdown_all()
        sys.exit(0)
