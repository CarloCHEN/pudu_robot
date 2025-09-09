from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ReportDetailLevel(Enum):
    SUMMARY = "summary"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"

class DeliveryMethod(Enum):
    IN_APP = "in-app"
    EMAIL = "email"

class ScheduleFrequency(Enum):
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class ReportConfig:
    """Configuration class for report generation based on HTML form data"""

    def __init__(self, form_data: Dict[str, Any], customer_id: str):
        self.customer_id = customer_id
        self.form_data = form_data
        self._parse_configuration()

    def _parse_configuration(self):
        """Parse HTML form data into structured configuration"""
        # Service Selection
        self.service = self.form_data.get('service', 'robot-management')
        self.content_categories = self.form_data.get('contentCategories', [])

        # Hardware Selection
        self.location = self._parse_location()
        self.robot = self._parse_robot()
        self.robot_types = self.form_data.get('robotTypes', [])

        # Report Configuration
        self.time_range = self.form_data.get('timeRange', 'last-30-days')
        self.custom_date_range = self._parse_custom_dates()
        self.detail_level = ReportDetailLevel(self.form_data.get('detailLevel', 'detailed'))
        self.delivery = DeliveryMethod(self.form_data.get('delivery', 'in-app'))
        self.schedule = ScheduleFrequency(self.form_data.get('schedule', 'immediate'))

        # Email configuration
        self.email_recipients = self.form_data.get('emailRecipients', [])

        # Recurring schedule configuration
        self.recurring_frequency = self.form_data.get('recurringFrequency', 'weekly')
        self.recurring_start_date = self.form_data.get('recurringStartDate')

    def _parse_location(self) -> Dict[str, str]:
        """Parse location selection"""
        location_data = self.form_data.get('location', {})
        return {
            'country': location_data.get('country', ''),
            'state': location_data.get('state', ''),
            'city': location_data.get('city', ''),
            'building': location_data.get('building', '')
        }

    def _parse_robot(self) -> Dict[str, str]:
        """Parse robot selection"""
        robot_data = self.form_data.get('robot', {})
        return {
            'name': robot_data.get('name', ''),
            'serialNumber': robot_data.get('serialNumber', '')
        }

    def _parse_custom_dates(self) -> Optional[Dict[str, str]]:
        """Parse custom date range if specified"""
        if self.time_range == 'custom':
            return {
                'start_date': self.form_data.get('customStartDate'),
                'end_date': self.form_data.get('customEndDate')
            }
        return None

    def get_date_range(self, include_comparison_period: bool = False) -> Tuple[str, str]:
        """
        Get actual start and end dates based on configuration

        Args:
            include_comparison_period: If True, extends date range to include previous period for comparison

        Returns:
            Tuple of (start_date, end_date) strings
        """
        now = datetime.now()

        if self.time_range == 'custom' and self.custom_date_range:
            start_date = self.custom_date_range['start_date']
            end_date = self.custom_date_range['end_date']

            if include_comparison_period:
                # Calculate previous period length and extend start date
                current_start = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S') if ' ' in start_date else datetime.strptime(start_date, '%Y-%m-%d')
                current_end = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S') if ' ' in end_date else datetime.strptime(end_date, '%Y-%m-%d')
                period_length = current_end - current_start
                comparison_start = current_start - period_length
                start_date = comparison_start.strftime('%Y-%m-%d 00:00:00')

            return start_date, end_date

        elif self.time_range == 'last-7-days':
            days = 7
            if include_comparison_period:
                days = 14  # Include previous 7 days for comparison
            start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d 00:00:00')
            end_date = now.strftime('%Y-%m-%d 23:59:59')

        elif self.time_range == 'last-30-days':
            days = 30
            if include_comparison_period:
                days = 60  # Include previous 30 days for comparison
            start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d 00:00:00')
            end_date = now.strftime('%Y-%m-%d 23:59:59')

        elif self.time_range == 'last-90-days':
            days = 90
            if include_comparison_period:
                days = 180  # Include previous 90 days for comparison
            start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d 00:00:00')
            end_date = now.strftime('%Y-%m-%d 23:59:59')

        else:
            # Default to last 30 days
            days = 30
            if include_comparison_period:
                days = 60
            start_date = (now - timedelta(days=days)).strftime('%Y-%m-%d 00:00:00')
            end_date = now.strftime('%Y-%m-%d 23:59:59')

        return start_date, end_date

    def get_comparison_periods(self) -> Tuple[Tuple[str, str], Tuple[str, str]]:
        """
        Get current and previous period date ranges for comparison

        Returns:
            Tuple of ((current_start, current_end), (previous_start, previous_end))
        """
        now = datetime.now()

        if self.time_range == 'custom' and self.custom_date_range:
            current_start_str = self.custom_date_range['start_date']
            current_end_str = self.custom_date_range['end_date']

            current_start = datetime.strptime(current_start_str, '%Y-%m-%d %H:%M:%S') if ' ' in current_start_str else datetime.strptime(current_start_str, '%Y-%m-%d')
            current_end = datetime.strptime(current_end_str, '%Y-%m-%d %H:%M:%S') if ' ' in current_end_str else datetime.strptime(current_end_str, '%Y-%m-%d')

            period_length = current_end - current_start
            previous_start = current_start - period_length
            previous_end = current_start

        elif self.time_range == 'last-7-days':
            current_start = now - timedelta(days=7)
            current_end = now
            previous_start = now - timedelta(days=14)
            previous_end = now - timedelta(days=7)

        elif self.time_range == 'last-30-days':
            current_start = now - timedelta(days=30)
            current_end = now
            previous_start = now - timedelta(days=60)
            previous_end = now - timedelta(days=30)

        elif self.time_range == 'last-90-days':
            current_start = now - timedelta(days=90)
            current_end = now
            previous_start = now - timedelta(days=180)
            previous_end = now - timedelta(days=90)

        else:
            # Default to last 30 days
            current_start = now - timedelta(days=30)
            current_end = now
            previous_start = now - timedelta(days=60)
            previous_end = now - timedelta(days=30)

        current_period = (
            current_start.strftime('%Y-%m-%d 00:00:00'),
            current_end.strftime('%Y-%m-%d 23:59:59')
        )

        previous_period = (
            previous_start.strftime('%Y-%m-%d 00:00:00'),
            previous_end.strftime('%Y-%m-%d 23:59:59')
        )

        return current_period, previous_period

    def get_target_robots(self) -> List[str]:
        """Get list of target robot serial numbers based on configuration"""
        # NOTE: This method returns empty list if location-based or name-based selection
        # Actual robot resolution is handled by RobotLocationResolver in the generator

        # Only return direct serial number if specified
        robot_sn = self.robot.get('serialNumber', '').strip()
        if robot_sn:
            return [robot_sn]

        # For all other cases (name-based or location-based), return empty list
        # The ReportGenerator will handle the resolution using RobotLocationResolver
        return []

    def get_eventbridge_schedule_expression(self) -> Optional[str]:
        """Generate EventBridge cron expression for scheduled reports"""
        if self.schedule == ScheduleFrequency.IMMEDIATE:
            return None

        # Default to 8 AM for all scheduled reports
        if self.schedule == ScheduleFrequency.DAILY:
            return "cron(0 8 * * ? *)"  # Daily at 8 AM
        elif self.schedule == ScheduleFrequency.WEEKLY:
            return "cron(0 8 ? * MON *)"  # Weekly on Monday at 8 AM
        elif self.schedule == ScheduleFrequency.MONTHLY:
            return "cron(0 8 1 * ? *)"  # Monthly on 1st at 8 AM

        return None

    def get_content_categories_display(self) -> List[str]:
        """Get human-readable content category names"""
        category_map = {
            'robot-status': 'Robot Status & Events',
            'cleaning-tasks': 'Cleaning Tasks',
            'charging-tasks': 'Charging Tasks',
            'performance': 'Performance Analytics',
            'cost': 'Cost Analysis'
        }
        return [category_map.get(cat, cat) for cat in self.content_categories]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for storage/transmission"""
        return {
            'customer_id': self.customer_id,
            'service': self.service,
            'content_categories': self.content_categories,
            'location': self.location,
            'robot': self.robot,
            'robot_types': self.robot_types,
            'time_range': self.time_range,
            'custom_date_range': self.custom_date_range,
            'detail_level': self.detail_level.value,
            'delivery': self.delivery.value,
            'schedule': self.schedule.value,
            'email_recipients': self.email_recipients,
            'recurring_frequency': self.recurring_frequency,
            'recurring_start_date': self.recurring_start_date
        }

    def to_json(self) -> str:
        """Convert configuration to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportConfig':
        """Create ReportConfig from dictionary"""
        customer_id = data.pop('customer_id')
        return cls(data, customer_id)

    @classmethod
    def from_json(cls, json_str: str) -> 'ReportConfig':
        """Create ReportConfig from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __str__(self) -> str:
        """String representation for debugging"""
        return f"ReportConfig(customer={self.customer_id}, detail={self.detail_level.value}, schedule={self.schedule.value})"

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        if not self.customer_id:
            errors.append("Customer ID is required")

        if not self.content_categories:
            errors.append("At least one content category must be selected")

        if self.time_range == 'custom' and not self.custom_date_range:
            errors.append("Custom date range must be specified when time range is 'custom'")

        if self.delivery == DeliveryMethod.EMAIL and not self.email_recipients:
            errors.append("Email recipients must be specified for email delivery")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validate()) == 0