import sqlite3
from core.config import DB_PATH

def get_db():
    """Mở kết nối SQLite với row_factory và chế độ WAL mode tối ưu tốc độ ghi"""
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def init_db():
    """Khởi tạo cấu trúc bảng và tự động migrate schema"""
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discord_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL,
                discord_id TEXT DEFAULT '',
                discord_username TEXT DEFAULT '',
                discord_avatar TEXT DEFAULT '',
                avatar_decoration TEXT DEFAULT '',
                banner TEXT DEFAULT '',
                custom_status TEXT DEFAULT '',
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Tự động migrate các cột cho bảng users
        cursor.execute("PRAGMA table_info(users)")
        cols = [r['name'] for r in cursor.fetchall()]
        for col_name in ['discord_token', 'discord_id', 'discord_username', 'discord_avatar', 'config']:
            if col_name not in cols:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} TEXT DEFAULT ''")
                except Exception:
                    pass

        # Tự động migrate các cột cho bảng discord_accounts
        cursor.execute("PRAGMA table_info(discord_accounts)")
        d_cols = [r['name'] for r in cursor.fetchall()]
        for col_name in ['avatar_decoration', 'banner', 'custom_status', 'is_active']:
            if col_name not in d_cols:
                try:
                    cursor.execute(f"ALTER TABLE discord_accounts ADD COLUMN {col_name} TEXT DEFAULT ''")
                except Exception:
                    pass

        # Tự động migrate token của user vào discord_accounts nếu chưa có
        cursor.execute("SELECT id, discord_token, discord_id, discord_username, discord_avatar FROM users WHERE discord_token != '' AND discord_token IS NOT NULL")
        for u in cursor.fetchall():
            cursor.execute("SELECT id FROM discord_accounts WHERE user_id = ? AND token = ?", (u['id'], u['discord_token']))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO discord_accounts (user_id, token, discord_id, discord_username, discord_avatar, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (u['id'], u['discord_token'], u['discord_id'], u['discord_username'], u['discord_avatar']))
        conn.commit()
