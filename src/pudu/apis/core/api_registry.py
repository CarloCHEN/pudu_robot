"""
API注册中心 - 自动发现和注册API适配器
"""

import importlib
import logging
import os
import sys
from typing import Dict, Optional
from .api_interface import RobotAPIInterface

logger = logging.getLogger(__name__)


class APIRegistry:
    """API注册中心，负责自动发现和注册API适配器"""

    def __init__(self):
        self._adapters: Dict[str, any] = {}
        self._instances: Dict[str, RobotAPIInterface] = {}
        self._auto_discover()

    def _auto_discover(self):
        """自动发现所有适配器"""
        try:
            # Get the current package structure
            # We're in: pudu.apis.core.api_registry
            # We want: pudu.apis.adapters

            current_package = __name__.rsplit('.', 1)[0]  # Gets 'pudu.apis.core'
            parent_package = current_package.rsplit('.', 1)[0]  # Gets 'pudu.apis'
            adapters_package = f"{parent_package}.adapters"

            # Get the adapters directory path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            adapters_path = os.path.join(parent_dir, 'adapters')

            if not os.path.exists(adapters_path):
                logger.warning(f"Adapters path does not exist: {adapters_path}")
                return

            logger.info(f"Discovering adapters in package: {adapters_package}")

            # Discover all adapter files
            for filename in os.listdir(adapters_path):
                if filename.endswith('_adapter.py') and not filename.startswith('__'):
                    module_name = filename[:-3]  # Remove .py extension
                    full_module_name = f"{adapters_package}.{module_name}"

                    try:
                        # Import using the full package path
                        module = importlib.import_module(full_module_name)

                        # Check if module has required attributes
                        if hasattr(module, 'API_NAME') and hasattr(module, 'create_adapter'):
                            api_name = getattr(module, 'API_NAME')
                            create_adapter_func = getattr(module, 'create_adapter')

                            # Register the adapter
                            self._adapters[api_name] = create_adapter_func
                            logger.info(f"自动发现并注册API适配器: {api_name} (from {full_module_name})")
                        else:
                            logger.warning(f"模块 {full_module_name} 缺少 API_NAME 或 create_adapter")
                    except Exception as e:
                        logger.warning(f"发现适配器 {module_name} 时出错: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
        except Exception as e:
            logger.error(f"自动发现适配器时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def register_adapter(self, api_name: str, create_adapter_func):
        """注册API适配器创建函数

        Args:
            api_name: API名称
            create_adapter_func: 创建适配器的函数
        """
        self._adapters[api_name] = create_adapter_func
        logger.info(f"注册API适配器: {api_name}")

    def get_adapter_class(self, api_name: str):
        """获取适配器创建函数

        Args:
            api_name: API名称

        Returns:
            创建适配器的函数，如果不存在则返回None
        """
        return self._adapters.get(api_name)

    def create_adapter_instance(self, api_name: str, config: Optional[Dict] = None) -> Optional[RobotAPIInterface]:
        """创建适配器实例

        Args:
            api_name: API名称
            config: 配置字典

        Returns:
            适配器实例，如果创建失败则返回None
        """
        # Create a cache key based on api_name and config
        cache_key = f"{api_name}_{str(config)}"

        # Check if instance already exists in cache
        if cache_key in self._instances:
            logger.debug(f"使用缓存的API适配器实例: {api_name}")
            return self._instances[cache_key]

        # Get the create function
        create_func = self.get_adapter_class(api_name)
        if not create_func:
            logger.error(f"未找到API适配器: {api_name}")
            return None

        try:
            # Create new instance
            instance = create_func(config)

            # Cache the instance
            self._instances[cache_key] = instance
            logger.info(f"创建API适配器实例: {api_name}")
            return instance
        except Exception as e:
            logger.error(f"创建API适配器实例 {api_name} 失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def list_available_apis(self) -> list:
        """列出所有可用的API

        Returns:
            可用的API名称列表
        """
        return list(self._adapters.keys())

    def is_api_available(self, api_name: str) -> bool:
        """检查API是否可用

        Args:
            api_name: API名称

        Returns:
            如果API可用返回True，否则返回False
        """
        return api_name in self._adapters

    def clear_instances(self):
        """清除所有实例（用于测试或重新初始化）"""
        self._instances.clear()
        logger.info("清除所有API适配器实例")


# 全局注册中心实例
api_registry = APIRegistry()