# main.py
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
    'configs/database_config.yaml',
    'database_config.yaml',
    '../configs/database_config.yaml',
]

database_config_path = None
for path in config_paths:
    if os.path.exists(path):
        database_config_path = path
        break

if not database_config_path:
    logger.error("Database configuration file not found!")
    database_config_path = 'configs/database_config.yaml'  # Use default path


def detect_brand_from_data(data: dict) -> str:
    """
    Auto-detect brand from incoming callback data structure

    Args:
        data: Request JSON body

    Returns:
        Brand name ('pudu' or 'gas')
    """
    # Gas robots have these distinctive fields
    if 'messageTypeId' in data and 'appId' in data:
        logger.info("🤖 Detected Gas robot callback (messageTypeId + appId)")
        return 'gas'

    # Pudu robots have callback_type field
    if 'callback_type' in data:
        logger.info("🤖 Detected Pudu robot callback (callback_type)")
        return 'pudu'

    # Additional Gas detection - check for payload structure
    if 'payload' in data and isinstance(data.get('payload'), dict):
        payload = data['payload']
        if 'serialNumber' in payload or 'taskReport' in payload:
            logger.info("🤖 Detected Gas robot callback (payload structure)")
            return 'gas'

    # Fallback: Check for Pudu-specific fields
    if 'sn' in data or 'robot_id' in data:
        logger.info("🤖 Detected Pudu robot callback (sn field)")
        return 'pudu'

    # Default to pudu for backward compatibility
    logger.warning("⚠️ Could not definitively detect brand, defaulting to Pudu")
    return 'pudu'


def unified_webhook_handler():
    """
    Unified webhook endpoint that auto-detects brand and processes accordingly
    """
    try:
        # Log incoming request
        logger.info(f"Received webhook callback from {request.remote_addr}")

        # Validate request is JSON
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify(
                CallbackResponse(status=CallbackStatus.ERROR, message="Request must be JSON").to_dict()
            ), 400

        # Parse JSON body
        try:
            data = request.get_json()
        except BadRequest:
            logger.error("Malformed JSON received")
            return jsonify(
                CallbackResponse(status=CallbackStatus.ERROR, message="Malformed JSON").to_dict()
            ), 400

        logger.info(f"Callback data: {json.dumps(data, indent=2)}")

        # Auto-detect brand from data structure
        brand = detect_brand_from_data(data)
        logger.info(f"🎯 Processing as {brand.upper()} callback")

        # Initialize brand-specific callback handler
        callback_handler = CallbackHandler(database_config_path, brand=brand)

        # Initialize database configuration for notifications
        try:
            db_config = DatabaseConfig(database_config_path)
            logger.info("Dynamic database configuration initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database configuration: {e}")
            db_config = None

        # Lowercase all headers for consistent access
        lower_headers = {k.lower(): v for k, v in request.headers.items()}
        logger.debug(f"Request headers (lowercased): {lower_headers}")

        # Verify request using brand-specific verification
        is_valid, error_message = callback_handler.verify_request(data, lower_headers)

        if not is_valid:
            logger.error(f"{brand.upper()} verification failed: {error_message}")
            callback_handler.close()
            if db_config:
                db_config.close()
            return jsonify(
                CallbackResponse(status=CallbackStatus.ERROR, message=error_message).to_dict()
            ), 401

        logger.info(f"{brand.upper()} verification passed ✅")

        # Process the callback
        response = callback_handler.process_callback(data)

        # Write to database with change detection and dynamic routing
        try:
            database_names, table_names, changes_detected = (
                callback_handler.write_to_database_with_change_detection(data)
            )
            logger.info(f"Database write completed. Changes detected in {len(changes_detected)} tables.")
        except Exception as e:
            logger.error(f"Failed to write callback to database: {e}", exc_info=True)
            database_names, table_names, changes_detected = [], [], {}

        # Send notifications for detected changes
        if notification_service and changes_detected and db_config:
            # Get abstract callback type for notification context
            abstract_type = callback_handler.brand_config.map_callback_type(data)
            callback_type = abstract_type or "unknown"

            notification_databases = db_config.get_notification_databases()

            total_successful_notifications = 0
            total_failed_notifications = 0

            for (database_name, table_name), changes in changes_detected.items():
                try:
                    # Check if this database needs notifications
                    if database_name in notification_databases:
                        logger.info(
                            f"Sending notifications for {len(changes)} changes in {database_name}.{table_name}"
                        )

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

            logger.info(
                f"📧 Total notifications: {total_successful_notifications} successful, "
                f"{total_failed_notifications} failed"
            )

        callback_handler.close()
        if db_config:
            db_config.close()

        # Return result
        return jsonify(response.to_dict()), 200 if response.status == CallbackStatus.SUCCESS else 400

    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}", exc_info=True)
        return (
            jsonify(
                CallbackResponse(
                    status=CallbackStatus.ERROR,
                    message=f"Internal server error: {str(e)}"
                ).to_dict()
            ),
            500,
        )


