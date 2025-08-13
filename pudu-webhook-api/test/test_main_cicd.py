#!/usr/bin/env python3
"""
CI/CD Test version of main.py that uses mock services
This version avoids any AWS service calls and uses mock services
"""

import json
import logging
import os
import time
from datetime import datetime
from enum import Enum

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

# Simple fallback models for CI/CD
class CallbackStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

class CallbackResponse:
    def __init__(self, status, message, timestamp=None, data=None):
        self.status = status
        self.message = message
        self.timestamp = timestamp or int(time.time())
        self.data = data or {}

    def to_dict(self):
        return {
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "message": self.message,
            "timestamp": self.timestamp,
            "data": self.data
        }

# Simple fallback config
class Config:
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    PUDU_CALLBACK_CODE = os.getenv("PUDU_CALLBACK_CODE", "test_callback_code")

# Mock database operations
class MockDatabaseWriter:
    def __init__(self):
        self.data = {}

    def write_to_database_with_change_detection(self, data):
        callback_type = data.get("callback_type", "unknown")
        robot_sn = data.get("data", {}).get("sn", "unknown")

        # Store the data
        if callback_type not in self.data:
            self.data[callback_type] = []
        self.data[callback_type].append(data)

        # Return mock response
        changes = {
            f"{robot_sn}_change": {
                'robot_sn': robot_sn,
                'database_key': f'mock_key_{robot_sn}'
            }
        }
        return ["mock_db"], ["mock_table"], {"mock_table": changes}

# Mock notification service
class MockNotificationService:
    def __init__(self):
        self.notifications = []

    def send_notification(self, **kwargs):
        self.notifications.append(kwargs)
        return True

# Simple callback handler
class SimpleCallbackHandler:
    def __init__(self):
        self.database_writer = MockDatabaseWriter()

    def process_callback(self, data):
        callback_type = data.get("callback_type", "unknown")
        robot_sn = data.get("data", {}).get("sn", "unknown")

        # Basic validation
        if not callback_type or not robot_sn:
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Missing required fields"
            )

        return CallbackResponse(
            status=CallbackStatus.SUCCESS,
            message=f"Processed {callback_type} for robot {robot_sn}",
            data={"robot_sn": robot_sn, "callback_type": callback_type}
        )

    def write_to_database_with_change_detection(self, data):
        return self.database_writer.write_to_database_with_change_detection(data)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize mock services
callback_handler = SimpleCallbackHandler()
notification_service = MockNotificationService()

@app.route("/api/pudu/webhook", methods=["POST"])
def pudu_webhook():
    """CI/CD Test webhook endpoint using mock services"""
    try:
        logger.info(f"🧪 CI/CD Test webhook received callback from {request.remote_addr}")

        # Validate request
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify(CallbackResponse(status=CallbackStatus.ERROR, message="Request must be JSON").to_dict()), 400

        # Parse JSON body
        try:
            data = request.get_json()
        except BadRequest:
            logger.error("Malformed JSON received")
            return jsonify(CallbackResponse(status=CallbackStatus.ERROR, message="Malformed JSON").to_dict()), 400

        logger.info(f"📝 CI/CD Test callback data: {json.dumps(data, indent=2)}")

        # Extract CallbackCode from headers (case-insensitive)
        headers = {k.lower(): v for k, v in request.headers.items()}
        received_callback_code = headers.get("callbackcode")

        if not received_callback_code:
            logger.error("Missing CallbackCode in request headers")
            return jsonify(CallbackResponse(status=CallbackStatus.ERROR, message="Missing CallbackCode header").to_dict()), 400

        # Verify CallbackCode
        expected_callback_code = Config.PUDU_CALLBACK_CODE
        if received_callback_code != expected_callback_code:
            logger.error(f"Invalid CallbackCode received: {received_callback_code}")
            return jsonify(CallbackResponse(status=CallbackStatus.ERROR, message="Invalid CallbackCode").to_dict()), 401

        # Process the callback
        response = callback_handler.process_callback(data)

        # Mock database write
        try:
            database_names, table_names, changes_detected = callback_handler.write_to_database_with_change_detection(data)
            logger.info(f"✅ Mock database write completed")
        except Exception as e:
            logger.error(f"❌ Mock database write failed: {e}")
            database_names, table_names, changes_detected = [], [], {}

        # Mock notification
        if changes_detected:
            try:
                for changes in changes_detected.values():
                    for change_info in changes.values():
                        robot_sn = change_info.get('robot_sn', 'unknown')
                        notification_service.send_notification(
                            robot_sn=robot_sn,
                            notification_type="robot_status",
                            title=f"CI/CD Test: {data.get('callback_type', 'unknown')}",
                            content=f"Test notification for robot {robot_sn}",
                            severity="event",
                            status="normal"
                        )
                logger.info(f"✅ Mock notifications sent")
            except Exception as e:
                logger.error(f"❌ Mock notification failed: {e}")

        return jsonify(response.to_dict()), 200

    except Exception as e:
        logger.error(f"❌ Error processing CI/CD test callback: {str(e)}", exc_info=True)
        return (
            jsonify(CallbackResponse(status=CallbackStatus.ERROR, message=f"Internal server error: {str(e)}").to_dict()),
            500,
        )

@app.route("/api/pudu/webhook/health", methods=["GET"])
def health_check():
    """Health check endpoint for CI/CD testing"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "service": "pudu-callback-api-cicd-test",
        "mode": "ci-cd-testing",
        "features": {
            "mock_database": "enabled",
            "mock_notifications": "enabled",
            "aws_services": "disabled"
        },
        "test_data": {
            "callbacks_processed": len(callback_handler.database_writer.data),
            "notifications_sent": len(notification_service.notifications)
        }
    })

if __name__ == "__main__":
    logger.info("🧪 Starting Pudu Callback API CI/CD Test Server...")
    logger.info("=" * 60)
    logger.info("🚧 CI/CD TEST MODE ENABLED")
    logger.info("📊 Using MOCK database and notification services")
    logger.info("🚫 NO AWS service calls will be made")
    logger.info("=" * 60)

    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)