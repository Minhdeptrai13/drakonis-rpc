"""
Core Registry System (Trọng tâm kiến trúc Modular)
Nơi định nghĩa các Mục Lớn và cơ chế để các Mục Nhỏ (Modules con) gọi vào khai báo, đăng ký.
"""
from typing import Dict, List, Optional, Callable, Any
from flask import Flask, Blueprint

class MajorCategory:
    """Đại diện cho một Mục Lớn trong hệ thống (VD: RPC, Auto Quest, Lyric Sync, Auth & Accounts, Captcha)"""
    def __init__(self, key: str, title: str, description: str = ""):
        self.key = key
        self.title = title
        self.description = description
        self.submodules: Dict[str, 'SubModule'] = {}

    def register_submodule(self, submodule: 'SubModule'):
        self.submodules[submodule.key] = submodule
        return submodule

    def __repr__(self):
        return f"<MajorCategory '{self.key}': {len(self.submodules)} submodules>"


class SubModule:
    """Đại diện cho một Mục Nhỏ (Module chức năng) đăng ký vào Mục Lớn tương ứng"""
    def __init__(
        self,
        key: str,
        category_key: str,
        title: str,
        blueprint: Optional[Blueprint] = None,
        worker: Optional[Any] = None,
        init_handler: Optional[Callable[[Flask], None]] = None,
        cleanup_handler: Optional[Callable[[], None]] = None
    ):
        self.key = key
        self.category_key = category_key
        self.title = title
        self.blueprint = blueprint
        self.worker = worker
        self.init_handler = init_handler
        self.cleanup_handler = cleanup_handler


class CoreRegistry:
    """Hệ thống Quản lý và Điều phối Toàn Cục các Mục Lớn & Mục Nhỏ"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoreRegistry, cls).__new__(cls)
            cls._instance.categories: Dict[str, MajorCategory] = {}
            cls._instance._is_initialized = False
        return cls._instance

    def register_category(self, key: str, title: str, description: str = "") -> MajorCategory:
        """Khai báo một Mục Lớn vào hệ thống Core"""
        if key not in self.categories:
            self.categories[key] = MajorCategory(key, title, description)
        return self.categories[key]

    def register_module(self, submodule: SubModule) -> SubModule:
        """Một mục nhỏ gọi vào khai báo xin vào mục lớn tương ứng"""
        if submodule.category_key not in self.categories:
            # Tự động tạo mục lớn nếu chưa khai báo trước
            self.register_category(submodule.category_key, submodule.category_key.upper())
        
        category = self.categories[submodule.category_key]
        category.register_submodule(submodule)
        return submodule

    def get_category(self, key: str) -> Optional[MajorCategory]:
        return self.categories.get(key)

    def get_submodule(self, category_key: str, module_key: str) -> Optional[SubModule]:
        cat = self.get_category(category_key)
        if cat:
            return cat.submodules.get(module_key)
        return None

    def bind_to_app(self, app: Flask):
        """Kích hoạt và nạp tất cả các Blueprint cùng Init Handlers vào Flask App"""
        for cat_key, category in self.categories.items():
            for mod_key, sub in category.submodules.items():
                if sub.blueprint:
                    app.register_blueprint(sub.blueprint)
                if sub.init_handler:
                    try:
                        sub.init_handler(app)
                    except Exception as e:
                        print(f"[CoreRegistry] Lỗi khởi tạo submodule {mod_key}: {e}")
        self._is_initialized = True

    def shutdown_all(self):
        """Dừng an toàn tất cả các workers và dọn dẹp tài nguyên khi tắt server"""
        print("[CoreRegistry] Đang dọn dẹp tiến trình và dừng các workers...")
        for cat_key, category in self.categories.items():
            for mod_key, sub in category.submodules.items():
                if sub.cleanup_handler:
                    try:
                        sub.cleanup_handler()
                    except Exception as e:
                        print(f"[CoreRegistry] Lỗi dọn dẹp submodule {mod_key}: {e}")
                elif sub.worker and hasattr(sub.worker, 'stop'):
                    try:
                        sub.worker.stop()
                    except Exception as e:
                        print(f"[CoreRegistry] Lỗi dừng worker {mod_key}: {e}")


# Singleton Registry instance dùng chung toàn project
registry = CoreRegistry()
