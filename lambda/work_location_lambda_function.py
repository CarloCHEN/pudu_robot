import json
import logging
from datetime import datetime
import os
import sys

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to run the robot work location service every 1 minute
    Handles coordinate transformations and archival with 30-day retention
    Triggered by EventBridge rule
    """
    start_time = datetime.now()
    function_name = context.function_name if context else 'unknown'

    try:
        logger.info("🗺️ Starting Pudu robot work location service Lambda")
        logger.info(f"📅 Lambda execution time: {start_time}")
        logger.info(f"🔧 Event received: {json.dumps(event)}")
        logger.info(f"🐍 Python path: {sys.path}")

        # Add current directory to Python path to ensure imports work
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # Import modules
        try:
            from pudu.services.work_location_service import WorkLocationService
            from pudu.configs.database_config_loader import DynamicDatabaseConfig
            logger.info("✅ Successfully imported work location service modules")
        except ImportError as e:
            logger.error(f"❌ Failed to import work location service modules: {e}")
            logger.error(f"Current directory contents: {os.listdir('.')}")
            if os.path.exists('pudu'):
                logger.error(f"pudu directory contents: {os.listdir('pudu')}")
                if os.path.exists('pudu/services'):
                    logger.error(f"pudu/services directory contents: {os.listdir('pudu/services')}")
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

        # Load S3 configuration
        def _load_s3_config(config_path: str):
            try:
                import yaml
                with open(config_path, 'r') as file:
                    config = yaml.safe_load(file)
                    s3_config = config.get('s3_config', {})

                    if s3_config:
                        logger.info(f"Loaded S3 config: region={s3_config.get('region', 'us-east-2')}, "
                                  f"buckets={len(s3_config.get('buckets', {}))}")
                    else:
                        logger.warning("No S3 configuration found - archival may not work")

                    return s3_config
            except Exception as e:
                logger.error(f"Error loading S3 config: {e}")
                return {}

        # Initialize configuration and service
        logger.info("🔧 Initializing work location service...")
        config = DynamicDatabaseConfig(config_path)
        s3_config = _load_s3_config(config_path)

        # run backfill only on the first run of the day
        run_backfill = True 

        work_location_service = WorkLocationService(config, s3_config, run_backfill=run_backfill)

        # Run the work location service
        logger.info("▶️ Starting work location service execution...")
        success = work_location_service.run_work_location_updates()

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️ Execution time: {execution_time:.2f} seconds")

        if success:
            logger.info("✅ Work location service completed successfully")
        else:
            logger.error("❌ Work location service completed with failures")

        # Return response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Work location service completed successfully' if success else 'Work location service completed with failures',
                'execution_time_seconds': execution_time,
                'success': success,
                'timestamp': datetime.now().isoformat(),
                'service': 'work_location'
            })
        }

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"Work location service execution failed: {str(e)}"
        logger.error(f"💥 {error_msg}", exc_info=True)

        # Return error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': error_msg,
                'error': str(e),
                'execution_time_seconds': execution_time,
                'success': False,
                'timestamp': datetime.now().isoformat(),
                'service': 'work_location'
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
        'function_name': 'test-pudu-robot-work-location',
        'function_version': '1',
        'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-pudu-robot-work-location',
        'memory_limit_in_mb': 512,
        'remaining_time_in_millis': lambda: 300000
    })()

    result = lambda_handler(test_event, test_context)
    print(f"Test result: {json.dumps(result, indent=2)}")