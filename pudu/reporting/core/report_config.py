from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
import json
import logging
from enum import Enum
import pytz  # Add this import

logger = logging.getLogger(__name__)

class ReportDetailLevel(Enum):
    OVERVIEW = "overview"
    DETAILED = "detailed"
    IN_DEPTH = "in-depth"

class OutputFormat(Enum):
    HTML = "html"
    PDF = "pdf"

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

    def __init__(self, form_data: Dict[str, Any], database_name: str):
        self.database_name = database_name
        self.form_data = form_data
        self._parse_configuration()

    def _parse_configuration(self):
        """Parse HTML form data into structured configuration"""
        # Service Selection
        self.service = self.form_data.get('service', 'robot-management')
        self.content_categories = self.form_data.get('contentCategories', ["charging-performance", "cleaning-performance", "resource-utilization", "financial-performance"])

        # Database primary key
        self.mainKey = self.form_data.get('mainKey', '')

        # Hardware Selection - Enhanced for multiple selections
        self.location = self._parse_location()
        self.robot = self._parse_robot()

        # Report Configuration
        self.time_range = self.form_data.get('timeRange', 'last-30-days')
        self.custom_date_range = self._parse_custom_dates()
        self.timezone = self.form_data.get('timezone', 'America/New_York') # Enhanced to use form data
        self.detail_level = ReportDetailLevel(self.form_data.get('detailLevel', 'detailed'))
        self.delivery = DeliveryMethod(self.form_data.get('delivery', 'in-app'))
        self.schedule = ScheduleFrequency(self.form_data.get('schedule', 'immediate'))
        self.report_name = self.form_data.get('reportName', 'Report')

        # Output format
        self.output_format = self.form_data.get('outputFormat', 'html')

        # Email configuration
        self.email_recipients = self.form_data.get('emailRecipients', [])

        # Recurring schedule configuration
        self.recurring_frequency = self.form_data.get('recurringFrequency', 'weekly')
        self.recurring_start_date = self.form_data.get('recurringStartDate')

    def _get_user_timezone(self):
        """Get timezone object for user's timezone"""
        try:
            return pytz.timezone(self.timezone)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {self.timezone}, falling back to America/New_York")
            return pytz.timezone('America/New_York')

    def _convert_to_utc_string(self, dt: datetime) -> str:
        """Convert datetime to UTC string for database queries"""
        user_tz = self._get_user_timezone()
        utc = pytz.UTC

        # If datetime is naive, assume it's in user's timezone
        if dt.tzinfo is None:
            dt = user_tz.localize(dt)

        # Convert to UTC
        utc_dt = dt.astimezone(utc)
        return utc_dt.strftime('%Y-%m-%d %H:%M:%S')

    def _parse_location(self) -> Dict[str, Union[str, List[str]]]:
        """Parse location selection - Enhanced to support multiple selections"""
        location_data = self.form_data.get('location', {})

        # Handle both single values and arrays for each location level
        def normalize_location_value(value):
            if value is None:
                return []
            elif isinstance(value, str):
                return [value] if value.strip() else []
            elif isinstance(value, list):
                return [v.strip() for v in value if v and v.strip()]
            else:
                return []

        return {
            'countries': normalize_location_value(location_data.get('country') or location_data.get('countries')),
            'states': normalize_location_value(location_data.get('state') or location_data.get('states')),
            'cities': normalize_location_value(location_data.get('city') or location_data.get('cities')),
            'buildings': normalize_location_value(location_data.get('building') or location_data.get('buildings'))
        }

    def _parse_robot(self) -> Dict[str, Union[str, List[str]]]:
        """Parse robot selection - Enhanced to support multiple selections"""
        robot_data = self.form_data.get('robot', {})

        # Handle both single values and arrays
        def normalize_robot_value(value):
            if value is None:
                return []
            elif isinstance(value, str):
                return [value] if value.strip() else []
            elif isinstance(value, list):
                return [v.strip() for v in value if v and v.strip()]
            else:
                return []

        return {
            'names': normalize_robot_value(robot_data.get('name') or robot_data.get('names')),
            'serialNumbers': normalize_robot_value(robot_data.get('serialNumber') or robot_data.get('serialNumbers'))
        }

    def _parse_custom_dates(self) -> Optional[Dict[str, str]]:
        """Parse custom date range if specified"""
        if self.time_range == 'custom':
            return {
                'start_date': self.form_data.get('customStartDate'),
                'end_date': self.form_data.get('customEndDate')
            }
        # if custom start date and end date are provided, use them
        elif self.form_data.get('customStartDate') and self.form_data.get('customEndDate'):
            return {
                'start_date': self.form_data.get('customStartDate'),
                'end_date': self.form_data.get('customEndDate')
            }
        return None

    def get_date_range(self, include_comparison_period: bool = False) -> Tuple[str, str]:
        """
        Get actual start and end dates based on configuration, converted to UTC for database queries

        Args:
            include_comparison_period: If True, extends date range to include previous period for comparison

        Returns:
            Tuple of (start_date, end_date) strings in UTC format for database queries
        """
        user_tz = self._get_user_timezone()
        now = datetime.now(user_tz)

        if self.time_range == 'custom' and self.custom_date_range:
            start_date_str = self.custom_date_range['start_date']
            end_date_str = self.custom_date_range['end_date']

            # Parse user dates (assume they are in user's timezone)
            try:
                if ' ' in start_date_str:
                    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
                    start_dt = start_dt.replace(hour=0, minute=0, second=0)

                if ' ' in end_date_str:
                    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)

                # Localize to user timezone
                start_dt = user_tz.localize(start_dt)
                end_dt = user_tz.localize(end_dt)

            except ValueError as e:
                logger.error(f"Error parsing custom dates: {e}")
                # Fallback to last 30 days
                start_dt = now - timedelta(days=30)
                start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)

            if include_comparison_period:
                # Calculate previous period length and extend start date
                period_length = end_dt - start_dt
                start_dt = start_dt - period_length

            return self._convert_to_utc_string(start_dt), self._convert_to_utc_string(end_dt)

        elif self.time_range == 'last-7-days' or self.time_range == 'last_7_days' or '7' in self.time_range:
            days = 7
            if include_comparison_period:
                days = 14  # Include previous 7 days for comparison
            start_dt = now - timedelta(days=days)
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)

        elif self.time_range == 'last-30-days' or self.time_range == 'last_30_days' or '30' in self.time_range:
            days = 30
            if include_comparison_period:
                days = 60  # Include previous 30 days for comparison
            start_dt = now - timedelta(days=days)
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)

        elif self.time_range == 'last-90-days' or self.time_range == 'last_90_days' or '90' in self.time_range:
            days = 90
            if include_comparison_period:
                days = 180  # Include previous 90 days for comparison
            start_dt = now - timedelta(days=days)
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)

        else:
            # Default to last 30 days
            days = 30
            if include_comparison_period:
                days = 60
            start_dt = now - timedelta(days=days)
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)

        return self._convert_to_utc_string(start_dt), self._convert_to_utc_string(end_dt)

    def get_comparison_periods(self) -> Tuple[Tuple[str, str], Tuple[str, str]]:
        """
        Get current and previous period date ranges for comparison, converted to UTC for database queries

        Returns:
            Tuple of ((current_start, current_end), (previous_start, previous_end)) in UTC format
        """
        user_tz = self._get_user_timezone()
        now = datetime.now(user_tz)

        # --- Custom range ---
        if self.time_range == 'custom' and self.custom_date_range:
            current_start_str = self.custom_date_range['start_date']
            current_end_str = self.custom_date_range['end_date']

            try:
                if ' ' in current_start_str:
                    current_start = datetime.strptime(current_start_str, '%Y-%m-%d %H:%M:%S')
                else:
                    current_start = datetime.strptime(current_start_str, '%Y-%m-%d')
                    current_start = current_start.replace(hour=0, minute=0, second=0)

                if ' ' in current_end_str:
                    current_end = datetime.strptime(current_end_str, '%Y-%m-%d %H:%M:%S')
                else:
                    current_end = datetime.strptime(current_end_str, '%Y-%m-%d')
                    current_end = current_end.replace(hour=23, minute=59, second=59)

                # Localize to user timezone
                current_start = user_tz.localize(current_start)
                current_end = user_tz.localize(current_end)

            except ValueError as e:
                logger.error(f"Error parsing custom dates: {e}")
                # Fallback to last 30 days
                current_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
                current_start = now - timedelta(days=30)
                current_start = current_start.replace(hour=0, minute=0, second=0, microsecond=0)

            # Previous period (same length, ends right before current starts)
            period_length = current_end - current_start
            previous_end = current_start - timedelta(seconds=1)
            previous_start = previous_end - period_length

        # --- Last 7 days ---
        elif self.time_range in ['last-7-days', 'last_7_days'] or '7' in self.time_range:
            current_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            current_start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)

            period_length = current_end - current_start
            previous_end = current_start - timedelta(seconds=1)
            previous_start = previous_end - period_length

        # --- Last 30 days ---
        elif self.time_range in ['last-30-days', 'last_30_days'] or '30' in self.time_range:
            current_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            current_start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)

            period_length = current_end - current_start
            previous_end = current_start - timedelta(seconds=1)
            previous_start = previous_end - period_length

        # --- Last 90 days ---
        elif self.time_range in ['last-90-days', 'last_90_days'] or '90' in self.time_range:
            current_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            current_start = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)

            period_length = current_end - current_start
            previous_end = current_start - timedelta(seconds=1)
            previous_start = previous_end - period_length

        # --- Default: last 30 days ---
        else:
            current_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            current_start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)

            period_length = current_end - current_start
            previous_end = current_start - timedelta(seconds=1)
            previous_start = previous_end - period_length

        # Convert to UTC strings
        current_period = (
            self._convert_to_utc_string(current_start),
            self._convert_to_utc_string(current_end)
        )
        previous_period = (
            self._convert_to_utc_string(previous_start),
            self._convert_to_utc_string(previous_end)
        )
        return current_period, previous_period

    def get_display_date_range(self) -> str:
        """
        Get user-friendly date range string for display in user's timezone

        Returns:
            Human-readable date range string in user's timezone
        """
        user_tz = self._get_user_timezone()
        now = datetime.now(user_tz)

        if self.time_range == 'custom' and self.custom_date_range:
            start_date_str = self.custom_date_range['start_date']
            end_date_str = self.custom_date_range['end_date']

            try:
                if ' ' in start_date_str:
                    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')

                if ' ' in end_date_str:
                    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')

                return f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
            except ValueError:
                # Fallback to range description
                pass

        # For predefined ranges, calculate and display the actual dates
        if '7' in self.time_range:
            start_dt = now - timedelta(days=7)
            end_dt = now
            return f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} (Last 7 days)"
        elif '30' in self.time_range:
            start_dt = now - timedelta(days=30)
            end_dt = now
            return f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} (Last 30 days)"
        elif '90' in self.time_range:
            start_dt = now - timedelta(days=90)
            end_dt = now
            return f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} (Last 90 days)"
        else:
            start_dt = now - timedelta(days=30)
            end_dt = now
            return f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')} (Last 30 days)"

    def get_target_robots(self) -> List[str]:
        """Get list of target robot serial numbers based on configuration - Enhanced for multiple selections"""
        # NOTE: This method returns empty list if location-based or name-based selection
        # Actual robot resolution is handled by RobotLocationResolver in the generator

        # Only return direct serial numbers if specified
        robot_sns = self.robot.get('serialNumbers', [])
        if robot_sns:
            return robot_sns

        # For all other cases (name-based or location-based), return empty list
        # The ReportGenerator will handle the resolution using RobotLocationResolver
        return []

    def has_location_criteria(self) -> bool:
        """Check if any location criteria are specified"""
        return any(self.location.get(key, []) for key in ['countries', 'states', 'cities', 'buildings'])

    def has_robot_criteria(self) -> bool:
        """Check if any robot criteria are specified"""
        return any(self.robot.get(key, []) for key in ['names', 'serialNumbers'])

    def get_location_summary(self) -> str:
        """Get human-readable summary of location criteria"""
        summaries = []

        if self.location.get('countries'):
            countries = self.location['countries']
            if len(countries) == 1:
                summaries.append(f"Country: {countries[0]}")
            else:
                summaries.append(f"Countries: {', '.join(countries)}")

        if self.location.get('states'):
            states = self.location['states']
            if len(states) == 1:
                summaries.append(f"State: {states[0]}")
            else:
                summaries.append(f"States: {', '.join(states)}")

        if self.location.get('cities'):
            cities = self.location['cities']
            if len(cities) == 1:
                summaries.append(f"City: {cities[0]}")
            else:
                summaries.append(f"Cities: {', '.join(cities)}")

        if self.location.get('buildings'):
            buildings = self.location['buildings']
            if len(buildings) == 1:
                summaries.append(f"Building: {buildings[0]}")
            else:
                summaries.append(f"Buildings: {len(buildings)} selected")

        return "; ".join(summaries) if summaries else "All locations"

    def get_robot_summary(self) -> str:
        """Get human-readable summary of robot criteria"""
        summaries = []

        if self.robot.get('names'):
            names = self.robot['names']
            if len(names) == 1:
                summaries.append(f"Robot: {names[0]}")
            else:
                summaries.append(f"Robots: {len(names)} by name")

        if self.robot.get('serialNumbers'):
            sns = self.robot['serialNumbers']
            if len(sns) == 1:
                summaries.append(f"Robot SN: {sns[0]}")
            else:
                summaries.append(f"Robots: {len(sns)} by serial number")

        return "; ".join(summaries) if summaries else "All robots"

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
            'database_name': self.database_name,
            'service': self.service,
            'content_categories': self.content_categories,
            'location': self.location,
            'robot': self.robot,
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
        database_name = data.pop('database_name')
        return cls(data, database_name)

    @classmethod
    def from_json(cls, json_str: str) -> 'ReportConfig':
        """Create ReportConfig from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __str__(self) -> str:
        """String representation for debugging"""
        return f"ReportConfig(customer={self.database_name}, detail={self.detail_level.value}, schedule={self.schedule.value})"

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        if not self.database_name:
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