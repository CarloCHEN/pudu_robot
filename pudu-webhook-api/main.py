import json
import logging
from datetime import datetime
import os
from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

from callback_handler import CallbackHandler
from config import Config
from configs.database_config import DatabaseConfig
from models import CallbackResponse, CallbackStatus
from notifications import NotificationService
from notifications.notification_sender import send_change_based_notifications

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(Config.LOG_FILE), logging.StreamHandler()],
)

app = Flask(__name__)
logger = logging.getLogger(__name__)


# Initialize notification service
try:
    notification_service = NotificationService()
    logger.info("Notification service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize notification service: {e}")
    notification_service = None

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


@app.route("/api/pudu/webhook", methods=["POST"])
def pudu_webhook():
    """
    Webhook endpoint with dynamic database routing and change detection
    """
    # Initialize enhanced callback handler with dynamic database config
    callback_handler = CallbackHandler(config_path)
    # Initialize dynamic database configuration
    try:
        db_config = DatabaseConfig(config_path)
        logger.info("Dynamic database configuration initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database configuration: {e}")
        db_config = None

    try:
        # Log incoming request
        logger.info(f"Received callback from {request.remote_addr}")

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

        logger.info(f"Callback data: {json.dumps(data, indent=2)}")

        # Lowercase all headers for consistent access
        lower_headers = {k.lower(): v for k, v in request.headers.items()}
        logger.info(f"Request headers (lowercased): {lower_headers}")

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

        # Write to database with change detection and dynamic routing
        try:
            database_names, table_names, changes_detected = callback_handler.write_to_database_with_change_detection(data)
            logger.info(f"Database write completed. Changes detected in {len(changes_detected)} tables.")
        except Exception as e:
            logger.error(f"Failed to write callback to database: {e}")
            database_names, table_names, changes_detected = [], [], {}

        # Send notifications for detected changes
        if notification_service and changes_detected and db_config:
            callback_type = data.get("callback_type", "unknown")
            notification_databases = db_config.get_notification_databases()

            total_successful_notifications = 0
            total_failed_notifications = 0

            for (database_name, table_name), changes in changes_detected.items():
                try:
                    # Check if this database needs notifications
                    if database_name in notification_databases:
                        logger.info(f"Sending notifications for {len(changes)} changes in {database_name}.{table_name}")

                        successful, failed = send_change_based_notifications(
                            notification_service=notification_service,
                            database_name=database_name,
                            table_name=table_name,
                            changes_dict=changes,
                            callback_type=callback_type
                        )

                        total_successful_notifications += successful
                        total_failed_notifications += failed
                    else:
                        logger.info(f"Skipping notifications for {database_name} (not in notification list)")

                except Exception as e:
                    logger.error(f"Failed to send notifications for {database_name}.{table_name}: {e}")
                    total_failed_notifications += len(changes)

            logger.info(f"📧 Total notifications: {total_successful_notifications} successful, {total_failed_notifications} failed")

        callback_handler.close()
        if db_config:
            db_config.close()
        # Return result
        return jsonify(response.to_dict()), 200 if response.status == CallbackStatus.SUCCESS else 400

    except Exception as e:
        callback_handler.close()
        if db_config:
            db_config.close()
        logger.error(f"Error processing callback: {str(e)}", exc_info=True)
        return (
            jsonify(CallbackResponse(status=CallbackStatus.ERROR, message=f"Internal server error: {str(e)}").to_dict()),
            500,
        )


@app.route("/api/pudu/webhook/health", methods=["GET"])
def health_check():
    """Enhanced health check endpoint"""

    # Initialize dynamic database configuration
    try:
        db_config = DatabaseConfig(config_path)
        logger.info("Dynamic database configuration initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database configuration: {e}")
        db_config = None

    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "service": "pudu-callback-api-enhanced",
            "features": {
                "dynamic_database_routing": "enabled" if db_config else "disabled",
                "change_detection": "enabled",
                "notification_service": "enabled" if notification_service else "disabled",
            },
            "database_config": {
                "main_database": db_config.main_database_name if db_config else "unknown",
                "notification_databases": len(db_config.get_notification_databases()) if db_config else 0,
            }
        }
    )


if __name__ == "__main__":
    # Initialize enhanced callback handler with dynamic database config
    callback_handler = CallbackHandler(config_path)
    # Initialize dynamic database configuration
    try:
        db_config = DatabaseConfig(config_path)
        logger.info("Dynamic database configuration initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database configuration: {e}")
        db_config = None

    logger.info("Starting Pudu Robot Callback API Server...")
    logger.info(f"🔄 Dynamic database routing: {'✅ Enabled' if db_config else '❌ Disabled'}")
    logger.info(f"📧 Notification service: {'✅ Enabled' if notification_service else '❌ Disabled'}")
    logger.info(f"🔍 Change detection: ✅ Enabled")

    try:
        app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    finally:
        # Cleanup
        callback_handler.close()
        if db_config:
            db_config.close()