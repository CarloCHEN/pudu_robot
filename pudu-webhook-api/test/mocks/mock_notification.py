"""
Mock Notification Service for Testing
Validates notification operations without requiring actual HTTP calls
"""

import http.client
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

logger = logging.getLogger(__name__)


class MockHTTPResponse:
    """Mock HTTP response"""

    def __init__(self, status: int = 200, data: str = '{"status": "success"}'):
        self.status = status
        self._data = data.encode("utf-8")

    def read(self):
        return self._data


class MockHTTPConnection:
    """Mock HTTP connection that captures requests"""

    def __init__(self, host: str):
        self.host = host
        self.requests = []
        self.is_connected = True

    def request(self, method: str, endpoint: str, payload: str, headers: Dict[str, str]):
        """Capture request details"""
        request_data = {"method": method, "endpoint": endpoint, "payload": payload, "headers": headers, "host": self.host}
        self.requests.append(request_data)

        logger.info(f"🌐 Mock HTTP Request captured:")
        logger.info(f"   Method: {method}")
        logger.info(f"   Host: {self.host}")
        logger.info(f"   Endpoint: {endpoint}")
        logger.info(f"   Headers: {headers}")
        logger.info(f"   Payload: {payload}")

    def getresponse(self):
        """Return mock response"""
        return MockHTTPResponse()

    def close(self):
        self.is_connected = False


class MockNotificationService:
    """
    Mock Notification Service that validates notification operations
    Tests connectivity and captures all notification attempts
    """

    def __init__(self):
        self.api_host = "mock-notification-api.example.com"
        self.endpoint = "/mock/notification/send"
        self.headers = {"Content-Type": "application/json"}
        self.sent_notifications = []
        self.connection_attempts = []

        logger.info(f"MockNotificationService initialized")
        logger.info(f"Mock API Host: {self.api_host}")
        logger.info(f"Mock Endpoint: {self.endpoint}")

    def send_notification(
        self, robot_id: str, notification_type: str, title: str, content: str, severity: str, status: str
    ) -> bool:
        """
        Mock send notification that captures and validates notification data
        """
        try:
            # Create mock connection
            mock_conn = MockHTTPConnection(self.api_host)

            # Build payload exactly like real service
            payload_data = {
                "robotId": robot_id,
                "notificationType": notification_type,
                "title": title,
                "content": content,
                "severity": severity,
                "status": status,
            }

            payload = json.dumps(payload_data)

            # Simulate request
            mock_conn.request("POST", self.endpoint, payload, self.headers)
            response = mock_conn.getresponse()

            # Store notification details for testing
            notification_record = {
                "robot_id": robot_id,
                "notification_type": notification_type,
                "title": title,
                "content": content,
                "severity": severity,
                "status": status,
                "payload": payload_data,
                "success": response.status == 200,
            }

            self.sent_notifications.append(notification_record)

            logger.info(f"✅ Mock notification sent for robot {robot_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Severity: {severity}, Status: {status}")
            logger.info(f"   Notification Type: {notification_type}")

            mock_conn.close()
            return True

        except Exception as e:
            logger.error(f"❌ Mock notification failed for robot {robot_id}: {e}")
            return False

    def test_connection(self) -> bool:
        """Mock connection test"""
        try:
            mock_conn = MockHTTPConnection(self.api_host)
            mock_conn.request("HEAD", "/", "", {})
            response = mock_conn.getresponse()

            self.connection_attempts.append({"success": True, "status": response.status, "host": self.api_host})

            logger.info(f"🔗 Mock connection test successful to {self.api_host}")
            mock_conn.close()
            return True

        except Exception as e:
            self.connection_attempts.append({"success": False, "error": str(e), "host": self.api_host})
            logger.error(f"🔗 Mock connection test failed: {e}")
            return False

    def get_sent_notifications(self, robot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sent notifications for testing verification"""
        if robot_id:
            return [n for n in self.sent_notifications if n["robot_id"] == robot_id]
        return self.sent_notifications

    def get_notifications_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Get notifications filtered by severity"""
        return [n for n in self.sent_notifications if n["severity"] == severity]

    def get_notifications_by_type(self, notification_type: str) -> List[Dict[str, Any]]:
        """Get notifications filtered by type"""
        return [n for n in self.sent_notifications if n["notification_type"] == notification_type]

    def clear_notifications(self):
        """Clear all stored notifications for fresh test"""
        self.sent_notifications.clear()
        logger.info("Cleared all mock notifications")

    def validate_notification_format(self, notification: Dict[str, Any]) -> bool:
        """Validate notification format"""
        required_fields = ["robot_id", "notification_type", "title", "content", "severity", "status"]

        for field in required_fields:
            if field not in notification:
                logger.error(f"❌ Missing required field: {field}")
                return False

        # Validate severity values
        valid_severities = ["fatal", "error", "warning", "event", "success", "neutral"]
        if notification["severity"] not in valid_severities:
            logger.error(f"❌ Invalid severity: {notification['severity']}. Valid: {valid_severities}")
            return False

        # Validate status values
        valid_statuses = ["completed", "failed", "warning", "charging", "offline", "online", "normal", "abnormal", "active"]
        if notification["status"] not in valid_statuses:
            logger.error(f"❌ Invalid status: {notification['status']}. Valid: {valid_statuses}")
            return False

        logger.info(f"✅ Notification format validation passed")
        return True

    def print_summary(self):
        """Print summary of all notification operations"""
        logger.info("\n" + "=" * 60)
        logger.info("NOTIFICATION OPERATION SUMMARY")
        logger.info("=" * 60)

        logger.info(f"Total notifications sent: {len(self.sent_notifications)}")
        logger.info(f"Connection tests performed: {len(self.connection_attempts)}")

        if not self.sent_notifications:
            logger.info("No notifications sent")
            return

        # Group by severity
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        by_robot = defaultdict(int)

        for notification in self.sent_notifications:
            by_severity[notification["severity"]] += 1
            by_type[notification["notification_type"]] += 1
            by_robot[notification["robot_id"]] += 1

        logger.info(f"\nNotifications by severity:")
        for severity, count in by_severity.items():
            logger.info(f"  {severity}: {count}")

        logger.info(f"\nNotifications by type:")
        for ntype, count in by_type.items():
            logger.info(f"  {ntype}: {count}")

        logger.info(f"\nNotifications by robot:")
        for robot, count in by_robot.items():
            logger.info(f"  {robot}: {count}")

        logger.info("\nRecent notifications:")
        for i, notification in enumerate(self.sent_notifications[-5:], 1):
            logger.info(f"  {i}. [{notification['severity']}] {notification['title']} - Robot: {notification['robot_id']}")
