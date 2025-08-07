import json
import logging
from datetime import datetime

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest

from callback_handler import CallbackHandler
from config import Config
from database_config import DatabaseConfig
from database_writer import DatabaseWriter
from models import CallbackResponse, CallbackStatus
from notifications import NotificationService, send_webhook_notification

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(Config.LOG_FILE), logging.StreamHandler()],
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize callback handler
callback_handler = CallbackHandler()

# Initialize database writer
try:
    database_writer = DatabaseWriter()
    logger.info("Database writer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database writer: {e}")
    database_writer = None

# Initialize notification service
try:
    notification_service = NotificationService()
    logger.info("Notification service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize notification service: {e}")
    notification_service = None


# curl -X POST "http://34.230.84.10:8000/api/pudu/webhook" -H "Content-Type: application/json" -H "CallbackCode: 1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq" -d '{"callback_type": "robotStatus", "data": {"robot_sn": "x123", "robot_status": "ONLINE", "timestamp": 123456}}'
@app.route("/api/pudu/webhook", methods=["POST"])
def pudu_webhook():
    """
    Main webhook endpoint for receiving Pudu robot callbacks
    """
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

        # Write to database if writer is available
        if database_writer:
            try:
                database_names, table_names, primary_key_values = callback_handler.write_to_database(data, database_writer)
            except Exception as e:
                logger.error(f"Failed to write callback to database: {e}")

        # Send notification if service is available
        if notification_service:
            config = DatabaseConfig()
            list_of_db_notification_needed = config.get_notification_needed()
            for database_name, table_name in zip(database_names, table_names):
                if database_name in list_of_db_notification_needed:
                    payload = {
                        "database_name": database_name,
                        "table_name": table_name,
                        "primary_key_values": primary_key_values
                    }
                    logger.info(f"Sending notification for {database_name}.{table_name} with payload: {payload}")
                    try:
                        send_webhook_notification(
                            callback_type=data.get("callback_type"),
                            callback_data=data.get("data", {}),
                            payload=payload,
                            notification_service=notification_service
                        )
                    except Exception as e:
                        logger.error(f"Failed to send notification for {database_name}.{table_name}: {e}")

        # Return result
        return jsonify(response.to_dict()), 200 if response.status == CallbackStatus.SUCCESS else 400

    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}", exc_info=True)
        return (
            jsonify(CallbackResponse(status=CallbackStatus.ERROR, message=f"Internal server error: {str(e)}").to_dict()),
            500,
        )


# curl -X GET "http://34.230.84.10:8000/api/pudu/webhook/health"
@app.route("/api/pudu/webhook/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "service": "pudu-callback-api",
            "notification_service": "enabled" if notification_service else "disabled",
            "database_writer": "enabled" if database_writer else "disabled",
        }
    )


if __name__ == "__main__":
    logger.info("Starting Pudu Robot Callback API Server...")
    logger.info(f"Notification service: {'✅ Enabled' if notification_service else '❌ Disabled'}")
    logger.info(f"Database writer: {'✅ Enabled' if database_writer else '❌ Disabled'}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
