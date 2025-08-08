"""
Test version of main.py that uses mock services instead of real database/notifications
Run this for endpoint testing instead of the production main.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Change to the parent directory so imports work correctly
os.chdir(Path(__file__).parent.parent)

import json
import logging
from datetime import datetime

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

# Set environment variables before importing modules that need them
if not os.getenv("PORT"):
    os.environ["PORT"] = "8000"

if not os.getenv("DEBUG"):
    os.environ["DEBUG"] = "true"

if not os.getenv("PUDU_CALLBACK_CODE"):
    os.environ["PUDU_CALLBACK_CODE"] = "1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq"

# Import mock services from test directory
from test.mocks.mock_database import MockDatabaseWriter
from test.mocks.mock_notification import MockNotificationService

# Try to import the required modules, with fallbacks for import errors
try:
    from callback_handler import CallbackHandler
    CALLBACK_HANDLER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Could not import CallbackHandler: {e}")
    CALLBACK_HANDLER_AVAILABLE = False
    # Create a simple fallback handler
    class SimpleCallbackHandler:
        def process_callback(self, data):
            from models import CallbackResponse, CallbackStatus
            callback_type = data.get("callback_type", "unknown")
            robot_sn = data.get("data", {}).get("sn", "unknown")
            return CallbackResponse(
                status=CallbackStatus.SUCCESS,
                message=f"Processed {callback_type} for robot {robot_sn}",
                data={"robot_sn": robot_sn, "callback_type": callback_type}
            )

        def write_to_database_with_change_detection(self, data):
            # Mock implementation
            return ["mock_db"], ["mock_table"], {
                "mock_change": {
                    'robot_id': data.get("data", {}).get("sn", "unknown"),
                    'database_key': 'mock_key_123'
                }
            }

try:
    from config import Config
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Could not import Config: {e}")
    CONFIG_AVAILABLE = False
    # Create a simple fallback config
    class SimpleConfig:
        HOST = os.getenv("HOST", "0.0.0.0")
        PORT = int(os.getenv("PORT", 8000))
        DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        PUDU_CALLBACK_CODE = os.getenv("PUDU_CALLBACK_CODE", "")

try:
    from models import CallbackResponse, CallbackStatus
    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Could not import models: {e}")
    MODELS_AVAILABLE = False
    # Create simple fallback models
    from enum import Enum
    import time

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

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Get configuration file path - try multiple locations
config_paths = [
    'database_config.yaml',
    'configs/database_config.yaml',
    '../configs/database_config.yaml',
    'pudu/configs/database_config.yaml'
]

config_path = None
for path in config_paths:
    if os.path.exists(path):
        config_path = path
        break

# Use appropriate config and handler
Config = Config if CONFIG_AVAILABLE else SimpleConfig
callback_handler = CallbackHandler(config_path) if CALLBACK_HANDLER_AVAILABLE else SimpleCallbackHandler()

# Initialize MOCK database writer for testing
try:
    database_writer = MockDatabaseWriter()
    logger.info("✅ Mock database writer initialized for testing")
except Exception as e:
    logger.error(f"Failed to initialize mock database writer: {e}")
    database_writer = None

# Initialize MOCK notification service for testing
try:
    notification_service = MockNotificationService()
    logger.info("✅ Mock notification service initialized for testing")
except Exception as e:
    logger.error(f"Failed to initialize mock notification service: {e}")
    notification_service = None


@app.route("/api/pudu/webhook", methods=["POST"])
def pudu_webhook():
    """
    Test webhook endpoint using mock services
    """
    try:
        # Log incoming request
        logger.info(f"🔍 Test webhook received callback from {request.remote_addr}")

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

        logger.info(f"📝 Test callback data: {json.dumps(data, indent=2)}")

        # Lowercase all headers for consistent access
        lower_headers = {k.lower(): v for k, v in request.headers.items()}

        # Extract CallbackCode from headers (case-insensitive)
        received_callback_code = lower_headers.get("callbackcode") or lower_headers.get("x-callback-code")

        if not received_callback_code:
            logger.error("Missing CallbackCode in request headers")
            return jsonify(CallbackResponse(status=CallbackStatus.ERROR, message="Missing CallbackCode header").to_dict()), 400

        # Get expected code from config
        expected_callback_code = Config.PUDU_CALLBACK_CODE
        if not expected_callback_code:
            logger.error("PUDU_CALLBACK_CODE not configured in environment")
            return jsonify(CallbackResponse(status=CallbackStatus.ERROR, message="Server configuration error").to_dict()), 500

        # Verify CallbackCode
        if received_callback_code != expected_callback_code:
            logger.error(f"Invalid CallbackCode received: {received_callback_code}")
            return jsonify(CallbackResponse(status=CallbackStatus.ERROR, message="Invalid CallbackCode").to_dict()), 401

        # Process the callback
        response = callback_handler.process_callback(data)

        # Write to MOCK database if writer is available
        database_names = []
        table_names = []
        changes_detected = {}

        if database_writer and hasattr(callback_handler, 'write_to_database_with_change_detection'):
            try:
                logger.info(f"📊 Writing to mock database: {data.get('callback_type')}")
                database_names, table_names, changes_detected = callback_handler.write_to_database_with_change_detection(data)
                logger.info("✅ Mock database write completed")
            except Exception as e:
                logger.error(f"❌ Failed to write callback to mock database: {e}")

        # Send MOCK notification if service is available and changes detected
        if notification_service and changes_detected:
            try:
                logger.info(f"📨 Sending mock notifications: {data.get('callback_type')}")

                # Send notifications for each change
                for (db_name, table_name), changes in changes_detected.items():
                    for change_id, change_info in changes.items():
                        robot_sn = change_info.get('robot_id', 'unknown')
                        callback_type = data.get("callback_type", "unknown")

                        payload = {
                            "database_name": db_name,
                            "table_name": table_name,
                            "related_biz_id": change_info.get('database_key'),
                            "related_biz_type": callback_type
                        }

                        # Generate appropriate notification based on callback type
                        if callback_type == "robotStatus":
                            title = f"Robot Status: {data.get('data', {}).get('run_status', 'Unknown')}"
                            content = f"Robot {robot_sn} status changed"
                            severity = "success" if "online" in str(data.get('data', {}).get('run_status', '')).lower() else "event"
                        elif callback_type == "robotErrorWarning":
                            error_level = data.get('data', {}).get('error_level', 'info')
                            title = f"Robot Error: {data.get('data', {}).get('error_type', 'Unknown')}"
                            content = f"Robot {robot_sn} has a {error_level} level error"
                            severity = "fatal" if error_level.upper() == "FATAL" else "error" if error_level.upper() == "ERROR" else "warning"
                        elif callback_type == "notifyRobotPower":
                            power = data.get('data', {}).get('power', 0)
                            title = f"Battery: {power}%"
                            content = f"Robot {robot_sn} battery at {power}%"
                            severity = "fatal" if power < 5 else "error" if power < 10 else "warning" if power < 20 else "success"
                        else:
                            title = f"Test: {callback_type}"
                            content = f"Test notification for robot {robot_sn}"
                            severity = "event"

                        success = notification_service.send_notification(
                            robot_id=robot_sn,
                            notification_type="robot_status",
                            title=title,
                            content=content,
                            severity=severity,
                            status="normal",
                            payload=payload
                        )

                        if success:
                            logger.info(f"✅ Mock notification sent for {robot_sn}")
                        else:
                            logger.warning(f"⚠️ Mock notification failed for {robot_sn}")

            except Exception as e:
                logger.error(f"❌ Failed to send mock notification: {e}")

        # Return result
        return jsonify(response.to_dict()), 200 if response.status == CallbackStatus.SUCCESS else 400

    except Exception as e:
        logger.error(f"❌ Error processing test callback: {str(e)}", exc_info=True)
        return (
            jsonify(CallbackResponse(status=CallbackStatus.ERROR, message=f"Internal server error: {str(e)}").to_dict()),
            500,
        )


@app.route("/api/pudu/webhook/health", methods=["GET"])
def health_check():
    """Health check endpoint for testing"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "service": "pudu-callback-api-test",
            "mode": "testing",
            "features": {
                "callback_handler": "available" if CALLBACK_HANDLER_AVAILABLE else "fallback",
                "config": "available" if CONFIG_AVAILABLE else "fallback",
                "models": "available" if MODELS_AVAILABLE else "fallback",
                "database_writer": "enabled" if database_writer else "disabled",
                "notification_service": "enabled" if notification_service else "disabled",
            },
            "mock_data": {
                "database_records": len(database_writer.get_written_data()) if database_writer else 0,
                "notifications_sent": len(notification_service.get_sent_notifications()) if notification_service else 0,
            },
        }
    )


