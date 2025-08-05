"""
Test version of main.py that uses mock services instead of real database/notifications
Run this for endpoint testing instead of the production main.py
"""

import os
import sys
from pathlib import Path

from werkzeug.exceptions import BadRequest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Change to the parent directory so imports work correctly
os.chdir(Path(__file__).parent.parent)

import json
import logging
from datetime import datetime

from flask import Flask, jsonify, request

from config import Config

if not os.getenv("PORT"):
    os.environ["PORT"] = "8000"

if not os.getenv("DEBUG"):
    os.environ["DEBUG"] = "true"

# Import mock services
from test.mocks.mock_database import MockDatabaseWriter
from test.mocks.mock_notification import MockNotificationService

from callback_handler import CallbackHandler
from config import Config
from models import CallbackResponse, CallbackStatus

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize callback handler
callback_handler = CallbackHandler()

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
        if database_writer:
            try:
                logger.info(f"📊 Writing to mock database: {data.get('callback_type')}")
                database_names, table_names, primary_key_values = callback_handler.write_to_database(data, database_writer)
                logger.info("✅ Mock database write completed")
            except Exception as e:
                logger.error(f"❌ Failed to write callback to mock database: {e}")

        # Send MOCK notification if service is available
        if notification_service:
            for database_name, table_name in zip(database_names, table_names):
                try:
                    logger.info(f"📨 Sending mock notification: {data.get('callback_type')}")

                    # Import here to avoid circular imports
                    from test.mocks.mock_notification import MockNotificationService

                    # Simple mock notification for testing
                    robot_sn = data.get("data", {}).get("sn", "unknown")
                    callback_type = data.get("callback_type", "unknown")
                    payload = {
                        "database_name": database_name,
                        "table_name": table_name,
                        "primary_key_values": primary_key_values
                    }

                    success = notification_service.send_notification(
                        robot_id=robot_sn,
                        notification_type="robot_status",
                        title=f"Test: {callback_type}",
                        content=f"Test notification for robot {robot_sn}",
                        severity="event",
                        status="normal",
                        payload=payload
                    )

                    if success:
                        logger.info("✅ Mock notification sent successfully")
                    else:
                        logger.warning("⚠️ Mock notification failed")

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
            "notification_service": "mock_enabled" if notification_service else "mock_disabled",
            "database_writer": "mock_enabled" if database_writer else "mock_disabled",
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
    logger.info(f"✅ Mock notification service: {'Enabled' if notification_service else 'Disabled'}")
    logger.info(f"✅ Mock database writer: {'Enabled' if database_writer else 'Disabled'}")
    logger.info("=" * 60)
    logger.info("🌐 Additional test endpoints available:")
    logger.info("   POST /api/pudu/webhook/test/reset - Reset test data")
    logger.info("   GET  /api/pudu/webhook/test/summary - Get test summary")
    logger.info("=" * 60)

    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
