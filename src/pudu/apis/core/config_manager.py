"""
配置管理器 - 管理API配置和映射
"""

import yaml
import os
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), '..', 'configs')
        self._api_config = None
        self._api_mapping = None
        self._credentials = None
        self._current_customer = None
        self._load_configs()
        self._load_credentials()

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

    def get_api_priority(self, api_name: str) -> int:
        """获取API优先级"""
        api_config = self.get_api_config(api_name)
        return api_config.get('priority', 999) if api_config else 999

    def get_function_mapping(self, function_name: str, api_name: str) -> Optional[str]:
        """获取函数映射"""
        return self._api_mapping.get('function_mapping', {}).get(function_name, {}).get(api_name)

    def is_api_enabled(self, api_name: str) -> bool:
        """检查API是否在全局配置中启用（不考虑客户）"""
        api_config = self._api_config.get('apis', {}).get(api_name, {})
        return api_config.get('enabled', False)

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

    def _load_credentials(self):
        """加载凭证配置文件"""
        try:
            # Try environment variable first
            credentials_path = os.getenv('ROBOT_API_CREDENTIALS_PATH')

            # Fall back to default location
            if not credentials_path:
                credentials_path = os.path.join(self.config_dir, 'credentials.yaml')

            if os.path.exists(credentials_path):
                with open(credentials_path, 'r', encoding='utf-8') as f:
                    self._credentials = yaml.safe_load(f)
                logger.info(f"成功加载凭证文件: {credentials_path}")
            else:
                logger.warning(f"凭证文件不存在: {credentials_path}, 使用默认配置")
                self._credentials = {'customers': {}}

        except Exception as e:
            logger.error(f"加载凭证文件失败: {e}")
            self._credentials = {'customers': {}}

    def get_customers_from_env(self, env_variable_name: str = 'ROBOT_API_CUSTOMERS') -> List[str]:
            """获取环境变量中配置的客户列表

            Returns:
                客户名称列表，从环境变量 env_variable_name 读取
                如果环境变量未设置，返回所有可用客户
            """
            env_customers = os.getenv(env_variable_name, '').strip()

            if env_customers:
                # Parse comma-separated list
                customer_list = [c.strip() for c in env_customers.split(',') if c.strip()]

                # Validate customers exist in credentials
                available_customers = self.list_customers()
                valid_customers = [c for c in customer_list if c in available_customers]

                if not valid_customers:
                    logger.warning(f"No valid customers found in {env_variable_name}: {env_customers}")
                    logger.warning(f"Available customers: {available_customers}")
                    return []

                invalid = [c for c in customer_list if c not in available_customers]
                if invalid:
                    logger.warning(f"Invalid customers in {env_variable_name} (will be skipped): {invalid}")

                logger.info(f"Processing customers from environment: {valid_customers}")
                return valid_customers
            else:
                # If no env variable, return all customers except 'default'
                all_customers = self.list_customers()
                customers = [c for c in all_customers if c != 'default']
                logger.info(f"No {env_variable_name} set, processing all customers: {customers}")
                return customers

    def set_customer(self, customer_name: str):
        """设置当前客户

        Args:
            customer_name: 客户名称
        """
        customers = self._credentials.get('customers', {})
        if customer_name not in customers:
            available = list(customers.keys())
            raise ValueError(f"客户 '{customer_name}' 不存在。可用客户: {available}")

        self._current_customer = customer_name
        logger.info(f"切换到客户: {customer_name}")

    def get_current_customer(self) -> str:
        """获取当前客户名称"""
        return self._current_customer or os.getenv('ROBOT_API_CUSTOMER', 'default')

    def get_customer_credentials(self, api_name: str, customer_name: str = None) -> dict:
        """获取指定客户的API凭证

        Args:
            api_name: API名称 (pudu 或 gas)
            customer_name: 客户名称，如果不提供则使用当前客户

        Returns:
            包含凭证的字典
        """
        customer = customer_name or self.get_current_customer()
        customers = self._credentials.get('customers', {})

        # Try to get credentials for specific customer
        if customer in customers:
            api_creds = customers[customer].get(api_name, {})
            if api_creds and api_creds.get('enabled', True):
                return api_creds

        # Fall back to default
        if 'default' in customers:
            default_creds = customers['default'].get(api_name, {})
            if default_creds and default_creds.get('enabled', True):
                logger.warning(f"使用默认凭证 for {api_name} (customer: {customer})")
                return default_creds

        logger.error(f"未找到 {api_name} 的凭证 (customer: {customer})")
        return {}

    def get_customer_enabled_apis(self, customer_name: str = None) -> list:
        """获取客户启用的API列表

        Args:
            customer_name: 客户名称

        Returns:
            启用的API名称列表
        """
        customer = customer_name or self.get_current_customer()
        customers = self._credentials.get('customers', {})

        if customer not in customers:
            return []

        enabled_apis = []
        customer_config = customers[customer]

        for api_name in ['pudu', 'gas']:
            api_config = customer_config.get(api_name, {})
            if api_config.get('enabled', False):
                enabled_apis.append(api_name)

        return enabled_apis

    def list_customers(self) -> list:
        """列出所有可用的客户

        Returns:
            客户名称列表
        """
        return list(self._credentials.get('customers', {}).keys())

    def get_api_config(self, api_name: str, customer_name: str = None) -> Optional[Dict[str, Any]]:
        """获取指定API的配置（合并凭证）

        Args:
            api_name: API名称
            customer_name: 客户名称

        Returns:
            包含凭证的完整配置
        """
        # Get base config from api_config.yaml
        base_config = self._api_config.get('apis', {}).get(api_name, {})

        # Get customer-specific credentials
        credentials = self.get_customer_credentials(api_name, customer_name)

        # Merge credentials into config
        merged_config = base_config.copy()
        if 'config' not in merged_config:
            merged_config['config'] = {}

        # Update with customer credentials (remove 'enabled' key)
        creds_copy = credentials.copy()
        creds_copy.pop('enabled', None)
        merged_config['config'].update(creds_copy)

        return merged_config

    def reload_configs(self):
        """重新加载所有配置文件"""
        self._load_configs()
        self._load_credentials()
        logger.info("重新加载所有配置文件完成")


# 全局配置管理器实例
config_manager = ConfigManager()