# Unified webhook endpoint - auto-detects brand
@app.route("/api/webhook", methods=["POST"])
def webhook():
    """Unified webhook endpoint - auto-detects brand from data structure"""
    return unified_webhook_handler()


# Brand-specific endpoints (for backward compatibility)
@app.route("/api/pudu/webhook", methods=["POST"])
def pudu_webhook():
    """Pudu robot webhook endpoint (backward compatibility)"""
    logger.info("📍 Called via Pudu-specific endpoint")
    return unified_webhook_handler()


@app.route("/api/gas/webhook", methods=["POST"])
def gas_webhook():
    """Gas robot webhook endpoint (backward compatibility)"""
    logger.info("📍 Called via Gas-specific endpoint")
    return unified_webhook_handler()


@app.route("/api/webhook/health", methods=["GET"])
def health_check():
    """Enhanced health check endpoint with multi-brand information"""

    # Get handler info for both brands
    handler_info = {}
    for brand in ['pudu', 'gas']:
        try:
            handler = CallbackHandler(database_config_path, brand=brand)
            handler_info[brand] = handler.get_handler_info()
            handler.close()
        except Exception as e:
            logger.error(f"Failed to get {brand} handler info: {e}")
            handler_info[brand] = {"error": str(e)}

    # Get database config info
    try:
        db_config = DatabaseConfig(database_config_path)
        db_info = {
            "main_database": db_config.main_database_name,
            "notification_databases": len(db_config.get_notification_databases()),
        }
        db_config.close()
    except Exception as e:
        logger.error(f"Failed to get database config: {e}")
        db_info = {"error": str(e)}

    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "service": "robot-webhook-api",
            "version": "2.0-unified",
            "features": {
                "auto_brand_detection": "enabled",
                "multi_brand_support": "enabled",
                "dynamic_database_routing": "enabled",
                "change_detection": "enabled",
                "notification_service": "enabled" if notification_service else "disabled",
            },
            "supported_brands": {
                "pudu": handler_info.get('pudu', {}),
                "gas": handler_info.get('gas', {})
            },
            "database_config": db_info,
            "supported_endpoints": [
                "/api/webhook (auto-detects brand)",
                "/api/pudu/webhook (legacy)",
                "/api/gas/webhook (legacy)"
            ]
        }
    )


@app.route("/api/<brand>/webhook/health", methods=["GET"])
def brand_health_check(brand: str):
    """Brand-specific health check endpoint"""

    # Validate brand
    supported_brands = ["pudu", "gas"]
    if brand not in supported_brands:
        return jsonify({
            "status": "error",
            "message": f"Unsupported brand: {brand}",
            "supported_brands": supported_brands
        }), 400

    try:
        handler = CallbackHandler(database_config_path, brand=brand)
        handler_info = handler.get_handler_info()
        handler.close()

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "brand": brand,
            "endpoints": [
                f"/api/{brand}/webhook (legacy)",
                "/api/webhook (auto-detect)"
            ],
            "configuration": handler_info
        })
    except Exception as e:
        logger.error(f"Failed to get {brand} handler info: {e}")
        return jsonify({
            "status": "error",
            "brand": brand,
            "message": str(e)
        }), 500


if __name__ == "__main__":
    logger.info("Starting Multi-Brand Robot Callback API Server...")
    logger.info(f"🤖 Auto-detection: ✅ Enabled (Pudu & Gas)")
    logger.info(f"🔄 Dynamic database routing: ✅ Enabled")
    logger.info(f"📧 Notification service: {'✅ Enabled' if notification_service else '❌ Disabled'}")
    logger.info(f"🔍 Change detection: ✅ Enabled")
    logger.info(f"🌐 Supported endpoints:")
    logger.info(f"   - POST /api/webhook (auto-detects brand) ⭐ PRIMARY")
    logger.info(f"   - POST /api/pudu/webhook (legacy)")
    logger.info(f"   - POST /api/gas/webhook (legacy)")
    logger.info(f"   - GET  /api/webhook/health")
    logger.info(f"   - GET  /api/<brand>/webhook/health")

    try:
        app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    finally:
        logger.info("Shutting down server...")