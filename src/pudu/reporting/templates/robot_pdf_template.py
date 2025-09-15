from typing import Dict, Any
from datetime import datetime
import logging
from ..core.report_config import ReportConfig
from ..calculators.chart_data_formatter import ChartDataFormatter

logger = logging.getLogger(__name__)

class RobotPDFTemplate:
    """PDF template generator using actual database metrics (static version of HTML template)"""

    def __init__(self):
        self.chart_formatter = ChartDataFormatter()

    def generate_comprehensive_pdf_content(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate comprehensive PDF-ready HTML content (static version without interactivity)"""
        try:
            self.chart_images = self.chart_formatter.generate_pdf_chart_images(content)

            content_categories = config.content_categories

            # Always include executive summary
            sections = [self._generate_executive_summary(content)]

            # Task Performance section
            if any(cat in content_categories for cat in ['executive-summary', 'fleet-management', 'facility-performance', 'task-performance', 'cleaning-performance']):
                sections.append(self._generate_task_section(content))

            # Facility-Specific Performance section
            if any(cat in content_categories for cat in ['facility-performance', 'cleaning-performance']):
                sections.append(self._generate_facility_section(content))

            # Resource Utilization & Efficiency section
            if 'resource-utilization' in content_categories:
                sections.append(self._generate_resource_section(content))

            # Financial Performance section
            if 'financial-performance' in content_categories:
                sections.append(self._generate_financial_section(content))

            # Charging Sessions Performance section
            if 'charging-performance' in content_categories:
                sections.append(self._generate_charging_section(content))

            # Always include conclusion
            sections.append(self._generate_conclusion(content))
            sections.append(self._generate_footer(content))

            html_content = f"""<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{content.get('title', 'Robot Performance Report')} - {content.get('period', 'Latest Period')}</title>
                {self._get_pdf_styles()}
            </head>
            <body>
                <div class="container">
                    <h1>{content.get('title', 'Robot Performance Report')}</h1>
                    <p class="subtitle">{content.get('period', 'Latest Period')}</p>
                    {''.join(sections)}
                </div>
            </body>
            </html>"""

            return html_content

        except Exception as e:
            logger.error(f"Error generating PDF content: {e}")
            return f"""<!DOCTYPE html>
            <html><head><title>Error</title></head>
            <body><h1>Report Generation Error</h1><p>{str(e)}</p></body></html>
            """

    def _get_chart_image_html(self, chart_key: str, alt_text: str, max_width: int = 100, max_height: int = 300) -> str:
        """Generate HTML for chart image if available"""
        if hasattr(self, 'chart_images') and chart_key in self.chart_images:
            return f"""
            <div style="text-align: center; margin: 20px 0;">
                <img src="{self.chart_images[chart_key]}"
                    alt="{alt_text}"
                    style="max-width: {max_width}%; height: {max_height}px; border-radius: 5px;">
            </div>"""
        return ""

    def _get_pdf_styles(self) -> str:
        """Get PDF-optimized CSS styles (no tooltips, hover effects, or interactive elements)"""
        return """
        <style>
            body {
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: white;
                color: #333;
                font-size: 12px;
            }

            .container {
                max-width: 100%;
                margin: 0 auto;
                background: white;
                padding: 20px;
            }

            h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 5px;
                font-size: 24px;
                page-break-after: avoid;
            }

            .subtitle {
                text-align: center;
                color: #7f8c8d;
                font-size: 16px;
                margin-bottom: 15px;
            }

            h2 {
                color: #34495e;
                border-bottom: 3px solid #3498db;
                padding-bottom: 8px;
                margin-top: 20px;
                font-size: 18px;
                page-break-after: avoid;
            }

            h3 {
                color: #2980b9;
                margin-top: 20px;
                font-size: 16px;
                page-break-after: avoid;
            }

            h4 {
                color: #2c3e50;
                margin-top: 15px;
                font-size: 14px;
                page-break-after: avoid;
            }

            .highlight-box {
                background: #f8f9fa;
                border-left: 5px solid #3498db;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
                page-break-inside: avoid;
            }

            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 15px 0;
                page-break-inside: avoid;
            }

            .metric-card {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 5px;
                padding: 15px;
                text-align: center;
                page-break-inside: avoid;
            }

            .metric-value {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
            }

            .metric-label {
                color: #7f8c8d;
                font-size: 11px;
                margin-top: 5px;
            }

            .two-column {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 15px 0;
                page-break-inside: avoid;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                background: white;
                font-size: 11px;
                page-break-inside: avoid;
            }

            th, td {
                padding: 8px;
                text-align: left;
                border: 1px solid #e9ecef;
                vertical-align: top;
            }

            th {
                background: #f8f9fa;
                color: #2c3e50;
                font-weight: 600;
                font-size: 10px;
            }

            .progress-container {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 8px 0;
            }

            .progress-bar {
                width: 100px;
                height: 12px;
                background: #e9ecef;
                border-radius: 6px;
                overflow: hidden;
                display: inline-block;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #28a745, #20c997);
            }

            .progress-text {
                display: inline-block;
                margin-left: 8px;
                font-weight: bold;
                color: #2c3e50;
                font-size: 11px;
            }

            .map-section {
                margin: 20px 0;
                padding: 15px;
                background: #f8f9fa;
                border-radius: 5px;
                page-break-inside: avoid;
            }

            .map-metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 10px;
                margin: 10px 0;
            }

            .map-metric {
                background: white;
                padding: 8px;
                border-radius: 3px;
                text-align: center;
                border: 1px solid #dee2e6;
                font-size: 10px;
            }

            ul {
                margin: 10px 0;
                padding-left: 20px;
            }

            li {
                margin: 5px 0;
                font-size: 12px;
            }

            p {
                margin: 10px 0;
                font-size: 12px;
            }

            .location-efficiency-single-column {
                display: flex;
                flex-direction: column;
                gap: 15px;
                margin: 20px 0;
            }

            .location-efficiency-single-line {
                background: #f8f9fa;
                border-radius: 5px;
                padding: 15px;
                border: 1px solid #e9ecef;
                margin: 10px 0;
                page-break-inside: avoid;
            }

            .location-single-line-content {
                display: grid;
                grid-template-columns: 1fr 300px;
                gap: 20px;
                align-items: flex-start;
            }

            .location-stats-compact {
                display: flex;
                flex-direction: column;
                gap: 8px;
                min-width: 300px;
                max-width: 300px;
                font-size: 11px;
            }

            .stat-row {
                display: flex;
                align-items: flex-start;
                gap: 8px;
                padding: 5px 0;
                border-bottom: 1px solid #e9ecef;
                flex-wrap: wrap;
            }

            .stat-row:last-child {
                border-bottom: none;
            }

            .stat-label {
                font-weight: 600;
                color: #495057;
                min-width: 80px;
                font-size: 10px;
                flex-shrink: 0;
            }

            .stat-value {
                font-weight: bold;
                color: #2c3e50;
                font-size: 11px;
                flex-shrink: 0;
            }

            .stat-comparison {
                font-size: 9px;
                font-style: italic;
                margin-left: 5px;
                flex-shrink: 0;
            }

            footer {
                margin-top: 40px;
                padding-top: 15px;
                border-top: 2px solid #e9ecef;
                text-align: center;
                color: #7f8c8d;
                font-size: 10px;
                page-break-inside: avoid;
            }

            /* Page break optimization */
            .section {
                page-break-inside: avoid;
            }

            .chart-container {
                page-break-inside: avoid;
            }

            @media print {
                body {
                    margin: 0;
                    padding: 10px;
                }
                .container {
                    padding: 10px;
                }
                .section {
                    page-break-before: avoid;
                }
                table {
                    page-break-inside: avoid;
                }
                .metrics-grid {
                    page-break-inside: avoid;
                }
                .highlight-box {
                    page-break-inside: avoid;
                }
                .two-column {
                    page-break-inside: avoid;
                }
                .location-efficiency-single-column {
                    page-break-inside: avoid;
                }
            }
        </style>"""

    def _generate_executive_summary(self, content: Dict[str, Any]) -> str:
        """Generate executive summary section (PDF version - no tooltips)"""
        fleet_data = content.get('fleet_performance', {})
        task_data = content.get('task_performance', {})
        resource_data = content.get('resource_utilization', {})
        cost_data = content.get('cost_analysis', {})
        comparisons = content.get('period_comparisons', {})
        individual_robots = content.get('individual_robots', [])

        period_desc = content.get('period', 'the reporting period')

        def format_value(value, suffix="", format_type="number"):
            if value == 'N/A' or value is None:
                return 'N/A'
            if format_type == "number":
                return f"{value:,.1f}{suffix}" if isinstance(value, (int, float)) else f"{value}{suffix}"
            elif format_type == "percent":
                return f"{value}%" if isinstance(value, (int, float)) else f"{value}"
            return str(value)

        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value):
            if value == 'N/A' or not value:
                return '#6c757d'
            elif value.startswith('+'):
                return '#28a745'
            elif value.startswith('-'):
                return '#dc3545'
            else:
                return '#6c757d'

        days_ratio = fleet_data.get('days_ratio', fleet_data.get('days_with_tasks', 0))

        # Generate robot performance table
        robot_rows = ""
        if individual_robots:
            for robot in individual_robots[:10]:
                robot_rows += f"""
                <tr>
                    <td>{robot.get('robot_id', 'Unknown')}</td>
                    <td>{robot.get('location', 'Unknown Location')}</td>
                    <td>{robot.get('total_tasks', 0)}</td>
                    <td>{robot.get('tasks_completed', 0)}</td>
                    <td>{robot.get('total_area_cleaned', 0):,.0f} sq ft</td>
                    <td>{robot.get('average_coverage', 0):.1f}%</td>
                    <td>{robot.get('days_with_tasks', 0)}</td>
                    <td>{robot.get('running_hours', 0)} hrs</td>
                </tr>"""

        if not robot_rows:
            robot_rows = '<tr><td colspan="8">No robot data available</td></tr>'

        return f"""
        <section id="executive-summary" class="section">
            <h2>📊 Executive Summary</h2>
            <div class="highlight-box">
                <p>Robot deployment during {period_desc} processed {format_value(task_data.get('total_tasks', 0))} total tasks,
                covering {format_value(resource_data.get('total_area_cleaned_sqft', 0), ' square feet')} with
                {format_value(fleet_data.get('total_running_hours', 0), ' total running hours')}.</p>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{fleet_data.get('total_robots', 0)}</div>
                    <div class="metric-label">Total Robots</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{format_value(resource_data.get('total_area_cleaned_sqft', 0))}</div>
                    <div class="metric-label">Sq Ft Cleaned</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('total_area_cleaned', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('total_area_cleaned', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{format_value(task_data.get('coverage_efficiency', 0), '%', 'percent')}</div>
                    <div class="metric-label">Coverage</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('coverage_efficiency', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('coverage_efficiency', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{format_value(fleet_data.get('total_running_hours', 0))}</div>
                    <div class="metric-label">Total Running Hours</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('running_hours', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('running_hours', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{fleet_data.get('avg_daily_running_hours_per_robot', 0):.1f}</div>
                    <div class="metric-label">Avg Daily Hours/Robot</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('avg_daily_running_hours_per_robot', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('avg_daily_running_hours_per_robot', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{days_ratio}</div>
                    <div class="metric-label">Days with Tasks</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('days_with_tasks', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('days_with_tasks', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{format_value(resource_data.get('total_energy_consumption_kwh', 0), ' kWh')}</div>
                    <div class="metric-label">Energy Used</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('energy_consumption', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('energy_consumption', 'N/A'))}
                    </div>
                </div>
            </div>

            <h3>🎯 Key Achievements</h3>
            <ul style="font-size: 11px; color: #2c3e50;">
                <li>{format_value(task_data.get('total_tasks', 0))} total tasks processed during reporting period</li>
                <li>{format_value(resource_data.get('total_area_cleaned_sqft', 0))} square feet cleaned across all locations</li>
                <li>{format_value(fleet_data.get('total_robots', 0))} robots actively deployed and monitored</li>
                <li>{format_value(content.get('charging_performance', {}).get('total_sessions', 0))} charging sessions during the period</li>
            </ul>

            <h3>🤖 Individual Robot Performance</h3>
            <table>
                <thead>
                    <tr>
                        <th>Robot ID</th>
                        <th>Location</th>
                        <th>Total Tasks</th>
                        <th>Completed</th>
                        <th>Area Cleaned</th>
                        <th>Avg Coverage</th>
                        <th>Days with Tasks</th>
                        <th>Running Hours</th>
                    </tr>
                </thead>
                <tbody>
                    {robot_rows}
                </tbody>
            </table>
        </section>"""

    def _generate_task_section(self, content: Dict[str, Any]) -> str:
        """Generate task performance section (PDF version - shows weekly averages)"""
        task_data = content.get('task_performance', {})
        facilities = content.get('facility_performance', {}).get('facilities', {})
        comparisons = content.get('period_comparisons', {})
        facility_comparisons = comparisons.get('facility_comparisons', {})

        avg_duration = task_data.get('avg_task_duration_minutes', 0)
        weekend_completion = task_data.get('weekend_schedule_completion', 0)

        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value):
            if value == 'N/A' or not value:
                return '#6c757d'
            elif value.startswith('+'):
                return '#28a745'
            elif value.startswith('-'):
                return '#dc3545'
            else:
                return '#6c757d'

        # Generate location-based efficiency summaries (no charts in PDF)
        location_efficiency_section = ""
        facility_task_metrics = content.get('facility_task_metrics', {})
        facility_breakdown_metrics = content.get('facility_breakdown_metrics', {})
        facility_efficiency = content.get('facility_efficiency_metrics', {})

        if facility_task_metrics:
            location_efficiency_section = """
            <h3>Task Efficiency by Location</h3>
            <p>Location-specific performance showing average operational metrics for each facility.</p>

            <div class="location-efficiency-single-column">"""

            for location_name, facility_task_data in facility_task_metrics.items():
                facility_comp = facility_comparisons.get(location_name, {}) if isinstance(facility_comparisons, dict) else {}
                facility_breakdown = facility_breakdown_metrics.get(location_name, {}) if isinstance(facility_breakdown_metrics, dict) else {}
                facility_eff = facility_efficiency.get(location_name, {}) if isinstance(facility_efficiency, dict) else {}

                facility_avg_duration = facility_task_data.get('avg_duration_minutes', avg_duration) if facility_task_data else avg_duration
                primary_mode = facility_task_data.get('primary_mode', 'Mixed tasks') if facility_task_data else 'Mixed tasks'

                highest_coverage_day = facility_breakdown.get('highest_coverage_day', 'N/A') if facility_breakdown else 'N/A'
                lowest_coverage_day = facility_breakdown.get('lowest_coverage_day', 'N/A') if facility_breakdown else 'N/A'

                coverage_comparison_high = facility_comp.get('highest_coverage_day', 'N/A') if facility_comp else 'N/A'
                coverage_comparison_low = facility_comp.get('lowest_coverage_day', 'N/A') if facility_comp else 'N/A'

                days_ratio = facility_eff.get('days_ratio', 'N/A') if facility_eff else 'N/A'

                location_efficiency_section += f"""
                <div class="location-efficiency-single-line">
                    <h4>{location_name}</h4>
                    <div class="location-single-line-content">
                        <div>
                            {self._get_location_charts_html(location_name)}
                        </div>
                        <div class="location-stats-compact">
                            <div class="stat-row">
                                <span class="stat-label">Task Mode:</span>
                                <span class="stat-value">{primary_mode}</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-label">Avg Duration:</span>
                                <span class="stat-value">{facility_avg_duration:.1f} min</span>
                                <span class="stat-comparison" style="color: {get_comparison_color(facility_comp.get('avg_task_duration', 'N/A') if facility_comp else 'N/A')};">
                                    (vs last: {format_comparison(facility_comp.get('avg_task_duration', 'N/A') if facility_comp else 'N/A')})
                                </span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-label">Days with Tasks:</span>
                                <span class="stat-value">{days_ratio}</span>
                                <span class="stat-comparison" style="color: {get_comparison_color(facility_comp.get('days_with_tasks', 'N/A') if facility_comp else 'N/A')};">
                                    (vs last: {format_comparison(facility_comp.get('days_with_tasks', 'N/A') if facility_comp else 'N/A')})
                                </span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-label">Highest Coverage:</span>
                                <span class="stat-value">{highest_coverage_day}</span>
                                <span class="stat-comparison">(vs last: {coverage_comparison_high})</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-label">Lowest Coverage:</span>
                                <span class="stat-value">{lowest_coverage_day}</span>
                                <span class="stat-comparison">(vs last: {coverage_comparison_low})</span>
                            </div>
                        </div>
                    </div>
                </div>"""

            location_efficiency_section += """
            </div>"""
        else:
            location_efficiency_section = f"""
            <h3>Task Performance Summary</h3>
            <div class="two-column">
                <div>
                    <h4>Overall Task Patterns</h4>
                    <ul>
                        <li><strong>Average Task Duration:</strong> {avg_duration:.1f} minutes (vs last period: <span style="color: {get_comparison_color(comparisons.get('avg_duration', 'N/A'))};">{format_comparison(comparisons.get('avg_duration', 'N/A'))}</span>)</li>
                        <li><strong>Weekend completion:</strong> {weekend_completion:.1f}%</li>
                    </ul>
                </div>
            </div>"""

        return f"""
        <section id="task-performance" class="section">
            <h2>📋 Task & Schedule Performance</h2>

            <h3>Task Management Efficiency</h3>
            <p>Task tracking across all facilities: {task_data.get('total_tasks', 0)} total tasks with {task_data.get('total_area_cleaned', 0):,.0f} sq ft total coverage and {avg_duration:.1f} minutes average task duration.</p>

            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Total</th>
                        <th>Completed</th>
                        <th>In Progress</th>
                        <th>Average Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>All Facilities</strong></td>
                        <td>{task_data.get('total_tasks', 0)}</td>
                        <td>{task_data.get('completed_tasks', 0)}</td>
                        <td>0</td>
                        <td>
                            {avg_duration:.1f} min
                            <span style="color: {get_comparison_color(comparisons.get('avg_duration', 'N/A'))}; font-size: 9px; margin-left: 5px;">
                                (vs last: {format_comparison(comparisons.get('avg_duration', 'N/A'))})
                            </span>
                        </td>
                    </tr>
                </tbody>
            </table>
            <div class="chart-container" style="display: flex; justify-content: space-between; align-items: center; margin: 15px 0;">
                <div style="flex: 1; text-align: center;">
                    {self._get_chart_image_html('task_status_chart', 'Task Status Distribution', 80, 250)}
                </div>
                <div style="flex: 1; text-align: center;">
                    {self._get_chart_image_html('task_mode_chart', 'Task Mode Distribution', 80, 250)}
                </div>
            </div>

            {location_efficiency_section}
        </section>"""

    def _get_location_charts_html(self, location_name: str) -> str:
        """Generate HTML for all location-specific charts"""
        html = ""
        if hasattr(self, 'chart_images'):
            if 'location_chart' in self.chart_images:
                img_data = self.chart_images['location_chart'].get(location_name, '')
                html = f"""
                    <div style="text-align: center; margin: 15px 0;">
                        <img src="{img_data}"
                             alt="{location_name} Performance"
                             style="max-width: 100%; height: 200px; border: 1px solid #ddd; border-radius: 5px;">
                    </div>"""
        return html

    def _generate_facility_section(self, content: Dict[str, Any]) -> str:
        """Generate facility performance section (PDF version)"""
        facilities = content.get('facility_performance', {}).get('facilities', {})
        facility_efficiency = content.get('facility_efficiency_metrics', {})
        map_performance_by_building = content.get('map_performance_by_building', {})
        comparisons = content.get('period_comparisons', {})
        facility_comparisons = comparisons.get('facility_comparisons', {})
        map_comparisons = comparisons.get('map_comparisons', {})

        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value):
            if value == 'N/A' or not value:
                return '#6c757d'
            elif value.startswith('+'):
                return '#28a745'
            elif value.startswith('-'):
                return '#dc3545'
            else:
                return '#6c757d'

        # Generate facility performance tables
        facility_sections = ""
        for facility_name, metrics in facilities.items():
            facility_comp = facility_comparisons.get(facility_name, {})
            facility_eff = facility_efficiency.get(facility_name, {})

            total_tasks = metrics.get('total_tasks', 0)
            coverage_eff = metrics.get('coverage_efficiency', 0)
            water_efficiency = facility_eff.get('water_efficiency', 0)
            time_efficiency = facility_eff.get('time_efficiency', 0)

            facility_sections += f"""
            <div>
                <h3>{facility_name}</h3>
                <p>Performance metrics for {facility_name}: {total_tasks} total tasks, {metrics.get('area_cleaned', 0):,.0f} sq ft total area cleaned, {coverage_eff:.1f}% average coverage, {time_efficiency:.1f} sq ft/hour time efficiency, and {water_efficiency:.1f} sq ft/fl oz water efficiency.</p>

                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Performance</th>
                            <th>vs Last Period</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Total Area Cleaned</td>
                            <td>{metrics.get('area_cleaned', 0):,.0f} sq ft</td>
                            <td style="color: {get_comparison_color(facility_comp.get('area_cleaned', 'N/A'))};">{format_comparison(facility_comp.get('area_cleaned', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Average Coverage</td>
                            <td>{coverage_eff:.1f}%</td>
                            <td style="color: {get_comparison_color(facility_comp.get('coverage_efficiency', 'N/A'))};">{format_comparison(facility_comp.get('coverage_efficiency', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Running Hours</td>
                            <td>{metrics.get('running_hours', 0):.1f} hours</td>
                            <td style="color: {get_comparison_color(facility_comp.get('running_hours', 'N/A'))};">{format_comparison(facility_comp.get('running_hours', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Time Efficiency</td>
                            <td>{time_efficiency:.1f} sq ft/hr</td>
                            <td style="color: {get_comparison_color(facility_comp.get('time_efficiency', 'N/A'))};">{format_comparison(facility_comp.get('time_efficiency', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Power Efficiency</td>
                            <td>{metrics.get('power_efficiency', 0):,.0f} sq ft/kWh</td>
                            <td style="color: {get_comparison_color(facility_comp.get('power_efficiency', 'N/A'))};">{format_comparison(facility_comp.get('power_efficiency', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Water Efficiency</td>
                            <td>{water_efficiency:.1f} sq ft/fl oz</td>
                            <td style="color: {get_comparison_color(facility_comp.get('water_efficiency', 'N/A'))};">{format_comparison(facility_comp.get('water_efficiency', 'N/A'))}</td>
                        </tr>
                    </tbody>
                </table>
            </div>"""

        if not facility_sections:
            facility_sections = '<div><p>No facility-specific data available</p></div>'

        # Generate map-specific performance section (PDF version)
        map_sections = ""
        if map_performance_by_building:
            map_sections = """
            <h3>Map-Specific Performance</h3>
            <p><strong>Coverage calculation:</strong> (actual area / planned area) × 100. Other metrics include area cleaned (sq ft), running hours, and efficiency ratios.</p>"""

            for building_name, maps in map_performance_by_building.items():
                if maps and len(maps) > 0:
                    map_sections += f"""
                    <div class="map-section">
                        <h4>{building_name} Maps</h4>
                        <div class="building-maps">"""

                    for map_data in maps:
                        map_name = map_data.get('map_name', 'Unknown Map')
                        coverage = map_data.get('coverage_percentage', 0)
                        map_comp = map_comparisons.get(building_name, {}).get(map_name, {})

                        map_sections += f"""
                        <div style="margin: 10px 0; border: 1px solid #dee2e6; border-radius: 3px; padding: 10px;">
                            <h5>{map_name}</h5>
                            <div class="progress-container">
                                <span>Coverage:</span>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {min(coverage, 100)}%"></div>
                                </div>
                                <span class="progress-text">{coverage:.1f}%</span>
                                <span style="color: {get_comparison_color(map_comp.get('coverage_percentage', 'N/A'))}; font-size: 9px; margin-left: 8px;">
                                    vs last: {format_comparison(map_comp.get('coverage_percentage', 'N/A'))}
                                </span>
                            </div>
                            <div class="map-metrics">
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('area_cleaned', 0):,.0f}</div>
                                    <div style="font-size: 9px; color: #6c757d;">Area Cleaned (sq ft)</div>
                                    <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('area_cleaned', 'N/A'))};">
                                        vs last: {format_comparison(map_comp.get('area_cleaned', 'N/A'))}
                                    </div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('running_hours', 0):.1f}</div>
                                    <div style="font-size: 9px; color: #6c757d;">Running Hours</div>
                                    <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('running_hours', 'N/A'))};">
                                        vs last: {format_comparison(map_comp.get('running_hours', 'N/A'))}
                                    </div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('time_efficiency', 0):.0f}</div>
                                    <div style="font-size: 9px; color: #6c757d;">Time Eff (sq ft/hr)</div>
                                    <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('time_efficiency', 'N/A'))};">
                                        vs last: {format_comparison(map_comp.get('time_efficiency', 'N/A'))}
                                    </div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('power_efficiency', 0):.0f}</div>
                                    <div style="font-size: 9px; color: #6c757d;">Power Eff (sq ft/kWh)</div>
                                    <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('power_efficiency', 'N/A'))};">
                                        vs last: {format_comparison(map_comp.get('power_efficiency', 'N/A'))}
                                    </div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('water_efficiency', 0):.1f}</div>
                                    <div style="font-size: 9px; color: #6c757d;">Water Eff (sq ft/fl oz)</div>
                                    <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('water_efficiency', 'N/A'))};">
                                        vs last: {format_comparison(map_comp.get('water_efficiency', 'N/A'))}
                                    </div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('days_with_tasks', 0)}</div>
                                    <div style="font-size: 9px; color: #6c757d;">Days with Tasks</div>
                                    <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('days_with_tasks', 'N/A'))};">
                                        vs last: {format_comparison(map_comp.get('days_with_tasks', 'N/A'))}
                                    </div>
                                </div>
                            </div>
                        </div>"""

                    map_sections += """
                        </div>
                    </div>"""
        else:
            map_sections = """
            <h3>Map-Specific Performance</h3>
            <p>No map-specific performance data available</p>"""

        return f"""
        <section id="facility-performance" class="section">
            <h2>🏢 Facility-Specific Performance</h2>

            <div class="two-column">
                {facility_sections}
            </div>

            {map_sections}
        </section>"""

    def _generate_resource_section(self, content: Dict[str, Any]) -> str:
        """Generate resource utilization section (PDF version)"""
        resource_data = content.get('resource_utilization', {})
        comparisons = content.get('period_comparisons', {})
        facility_comparisons = comparisons.get('facility_comparisons', {})

        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value):
            if value == 'N/A' or not value:
                return '#6c757d'
            elif value.startswith('+'):
                return '#dc3545'  # Red for increased consumption (bad)
            elif value.startswith('-'):
                return '#28a745'  # Green for decreased consumption (good)
            else:
                return '#6c757d'

        # Calculate resource usage by facility
        facility_breakdown = ""
        facility_resource_metrics = content.get('facility_resource_metrics', {})
        if facility_resource_metrics:
            facility_breakdown = """
            <div class="two-column">
                <div>
                    <h4>Energy Usage by Facility</h4>
                    <ul>"""

            for facility_name, resource_metrics in facility_resource_metrics.items():
                facility_comp = facility_comparisons.get(facility_name, {})
                facility_breakdown += f"""<li><strong>{facility_name}:</strong> {resource_metrics.get('energy_consumption_kwh', 0):.1f} kWh
                    <span style="color: {get_comparison_color(facility_comp.get('energy_consumption_facility', 'N/A'))};">
                        (vs last: {format_comparison(facility_comp.get('energy_consumption_facility', 'N/A'))})
                    </span>
                </li>"""

            facility_breakdown += """
                    </ul>
                </div>
                <div>
                    <h4>Water Usage by Facility</h4>
                    <ul>"""

            for facility_name, resource_metrics in facility_resource_metrics.items():
                facility_comp = facility_comparisons.get(facility_name, {})
                facility_breakdown += f"""<li><strong>{facility_name}:</strong> {resource_metrics.get('water_consumption_floz', 0):.0f} fl oz
                    <span style="color: {get_comparison_color(facility_comp.get('water_consumption_facility', 'N/A'))};">
                        (vs last: {format_comparison(facility_comp.get('water_consumption_facility', 'N/A'))})
                    </span>
                </li>"""

            facility_breakdown += """
                    </ul>
                </div>
            </div>"""
        else:
            # Fallback if no facility-specific resource data
            total_energy = resource_data.get('total_energy_consumption_kwh', 0)
            total_water = resource_data.get('total_water_consumption_floz', 0)

            facility_breakdown = f"""
            <div class="two-column">
                <div>
                    <h4>Power Consumption Analysis</h4>
                    <ul>
                        <li><strong>Total consumption:</strong> {total_energy:.2f} kWh
                            <span style="color: {get_comparison_color(comparisons.get('energy_consumption', 'N/A'))};">
                                (vs last: {format_comparison(comparisons.get('energy_consumption', 'N/A'))})
                            </span>
                        </li>
                        <li><strong>Efficiency:</strong> {resource_data.get('area_per_kwh', 0):.0f} sq ft per kWh</li>
                    </ul>
                </div>
                <div>
                    <h4>Water Usage Optimization</h4>
                    <ul>
                        <li><strong>Total usage:</strong> {total_water:.0f} fl oz
                            <span style="color: {get_comparison_color(comparisons.get('water_consumption', 'N/A'))};">
                                (vs last: {format_comparison(comparisons.get('water_consumption', 'N/A'))})
                            </span>
                        </li>
                        <li><strong>Efficiency:</strong> {resource_data.get('area_per_gallon', 0):.0f} sq ft per gallon</li>
                    </ul>
                </div>
            </div>"""

        return f"""
        <section id="resource-utilization" class="section">
            <h2>⚡ Resource Utilization & Efficiency</h2>

            <h3>Resource Performance Overview</h3>
            <p>Resource utilization summary: {resource_data.get('total_energy_consumption_kwh', 0):.2f} kWh total energy consumption, {resource_data.get('total_water_consumption_floz', 0):.0f} fl oz total water usage, {resource_data.get('area_per_kwh', 0):.0f} sq ft per kWh energy efficiency, and {resource_data.get('area_per_gallon', 0):.0f} sq ft per gallon water efficiency.</p>

            {self._get_chart_image_html('resource_chart', 'Weekly Resource Utilization')}

            {facility_breakdown}

        </section>"""

    def _generate_financial_section(self, content: Dict[str, Any]) -> str:
        """Generate financial performance section (PDF version)"""
        cost_data = content.get('cost_analysis', {})
        comparisons = content.get('period_comparisons', {})

        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value, metric_type):
            if value == 'N/A' or not value:
                return '#6c757d'
            if 'cost' in str(metric_type).lower():
                if value.startswith('+'):
                    return '#dc3545'  # Red for increased costs (bad)
                elif value.startswith('-'):
                    return '#28a745'  # Green for decreased costs (good)
            elif 'savings' in str(metric_type).lower():
                if value.startswith('+'):
                    return '#28a745'  # Green for increased savings (good)
                elif value.startswith('-'):
                    return '#dc3545'  # Red for decreased savings (bad)
            else:
                return '#28a745' # Green for ROI

        def safe_format(value, prefix="$", suffix=""):
            if value == 'N/A' or value is None:
                return 'N/A'
            try:
                return f"{prefix}{float(value):,.2f}{suffix}"
            except:
                return str(value)

        return f"""
        <section id="financial-performance" class="section">
            <h2>💰 Financial Performance</h2>

            <p>Financial analysis based on actual resource usage: {safe_format(cost_data.get('cost_per_sqft', 0), '$', '/sq ft')} average cost per square foot, {safe_format(cost_data.get('total_cost', 0))} total operational cost, {cost_data.get('hours_saved', 0):.1f} hours saved compared to manual cleaning, and {safe_format(cost_data.get('savings', 0))} in realized savings.</p>

            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>vs Previous Period</th>
                        <th>Notes</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Cost per Sq Ft</td>
                        <td>{safe_format(cost_data.get('cost_per_sqft', 0), '$', '/sq ft')}</td>
                        <td style="color: {get_comparison_color(comparisons.get('cost_per_sqft', 'N/A'), 'cost_per_sqft')};">{format_comparison(comparisons.get('cost_per_sqft', 'N/A'))}</td>
                        <td>Water + energy cost per area cleaned</td>
                    </tr>
                    <tr>
                        <td>Total Cost</td>
                        <td>{safe_format(cost_data.get('total_cost', 0))}</td>
                        <td style="color: {get_comparison_color(comparisons.get('total_cost', 'N/A'), 'total_cost')};">{format_comparison(comparisons.get('total_cost', 'N/A'))}</td>
                        <td>Robot operational cost this period</td>
                    </tr>
                    <tr>
                        <td>Savings</td>
                        <td>{safe_format(cost_data.get('savings', 0))}</td>
                        <td style="color: {get_comparison_color(comparisons.get('savings', 'N/A'), 'savings')};">{format_comparison(comparisons.get('savings', 'N/A'))}</td>
                        <td>Savings vs manual cleaning (${cost_data.get('hourly_wage', 25)}/hr)</td>
                    </tr>
                    <tr>
                        <td>Hours Saved vs Manual</td>
                        <td>{cost_data.get('hours_saved', 0):.1f} hrs</td>
                        <td style="color: {get_comparison_color(comparisons.get('hours_saved', 'N/A'), 'hours_saved')};">{format_comparison(comparisons.get('hours_saved', 'N/A'))}</td>
                        <td>Time saved compared to manual cleaning</td>
                    </tr>
                    <tr>
                        <td>Annual Projected Savings</td>
                        <td>{safe_format(cost_data.get('annual_projected_savings', 0))}</td>
                        <td style="color: {get_comparison_color(comparisons.get('annual_projected_savings', 'N/A'), 'annual_projected_savings')};">{format_comparison(comparisons.get('annual_projected_savings', 'N/A'))}</td>
                        <td>Projected annual savings</td>
                    </tr>
                    <tr>
                        <td>ROI Impact</td>
                        <td>N/A</td>
                        <td>N/A</td>
                        <td>Requires investment data</td>
                    </tr>
                </tbody>
            </table>

            {self._get_chart_image_html('financial_chart', 'Weekly Financial Performance')}

            <div class="highlight-box">
                <h3>💡 Financial Impact Summary</h3>
                <div class="metrics-grid">
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('total_cost', 0))}</strong></div>
                        <div>Total operational cost</div>
                        <div style="color: {get_comparison_color(comparisons.get('total_cost', 'N/A'), 'total_cost')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('total_cost', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('human_cost', 0))}</strong></div>
                        <div>Equivalent manual cost</div>
                        <div style="color: {get_comparison_color(comparisons.get('human_cost', 'N/A'), 'human_cost')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('human_cost', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('savings', 0))}</strong></div>
                        <div>Savings realized</div>
                        <div style="color: {get_comparison_color(comparisons.get('savings', 'N/A'), 'savings')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('annual_projected_savings', 0))}</strong></div>
                        <div>Annual projected savings</div>
                        <div style="color: {get_comparison_color(comparisons.get('annual_projected_savings', 'N/A'), 'annual_projected_savings')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('annual_projected_savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{cost_data.get('hours_saved', 0):.1f} hrs</strong></div>
                        <div>Hours saved vs manual</div>
                        <div style="color: {get_comparison_color(comparisons.get('hours_saved', 'N/A'), 'hours_saved')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('hours_saved', 'N/A'))}
                        </div>
                    </div>
                </div>
                <p style="margin-top: 15px; font-size: 10px; opacity: 0.8;">
                    {cost_data.get('note', 'Cost calculations based on actual resource usage and human cleaning speed benchmarks.')}
                </p>
            </div>

        </section>"""

    def _generate_charging_section(self, content: Dict[str, Any]) -> str:
        """Generate charging performance section (PDF version)"""
        charging_data = content.get('charging_performance', {})
        comparisons = content.get('period_comparisons', {})
        facility_comparisons = comparisons.get('facility_comparisons', {})

        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value):
            if value == 'N/A' or not value:
                return '#6c757d'
            elif value.startswith('+'):
                return '#28a745'
            elif value.startswith('-'):
                return '#dc3545'
            else:
                return '#6c757d'

        # Calculate charging patterns by location
        charging_by_location = ""
        facility_charging_metrics = content.get('facility_charging_metrics', {})

        if facility_charging_metrics:
            charging_by_location = """
            <h3>Charging Patterns by Location</h3>
            <table>
                <thead>
                    <tr>
                        <th>Location</th>
                        <th>Sessions</th>
                        <th>Avg Duration</th>
                        <th>Median Duration</th>
                        <th>Avg Power Gain</th>
                        <th>Median Power Gain</th>
                    </tr>
                </thead>
                <tbody>"""

            for facility_name, charging_metrics in facility_charging_metrics.items():
                facility_comp = facility_comparisons.get(facility_name, {})
                charging_by_location += f"""
                    <tr>
                        <td>{facility_name}</td>
                        <td>{charging_metrics.get('total_sessions', 0)}
                            <div style="font-size: 9px; color: {get_comparison_color(facility_comp.get('total_sessions', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('total_sessions', 'N/A'))}
                            </div>
                        </td>
                        <td>{charging_metrics.get('avg_duration_minutes', 0):.1f} min
                            <div style="font-size: 9px; color: {get_comparison_color(facility_comp.get('avg_charging_duration', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('avg_charging_duration', 'N/A'))}
                            </div>
                        </td>
                        <td>{charging_metrics.get('median_duration_minutes', 0):.1f} min
                            <div style="font-size: 9px; color: {get_comparison_color(facility_comp.get('median_charging_duration', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('median_charging_duration', 'N/A'))}
                            </div>
                        </td>
                        <td>+{charging_metrics.get('avg_power_gain_percent', 0):.1f}%
                            <div style="font-size: 9px; color: {get_comparison_color(facility_comp.get('avg_power_gain_facility', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('avg_power_gain_facility', 'N/A'))}
                            </div>
                        </td>
                        <td>+{charging_metrics.get('median_power_gain_percent', 0):.1f}%
                            <div style="font-size: 9px; color: {get_comparison_color(facility_comp.get('median_power_gain_facility', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('median_power_gain_facility', 'N/A'))}
                            </div>
                        </td>
                    </tr>"""

            charging_by_location += """
                </tbody>
            </table>"""
        else:
            charging_by_location = "<h3>Charging Patterns by Location</h3><p>Location-specific charging data not available</p>"

        return f"""
        <section id="charging-performance" class="section">
            <h2>🔋 Charging Sessions Performance</h2>

            <p>Charging patterns and battery management during the reporting period: {charging_data.get('total_sessions', 0)} total sessions, {charging_data.get('avg_charging_duration_minutes', 0):.1f} minutes average duration, and {charging_data.get('avg_power_gain_percent', 0):.1f}% average power gain per session.</p>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{charging_data.get('total_sessions', 0)}</div>
                    <div class="metric-label">Total Charging Sessions</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('charging_sessions', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('charging_sessions', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{charging_data.get('avg_charging_duration_minutes', 0):.1f} min</div>
                    <div class="metric-label">Avg Charging Duration</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('avg_charging_duration', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('avg_charging_duration', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{charging_data.get('median_charging_duration_minutes', 0):.1f} min</div>
                    <div class="metric-label">Median Charging Duration</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('median_charging_duration', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('median_charging_duration', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">+{charging_data.get('avg_power_gain_percent', 0):.1f}%</div>
                    <div class="metric-label">Avg Power Gain per Session</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('avg_power_gain', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('avg_power_gain', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">+{charging_data.get('median_power_gain_percent', 0):.1f}%</div>
                    <div class="metric-label">Median Power Gain per Session</div>
                    <div style="font-size: 9px; margin-top: 3px; color: {get_comparison_color(comparisons.get('median_power_gain', 'N/A'))};">
                        vs last: {format_comparison(comparisons.get('median_power_gain', 'N/A'))}
                    </div>
                </div>
            </div>

            <h3>Charging Performance Summary</h3>
            <p>Weekly average charging performance shows consistent battery management across all locations with typical session duration of {charging_data.get('median_charging_duration_minutes', 0):.1f} minutes and median power gain of {charging_data.get('median_power_gain_percent', 0):.1f}% per session.</p>
            {self._get_chart_image_html('charging_chart', 'Weekly Charging Performance')}
            {charging_by_location}

        </section>"""

    def _generate_conclusion(self, content: Dict[str, Any]) -> str:
        """Generate conclusion section (PDF version)"""
        fleet_data = content.get('fleet_performance', {})
        task_data = content.get('task_performance', {})
        resource_data = content.get('resource_utilization', {})
        charging_data = content.get('charging_performance', {})

        period = content.get('period', 'the reporting period')

        def format_value(value, suffix=""):
            if value == 'N/A' or value is None:
                return 'N/A'
            return f"{value:,.1f}{suffix}" if isinstance(value, (int, float)) else f"{value}{suffix}"

        return f"""
        <section id="conclusion" class="section">
            <h2>🎯 Conclusion</h2>

            <div class="highlight-box">
                <p>{period.title()} performance summary: {format_value(task_data.get('completion_rate', 0), '%')} task completion rate across
                {format_value(fleet_data.get('total_robots', 0))} robot(s),
                {format_value(task_data.get('total_tasks', 0))} tasks completed,
                {format_value(resource_data.get('total_area_cleaned_sqft', 0))} sq ft cleaned,
                {format_value(charging_data.get('total_sessions', 0))} charging sessions,
                {format_value(resource_data.get('total_energy_consumption_kwh', 0))} kWh energy consumption,
                and {format_value(resource_data.get('total_water_consumption_floz', 0))} fl oz water usage.</p>
            </div>
        </section>"""

    def _generate_footer(self, content: Dict[str, Any]) -> str:
        """Generate footer with metadata (PDF version)"""
        generation_time = content.get('generation_time', datetime.now())
        robots_count = content.get('robots_included', 0)

        return f"""
        <footer>
            <p><strong>{content.get('title', 'Robot Performance Report')}</strong><br>
            Period: {content.get('period', 'N/A')}<br>
            Robots Included: {robots_count}<br>
            Generated: {generation_time.strftime('%B %d, %Y at %I:%M %p') if hasattr(generation_time, 'strftime') else str(generation_time)}</p>
        </footer>"""
