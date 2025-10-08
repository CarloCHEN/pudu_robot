"""
API工厂 - 根据配置创建和管理API实例
"""

import logging
from typing import Optional, List
from .api_registry import api_registry
from .config_manager import config_manager
from .api_interface import RobotAPIInterface

logger = logging.getLogger(__name__)


class APIFactory:
    """API工厂类"""

    _instance = None
    _current_api = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_default_api(cls) -> RobotAPIInterface:
        """获取默认API实例"""
        if cls._current_api is None:
            cls._current_api = cls.create_api()
        return cls._current_api

    @classmethod
    def create_api(cls, api_name: Optional[str] = None) -> Optional[RobotAPIInterface]:
        """创建API实例"""
        if api_name is None:
            api_name = config_manager.get_optimal_api()

        if not config_manager.is_api_enabled(api_name):
            logger.warning(f"API {api_name} 未启用，尝试使用默认API")
            api_name = config_manager.get_default_api()

        if not api_registry.is_api_available(api_name):
            logger.error(f"API {api_name} 不可用")
            return None

        api_config = config_manager.get_api_config(api_name)
        instance = api_registry.create_adapter_instance(api_name, api_config.get('config', {}))

        if instance:
            logger.info(f"成功创建API实例: {api_name}")
        else:
            logger.error(f"创建API实例失败: {api_name}")

        return instance

    @classmethod
    def create_api_with_fallback(cls, preferred_apis: Optional[List[str]] = None) -> Optional[RobotAPIInterface]:
        """创建带故障转移的API实例"""
        if preferred_apis is None:
            preferred_apis = config_manager.get_enabled_apis()
            # 按优先级排序
            preferred_apis.sort(key=lambda x: config_manager.get_api_priority(x))

        for api_name in preferred_apis:
            try:
                instance = cls.create_api(api_name)
                if instance:
                    logger.info(f"使用API: {api_name}")
                    return instance
            except Exception as e:
                logger.warning(f"API {api_name} 创建失败: {e}")
                continue

        logger.error("所有API都创建失败")
        return None

    @classmethod
    def create_load_balanced_api(cls) -> Optional[RobotAPIInterface]:
        """创建负载均衡API实例（简单轮询）"""
        enabled_apis = config_manager.get_enabled_apis()
        if not enabled_apis:
            return cls.create_api()

        # 简单的轮询策略
        import random
        api_name = random.choice(enabled_apis)
        return cls.create_api(api_name)

    @classmethod
    def switch_api(cls, api_name: str) -> bool:
        """切换API"""
        if not config_manager.is_api_enabled(api_name):
            logger.error(f"无法切换到未启用的API: {api_name}")
            return False

        if not api_registry.is_api_available(api_name):
            logger.error(f"无法切换到不可用的API: {api_name}")
            return False

        try:
            cls._current_api = cls.create_api(api_name)
            logger.info(f"成功切换到API: {api_name}")
            return True
        except Exception as e:
            logger.error(f"切换API失败: {e}")
            return False

    @classmethod
    def get_available_apis(cls) -> List[str]:
        """获取可用的API列表"""
        return api_registry.list_available_apis()

    @classmethod
    def get_enabled_apis(cls) -> List[str]:
        """获取启用的API列表"""
        return config_manager.get_enabled_apis()

    @classmethod
    def reload_configs(cls):
        """重新加载配置"""
        config_manager.reload_configs()
        # 清除当前实例，下次获取时会重新创建
        cls._current_api = None
        logger.info("重新加载配置完成")

    @classmethod
    def clear_cache(cls):
        """清除缓存"""
        api_registry.clear_instances()
        cls._current_api = None
        logger.info("清除API缓存完成")


# 便捷函数
def get_api(api_name: Optional[str] = None) -> Optional[RobotAPIInterface]:
    """获取API实例的便捷函数"""
    return APIFactory.get_default_api() if api_name is None else APIFactory.create_api(api_name)

def get_api_with_fallback(preferred_apis: Optional[List[str]] = None) -> Optional[RobotAPIInterface]:
    """获取带故障转移的API实例的便捷函数"""
    return APIFactory.create_api_with_fallback(preferred_apis)

def switch_api(api_name: str) -> bool:
    """切换API的便捷函数"""
    return APIFactory.switch_api(api_name)
