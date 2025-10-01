"""
API注册中心 - 自动发现和注册API适配器
"""

import pkgutil
import importlib
import logging
from typing import Dict, Optional, Type
from .api_interface import RobotAPIInterface

logger = logging.getLogger(__name__)


class APIRegistry:
    """API注册中心，负责自动发现和注册API适配器"""
    
    def __init__(self):
        self._adapters: Dict[str, Type[RobotAPIInterface]] = {}
        self._instances: Dict[str, RobotAPIInterface] = {}
        self._auto_discover()
    
    def _auto_discover(self):
        """自动发现所有适配器"""
        try:
            # 动态导入adapters包
            import adapters
            
            for importer, modname, ispkg in pkgutil.iter_modules(adapters.__path__):
                if modname.endswith('_adapter'):
                    try:
                        module = importlib.import_module(f'adapters.{modname}')
                        if hasattr(module, 'API_NAME') and hasattr(module, 'create_adapter'):
                            api_name = getattr(module, 'API_NAME')
                            adapter_class = getattr(module, 'create_adapter')
                            self.register_adapter(api_name, adapter_class)
                            logger.info(f"自动发现并注册API适配器: {api_name}")
                    except Exception as e:
                        logger.warning(f"发现适配器 {modname} 时出错: {e}")
        except ImportError as e:
            logger.warning(f"无法导入adapters包: {e}")
    
    def register_adapter(self, api_name: str, adapter_class: Type[RobotAPIInterface]):
        """注册API适配器"""
        if not issubclass(adapter_class, RobotAPIInterface):
            raise ValueError(f"适配器 {api_name} 必须继承自 RobotAPIInterface")
        
        self._adapters[api_name] = adapter_class
        logger.info(f"注册API适配器: {api_name}")
    
    def get_adapter_class(self, api_name: str) -> Optional[Type[RobotAPIInterface]]:
        """获取适配器类"""
        return self._adapters.get(api_name)
    
    def create_adapter_instance(self, api_name: str, config: Optional[Dict] = None) -> Optional[RobotAPIInterface]:
        """创建适配器实例"""
        if api_name in self._instances:
            return self._instances[api_name]
        
        adapter_class = self.get_adapter_class(api_name)
        if not adapter_class:
            logger.error(f"未找到API适配器: {api_name}")
            return None
        
        try:
            instance = adapter_class(config)
            self._instances[api_name] = instance
            logger.info(f"创建API适配器实例: {api_name}")
            return instance
        except Exception as e:
            logger.error(f"创建API适配器实例 {api_name} 失败: {e}")
            return None
    
    def list_available_apis(self) -> list:
        """列出所有可用的API"""
        return list(self._adapters.keys())
    
    def is_api_available(self, api_name: str) -> bool:
        """检查API是否可用"""
        return api_name in self._adapters
    
    def clear_instances(self):
        """清除所有实例（用于测试或重新初始化）"""
        self._instances.clear()
        logger.info("清除所有API适配器实例")


# 全局注册中心实例
api_registry = APIRegistry()
