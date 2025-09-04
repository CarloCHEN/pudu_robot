# src/pudu/reporting/lambda/report_generator_lambda.py
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
    Lambda function to generate and deliver reports
    Triggered by EventBridge rules or direct API calls
    """
    start_time = datetime.now()
    function_name = context.function_name if context else 'unknown'

    try:
        logger.info("🚀 Starting report generation Lambda")
        logger.info(f"📅 Lambda execution time: {start_time}")
        logger.info(f"🔧 Event received: {json.dumps(event)}")

        # Add current directory to Python path to ensure imports work
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # Add parent directories for reporting modules
        reporting_dir = os.path.dirname(current_dir)
        pudu_dir = os.path.dirname(reporting_dir)
        src_dir = os.path.dirname(pudu_dir)

        for path in [reporting_dir, pudu_dir, src_dir]:
            if path not in sys.path:
                sys.path.insert(0, path)

        # Import report generation modules
        try:
            from pudu.reporting.core.report_generator import ReportGenerator
            from pudu.reporting.core.report_config import ReportConfig
            from pudu.reporting.services.report_delivery_service import ReportDeliveryService
            logger.info("✅ Successfully imported reporting modules")
        except ImportError as e:
            logger.error(f"❌ Failed to import reporting modules: {e}")
            logger.error(f"Current directory contents: {os.listdir('.')}")
            raise

        # Parse event to get report configuration
        customer_id = event.get('customer_id')
        report_config_data = event.get('report_config', {})
        trigger_source = event.get('trigger_source', 'direct')

        if not customer_id:
            raise ValueError("customer_id is required")

        if not report_config_data:
            raise ValueError("report_config is required")

        logger.info(f"🔧 Processing report for customer: {customer_id}")
        logger.info(f"📋 Trigger source: {trigger_source}")

        # Create report configuration
        report_config = ReportConfig(report_config_data, customer_id)

        # Validate configuration
        validation_errors = report_config.validate()
        if validation_errors:
            logger.error(f"❌ Report configuration validation failed: {validation_errors}")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': f"Configuration validation failed: {', '.join(validation_errors)}",
                    'customer_id': customer_id,
                    'timestamp': datetime.now().isoformat()
                })
            }

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
            raise FileNotFoundError("Configuration file not found")

        logger.info(f"🔧 Using config file: {config_path}")

        # Initialize report generator
        logger.info("🔧 Initializing report generator...")
        report_generator = ReportGenerator(config_path)

        # Generate report
        logger.info("▶️ Starting report generation...")
        generation_result = report_generator.generate_report(report_config)

        if not generation_result['success']:
            logger.error(f"❌ Report generation failed: {generation_result['error']}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': generation_result['error'],
                    'customer_id': customer_id,
                    'timestamp': datetime.now().isoformat()
                })
            }

        logger.info("✅ Report generation completed successfully")

        # Initialize delivery service
        logger.info("📧 Initializing delivery service...")
        delivery_service = ReportDeliveryService()

        # Deliver report
        logger.info(f"📤 Delivering report via {report_config.delivery.value}...")
        delivery_result = delivery_service.deliver_report(
            generation_result['report_html'],
            generation_result['metadata'],
            report_config
        )

        # Calculate total execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"⏱️ Total execution time: {execution_time:.2f} seconds")

        # Prepare response
        response_data = {
            'success': True,
            'customer_id': customer_id,
            'execution_time_seconds': execution_time,
            'generation_result': {
                'robots_included': len(generation_result.get('target_robots', [])),
                'records_processed': generation_result['metadata'].get('total_records_processed', 0),
                'detail_level': report_config.detail_level.value,
                'content_categories': report_config.content_categories
            },
            'delivery_result': {
                'method': delivery_result['delivery_method'],
                'success': delivery_result['success'],
                'storage_url': delivery_result.get('storage_url'),
                'email_sent': delivery_result.get('email_sent', False),
                'emails_successful': delivery_result.get('emails_successful', 0),
                'emails_total': delivery_result.get('emails_total', 0)
            },
            'timestamp': datetime.now().isoformat()
        }

        success_overall = generation_result['success'] and delivery_result['success']
        status_code = 200 if success_overall else 207  # 207 = Multi-Status (partial success)

        if success_overall:
            logger.info("✅ Report generation and delivery completed successfully")
        else:
            logger.warning("⚠️ Report generation completed with partial success")
            if delivery_result.get('error'):
                response_data['delivery_error'] = delivery_result['error']

        return {
            'statusCode': status_code,
            'body': json.dumps(response_data)
        }

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        error_msg = f"Report generation Lambda failed: {str(e)}"
        logger.error(f"💥 {error_msg}", exc_info=True)

        # Return error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': error_msg,
                'customer_id': event.get('customer_id', 'unknown'),
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat()
            })
        }

    finally:
        # Cleanup resources
        try:
            if 'report_generator' in locals():
                report_generator.close()
            logger.info("🔒 Resources cleaned up")
        except Exception as e:
            logger.warning(f"Warning during cleanup: {e}")

# For local testing
if __name__ == "__main__":
    # Test the Lambda function locally
    test_event = {
        "customer_id": "test-customer-123",
        "report_config": {
            "service": "robot-management",
            "contentCategories": ["robot-status", "cleaning-tasks", "performance"],
            "timeRange": "last-7-days",
            "detailLevel": "detailed",
            "delivery": "in-app",
            "schedule": "immediate"
        },
        "trigger_source": "test"
    }

    test_context = type('Context', (), {
        'function_name': 'test-report-generator',
        'function_version': '1',
        'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-report-generator',
        'memory_limit_in_mb': 1024,
        'remaining_time_in_millis': lambda: 300000
    })()

    result = lambda_handler(test_event, test_context)
    print(f"Test result: {json.dumps(result, indent=2)}")