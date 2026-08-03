from django.apps import AppConfig


class ModelingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.modeling'
    verbose_name = '主数据建模'

    def ready(self):
        # 启动时扫描 tech_plugins/ 加载所有技术函数插件
        # 延迟导入避免循环依赖（plugin_loader 会导入 formula_engine）
        try:
            from . import plugin_loader
            plugin_loader.load_all_plugins()
        except Exception:
            # 启动阶段失败不阻断服务，记录日志
            import logging
            logging.getLogger(__name__).exception('加载技术函数插件失败')
