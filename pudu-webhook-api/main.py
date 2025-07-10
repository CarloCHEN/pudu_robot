from flask import Flask, request, jsonify
import logging
import json
import time
from datetime import datetime
from dotenv import load_dotenv

from callback_handler import CallbackHandler
from models import CallbackResponse, CallbackStatus
from config import Config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize callback handler
callback_handler = CallbackHandler()

# curl -X POST "http://34.230.84.10:8000/api/pudu/webhook" -H "Content-Type: application/json" -H "CallbackCode: 1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq" -d '{"callback_type": "robotStatus", "data": {"robot_sn": "x123", "robot_status": "ONLINE", "timestamp": 123456}}'
@app.route('/api/pudu/webhook', methods=['POST'])
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
            return jsonify(CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Request must be JSON"
            ).to_dict()), 400

        # Parse JSON body
        data = request.get_json()
        logger.info(f"Callback data: {json.dumps(data, indent=2)}")

        # Lowercase all headers for consistent access
        lower_headers = {k.lower(): v for k, v in request.headers.items()}
        logger.info(f"Request headers (lowercased): {lower_headers}")

        # Extract CallbackCode from headers (case-insensitive)
        received_callback_code = (
            lower_headers.get("callbackcode") or
            lower_headers.get("x-callback-code")
        )

        if not received_callback_code:
            logger.error("Missing CallbackCode in request headers")
            return jsonify(CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Missing CallbackCode header"
            ).to_dict()), 400

        # Get expected code from config
        expected_callback_code = Config.PUDU_CALLBACK_CODE
        if not expected_callback_code:
            logger.error("PUDU_CALLBACK_CODE not configured in environment")
            return jsonify(CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Server configuration error"
            ).to_dict()), 500

        # Verify CallbackCode
        if received_callback_code != expected_callback_code:
            logger.error(f"Invalid CallbackCode received: {received_callback_code}")
            return jsonify(CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Invalid CallbackCode"
            ).to_dict()), 401

        # Process the callback
        response = callback_handler.process_callback(data)

        # Return result
        return jsonify(response.to_dict()), 200 if response.status == CallbackStatus.SUCCESS else 400

    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}", exc_info=True)
        return jsonify(CallbackResponse(
            status=CallbackStatus.ERROR,
            message=f"Internal server error: {str(e)}"
        ).to_dict()), 500

# curl -X GET "http://34.230.84.10:8000/api/pudu/webhook/health"
@app.route('/api/pudu/webhook/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime('%Y-%m-%d'),
        "service": "pudu-callback-api"
    })

if __name__ == '__main__':
    logger.info("Starting Pudu Callback API Server...")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
