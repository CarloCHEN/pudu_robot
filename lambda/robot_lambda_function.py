import json
import boto3
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
    Triggered by EventBridge rule
    """
    start_time = datetime.now()

    try:
        logger.info("🚀 Starting Pudu robot data pipeline Lambda")
        logger.info(f"📅 Lambda execution time: {start_time}")
        logger.info(f"🔧 Event received: {json.dumps(event)}")
        logger.info(f"🐍 Python path: {sys.path}")

        # Calculate time range (last 7 minutes with overlap for safety)
        now = datetime.now()
        end_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
        start_time_str = (now - timedelta(minutes=7)).strftime('%Y-%m-%d %H:%M:%S')

        logger.info(f"📅 Processing time range: {start_time_str} to {end_time_str}")

        # Add current directory to Python path to ensure imports work
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # Import your app module from the correct location
        try:
            from pudu.app.main import App
            logger.info("✅ Successfully imported pudu.app.main")
        except ImportError as e:
            logger.error(f"❌ Failed to import pudu.app.main: {e}")
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
        app = App(config_path)

        # Log configuration summary
        try:
            config_summary = app.get_config_summary()
            logger.info(f"📊 Configuration loaded: {config_summary.get('total_tables', 'N/A')} tables across {len(config_summary.get('databases', []))} databases")
        except Exception as e:
            logger.warning(f"⚠️ Could not get config summary: {e}")

        # Run the pipeline
        logger.info("▶️ Starting data pipeline execution...")
        success = app.run(start_time=start_time_str, end_time=end_time_str)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️ Execution time: {execution_time:.2f} seconds")

        if success:
            logger.info("✅ Pipeline completed successfully")

            # Return success response
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Pipeline completed successfully',
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'execution_time_seconds': execution_time,
                    'success': True,
                    'timestamp': datetime.now().isoformat()
                })
            }
        else:
            logger.error("❌ Pipeline completed with failures")

            # Return failure response but don't raise exception
            return {
                'statusCode': 200,  # Still return 200 to avoid Lambda retries
                'body': json.dumps({
                    'message': 'Pipeline completed with failures',
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'execution_time_seconds': execution_time,
                    'success': False,
                    'timestamp': datetime.now().isoformat()
                })
            }

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"Pipeline execution failed: {str(e)}"
        logger.error(f"💥 {error_msg}", exc_info=True)

        # Send error notification (optional)
        try:
            send_error_notification(error_msg, str(e))
        except Exception as notification_error:
            logger.error(f"Failed to send error notification: {notification_error}")

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

def send_error_notification(message, error_details):
    """
    Send error notification to SNS topic (optional)
    """
    try:
        sns_topic_arn = os.getenv('ERROR_SNS_TOPIC_ARN')
        if not sns_topic_arn:
            logger.info("No SNS topic configured for error notifications")
            return

        sns = boto3.client('sns')

        notification_message = {
            'title': '🚨 Pudu Robot Pipeline Error',
            'message': message,
            'error_details': error_details,
            'timestamp': datetime.now().isoformat(),
            'function_name': os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'unknown'),
            'region': os.getenv('AWS_REGION', 'unknown')
        }

        sns.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(notification_message, indent=2),
            Subject='Pudu Robot Pipeline Error'
        )

        logger.info("✅ Error notification sent successfully")

    except Exception as e:
        logger.error(f"Failed to send error notification: {e}")

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