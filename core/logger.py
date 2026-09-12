import time
import threading
from typing import List, Dict, Any

LOG_BUFFER: List[Dict[str, Any]] = []
MAX_LOG_ENTRIES = 120

QUEST_LOG_BUFFER: List[Dict[str, Any]] = []
QUEST_LOG_LOCK = threading.Lock()
MAX_QUEST_LOG_ENTRIES = 200

def log_event(message: str, level: str = 'info'):
    """Ghi log hệ thống cho Discord RPC Master"""
    timestamp = time.strftime('%H:%M:%S')
    entry = {'time': timestamp, 'message': str(message), 'level': level}
    LOG_BUFFER.append(entry)
    if len(LOG_BUFFER) > MAX_LOG_ENTRIES:
        LOG_BUFFER.pop(0)
    print(f'[{timestamp}] [{level.upper()}] {message}')

def quest_log(message: str, level: str = 'info'):
    """Ghi log cho tiến trình Auto Quest Discord"""
    timestamp = time.strftime('%H:%M:%S')
    entry = {'time': timestamp, 'message': str(message), 'level': level}
    with QUEST_LOG_LOCK:
        QUEST_LOG_BUFFER.append(entry)
        if len(QUEST_LOG_BUFFER) > MAX_QUEST_LOG_ENTRIES:
            QUEST_LOG_BUFFER.pop(0)
    print(f'[QUEST][{timestamp}] [{level.upper()}] {message}')
