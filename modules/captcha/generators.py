import io
import time
import uuid
import math
import random
import base64
import hashlib
import requests
from flask import session
from PIL import Image, ImageDraw

def generate_turnstile_captcha():
    """Cấp 1: Captcha một chạm thông minh phong cách Cloudflare Turnstile"""
    challenge_token = hashlib.sha256(f"{uuid.uuid4()}-{time.time()}-DIPRE".encode()).hexdigest()[:32]
    session['turnstile_token'] = challenge_token
    session['turnstile_issued_at'] = time.time()
    session['captcha_level'] = 1
    session['captcha_verified'] = False
    return {
        'level': 1,
        'type': 'turnstile',
        'challenge': challenge_token,
        'title': 'Xác thực một chạm bảo mật DIPRE Shield',
        'prompt': 'Tôi là con người'
    }

def generate_slide_captcha():
    """Cấp 2: Captcha trượt TikTok-style mảnh ghép puzzle khuyết"""
    width, height = 320, 160
    piece_w, piece_h = 46, 46

    bg_img = None
    try:
        urls = [
            'https://picsum.photos/320/160?random=' + str(random.randint(1, 9999)),
            'https://picsum.photos/320/160'
        ]
        url = random.choice(urls)
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            bg_img = Image.open(io.BytesIO(res.content)).convert('RGBA')
            if bg_img.size != (width, height):
                bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
    except Exception:
        bg_img = None

    if bg_img is None:
        bg_img = Image.new('RGBA', (width, height), (10, 12, 20, 255))
        draw = ImageDraw.Draw(bg_img)
        for y in range(height):
            r = int(12 + (30 - 12) * (y / height))
            g = int(15 + (20 - 15) * (y / height))
            b = int(28 + (65 - 28) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        for i in range(0, width, 24):
            draw.line([(i, 0), (i, height)], fill=(99, 102, 241, 35), width=1)
        for j in range(0, height, 20):
            draw.line([(0, j), (width, j)], fill=(6, 182, 212, 35), width=1)
        for _ in range(7):
            cx = random.randint(30, width - 30)
            cy = random.randint(20, height - 20)
            rad = random.randint(20, 40)
            draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(147, 51, 234, 90), width=2)
            draw.text((cx - 15, cy - 8), "DIPRE", fill=(56, 189, 248, 140))

    target_x = random.randint(85, width - piece_w - 20)
    target_y = random.randint(15, height - piece_h - 15)

    session['slide_target_x'] = target_x
    session['slide_target_y'] = target_y
    session['captcha_level'] = 2
    session['captcha_verified'] = False
    session['slide_verified'] = False

    mask = Image.new('L', (piece_w, piece_h), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.rounded_rectangle([0, 0, piece_w - 1, piece_h - 1], radius=8, fill=255)

    crop = bg_img.crop((target_x, target_y, target_x + piece_w, target_y + piece_h))
    piece_img = Image.new('RGBA', (piece_w, piece_h), (0, 0, 0, 0))
    piece_img.paste(crop, (0, 0), mask)

    p_draw = ImageDraw.Draw(piece_img)
    p_draw.rounded_rectangle([0, 0, piece_w - 1, piece_h - 1], radius=8, outline=(129, 140, 248, 255), width=2)

    hole = Image.new('RGBA', (piece_w, piece_h), (0, 0, 0, 220))
    bg_img.paste(hole, (target_x, target_y), mask)
    bg_draw = ImageDraw.Draw(bg_img)
    bg_draw.rounded_rectangle([target_x, target_y, target_x + piece_w - 1, target_y + piece_h - 1], radius=8, outline=(255, 255, 255, 190), width=2)

    bg_buffer = io.BytesIO()
    bg_img.convert('RGB').save(bg_buffer, format='JPEG', quality=88)
    bg_base64 = base64.b64encode(bg_buffer.getvalue()).decode('utf-8')

    piece_buffer = io.BytesIO()
    piece_img.save(piece_buffer, format='PNG')
    piece_base64 = base64.b64encode(piece_buffer.getvalue()).decode('utf-8')

    return {
        'level': 2,
        'type': 'slide',
        'bg_image': f"data:image/jpeg;base64,{bg_base64}",
        'piece_image': f"data:image/png;base64,{piece_base64}",
        'target_y': target_y,
        'piece_width': piece_w,
        'piece_height': piece_h,
        'bg_width': width,
        'bg_height': height,
        'prompt': 'Kéo thanh trượt để khớp mảnh ghép puzzle'
    }

def generate_circle_rotation_captcha():
    """Cấp 3: Captcha xoay vòng tròn đồng tâm khớp hình phong cách TikTok / Arkose Labs"""
    size = 260
    center = size // 2
    inner_radius = 70
    outer_radius = 120

    base_img = None
    try:
        url = 'https://picsum.photos/260/260?random=' + str(random.randint(1000, 9999))
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            base_img = Image.open(io.BytesIO(res.content)).convert('RGBA')
            if base_img.size != (size, size):
                base_img = base_img.resize((size, size), Image.Resampling.LANCZOS)
    except Exception:
        base_img = None

    if base_img is None:
        base_img = Image.new('RGBA', (size, size), (8, 10, 18, 255))
        draw = ImageDraw.Draw(base_img)
        for r in range(outer_radius, 20, -15):
            col = (int(90 + 160 * (r / outer_radius)), int(40 + 80 * (r / outer_radius)), 245, 255)
            draw.ellipse([center - r, center - r, center + r, center + r], outline=col, width=3)
        for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
            rad = math.radians(angle)
            x2 = center + int(outer_radius * math.cos(rad))
            y2 = center + int(outer_radius * math.sin(rad))
            draw.line([(center, center), (x2, y2)], fill=(56, 189, 248, 220), width=4)
        draw.regular_polygon((center, center, 42), 6, fill=(147, 51, 234, 210), outline=(255, 255, 255, 255))
        draw.text((center - 25, center - 8), "DIPRE", fill=(255, 255, 255, 255))

    secret_angle = random.choice([50, 75, 90, 120, 145, 180, 210, 240, 270, 295])
    session['rotate_target_angle'] = secret_angle
    session['captcha_level'] = 3
    session['captcha_verified'] = False

    inner_mask = Image.new('L', (size, size), 0)
    m_draw = ImageDraw.Draw(inner_mask)
    m_draw.ellipse([center - inner_radius, center - inner_radius, center + inner_radius, center + inner_radius], fill=255)

    inner_crop = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    inner_crop.paste(base_img, (0, 0), inner_mask)

    initial_rotated_inner = inner_crop.rotate(secret_angle, resample=Image.Resampling.BICUBIC, center=(center, center))

    outer_img = base_img.copy()
    o_draw = ImageDraw.Draw(outer_img)
    o_draw.ellipse([center - inner_radius, center - inner_radius, center + inner_radius, center + inner_radius], outline=(147, 51, 234, 255), width=3)
    o_draw.ellipse([center - outer_radius, center - outer_radius, center + outer_radius, center + outer_radius], outline=(6, 182, 212, 255), width=2)

    outer_mask = Image.eval(inner_mask, lambda a: 255 - a)
    outer_final = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    outer_final.paste(outer_img, (0, 0), outer_mask)

    buf_outer = io.BytesIO()
    outer_final.save(buf_outer, format='PNG')
    outer_b64 = base64.b64encode(buf_outer.getvalue()).decode('utf-8')

    buf_inner = io.BytesIO()
    initial_rotated_inner.save(buf_inner, format='PNG')
    inner_b64 = base64.b64encode(buf_inner.getvalue()).decode('utf-8')

    return {
        'level': 3,
        'type': 'rotate',
        'outer_image': f"data:image/png;base64,{outer_b64}",
        'inner_image': f"data:image/png;base64,{inner_b64}",
        'initial_angle': secret_angle,
        'size': size,
        'inner_radius': inner_radius,
        'prompt': 'Xoay vòng tròn đồng tâm sao cho hình ảnh khớp hoàn toàn'
    }
