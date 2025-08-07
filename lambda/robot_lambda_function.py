import json
import logging
from datetime import datetime, timedelta
import os
import sys

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to run the robot data pipeline every 5 minutes
    NOW INCLUDES: Support ticket monitoring and notifications
    Triggered by EventBridge rule
    """
    start_time = datetime.now()
    function_name = context.function_name if context else 'unknown'

    try:
        logger.info("🚀 Starting Pudu robot data pipeline Lambda")
        logger.info(f"📅 Lambda execution time: {start_time}")
        logger.info(f"🔧 Event received: {json.dumps(event)}")
        logger.info(f"🐍 Python path: {sys.path}")

        # Calculate time range from 00:00:00 to 23:59:59
        now = datetime.now()
        # Start of the previous day (00:00:00)
        start_time_str = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        # End of the current day (23:59:59)
        end_time_str = now.replace(hour=23, minute=59, second=59, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        logger.info(f"📅 Processing time range: {start_time_str} to {end_time_str}")

        # Add current directory to Python path to ensure imports work
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # Import your app module from the correct location
        try:
            from pudu.app.main import App
            from pudu.app.event_support import EventSupportApp
            logger.info("✅ Successfully imported pudu.app.main and pudu.app.event_support")
        except ImportError as e:
            logger.error(f"❌ Failed to import pudu.app.main and pudu.app.event_support: {e}")
            logger.error(f"Current directory contents: {os.listdir('.')}")
            if os.path.exists('pudu'):
                logger.error(f"pudu directory contents: {os.listdir('pudu')}")
                if os.path.exists('pudu/app'):
                    logger.error(f"pudu/app directory contents: {os.listdir('pudu/app')}")
            raise

        # Get configuration file path - try multiple locations
        config_paths = [
            'database_config.yaml',
            '../src/pudu/configs/database_config.yaml',
            'src/pudu/configs/database_config.yaml',
            'pudu/configs/database_config.yaml',
            '/opt/database_config.yaml'
        ]

        config_path = None
        for path in config_paths:
            if os.path.exists(path):
                config_path = path
                break

        if not config_path:
            logger.error(f"❌ Config file not found in any of these locations: {config_paths}")
            logger.error(f"Current directory contents: {os.listdir('.')}")
            raise FileNotFoundError("Configuration file not found")

        logger.info(f"🔧 Using config file: {config_path}")

        # Initialize app with configuration
        logger.info("🔧 Initializing application...")
        app = App(config_path) # Main app for robot data pipeline
        event_support_app = EventSupportApp(config_path) # App for support ticket monitoring and notifications

        # Monitor support tickets FIRST (before running main pipeline)
        logger.info("🎫 Monitoring support tickets...")
        success, ticket_count = event_support_app.run(function_name)
        if success:
            logger.info(f"✅ Support ticket monitoring completed successfully with {ticket_count} new tickets")
        else:
            logger.error("❌ Support ticket monitoring completed with failures")

        # Run the main robot data pipeline
        logger.info("▶️ Starting robot data pipeline execution...")
        success = app.run(start_time=start_time_str, end_time=end_time_str)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️ Execution time: {execution_time:.2f} seconds")

        if success:
            logger.info("✅ Pipeline completed successfully")
        else:
            logger.error("❌ Pipeline completed with failures")

        # Return response with ticket information
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Pipeline completed successfully' if success else 'Pipeline completed with failures',
                'start_time': start_time_str,
                'end_time': end_time_str,
                'execution_time_seconds': execution_time,
                'new_support_tickets': ticket_count,
                'success': success,
                'timestamp': datetime.now().isoformat()
            })
        }

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"Pipeline execution failed: {str(e)}"
        logger.error(f"💥 {error_msg}", exc_info=True)

        # Return error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': error_msg,
                'error': str(e),
                'execution_time_seconds': execution_time,
                'success': False,
                'timestamp': datetime.now().isoformat()
            })
        }


# For local testing
if __name__ == "__main__":
    # Test the Lambda function locally
    import sys
    import os

    # Add the src directory to Python path for local testing
    sys.path.insert(0, '../src')

    test_event = {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "detail": {}
    }

    test_context = type('Context', (), {
        'function_name': 'test-pudu-robot-pipeline',
        'function_version': '1',
        'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-pudu-robot-pipeline',
        'memory_limit_in_mb': 512,
        'remaining_time_in_millis': lambda: 300000
    })()

    result = lambda_handler(test_event, test_context)
    print(f"Test result: {json.dumps(result, indent=2)}")