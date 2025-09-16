import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from pudu.configs.database_config_loader import DynamicDatabaseConfig
from pudu.services.robot_database_resolver import RobotDatabaseResolver
from ..templates.robot_html_template import RobotPerformanceTemplate
from ..templates.robot_pdf_template import RobotPDFTemplate
from ..services.database_data_service import DatabaseDataService
from .report_config import ReportConfig, ReportDetailLevel
from ..calculators.chart_data_formatter import ChartDataFormatter

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Enhanced report generation service that creates comprehensive HTML and PDF reports"""

    def __init__(self, config_path: str = "database_config.yaml", output_dir: str = "reports"):
        """Initialize report generator with database infrastructure and both HTML/PDF capability"""
        self.config_path = config_path
        self.output_dir = output_dir
        self.config = DynamicDatabaseConfig(config_path)
        self.resolver = RobotDatabaseResolver(self.config.main_database_name)
        self.chart_formatter = ChartDataFormatter()

        # Initialize enhanced database data service
        self.data_service = DatabaseDataService(self.config)

        # Initialize both HTML and PDF templates
        self.html_template = RobotPerformanceTemplate()
        self.pdf_template = RobotPDFTemplate()

        # Initialize weasyprint for PDF generation
        self._init_pdf_capability()

        # Create output directory if it doesn't exist
        self._ensure_output_directory()

        logger.info("Initialized ReportGenerator with enhanced database data service and dual HTML/PDF capability")

    def _init_pdf_capability(self):
        """Initialize PDF generation capability"""
        try:
            from playwright.async_api import async_playwright
            self.pdf_enabled = True
            logger.info("Successfully initialized Playwright for PDF generation")
        except ImportError:
            logger.warning("Playwright not found. PDF generation disabled.")
            logger.warning("Install with: pip install playwright && playwright install chromium")
            self.pdf_enabled = False

    def _ensure_output_directory(self):
        """Ensure the output directory exists"""
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logger.info(f"Created output directory: {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to create output directory {self.output_dir}: {e}")
            raise

    async def _html_to_pdf_content_async(self, html_content: str) -> bytes:
        """Convert HTML content to PDF bytes using Playwright (async)"""
        if not self.pdf_enabled:
            raise Exception("PDF generation not available. Install playwright: pip install playwright")

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Set content and wait for it to load
                await page.set_content(html_content, wait_until='networkidle')

                # Generate PDF as bytes
                pdf_bytes = await page.pdf(
                    format='A4',
                    margin={
                        'top': '0.75in',
                        'right': '0.75in',
                        'bottom': '0.75in',
                        'left': '0.75in'
                    },
                    print_background=True
                )

                await browser.close()
                return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to convert HTML to PDF: {e}")
            raise Exception(f"Failed to convert HTML to PDF: {e}")

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
            logger.info(f"Successfully saved HTML report to {file_path} (Size: {file_size:,} bytes)")

            return file_path

        except Exception as e:
            logger.error(f"Failed to save HTML report: {e}")
            raise Exception(f"Failed to save HTML report: {e}")

    def save_report_pdf(self, html_content: str, filename: Optional[str] = None,
                   customer_id: Optional[str] = None) -> str:
        """
        Save PDF report from HTML content to a local file using Playwright

        Args:
            html_content: The HTML content to convert to PDF
            filename: Optional custom filename. If not provided, generates one automatically
            customer_id: Customer ID for filename generation

        Returns:
            str: Full path to the saved PDF file

        Raises:
            Exception: If PDF generation or saving fails
        """
        if not self.pdf_enabled:
            raise Exception("PDF generation not available. Install playwright: pip install playwright")

        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                customer_suffix = f"_{customer_id}" if customer_id else ""
                filename = f"robot_report{customer_suffix}_{timestamp}.pdf"

            # Ensure filename has .pdf extension
            if not filename.endswith('.pdf'):
                filename += '.pdf'

            # Create full file path
            file_path = os.path.join(self.output_dir, filename)

            # Convert HTML to PDF using Playwright
            logger.info("Converting HTML to PDF using Playwright...")
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Set content and wait for it to load
                page.set_content(html_content, wait_until='networkidle')

                # Generate PDF with options
                page.pdf(
                    path=file_path,
                    format='A4',
                    margin={
                        'top': '0.75in',
                        'right': '0.75in',
                        'bottom': '0.75in',
                        'left': '0.75in'
                    },
                    print_background=True
                )

                browser.close()

            file_size = os.path.getsize(file_path)
            logger.info(f"Successfully saved PDF report to {file_path} (Size: {file_size:,} bytes)")

            return file_path

        except Exception as e:
            logger.error(f"Failed to save PDF report: {e}")
            raise Exception(f"Failed to save PDF report: {e}")

    def generate_and_save_report(self, report_config: ReportConfig,
                               save_file: bool = True,
                               custom_filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate report and optionally save to file in specified format

        Args:
            report_config: Report configuration from user input
            output_format: Output format ("html" or "pdf")
            save_file: Whether to save to file (default: True)
            custom_filename: Custom filename for saved file

        Returns:
            Dict containing generated report data, metadata, and file path if saved
        """
        output_format = report_config.output_format.lower()
        # Validate output format
        if output_format.lower() not in ["html", "pdf"]:
            raise ValueError("output_format must be 'html' or 'pdf'")

        # Check PDF capability
        if output_format.lower() == "pdf" and not self.pdf_enabled:
            raise Exception("PDF generation not available. Install playwright: pip install playwright")

        # Generate the report data (same for both formats)
        result = self.generate_report(report_config)

        if not result['success']:
            return result

        report_html = result['report_html']

        # Save file if requested and generation was successful
        if save_file and report_html:
            try:
                if output_format.lower() == "html":
                    file_path = self.save_report_html(
                        report_html,
                        custom_filename,
                        report_config.customer_id
                    )
                else:  # PDF
                    file_path = self.save_report_pdf(
                        report_html,
                        custom_filename,
                        report_config.customer_id
                    )

                result['saved_file_path'] = file_path
                result['metadata']['saved_to_file'] = True
                result['metadata']['file_path'] = file_path
                result['metadata']['output_format'] = output_format.upper()

                logger.info(f"{output_format.upper()} report saved to: {file_path}")

            except Exception as e:
                logger.error(f"Failed to save {output_format.upper()} file: {e}")
                result['save_error'] = str(e)
                result['metadata']['saved_to_file'] = False
        else:
            result['metadata']['saved_to_file'] = False

        result['metadata']['output_format'] = output_format.upper()
        return result

    def generate_both_formats(self, report_config: ReportConfig,
                            html_filename: Optional[str] = None,
                            pdf_filename: Optional[str] = None,
                            save_files: bool = True) -> Dict[str, Any]:
        """
        Generate both HTML and PDF reports with the same data

        Args:
            report_config: Report configuration
            html_filename: Optional custom filename for HTML
            pdf_filename: Optional custom filename for PDF
            save_files: Whether to save files to disk

        Returns:
            Dict containing results for both formats
        """
        logger.info(f"Starting dual report generation (HTML + PDF) for customer {report_config.customer_id}")

        try:
            report_config.output_format = 'html'
            # Generate HTML report
            html_result = self.generate_and_save_report(
                report_config,
                save_file=save_files,
                custom_filename=html_filename
            )

            # Generate PDF report
            report_config.output_format = 'pdf'
            pdf_result = self.generate_and_save_report(
                report_config,
                save_file=save_files,
                custom_filename=pdf_filename
            )

            return {
                'success': html_result['success'] and pdf_result['success'],
                'html_result': html_result,
                'pdf_result': pdf_result,
                'metadata': {
                    'customer_id': report_config.customer_id,
                    'generation_time': datetime.now().isoformat(),
                    'formats_generated': ['HTML', 'PDF'] if html_result['success'] and pdf_result['success'] else
                                       (['HTML'] if html_result['success'] else []) +
                                       (['PDF'] if pdf_result['success'] else []),
                    'html_file_path': html_result.get('saved_file_path'),
                    'pdf_file_path': pdf_result.get('saved_file_path')
                }
            }

        except Exception as e:
            logger.error(f"Dual report generation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'html_result': {'success': False},
                'pdf_result': {'success': False},
                'metadata': {
                    'customer_id': report_config.customer_id,
                    'error_occurred': True
                }
            }

    def generate_report(self, report_config: ReportConfig) -> Dict[str, Any]:
        """
        Generate comprehensive report based on configuration using database queries with period comparison
        (This is the original HTML generation method - UNTOUCHED)

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

            # Create HTML or PDF report using template
            logger.info("Generating HTML or PDF report using comprehensive template...")
            if 'html' in report_config.output_format.lower(): # html
                report_html = self.html_template.generate_comprehensive_report(report_content, report_config)
            else: # pdf
                report_html = self.pdf_template.generate_comprehensive_pdf_content(report_content, report_config)

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
            'facility_breakdown_metrics': comprehensive_metrics.get('facility_breakdown_metrics', {}),  # for coverage by day
            'map_performance_by_building': comprehensive_metrics.get('map_performance_by_building', {}),
            'event_location_mapping': comprehensive_metrics.get('event_location_mapping', {}),
            'event_type_by_location': comprehensive_metrics.get('event_type_by_location', {}),
            'financial_trend_data': comprehensive_metrics.get('financial_trend_data', {}),  # for financial charts

            'daily_location_efficiency': comprehensive_metrics.get('daily_location_efficiency', {}),  # for location-specific task efficiency charts
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
        if report_config.report_name:
            return report_config.report_name
        elif report_config.detail_level == ReportDetailLevel.OVERVIEW:
            return "Overview Robot Performance Report"
        elif report_config.detail_level == ReportDetailLevel.DETAILED:
            return "Detailed Robot Performance Report"
        elif report_config.detail_level == ReportDetailLevel.IN_DEPTH:
            return "In-Depth Robot Performance Report"
        else:
            return "Robot Performance Report"

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
        'contentCategories': ['charging-performance', 'cleaning-performance', 'resource-utilization', 'financial-performance'],
        'timeRange': 'custom',
        "location": {
            "country": "us",
            "state": "fl",
            "city": "gainesville"
        },
        'customStartDate': '2025-08-20',
        'customEndDate': '2025-09-09',
        'detailLevel': 'detailed',
        'delivery': 'in-app',
        'schedule': 'immediate'
    }

    config = ReportConfig(test_form_data, 'test-customer-123')

    # Generate comprehensive report
    generator = ReportGenerator(output_dir="generated_reports")

    try:
        # Test HTML generation
        print("=== Testing HTML Generation ===")
        html_result = generator.generate_and_save_report(config, output_format="html", save_file=True)
        if html_result['success']:
            print(f"HTML report saved to: {html_result.get('saved_file_path')}")
        else:
            print(f"HTML generation error: {html_result['error']}")

        # Test PDF generation
        print("\n=== Testing PDF Generation ===")
        if generator.pdf_enabled:
            pdf_result = generator.generate_and_save_report(config, output_format="pdf", save_file=True)
            if pdf_result['success']:
                print(f"PDF report saved to: {pdf_result.get('saved_file_path')}")
            else:
                print(f"PDF generation error: {pdf_result['error']}")
        else:
            print("PDF generation not available (weasyprint not installed)")

        # Test dual format generation
        print("\n=== Testing Dual Format Generation ===")
        if generator.pdf_enabled:
            dual_result = generator.generate_both_formats(config, save_files=True)
            if dual_result['success']:
                print(f"HTML saved to: {dual_result['metadata'].get('html_file_path')}")
                print(f"PDF saved to: {dual_result['metadata'].get('pdf_file_path')}")
            else:
                print(f"Dual generation error: {dual_result.get('error')}")

    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        generator.close()