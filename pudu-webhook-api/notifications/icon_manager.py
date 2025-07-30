import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


class IconManager:
    """Manages notification icons based on severity and status"""

    def __init__(self, icons_config_path: Optional[str] = None):
        self.icons_config = {}
        self._load_icons_config(icons_config_path)

    def _load_icons_config(self, config_path: Optional[str]):
        """Load icons configuration from YAML file"""

        # environment variable (Lambda/production)
        if not config_path:
            config_path = os.getenv("ICONS_CONFIG_PATH", "icons.yaml")
            logger.info("Using environment variable for icons path")

        # Search for the config file in multiple locations
        search_paths = [
            config_path,  # Direct path
            Path(__file__).parent / config_path,  # Relative to this file
            Path(__file__).parent.parent.parent / config_path,  # Project root
            f"src/pudu/notifications/{config_path}",  # Source directory
            f"/opt/{config_path}",  # Lambda deployment path
        ]

        for path in search_paths:
            try:
                if Path(path).exists():
                    with open(path, "r", encoding="utf-8") as f:
                        self.icons_config = yaml.safe_load(f) or {}
                    logger.info(f"Loaded icons configuration from {path}")
                    return
            except Exception as e:
                logger.debug(f"Failed to load icons from {path}: {e}")
                continue

        logger.warning(f"Icons config file not found in any location, using defaults")
        self._load_default_icons()

    def _load_default_icons(self):
        """Load default icon configuration if file is not available"""
        self.icons_config = {
            "severity_icons": {"fatal": "🟣", "error": "🔴", "warning": "🟠", "event": "🔵", "success": "🟢", "neutral": "⚪"},
            "status_icons": {
                "completed": "✅",
                "failed": "❌",
                "warning": "⚠️",
                "in_progress": "⏳",
                "scheduled": "💤",
                "uncompleted": "🚫",
                "charging": "🔌",
                "offline": "📴",
                "online": "📶",
            },
            "display_rules": {
                "show_both_icons": ["fatal", "error", "warning"],
                "show_severity_only": ["event", "success", "neutral"],
            },
        }

    def get_severity_icon(self, severity: str) -> str:
        """Get icon for severity level"""
        return self.icons_config.get("severity_icons", {}).get(severity, "🔵")

    def get_status_icon(self, status: str) -> str:
        """Get icon for status tag"""
        return self.icons_config.get("status_icons", {}).get(status, "")

    def should_show_both_icons(self, severity: str) -> bool:
        """Determine if both severity and status icons should be shown"""
        show_both = self.icons_config.get("display_rules", {}).get("show_both_icons", [])
        return severity in show_both

    def format_title_with_icons(self, title: str, severity: str, status: Optional[str] = None) -> str:
        """
        Format notification title with appropriate icons

        Args:
            title: Original title text
            severity: Severity level (fatal, error, warning, event, success, neutral)
            status: Status tag (completed, failed, warning, etc.)

        Returns:
            Formatted title with icons
        """
        severity_icon = self.get_severity_icon(severity)

        # Check for special scenario combinations first
        scenario_title = self._get_scenario_title(title, severity, status)
        if scenario_title:
            return scenario_title

        # Standard formatting logic
        if status and self.should_show_both_icons(severity):
            status_icon = self.get_status_icon(status)
            if status_icon:
                return f"{severity_icon} {title} {status_icon}"

        # Just severity icon
        return f"{severity_icon} {title}"

    def _get_scenario_title(self, title: str, severity: str, status: Optional[str]) -> Optional[str]:
        """Check for predefined common scenarios and return formatted title"""
        scenarios = self.icons_config.get("common_scenarios", {})

        # Create a key for matching scenarios
        scenario_key = f"{severity}_{status}" if status else severity

        # Check specific combinations
        for scenario_name, scenario_config in scenarios.items():
            if scenario_config.get("severity") == severity and scenario_config.get("status") == status:

                title_format = scenario_config.get("title_format", "{title}")
                return title_format.format(title=title)

        return None

    def get_battery_warning_format(self, battery_level: int, title: str) -> str:
        """Special formatting for battery warnings based on level"""
        if battery_level < 5:
            return f"🟣 {title} ⚠️"  # Fatal + Warning
        elif battery_level < 10:
            return f"🔴 {title} ⚠️"  # Error + Warning
        elif battery_level < 20:
            return f"🟠 {title} ⚠️"  # Warning + Warning
        else:
            return f"🟢 {title}"  # Success only

    def get_task_status_format(self, task_status: str, title: str) -> str:
        """Special formatting for task status changes"""
        status_formats = {
            "Task Ended": "🟢 {title} ✅",
            "Task Completed": "🟢 {title} ✅",
            "Task Abnormal": "🔴 {title} ❌",
            "Task Interrupted": "🔴 {title} ❌",
            "Task Cancelled": "🟠 {title} 🚫",
            "Task Suspended": "🟠 {title} ⚠️",
            "In Progress": "🔵 {title} ⏳",
            "Not Started": "⚪ {title} 💤",
        }

        format_string = status_formats.get(task_status, "🔵 {title}")
        return format_string.format(title=title)

    def get_robot_status_format(self, robot_status: str, title: str) -> str:
        """Special formatting for robot status changes"""
        if "online" in robot_status.lower():
            return f"📶 {title}"
        elif "offline" in robot_status.lower():
            return f"🔴 {title} 📴"
        else:
            return f"🔵 {title}"


# Global icon manager instance
_icon_manager = None


def get_icon_manager(icons_config_path: Optional[str] = None) -> IconManager:
    """Get global icon manager instance"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager(icons_config_path)
    return _icon_manager


def init_icon_manager(icons_config_path: Optional[str] = None) -> IconManager:
    """Initialize icon manager"""
    global _icon_manager
    _icon_manager = IconManager(icons_config_path)
    return _icon_manager
