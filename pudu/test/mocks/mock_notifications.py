"""
Mock notification service for testing
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MockNotificationService:
    """Mock notification service that captures notifications"""

    def __init__(self):
        self.sent_notifications = []
        self.connection_attempts = []

    def send_notification(self, robot_sn: str, notification_type: str,
                         title: str, content: str, severity: str, status: str, payload: dict) -> bool:
        """Mock send notification that captures notification data"""
        notification = {
            "robot_sn": robot_sn,
            "notification_type": notification_type,
            "title": title,
            "content": content,
            "severity": severity,
            "status": status,
            "payload": payload,
            "success": True
        }

        self.sent_notifications.append(notification)
        logger.info(f"Mock notification sent for robot {robot_sn}: {title}")
        return True

    def get_sent_notifications(self, robot_sn: str = None) -> List[Dict[str, Any]]:
        """Get sent notifications, optionally filtered by robot_sn"""
        if robot_sn:
            return [n for n in self.sent_notifications if n["robot_sn"] == robot_sn]
        return self.sent_notifications

    def clear_notifications(self):
        """Clear all stored notifications"""
        self.sent_notifications.clear()

    def test_connection(self) -> bool:
        """Mock connection test"""
        self.connection_attempts.append({"success": True})
        return True