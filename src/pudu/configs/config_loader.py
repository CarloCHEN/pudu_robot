# src/pudu/config/config_loader.py

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Configuration loader that supports environment variables and .env files"""

    def __init__(self, env_file_path: Optional[str] = None):
        self.env_file_path = env_file_path
        self._load_env_file()

    def _load_env_file(self):
        """Load .env file if it exists"""
        env_paths = []

        # If specific path provided, use it
        if self.env_file_path:
            env_paths.append(self.env_file_path)

        # Default search paths
        env_paths.extend([
            '.env',
            'src/pudu/notifications/.env',
            '../src/pudu/notifications/.env',
            '/opt/.env'  # Lambda deployment path
        ])

        for env_path in env_paths:
            if os.path.exists(env_path):
                try:
                    self._load_env_from_file(env_path)
                    logger.info(f"Loaded environment variables from {env_path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load .env file {env_path}: {e}")

        logger.info("No .env file found, using system environment variables only")

    def _load_env_from_file(self, file_path: str):
        """Load environment variables from .env file"""
        try:
            # Try to use python-dotenv if available
            from dotenv import load_dotenv
            load_dotenv(file_path, override=False)  # Don't override existing env vars
        except ImportError:
            # Fallback: manual parsing
            logger.warning("python-dotenv not available, using manual parsing")
            self._manual_env_parse(file_path)

    def _manual_env_parse(self, file_path: str):
        """Manually parse .env file when python-dotenv is not available"""
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value

    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification service configuration"""
        return {
            'api_host': os.getenv('NOTIFICATION_API_HOST', ''),
            'api_endpoint': os.getenv('NOTIFICATION_API_ENDPOINT', ''),
            'icons_config_path': os.getenv('ICONS_CONFIG_PATH', 'icons.yaml')
        }

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'host': os.getenv('RDS_HOST'),
            'port': int(os.getenv('RDS_PORT', '3306')),
            'database': os.getenv('RDS_DATABASE'),
            'username': os.getenv('RDS_USERNAME'),
            'password': os.getenv('RDS_PASSWORD')
        }

    def get_log_level(self) -> str:
        """Get logging level"""
        return os.getenv('LOG_LEVEL', 'INFO')

# Global config instance
_config_loader = None

def get_config(env_file_path: Optional[str] = None) -> ConfigLoader:
    """Get global configuration instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(env_file_path)
    return _config_loader

def init_config(env_file_path: Optional[str] = None) -> ConfigLoader:
    """Initialize configuration"""
    global _config_loader
    _config_loader = ConfigLoader(env_file_path)
    return _config_loader