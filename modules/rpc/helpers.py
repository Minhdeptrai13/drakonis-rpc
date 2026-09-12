from core.config import ALLOWED_EXTENSIONS

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalize_rpc_config(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    out = dict(data)
    
    # Map snake_case to camelCase
    if 'name' in data and not data.get('activityName'):
        out['activityName'] = data['name']
    if 'activity_name' in data and not data.get('activityName'):
        out['activityName'] = data['activity_name']
    if not out.get('activityName'):
        out['activityName'] = 'Visual Studio Code'
        
    if 'activity_type' in data and not data.get('activityType'):
        out['activityType'] = data['activity_type']
    if 'stream_url' in data and not data.get('streamUrl'):
        out['streamUrl'] = data['stream_url']
    if 'large_image' in data and not data.get('largeImage'):
        out['largeImage'] = data['large_image']
    if 'small_image' in data and not data.get('smallImage'):
        out['smallImage'] = data['small_image']
    if 'large_text' in data and not data.get('largeText'):
        out['largeText'] = data['large_text']
    if 'small_text' in data and not data.get('smallText'):
        out['smallText'] = data['small_text']
    if 'app_id' in data and not data.get('appId'):
        out['appId'] = data['app_id']
    if 'use_timestamp' in data and not data.get('hasTimestamp'):
        out['hasTimestamp'] = bool(data['use_timestamp'])
        
    # Buttons
    buttons = data.get('buttons', [])
    if isinstance(buttons, list) and len(buttons) > 0:
        if len(buttons) >= 1 and isinstance(buttons[0], dict):
            out['btn1Label'] = buttons[0].get('label', '')
            out['btn1Url'] = buttons[0].get('url', '')
        if len(buttons) >= 2 and isinstance(buttons[1], dict):
            out['btn2Label'] = buttons[1].get('label', '')
            out['btn2Url'] = buttons[1].get('url', '')
            
    return out
