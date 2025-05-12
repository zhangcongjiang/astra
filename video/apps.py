from django.apps import AppConfig
import importlib
import pkgutil

class VideoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'video'
    def ready(self):
        package_name = 'video'
        package = importlib.import_module(package_name)
        modules = pkgutil.walk_packages(package.__path__, package.__name__ + '.')

        for module_info in modules:
            # 导入模块
            importlib.import_module(module_info.name)
