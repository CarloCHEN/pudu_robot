import http.client
import json
import logging
# Configure logging 
logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications to web API"""

    def __init__(self, api_host: str = "alb-streamnexus-demo-775802511.us-east-1.elb.amazonaws.com"):
        self.api_host = api_host
        self.endpoint = "/notification-api/robot/notification/send"
        self.headers = {'Content-Type': 'application/json'}

    def send_notification(self, robot_id: str, notification_type: str, title: str, content: str,
                         priority: str = "low", severity: str = "low") -> bool:
        """Send notification to web API"""
        try:
            # Change this line from HTTPSConnection to HTTPConnection
            conn = http.client.HTTPConnection(self.api_host)
            payload = json.dumps({
                "robotId": robot_id,
                "notificationType": notification_type,
                "title": title,
                "content": content,
                "priority": priority,
                "severity": severity,
            })

            conn.request("POST", self.endpoint, payload, self.headers)
            res = conn.getresponse()
            data = res.read()

            if res.status == 200:
                logger.info(f"✅ Notification sent successfully for robot {robot_id}: {title}")
                return True
            else:
                logger.error(f"❌ Failed to send notification for robot {robot_id}. Status: {res.status}, Response: {data.decode('utf-8')}")
                return False

        except Exception as e:
            logger.error(f"❌ Exception sending notification for robot {robot_id}: {e}")
            return False
        finally:
            try:
                conn.close()
            except:
                pass