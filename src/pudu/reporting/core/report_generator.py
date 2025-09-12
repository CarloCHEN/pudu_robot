import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from pudu.configs.database_config_loader import DynamicDatabaseConfig
from pudu.services.robot_database_resolver import RobotDatabaseResolver
from ..templates.robot_performance_template import RobotPerformanceTemplate
from ..services.database_data_service import DatabaseDataService
from .report_config import ReportConfig, ReportDetailLevel

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Enhanced report generation service that creates comprehensive HTML reports"""

    def __init__(self, config_path: str = "database_config.yaml", output_dir: str = "reports"):
        """Initialize report generator with database infrastructure"""
        self.config_path = config_path
        self.output_dir = output_dir
        self.config = DynamicDatabaseConfig(config_path)
        self.resolver = RobotDatabaseResolver(self.config.main_database_name)

        # Initialize enhanced database data service
        self.data_service = DatabaseDataService(self.config)

        # Create output directory if it doesn't exist
        self._ensure_output_directory()

        logger.info("Initialized ReportGenerator with enhanced database data service")

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
        Generate comprehensive report based on configuration using database queries with period comparison

        Args:
            report_config: Report configuration from user input

        Returns:
            Dict containing generated report data and metadata
        """
        logger.info(f"Starting comprehensive report generation with comparison for customer {report_config.customer_id}")
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

            # Get current and previous period date ranges for comparison
            (current_start, current_end), (previous_start, previous_end) = report_config.get_comparison_periods()
            logger.info(f"Current period: {current_start} to {current_end}")
            logger.info(f"Previous period: {previous_start} to {previous_end}")

            # Filter robots based on configuration
            target_robots = self._resolve_target_robots(report_config)
            if not target_robots:
                logger.warning(f"No robots found for customer {report_config.customer_id} with given criteria")
                target_robots = self._get_all_customer_robots(report_config.customer_id)

            logger.info(f"Targeting {len(target_robots)} robots for report generation")

            # Fetch current period data
            logger.info("Fetching current period data...")
            current_data = self.data_service.fetch_all_report_data(
                target_robots, current_start, current_end, report_config.content_categories
            )

            # Fetch previous period data for comparison
            logger.info("Fetching previous period data for comparison...")
            previous_data = self.data_service.fetch_all_report_data(
                target_robots, previous_start, previous_end, report_config.content_categories
            )

            # Calculate comprehensive metrics with comparison
            logger.info("Calculating comprehensive metrics with period comparison...")
            comprehensive_metrics = self.data_service.calculate_comprehensive_metrics_with_comparison(
                current_data, previous_data, current_start, current_end, previous_start, previous_end
            )

            # Generate structured report content
            logger.info("Generating structured report content...")
            report_content = self._generate_comprehensive_report_content(
                comprehensive_metrics, report_config, current_start, current_end, target_robots
            )

            # Create HTML report using enhanced template
            logger.info("Generating HTML report using comprehensive template...")
            template = RobotPerformanceTemplate()
            report_html = template.generate_comprehensive_report(report_content, report_config)

            # Calculate execution time and prepare metadata
            execution_time = (datetime.now() - start_time).total_seconds()

            # Enhanced metadata
            metadata = {
                'customer_id': report_config.customer_id,
                'generation_time': start_time.isoformat(),
                'execution_time_seconds': execution_time,
                'date_range': {'start': current_start, 'end': current_end},
                'comparison_period': {'start': previous_start, 'end': previous_end},
                'robots_included': len(target_robots),
                'detail_level': report_config.detail_level.value,
                'content_categories': report_config.content_categories,
                'total_records_processed': sum(len(data) if hasattr(data, '__len__') else 0
                                             for data in current_data.values()),
                'comparison_records_processed': sum(len(data) if hasattr(data, '__len__') else 0
                                                  for data in previous_data.values()),
                'metrics_calculated': list(comprehensive_metrics.keys()),
                'template_type': 'comprehensive_with_comparison_and_facility_breakdown',  # UPDATED
                'report_version': '2.2',  # UPDATED
                'new_features': [  # NEW
                    'avg_daily_running_hours_per_robot',
                    'days_with_tasks',
                    'facility_coverage_by_day',
                    'map_water_efficiency',
                    'comprehensive_vs_last_period',
                    'facility_breakdown_metrics'
                ]
            }

            logger.info(f"Comprehensive report with comparison generated successfully in {execution_time:.2f} seconds")

            return {
                'success': True,
                'error': None,
                'report_html': report_html,
                'metadata': metadata,
                'target_robots': target_robots,
                'comprehensive_metrics': comprehensive_metrics
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
            # TODO: Filter robots by customer_id
            # Use the resolver to get all robots and their database mappings
            all_robot_mapping = self.resolver.get_robot_database_mapping()

            # For now, return all robots (customer filtering would require additional logic)
            # In a real implementation, you'd filter by customer_id through the database
            return list(all_robot_mapping.keys())

        except Exception as e:
            logger.error(f"Error getting customer robots: {e}")
            return []

    def _generate_comprehensive_report_content(self, comprehensive_metrics: Dict[str, Any],
                                             report_config: ReportConfig, start_date: str,
                                             end_date: str, target_robots: List[str]) -> Dict[str, Any]:
        """
        Generate structured report content from comprehensive metrics - UPDATED with all new metrics
        """
        logger.info(f"Generating comprehensive report content with detail level: {report_config.detail_level.value}")

        # Build comprehensive content structure matching the enhanced template
        content = {
            'title': self._generate_report_title(report_config),
            'period': f"{start_date.split(' ')[0]} to {end_date.split(' ')[0]}",
            'generation_time': datetime.now(),
            'detail_level': report_config.detail_level,
            'content_categories': report_config.content_categories,
            'customer_id': report_config.customer_id,

            # Core metrics - pass comprehensive_metrics directly
            'fleet_performance': comprehensive_metrics.get('fleet_performance', {}),
            'task_performance': comprehensive_metrics.get('task_performance', {}),
            'charging_performance': comprehensive_metrics.get('charging_performance', {}),
            'resource_utilization': comprehensive_metrics.get('resource_utilization', {}),
            'event_analysis': comprehensive_metrics.get('event_analysis', {}),
            'facility_performance': comprehensive_metrics.get('facility_performance', {}),
            'cost_analysis': comprehensive_metrics.get('cost_analysis', {}),
            'trend_data': comprehensive_metrics.get('trend_data', {}),
            'map_coverage': comprehensive_metrics.get('map_coverage', []),
            'period_comparisons': comprehensive_metrics.get('period_comparisons', {}),
            'comparison_metadata': comprehensive_metrics.get('comparison_metadata', {}),
            'individual_robots': comprehensive_metrics.get('individual_robots', []),
            'weekday_completion': comprehensive_metrics.get('weekday_completion', {}),

            'facility_task_metrics': comprehensive_metrics.get('facility_task_metrics', {}),
            'facility_charging_metrics': comprehensive_metrics.get('facility_charging_metrics', {}),
            'facility_resource_metrics': comprehensive_metrics.get('facility_resource_metrics', {}),
            'facility_efficiency_metrics': comprehensive_metrics.get('facility_efficiency_metrics', {}),
            'facility_breakdown_metrics': comprehensive_metrics.get('facility_breakdown_metrics', {}),  # NEW - for coverage by day
            'map_performance_by_building': comprehensive_metrics.get('map_performance_by_building', {}),
            'event_location_mapping': comprehensive_metrics.get('event_location_mapping', {}),
            'event_type_by_location': comprehensive_metrics.get('event_type_by_location', {}),
            'financial_trend_data': comprehensive_metrics.get('financial_trend_data', {}),  # NEW - for financial charts

            'avg_task_duration_minutes': comprehensive_metrics.get('task_performance', {}).get('avg_task_duration_minutes', 0),

            # Metadata
            'robots_included': len(target_robots),
            'target_robots': target_robots[:10],
            'total_target_robots': len(target_robots)
        }
        return content

    def _build_enhanced_executive_summary(self, comprehensive_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Build enhanced executive summary from comprehensive metrics with real data"""
        try:
            fleet_metrics = comprehensive_metrics.get('fleet_performance', {})
            task_metrics = comprehensive_metrics.get('task_performance', {})
            charging_metrics = comprehensive_metrics.get('charging_performance', {})
            cost_metrics = comprehensive_metrics.get('cost_analysis', {})
            resource_metrics = comprehensive_metrics.get('resource_utilization', {})

            return {
                # Core performance metrics from real data
                'fleet_availability_rate': fleet_metrics.get('fleet_availability_rate', 0.0),
                'monthly_cost_savings': cost_metrics.get('monthly_cost_savings', 'N/A'),  # N/A as requested
                'energy_saved_kwh': resource_metrics.get('total_energy_consumption_kwh', 0.0),
                'coverage_efficiency': task_metrics.get('coverage_efficiency', 0.0),
                'task_completion_rate': task_metrics.get('completion_rate', 0.0),
                'total_area_cleaned': resource_metrics.get('total_area_cleaned_sqft', 0.0),

                # Additional summary metrics
                'total_robots': fleet_metrics.get('total_robots', 0),
                'total_tasks': task_metrics.get('total_tasks', 0),
                'total_charging_sessions': charging_metrics.get('total_sessions', 0),
                'annual_projected_savings': cost_metrics.get('annual_projected_savings', 'N/A'),  # N/A as requested

                # Operational efficiency
                'completed_tasks': task_metrics.get('completed_tasks', 0),
                'cancelled_tasks': task_metrics.get('cancelled_tasks', 0),
                'operational_hours': fleet_metrics.get('total_operational_hours', 0.0),

                # Resource efficiency
                'water_consumption': resource_metrics.get('total_water_consumption_floz', 0.0),
                'energy_efficiency': resource_metrics.get('area_per_kwh', 0),

                # Quality metrics
                'duration_variance_tasks': task_metrics.get('duration_variance_tasks', 0),
                'avg_duration_ratio': task_metrics.get('avg_duration_ratio', 100.0),
                'charging_success_rate': charging_metrics.get('charging_success_rate', 0.0)
            }

        except Exception as e:
            logger.error(f"Error building enhanced executive summary: {e}")
            return {
                'fleet_availability_rate': 0.0,
                'monthly_cost_savings': 'N/A',
                'energy_saved_kwh': 0.0,
                'coverage_efficiency': 0.0,
                'task_completion_rate': 0.0,
                'total_area_cleaned': 0.0,
                'total_robots': 0,
                'total_tasks': 0,
                'total_charging_sessions': 0
            }

    def _build_executive_summary(self, comprehensive_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Build executive summary from comprehensive metrics"""
        try:
            fleet_metrics = comprehensive_metrics.get('fleet_performance', {})
            task_metrics = comprehensive_metrics.get('task_performance', {})
            charging_metrics = comprehensive_metrics.get('charging_performance', {})
            cost_metrics = comprehensive_metrics.get('cost_analysis', {})
            resource_metrics = comprehensive_metrics.get('resource_utilization', {})

            return {
                'fleet_availability_rate': fleet_metrics.get('fleet_availability_rate', 97.8),
                'monthly_cost_savings': cost_metrics.get('monthly_cost_savings', 12400),
                'energy_saved_kwh': resource_metrics.get('total_energy_consumption_kwh', 309.9),
                'coverage_efficiency': task_metrics.get('coverage_efficiency', 98.7),
                'task_completion_rate': task_metrics.get('completion_rate', 96.3),
                'total_area_cleaned': resource_metrics.get('total_area_cleaned_sqft', 847200),
                'total_robots': fleet_metrics.get('total_robots', 6),
                'total_tasks': task_metrics.get('total_tasks', 6001),
                'total_charging_sessions': charging_metrics.get('total_sessions', 1092),
                'annual_projected_savings': cost_metrics.get('annual_projected_savings', 148800)
            }

        except Exception as e:
            logger.error(f"Error building executive summary: {e}")
            return {
                'fleet_availability_rate': 97.8,
                'monthly_cost_savings': 12400,
                'energy_saved_kwh': 309.9,
                'coverage_efficiency': 98.7,
                'task_completion_rate': 96.3,
                'total_area_cleaned': 847200
            }

    def _generate_report_title(self, report_config: ReportConfig) -> str:
        """Generate appropriate report title"""
        if report_config.detail_level == ReportDetailLevel.SUMMARY:
            return "Robot Management Executive Summary"
        elif report_config.detail_level == ReportDetailLevel.COMPREHENSIVE:
            return "Comprehensive Robot Performance Analysis"
        else:
            return "Robotic Cleaning Fleet Performance Report"

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
    # Example configuration for testing comprehensive reports
    test_form_data = {
        'service': 'robot-management',
        'contentCategories': ['robot-status', 'cleaning-tasks', 'charging-tasks', 'performance', 'cost'],
        'timeRange': 'last-30-days',
        'detailLevel': 'comprehensive',
        'delivery': 'in-app',
        'schedule': 'immediate'
    }

    config = ReportConfig(test_form_data, 'test-customer-123')

    # Generate comprehensive report
    generator = ReportGenerator(output_dir="generated_reports")

    try:
        # Generate and save comprehensive report
        result = generator.generate_and_save_report(config, save_html=True)

        if result['success']:
            print(f"Comprehensive report generation result: {result['success']}")
            print(f"Report metadata: {result['metadata']}")
            if result.get('saved_file_path'):
                print(f"Comprehensive report saved to: {result['saved_file_path']}")

            # Print summary of calculated metrics
            if 'comprehensive_metrics' in result:
                metrics = result['comprehensive_metrics']
                print(f"Calculated metrics categories: {list(metrics.keys())}")
        else:
            print(f"Error: {result['error']}")

    except Exception as e:
        print(f"Error during comprehensive report generation: {e}")
    finally:
        generator.close()