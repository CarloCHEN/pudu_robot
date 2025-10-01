"""
配置管理器 - 管理API配置和映射
"""

import yaml
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'configs')
        self._api_config = None
        self._api_mapping = None
        self._load_configs()
    
    def _load_configs(self):
        """加载配置文件"""
        try:
            # 加载API配置
            api_config_path = os.path.join(self.config_dir, 'api_config.yaml')
            if os.path.exists(api_config_path):
                with open(api_config_path, 'r', encoding='utf-8') as f:
                    self._api_config = yaml.safe_load(f)
            else:
                self._api_config = self._get_default_api_config()
                self._save_config(api_config_path, self._api_config)
            
            # 加载API映射配置
            mapping_config_path = os.path.join(self.config_dir, 'api_mapping.yaml')
            if os.path.exists(mapping_config_path):
                with open(mapping_config_path, 'r', encoding='utf-8') as f:
                    self._api_mapping = yaml.safe_load(f)
            else:
                self._api_mapping = self._get_default_mapping_config()
                self._save_config(mapping_config_path, self._api_mapping)
                
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self._api_config = self._get_default_api_config()
            self._api_mapping = self._get_default_mapping_config()
    
    def _save_config(self, file_path: str, config: Dict[str, Any]):
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"保存配置文件 {file_path} 失败: {e}")
    
    def _get_default_api_config(self) -> Dict[str, Any]:
        """获取默认API配置"""
        return {
            'default_api': 'pudu',
            'apis': {
                'pudu': {
                    'enabled': True,
                    'priority': 1,
                    'config': {
                        'base_url': 'https://api.pudu.com'
                    }
                },
                'gas': {
                    'enabled': True,
                    'priority': 2,
                    'config': {
                        'base_url': 'https://openapi.gs-robot.com',
                        'client_id': 'muryFD4sL4XsVanqsHwX',
                        'client_secret': 'sWYjrp0D9X7gnkHLP727SeR5lJ1MFbUpOIumN6rt6tHwExvOOJk',
                        'open_access_key': '5d810a147b55ca9978afa82819b9625d'
                    }
                }
            }
        }
    
    def _get_default_mapping_config(self) -> Dict[str, Any]:
        """获取默认映射配置"""
        return {
            'function_mapping': {
                'get_robot_details': {
                    'pudu': 'get_robot_details',
                    'gas': 'get_robot_status'
                },
                'get_list_stores': {
                    'pudu': 'get_list_stores',
                    'gas': 'list_robots'  # 需要适配
                },
                'get_list_robots': {
                    'pudu': 'get_list_robots',
                    'gas': 'list_robots'
                }
            }
        }
    
    def get_default_api(self) -> str:
        """获取默认API"""
        return self._api_config.get('default_api', 'pudu')
    
    def get_enabled_apis(self) -> list:
        """获取启用的API列表"""
        enabled_apis = []
        for api_name, api_config in self._api_config.get('apis', {}).items():
            if api_config.get('enabled', False):
                enabled_apis.append(api_name)
        return enabled_apis
    
    def get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        """获取指定API的配置"""
        return self._api_config.get('apis', {}).get(api_name)
    
    def get_api_priority(self, api_name: str) -> int:
        """获取API优先级"""
        api_config = self.get_api_config(api_name)
        return api_config.get('priority', 999) if api_config else 999
    
    def get_function_mapping(self, function_name: str, api_name: str) -> Optional[str]:
        """获取函数映射"""
        return self._api_mapping.get('function_mapping', {}).get(function_name, {}).get(api_name)
    
    def is_api_enabled(self, api_name: str) -> bool:
        """检查API是否启用"""
        api_config = self.get_api_config(api_name)
        return api_config.get('enabled', False) if api_config else False
    
    def get_optimal_api(self) -> str:
        """获取最优API（优先级最高且启用的）"""
        enabled_apis = self.get_enabled_apis()
        if not enabled_apis:
            return self.get_default_api()
        
        # 按优先级排序
        enabled_apis.sort(key=lambda x: self.get_api_priority(x))
        return enabled_apis[0]
    
    def reload_configs(self):
        """重新加载配置文件"""
        self._load_configs()
        logger.info("重新加载配置文件")


# 全局配置管理器实例
config_manager = ConfigManager()
