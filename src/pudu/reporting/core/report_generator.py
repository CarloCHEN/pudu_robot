# src/pudu/reporting/core/report_generator.py
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

# Reuse existing infrastructure
from pudu.configs.database_config_loader import DynamicDatabaseConfig
from pudu.services.robot_database_resolver import RobotDatabaseResolver
from ..templates.robot_performance_template import RobotPerformanceTemplate
from ..services.database_data_service import DatabaseDataService
from .report_config import ReportConfig, ReportDetailLevel

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Main report generation service that uses database queries for historical data"""

    def __init__(self, config_path: str = "database_config.yaml", output_dir: str = "reports"):
        """Initialize report generator with database infrastructure"""
        self.config_path = config_path
        self.output_dir = output_dir
        self.config = DynamicDatabaseConfig(config_path)
        self.resolver = RobotDatabaseResolver(self.config.main_database_name)

        # Initialize database data service instead of using APIs
        self.data_service = DatabaseDataService(self.config)

        # Create output directory if it doesn't exist
        self._ensure_output_directory()

        logger.info("Initialized ReportGenerator with database data service")

    def _ensure_output_directory(self):
        """Ensure the output directory exists"""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logger.info(f"Created output directory: {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to create output directory {self.output_dir}: {e}")
            raise

    def save_report_html(self, html_content: str, filename: Optional[str] = None,
                        customer_id: Optional[str] = None) -> str:
        """
        Save HTML report content to a local file

        Args:
            html_content: The HTML content to save
            filename: Optional custom filename. If not provided, generates one automatically
            customer_id: Customer ID for filename generation

        Returns:
            str: Full path to the saved file

        Raises:
            Exception: If file saving fails
        """
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                customer_suffix = f"_{customer_id}" if customer_id else ""
                filename = f"robot_report{customer_suffix}_{timestamp}.html"

            # Ensure filename has .html extension
            if not filename.endswith('.html'):
                filename += '.html'

            # Create full file path
            file_path = os.path.join(self.output_dir, filename)

            # Save HTML content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            file_size = os.path.getsize(file_path)
            logger.info(f"Successfully saved report to {file_path} (Size: {file_size:,} bytes)")

            return file_path

        except Exception as e:
            logger.error(f"Failed to save HTML report: {e}")
            raise Exception(f"Failed to save HTML report: {e}")

    def generate_and_save_report(self, report_config: ReportConfig,
                               save_html: bool = True,
                               custom_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate report and optionally save HTML to file

        Args:
            report_config: Report configuration from user input
            save_html: Whether to save HTML to file (default: True)
            custom_filename: Custom filename for saved HTML

        Returns:
            Dict containing generated report data, metadata, and file path if saved
        """
        # Generate the report
        result = self.generate_report(report_config)

        # Save HTML to file if requested and generation was successful
        if save_html and result['success'] and result['report_html']:
            try:
                file_path = self.save_report_html(
                    result['report_html'],
                    custom_filename,
                    report_config.customer_id
                )
                result['saved_file_path'] = file_path
                result['metadata']['saved_to_file'] = True
                result['metadata']['file_path'] = file_path

                logger.info(f"Report saved to: {file_path}")

            except Exception as e:
                logger.error(f"Failed to save HTML file: {e}")
                result['save_error'] = str(e)
                result['metadata']['saved_to_file'] = False
        else:
            result['metadata']['saved_to_file'] = False

        return result

    def generate_report(self, report_config: ReportConfig) -> Dict[str, Any]:
        """
        Generate report based on configuration using database queries

        Args:
            report_config: Report configuration from user input

        Returns:
            Dict containing generated report data and metadata
        """
        logger.info(f"Starting report generation for customer {report_config.customer_id}")
        start_time = datetime.now()

        try:
            # Validate configuration
            validation_errors = report_config.validate()
            if validation_errors:
                logger.error(f"Report configuration validation failed: {validation_errors}")
                return {
                    'success': False,
                    'error': f"Configuration validation failed: {', '.join(validation_errors)}",
                    'report_html': None,
                    'metadata': {}
                }

            # Get date range for data fetching
            start_date, end_date = report_config.get_date_range()
            logger.info(f"Generating report for date range: {start_date} to {end_date}")

            # Filter robots based on configuration
            target_robots = self._resolve_target_robots(report_config)
            if not target_robots:
                logger.warning(f"No robots found for customer {report_config.customer_id} with given criteria")
                # Don't fail - generate report for all customer's robots
                target_robots = self._get_all_customer_robots(report_config.customer_id)

            logger.info(f"Targeting {len(target_robots)} robots for report generation")

            # Fetch data using database service instead of APIs
            report_data = self.data_service.fetch_all_report_data(
                target_robots, start_date, end_date, report_config.content_categories
            )

            # Generate report content based on selected categories and detail level
            report_content = self._generate_report_content(report_data, report_config, start_date, end_date)

            # Create HTML report using template
            template = RobotPerformanceTemplate()
            report_html = template.generate_report(report_content, report_config)

            # Calculate execution time and print summary
            execution_time = (datetime.now() - start_time).total_seconds()

            # Prepare metadata
            metadata = {
                'customer_id': report_config.customer_id,
                'generation_time': start_time.isoformat(),
                'execution_time_seconds': execution_time,
                'date_range': {'start': start_date, 'end': end_date},
                'robots_included': len(target_robots),
                'detail_level': report_config.detail_level.value,
                'content_categories': report_config.content_categories,
                'total_records_processed': sum(len(data) if hasattr(data, '__len__') else 0
                                             for data in report_data.values())
            }

            logger.info(f"Report generation completed successfully in {execution_time:.2f} seconds")

            return {
                'success': True,
                'error': None,
                'report_html': report_html,
                'metadata': metadata,
                'target_robots': target_robots
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Report generation failed after {execution_time:.2f} seconds: {e}", exc_info=True)

            return {
                'success': False,
                'error': str(e),
                'report_html': None,
                'metadata': {
                    'customer_id': report_config.customer_id,
                    'generation_time': start_time.isoformat(),
                    'execution_time_seconds': execution_time,
                    'error_occurred': True
                }
            }

    def _resolve_target_robots(self, report_config: ReportConfig) -> List[str]:
        """Resolve target robots based on configuration (name/SN or location)"""
        try:
            from ..services.robot_location_resolver import RobotLocationResolver
            location_resolver = RobotLocationResolver(self.config)

            # Check if specific robot selected by name or serial number
            robot_name = report_config.robot.get('name', '').strip()
            robot_sn = report_config.robot.get('serialNumber', '').strip()

            if robot_name or robot_sn:
                logger.info(f"Resolving robots by name='{robot_name}' or SN='{robot_sn}'")
                robots = location_resolver.resolve_robots_by_name_or_sn(robot_name, robot_sn)
                if robots:
                    return robots
                else:
                    logger.warning(f"No robots found with name='{robot_name}' or SN='{robot_sn}'")

            # Check if location-based selection
            location_criteria = report_config.location
            if any(location_criteria.values()):
                logger.info(f"Resolving robots by location: {location_criteria}")
                robots = location_resolver.resolve_robots_by_location(location_criteria)
                if robots:
                    return robots
                else:
                    logger.warning(f"No robots found matching location criteria: {location_criteria}")

            # If no specific criteria, return all robots for the customer
            logger.info("No specific robot criteria - returning all customer robots")
            return self._get_all_customer_robots(report_config.customer_id)

        except Exception as e:
            logger.error(f"Error resolving target robots: {e}")
            return []

    def _get_all_customer_robots(self, customer_id: str) -> List[str]:
        """Get all robots belonging to a customer"""
        try:
            # Use the resolver to get all robots and their database mappings
            all_robot_mapping = self.resolver.get_robot_database_mapping()

            # For now, return all robots (customer filtering would require additional logic)
            # In a real implementation, you'd filter by customer_id through the database
            return list(all_robot_mapping.keys())

        except Exception as e:
            logger.error(f"Error getting customer robots: {e}")
            return []

    def _generate_report_content(self, report_data: Dict[str, Any], report_config: ReportConfig,
                                start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate structured report content from raw database data"""
        logger.info(f"Generating report content with detail level: {report_config.detail_level.value}")

        content = {
            'title': self._generate_report_title(report_config),
            'period': f"{start_date} to {end_date}",
            'generation_time': datetime.now(),
            'detail_level': report_config.detail_level,
            'sections': {}
        }

        # Generate content based on selected categories and detail level
        if 'robot-status' in report_config.content_categories:
            content['sections']['robot_status'] = self._analyze_robot_status(
                report_data.get('robot_status', pd.DataFrame()), report_config.detail_level)

        if 'cleaning-tasks' in report_config.content_categories:
            content['sections']['cleaning_tasks'] = self._analyze_cleaning_tasks(
                report_data.get('cleaning_tasks', pd.DataFrame()), report_config.detail_level)

        if 'charging-tasks' in report_config.content_categories:
            content['sections']['charging_tasks'] = self._analyze_charging_tasks(
                report_data.get('charging_tasks', pd.DataFrame()), report_config.detail_level)

        if 'performance' in report_config.content_categories:
            content['sections']['performance'] = self._analyze_performance(
                report_data, report_config.detail_level)

        if 'cost' in report_config.content_categories:
            content['sections']['cost_analysis'] = self._analyze_costs(
                report_data, report_config.detail_level)

        return content

    def _generate_report_title(self, report_config: ReportConfig) -> str:
        """Generate appropriate report title"""
        if report_config.detail_level == ReportDetailLevel.SUMMARY:
            return "Robot Management Executive Summary"
        elif report_config.detail_level == ReportDetailLevel.COMPREHENSIVE:
            return "Comprehensive Robot Performance Analysis"
        else:
            return "Robot Management Performance Report"

    def _analyze_robot_status(self, robot_data: pd.DataFrame, detail_level: ReportDetailLevel) -> Dict[str, Any]:
        """Analyze robot status data from database"""
        if robot_data.empty:
            return {'summary': 'No robot status data available', 'details': {}}

        analysis = {
            'total_robots': len(robot_data),
            'summary': f"Analysis of {len(robot_data)} robots"
        }

        if detail_level in [ReportDetailLevel.DETAILED, ReportDetailLevel.COMPREHENSIVE]:
            # Add detailed analysis
            if 'status' in robot_data.columns:
                status_counts = robot_data['status'].value_counts().to_dict()
                analysis['status_distribution'] = status_counts

            if 'robot_sn' in robot_data.columns:
                analysis['robot_list'] = robot_data['robot_sn'].tolist()

            # Add battery level analysis
            if 'battery_level' in robot_data.columns:
                avg_battery = robot_data['battery_level'].mean()
                analysis['average_battery_level'] = round(avg_battery, 1) if pd.notna(avg_battery) else 0

        return analysis

    def _analyze_cleaning_tasks(self, tasks_data: pd.DataFrame, detail_level: ReportDetailLevel) -> Dict[str, Any]:
        """Analyze cleaning tasks data from database"""
        if tasks_data.empty:
            return {'summary': 'No cleaning tasks data available', 'details': {}}

        analysis = {
            'total_tasks': len(tasks_data),
            'summary': f"Analysis of {len(tasks_data)} cleaning tasks"
        }

        if detail_level in [ReportDetailLevel.DETAILED, ReportDetailLevel.COMPREHENSIVE]:
            # Add task status analysis
            if 'status' in tasks_data.columns:
                status_counts = tasks_data['status'].value_counts().to_dict()
                analysis['task_status_distribution'] = status_counts

            # Add task mode analysis
            if 'mode' in tasks_data.columns:
                mode_counts = tasks_data['mode'].value_counts().to_dict()
                analysis['task_mode_distribution'] = mode_counts

            # Calculate completion rate
            if 'status' in tasks_data.columns:
                total_tasks = len(tasks_data)
                completed_tasks = len(tasks_data[tasks_data['status'] == 'Task Ended'])
                analysis['completion_rate'] = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

            # Add efficiency analysis
            if 'efficiency' in tasks_data.columns:
                avg_efficiency = tasks_data['efficiency'].mean()
                analysis['average_efficiency'] = round(avg_efficiency, 1) if pd.notna(avg_efficiency) else 0

            # Add area coverage analysis
            if 'actual_area' in tasks_data.columns and 'plan_area' in tasks_data.columns:
                coverage_ratio = (tasks_data['actual_area'].sum() / tasks_data['plan_area'].sum()) * 100
                analysis['area_coverage_ratio'] = round(coverage_ratio, 1) if coverage_ratio > 0 else 0

        return analysis

    def _analyze_charging_tasks(self, charging_data: pd.DataFrame, detail_level: ReportDetailLevel) -> Dict[str, Any]:
        """Analyze charging tasks data from database"""
        if charging_data.empty:
            return {'summary': 'No charging data available', 'details': {}}

        analysis = {
            'total_sessions': len(charging_data),
            'summary': f"Analysis of {len(charging_data)} charging sessions"
        }

        if detail_level in [ReportDetailLevel.DETAILED, ReportDetailLevel.COMPREHENSIVE]:
            # Add charging duration analysis
            if 'duration' in charging_data.columns:
                # Convert duration to minutes if it's in string format like "0h 05min"
                durations = []
                for duration in charging_data['duration']:
                    if pd.notna(duration) and isinstance(duration, str):
                        # Parse duration like "0h 05min"
                        hours = 0
                        minutes = 0
                        if 'h' in duration:
                            hours = int(duration.split('h')[0])
                        if 'min' in duration:
                            min_part = duration.split('min')[0]
                            if 'h' in min_part:
                                minutes = int(min_part.split('h')[1].strip())
                            else:
                                minutes = int(min_part)
                        durations.append(hours * 60 + minutes)
                    elif pd.notna(duration):
                        durations.append(float(duration))

                if durations:
                    avg_duration = sum(durations) / len(durations)
                    analysis['average_charging_duration'] = round(avg_duration, 2)

            # Add power gain analysis
            if 'power_gain' in charging_data.columns:
                power_gains = []
                for gain in charging_data['power_gain']:
                    if pd.notna(gain) and isinstance(gain, str):
                        # Parse power gain like "+2%"
                        gain_val = float(gain.replace('+', '').replace('%', ''))
                        power_gains.append(gain_val)
                    elif pd.notna(gain):
                        power_gains.append(float(gain))

                if power_gains:
                    avg_power_gain = sum(power_gains) / len(power_gains)
                    analysis['average_power_gain'] = f"{round(avg_power_gain, 1)}%"

        return analysis

    def _analyze_performance(self, all_data: Dict[str, Any], detail_level: ReportDetailLevel) -> Dict[str, Any]:
        """Analyze overall performance metrics from database data"""
        analysis = {'summary': 'Performance analysis based on available data'}

        # Combine insights from all data sources
        events_data = all_data.get('events', pd.DataFrame())
        tasks_data = all_data.get('cleaning_tasks', pd.DataFrame())

        if not events_data.empty:
            if 'event_level' in events_data.columns:
                error_events = len(events_data[events_data['event_level'] == 'error'])
                warning_events = len(events_data[events_data['event_level'] == 'warning'])
                analysis['error_events'] = error_events
                analysis['warning_events'] = warning_events

            if 'event_type' in events_data.columns:
                event_type_counts = events_data['event_type'].value_counts().to_dict()
                analysis['event_types'] = event_type_counts

        if not tasks_data.empty and detail_level == ReportDetailLevel.COMPREHENSIVE:
            # Add more detailed performance metrics
            analysis['task_performance'] = {
                'total_tasks': len(tasks_data),
                'date_range_coverage': 'Based on selected date range'
            }

        return analysis

    def _analyze_costs(self, all_data: Dict[str, Any], detail_level: ReportDetailLevel) -> Dict[str, Any]:
        """Analyze cost-related metrics from database data"""
        # This is a placeholder - actual cost analysis would require cost data
        analysis = {
            'summary': 'Cost analysis - operational efficiency metrics',
            'note': 'Detailed cost analysis requires additional cost data configuration'
        }

        # Extract operational metrics that can indicate cost efficiency
        tasks_data = all_data.get('cleaning_tasks', pd.DataFrame())
        charging_data = all_data.get('charging_tasks', pd.DataFrame())

        if detail_level == ReportDetailLevel.COMPREHENSIVE:
            operational_metrics = {}

            # Task efficiency metrics
            if not tasks_data.empty:
                if 'duration' in tasks_data.columns and 'actual_area' in tasks_data.columns:
                    # Calculate area cleaned per hour
                    total_duration_hours = tasks_data['duration'].sum() / 60 if tasks_data['duration'].sum() > 0 else 1
                    total_area = tasks_data['actual_area'].sum()
                    operational_metrics['area_per_hour'] = round(total_area / total_duration_hours, 2)

                if 'water_consumption' in tasks_data.columns:
                    total_water = tasks_data['water_consumption'].sum()
                    operational_metrics['total_water_consumption'] = total_water

            # Charging efficiency metrics
            if not charging_data.empty:
                operational_metrics['charging_sessions'] = len(charging_data)
                if 'duration' in charging_data.columns:
                    # Parse charging durations
                    durations = []
                    for duration in charging_data['duration']:
                        if pd.notna(duration) and isinstance(duration, str):
                            hours = 0
                            minutes = 0
                            if 'h' in duration:
                                hours = int(duration.split('h')[0])
                            if 'min' in duration:
                                min_part = duration.split('min')[0]
                                if 'h' in min_part:
                                    minutes = int(min_part.split('h')[1].strip())
                                else:
                                    minutes = int(min_part)
                            durations.append(hours * 60 + minutes)

                    if durations:
                        operational_metrics['total_charging_time_minutes'] = sum(durations)

            analysis['operational_efficiency'] = operational_metrics

        return analysis

    def close(self):
        """Clean up resources"""
        try:
            self.config.close()
            self.resolver.close()
            logger.info("ReportGenerator resources cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Example usage and testing function
if __name__ == "__main__":
    # Example configuration for testing
    test_form_data = {
        'service': 'robot-management',
        'contentCategories': ['robot-status', 'cleaning-tasks', 'performance'],
        'timeRange': 'last-30-days',
        'detailLevel': 'detailed',
        'delivery': 'in-app',
        'schedule': 'immediate'
    }

    config = ReportConfig(test_form_data, 'test-customer-123')

    # Example 1: Generate report and save to default location
    generator = ReportGenerator(output_dir="generated_reports")

    try:
        # Generate and save report with default filename
        result = generator.generate_and_save_report(config, save_html=True)

        if result['success']:
            print(f"Report generation result: {result['success']}")
            print(f"Report metadata: {result['metadata']}")
            if result.get('saved_file_path'):
                print(f"Report saved to: {result['saved_file_path']}")
        else:
            print(f"Error: {result['error']}")

        # Example 2: Generate report and save with custom filename
        custom_result = generator.generate_and_save_report(
            config,
            save_html=True,
            custom_filename="custom_robot_report_2024"
        )

        if custom_result['success'] and custom_result.get('saved_file_path'):
            print(f"Custom report saved to: {custom_result['saved_file_path']}")

        # Example 3: Just save existing HTML content
        if result['success'] and result['report_html']:
            manual_save_path = generator.save_report_html(
                result['report_html'],
                "manual_save_example.html"
            )
            print(f"Manually saved report to: {manual_save_path}")

    except Exception as e:
        print(f"Error during report generation: {e}")
    finally:
        generator.close()