@app.route("/api/pudu/webhook/test/reset", methods=["POST"])
def reset_test_data():
    """Reset mock data for fresh testing"""
    try:
        if database_writer:
            database_writer.clear_written_data()
            logger.info("🧹 Mock database data cleared")

        if notification_service:
            notification_service.clear_notifications()
            logger.info("🧹 Mock notifications cleared")

        return jsonify({"status": "success", "message": "Test data reset successfully"})
    except Exception as e:
        logger.error(f"❌ Error resetting test data: {e}")
        return jsonify({"status": "error", "message": f"Failed to reset test data: {e}"}), 500


@app.route("/api/pudu/webhook/test/summary", methods=["GET"])
def test_summary():
    """Get summary of test operations"""
    try:
        summary = {"database_operations": {}, "notification_operations": {}, "test_mode": True}

        if database_writer:
            written_data = database_writer.get_written_data()
            summary["database_operations"] = {
                "total_tables": len(written_data),
                "tables": {table: len(records) for table, records in written_data.items()},
                "latest_records": {table: records[-3:] if records else [] for table, records in written_data.items()},
            }

        if notification_service:
            notifications = notification_service.get_sent_notifications()
            summary["notification_operations"] = {
                "total_notifications": len(notifications),
                "by_severity": {},
                "by_robot": {},
                "latest_notifications": notifications[-5:] if notifications else [],
            }

            # Group by severity and robot
            for notif in notifications:
                severity = notif.get("severity", "unknown")
                robot_id = notif.get("robot_id", "unknown")

                summary["notification_operations"]["by_severity"][severity] = (
                    summary["notification_operations"]["by_severity"].get(severity, 0) + 1
                )
                summary["notification_operations"]["by_robot"][robot_id] = (
                    summary["notification_operations"]["by_robot"].get(robot_id, 0) + 1
                )

        return jsonify(summary)

    except Exception as e:
        logger.error(f"❌ Error generating test summary: {e}")
        return jsonify({"status": "error", "message": f"Failed to generate summary: {e}"}), 500


if __name__ == "__main__":
    logger.info("🧪 Starting Pudu Callback API Test Server...")
    logger.info("=" * 60)
    logger.info("🔧 TEST MODE ENABLED")
    logger.info("📊 Using mock database writer")
    logger.info("📨 Using mock notification service")
    logger.info("🚫 NO real database or notification calls will be made")
    logger.info("=" * 60)
    logger.info(f"✅ Callback Handler: {'Available' if CALLBACK_HANDLER_AVAILABLE else 'Fallback'}")
    logger.info(f"✅ Config: {'Available' if CONFIG_AVAILABLE else 'Fallback'}")
    logger.info(f"✅ Models: {'Available' if MODELS_AVAILABLE else 'Fallback'}")
    logger.info(f"✅ Mock notification service: {'Enabled' if notification_service else 'Disabled'}")
    logger.info(f"✅ Mock database writer: {'Enabled' if database_writer else 'Disabled'}")
    logger.info("=" * 60)
    logger.info("🌐 Additional test endpoints available:")
    logger.info("   POST /api/pudu/webhook/test/reset - Reset test data")
    logger.info("   GET  /api/pudu/webhook/test/summary - Get test summary")
    logger.info("=" * 60)

    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
