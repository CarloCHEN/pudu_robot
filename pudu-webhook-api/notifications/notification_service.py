import http.client
import json
import logging
import os

# Configure logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to web API"""

    def __init__(self):
        # Load from environment variables (Lambda/production)
        self.api_host = os.getenv("NOTIFICATION_API_HOST", "")
        self.endpoint = os.getenv("NOTIFICATION_API_ENDPOINT", "")
        logger.info("Using environment variables for notification settings")

        self.headers = {"Content-Type": "application/json"}

        # Log configuration (without sensitive data)
        logger.info(f"NotificationService initialized with host: {self.api_host[:20]}...")

    def send_notification(
        self, robot_id: str, notification_type: str, title: str, content: str, severity: str, status: str, payload: dict
    ) -> bool:
        """
        Send notification to web API with severity and status

        Args:
            robot_id: ID of the robot
            notification_type: Type of notification
            title: Notification title
            content: Notification content
            severity: Notification severity level (fatal, error, warning, event, success, neutral)
            status: Notification status tag (completed, failed, warning, in_progress, etc.)
        """
        try:
            # Use HTTP connection (change to HTTPSConnection if you move to HTTPS)
            conn = http.client.HTTPConnection(self.api_host)

            # Build data - include status if provided
            notification_data = {
                "robotId": robot_id,
                "notificationType": notification_type,  # robotStatus, robot_status, robot_task, robotTask
                "title": title,
                "content": content,
                "severity": severity,
                "status": status,
                "payload": payload # for identifying the record in the database
            }

            notification_data_json = json.dumps(notification_data)

            conn.request("POST", self.endpoint, notification_data_json, self.headers)
            res = conn.getresponse()
            data = res.read()

            if res.status == 200:
                logger.info(
                    f"✅ Notification sent successfully for robot {robot_id}: {title} (severity: {severity}, status: {status})"
                )
                return True
            else:
                logger.error(
                    f"❌ Failed to send notification for robot {robot_id}. Status: {res.status}, Response: {data.decode('utf-8')}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Exception sending notification for robot {robot_id}: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass

    def test_connection(self) -> bool:
        """Test if the notification service is reachable"""
        try:
            conn = http.client.HTTPConnection(self.api_host)
            # Try a simple HEAD request to test connectivity
            conn.request("HEAD", "/")
            res = conn.getresponse()
            conn.close()

            logger.info(f"🔗 Connection test to {self.api_host}: Status {res.status}")
            return True
        except Exception as e:
            logger.error(f"🔗 Connection test failed for {self.api_host}: {e}")
            return False
