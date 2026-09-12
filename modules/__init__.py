"""
Package chứa toàn bộ các Modules Chức Năng của DiscordRPG.
Khi import package này, tất cả các SubModules sẽ tự động đăng ký vào Core Registry.
"""
from core.registry import registry

# Nạp các Mục Lớn vào Registry
registry.register_category('account', 'Quản Lý Tài Khoản & Bảo Mật', 'Xác thực người dùng, OAuth2 và quản lý đa token Discord')
registry.register_category('security', 'Bảo Mật Hệ Thống & Captcha', 'Lớp chắn bảo mật DIPRE Cyber Shield và cơ chế Captcha 3 cấp')
registry.register_category('rpc', 'Discord Rich Presence', 'Tùy biến trạng thái hoạt động Rich Presence Discord siêu cấp')
registry.register_category('quest', 'Discord Auto Quest', 'Tự động quét, nhận và cày hoàn thành nhiệm vụ Discord nhận quà')
registry.register_category('lyrics', 'Đồng Bộ Lời Bài Hát (Lyric Sync)', 'Đồng bộ lời bài hát NhacCuaTui / LRCLIB vào Custom Status Discord')

# Import các routes/modules để kích hoạt khai báo submodule vào các mục lớn
import modules.auth
import modules.account
import modules.captcha
import modules.rpc
import modules.quest
import modules.lyrics

__all__ = ['registry']
