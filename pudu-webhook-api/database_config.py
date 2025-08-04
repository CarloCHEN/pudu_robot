import os
from typing import Dict, List

import yaml


class DatabaseConfig:
    """Configuration manager for database and table specifications"""

    def __init__(self, config_path: str = "database_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            # Return default config if file not found
            return self._get_default_config()
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")

    def _get_default_config(self) -> dict:
        """Default configuration for webhook database operations"""
        return {
            "databases": ["ry-vue"],
            "tables": {
                "robot_status": [{"database": "ry-vue", "table_name": "mnt_robots_management", "primary_keys": ["robot_sn"]}],
                "robot_events": [
                    {"database": "ry-vue", "table_name": "mnt_robot_events", "primary_keys": ["robot_sn", "event_id"]}
                ],
            },
        }

    def get_table_configs(self) -> Dict[str, List[Dict]]:
        """Get all table configurations grouped by table type"""
        return self.config.get("tables", {})

    def get_notification_needed(self) -> List[str]:
        """Get list of databases that notification is needed"""
        return self.config.get("notification_needed", [])
