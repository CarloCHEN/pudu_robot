"""
核心框架层 - 提供统一的API接口和自动发现机制
"""

from .api_interface import RobotAPIInterface
from .api_registry import APIRegistry
from .api_factory import APIFactory
from .config_manager import ConfigManager

__all__ = [
    'RobotAPIInterface',
    'APIRegistry', 
    'APIFactory',
    'ConfigManager'
]
