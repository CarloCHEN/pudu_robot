# src/pudu/reporting/core/report_scheduler.py
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import boto3
import json
from botocore.exceptions import ClientError

# Reuse existing RDS infrastructure
from pudu.rds.rdsTable import RDSTable
from .report_config import ReportConfig, ScheduleFrequency

logger = logging.getLogger(__name__)

class ReportScheduler:
    """Manages report scheduling using AWS EventBridge and database tracking"""

    def __init__(self, region: str = 'us-east-2', database_name: str = 'ry-vue'):
        """Initialize report scheduler"""
        self.region = region
        self.database_name = database_name
        self.events_client = boto3.client('events', region_name=region)

        # Lambda function ARN that will process reports (will be set externally)
        self.lambda_function_arn = None

        # Initialize database table for schedule tracking
        self._init_schedule_table()

        logger.info(f"Initialized ReportScheduler for region {region}")

    def set_lambda_function_arn(self, arn: str):
        """Set the ARN of the Lambda function that will process reports"""
        self.lambda_function_arn = arn
        logger.info(f"Set report processor Lambda ARN: {arn}")

    def _init_schedule_table(self):
        """Initialize the report schedules table"""
        try:
            self.schedule_table = RDSTable(
                connection_config="credentials.yaml",
                database_name=self.database_name,
                table_name="mnt_report_schedules",
                fields=None,  # Will be auto-detected
                primary_keys=["id"],
                reuse_connection=True
            )
            logger.info("Initialized report schedules table connection")
        except Exception as e:
            logger.error(f"Failed to initialize schedule table: {e}")
            self.schedule_table = None

    def create_or_update_schedule(self, customer_id: str, report_config: ReportConfig) -> Dict[str, Any]:
        """
        Create or update a scheduled report

        Args:
            customer_id: Customer identifier
            report_config: Report configuration

        Returns:
            Dict with success status and details
        """
        try:
            logger.info(f"Creating/updating report schedule for customer {customer_id}")

            if report_config.schedule == ScheduleFrequency.IMMEDIATE:
                # For immediate reports, no scheduling needed
                return {
                    'success': True,
                    'schedule_id': None,
                    'message': 'Immediate report - no scheduling required'
                }

            # Check if customer already has a schedule for this type
            existing_schedule = self._get_existing_schedule(customer_id, report_config)

            if existing_schedule:
                return self._update_existing_schedule(existing_schedule, report_config)
            else:
                return self._create_new_schedule(customer_id, report_config)

        except Exception as e:
            logger.error(f"Error creating/updating schedule for customer {customer_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'schedule_id': None
            }

    def _get_existing_schedule(self, customer_id: str, report_config: ReportConfig) -> Optional[Dict]:
        """Check for existing schedule for this customer and report type"""
        try:
            if not self.schedule_table:
                return None

            query = f"""
                SELECT * FROM mnt_report_schedules
                WHERE customer_id = '{customer_id}'
                AND status = 'active'
                AND JSON_EXTRACT(report_config, '$.service') = '{report_config.service}'
                LIMIT 1
            """

            results = self.schedule_table.query_data(query)
            return results[0] if results else None

        except Exception as e:
            logger.error(f"Error checking existing schedule: {e}")
            return None

    def _create_new_schedule(self, customer_id: str, report_config: ReportConfig) -> Dict[str, Any]:
        """Create a new scheduled report"""
        try:
            # Generate unique rule name
            rule_name = f"report-{customer_id}-{report_config.schedule.value}-{int(datetime.now().timestamp())}"

            # Get schedule expression
            schedule_expression = report_config.get_eventbridge_schedule_expression()
            if not schedule_expression:
                raise ValueError(f"No schedule expression available for {report_config.schedule.value}")

            # Create EventBridge rule
            rule_arn = self._create_eventbridge_rule(rule_name, schedule_expression, customer_id, report_config)

            # Calculate next run time
            next_run_time = self._calculate_next_run_time(report_config.schedule)

            # Save to database
            schedule_data = {
                'customer_id': customer_id,
                'report_config': report_config.to_json(),
                'schedule_frequency': report_config.schedule.value,
                'eventbridge_rule_name': rule_name,
                'eventbridge_rule_arn': rule_arn,
                'next_run_time': next_run_time,
                'status': 'active',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if self.schedule_table:
                self.schedule_table.insert_data(schedule_data)
                logger.info(f"Created new report schedule: {rule_name}")

            return {
                'success': True,
                'schedule_id': rule_name,
                'rule_arn': rule_arn,
                'next_run_time': next_run_time,
                'message': f'Scheduled {report_config.schedule.value} report created'
            }

        except Exception as e:
            logger.error(f"Error creating new schedule: {e}")
            return {
                'success': False,
                'error': str(e),
                'schedule_id': None
            }

    def _update_existing_schedule(self, existing_schedule: Dict, report_config: ReportConfig) -> Dict[str, Any]:
        """Update an existing scheduled report"""
        try:
            rule_name = existing_schedule.get('eventbridge_rule_name')

            # Update EventBridge rule
            schedule_expression = report_config.get_eventbridge_schedule_expression()
            self._update_eventbridge_rule(rule_name, schedule_expression, report_config.customer_id, report_config)

            # Update database record
            next_run_time = self._calculate_next_run_time(report_config.schedule)

            update_data = {
                'report_config': report_config.to_json(),
                'schedule_frequency': report_config.schedule.value,
                'next_run_time': next_run_time,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            if self.schedule_table:
                # Update using filters (assuming there's an update method)
                filters = {'eventbridge_rule_name': rule_name}
                for field, value in update_data.items():
                    self.schedule_table.update_field_by_filters(field, value, filters)

                logger.info(f"Updated existing report schedule: {rule_name}")

            return {
                'success': True,
                'schedule_id': rule_name,
                'next_run_time': next_run_time,
                'message': f'Updated {report_config.schedule.value} report schedule'
            }

        except Exception as e:
            logger.error(f"Error updating existing schedule: {e}")
            return {
                'success': False,
                'error': str(e),
                'schedule_id': None
            }

    def _create_eventbridge_rule(self, rule_name: str, schedule_expression: str,
                                customer_id: str, report_config: ReportConfig) -> str:
        """Create EventBridge rule for scheduled reports"""
        try:
            # Create the rule
            response = self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                Description=f"Scheduled report for customer {customer_id}",
                State='ENABLED'
            )

            rule_arn = response['RuleArn']

            # Add Lambda target if function ARN is available
            if self.lambda_function_arn:
                target_input = {
                    'customer_id': customer_id,
                    'report_config': report_config.to_dict(),
                    'trigger_source': 'scheduled'
                }

                self.events_client.put_targets(
                    Rule=rule_name,
                    Targets=[{
                        'Id': '1',
                        'Arn': self.lambda_function_arn,
                        'Input': json.dumps(target_input)
                    }]
                )

                logger.info(f"Created EventBridge rule with Lambda target: {rule_name}")
            else:
                logger.warning(f"No Lambda function ARN set - rule created without target: {rule_name}")

            return rule_arn

        except ClientError as e:
            logger.error(f"Error creating EventBridge rule: {e}")
            raise

    def _update_eventbridge_rule(self, rule_name: str, schedule_expression: str,
                                customer_id: str, report_config: ReportConfig):
        """Update existing EventBridge rule"""
        try:
            # Update the rule
            self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                Description=f"Scheduled report for customer {customer_id} (updated)",
                State='ENABLED'
            )

            # Update target input
            if self.lambda_function_arn:
                target_input = {
                    'customer_id': customer_id,
                    'report_config': report_config.to_dict(),
                    'trigger_source': 'scheduled'
                }

                self.events_client.put_targets(
                    Rule=rule_name,
                    Targets=[{
                        'Id': '1',
                        'Arn': self.lambda_function_arn,
                        'Input': json.dumps(target_input)
                    }]
                )

            logger.info(f"Updated EventBridge rule: {rule_name}")

        except ClientError as e:
            logger.error(f"Error updating EventBridge rule: {e}")
            raise

    def delete_schedule(self, customer_id: str, schedule_id: str) -> Dict[str, Any]:
        """Delete a scheduled report"""
        try:
            # Remove EventBridge rule
            try:
                self.events_client.remove_targets(Rule=schedule_id, Ids=['1'])
                self.events_client.delete_rule(Name=schedule_id)
                logger.info(f"Deleted EventBridge rule: {schedule_id}")
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
                logger.warning(f"EventBridge rule not found: {schedule_id}")

            # Update database record status
            if self.schedule_table:
                filters = {'eventbridge_rule_name': schedule_id, 'customer_id': customer_id}
                self.schedule_table.update_field_by_filters('status', 'deleted', filters)
                self.schedule_table.update_field_by_filters('deleted_at',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), filters)

            return {
                'success': True,
                'message': f'Schedule {schedule_id} deleted successfully'
            }

        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_customer_schedules(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all active schedules for a customer"""
        try:
            if not self.schedule_table:
                return []

            query = f"""
                SELECT * FROM mnt_report_schedules
                WHERE customer_id = '{customer_id}'
                AND status = 'active'
                ORDER BY created_at DESC
            """

            results = self.schedule_table.query_data(query)
            schedules = []

            for result in results:
                if isinstance(result, dict):
                    schedules.append(result)
                elif isinstance(result, tuple):
                    # Convert tuple to dict if needed
                    # This would depend on the table schema
                    pass

            return schedules

        except Exception as e:
            logger.error(f"Error getting customer schedules: {e}")
            return []

    def _calculate_next_run_time(self, frequency: ScheduleFrequency) -> str:
        """Calculate next run time based on frequency"""
        now = datetime.now()

        if frequency == ScheduleFrequency.DAILY:
            # Next day at 8 AM
            next_run = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        elif frequency == ScheduleFrequency.WEEKLY:
            # Next Monday at 8 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:  # Today is Monday
                days_until_monday = 7
            next_run = (now + timedelta(days=days_until_monday)).replace(hour=8, minute=0, second=0, microsecond=0)
        elif frequency == ScheduleFrequency.MONTHLY:
            # Next month, 1st day at 8 AM
            if now.month == 12:
                next_run = datetime(now.year + 1, 1, 1, 8, 0, 0)
            else:
                next_run = datetime(now.year, now.month + 1, 1, 8, 0, 0)
        else:
            next_run = now

        return next_run.strftime('%Y-%m-%d %H:%M:%S')

    def close(self):
        """Clean up resources"""
        try:
            if self.schedule_table:
                self.schedule_table.close()
            logger.info("ReportScheduler resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Example usage
if __name__ == "__main__":
    # Example usage
    scheduler = ReportScheduler()

    # Example report config
    test_form_data = {
        'service': 'robot-management',
        'contentCategories': ['robot-status', 'cleaning-tasks'],
        'timeRange': 'last-30-days',
        'detailLevel': 'detailed',
        'delivery': 'email',
        'schedule': 'weekly',
        'emailRecipients': ['user@example.com']
    }

    config = ReportConfig(test_form_data, 'test-customer-123')

    try:
        result = scheduler.create_or_update_schedule('test-customer-123', config)
        print(f"Schedule creation result: {result}")
    finally:
        scheduler.close()