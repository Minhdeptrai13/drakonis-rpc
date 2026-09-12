import os
import sys

# Đảm bảo UTF-8 encoding trên console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Monkey-patch cho discord.py-self để tránh lỗi đóng loop và cho phép tạo app bot
import discord.http

def _patched_create_app(self, name: str, team_id=None):
    payload = {'name': name}
    if team_id is not None:
        payload['team_id'] = team_id
    return self.request(discord.http.Route('POST', '/applications'), json=payload)

discord.http.HTTPClient.create_app = _patched_create_app

def _safe_http_del(self):
    pass

discord.http.HTTPClient.__del__ = _safe_http_del

# Cấu hình đường dẫn và hằng số
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV_PATH = os.path.join(BASE_DIR, '.env')

if os.path.exists(ENV_PATH):
    try:
        with open(ENV_PATH, 'r', encoding='utf-8') as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass

DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SECRET_KEY = os.environ.get('SECRET_KEY', 'discord_rpc_master_secret_key_fixed')

# CLOUDFLARE TURNSTILE CAPTCHA CONFIG (FREE 100%, BẢO MẬT KHÔNG GIỚI HẠN)
# Mặc định sử dụng Official Cloudflare Test Key (Always Passes) để dev/test tức thì
CLOUDFLARE_TURNSTILE_SITE_KEY = os.environ.get('CLOUDFLARE_TURNSTILE_SITE_KEY', '1x00000000000000000000AA')
CLOUDFLARE_TURNSTILE_SECRET_KEY = os.environ.get('CLOUDFLARE_TURNSTILE_SECRET_KEY', '1x0000000000000000000000000000000AA')

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
