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
            detail_level = config.detail_level.value.lower()
            self.chart_images = self.chart_formatter.generate_pdf_chart_images(content)

            content_categories = config.content_categories

            # Always include executive summary
            sections = [self._generate_executive_summary(content, detail_level=detail_level)]

            # Task Performance section
            if any(cat in content_categories for cat in ['executive-summary', 'fleet-management', 'facility-performance', 'task-performance', 'cleaning-performance']):
                sections.append(self._generate_task_section(content, detail_level=detail_level))

            # Facility-Specific Performance section
            if any(cat in content_categories for cat in ['facility-performance', 'cleaning-performance']):
                sections.append(self._generate_facility_section(content, detail_level=detail_level))

            # Resource Utilization & Efficiency section
            if 'resource-utilization' in content_categories:
                sections.append(self._generate_resource_section(content, detail_level=detail_level))

            # Financial Performance section
            if 'financial-performance' in content_categories:
                sections.append(self._generate_financial_section(content, detail_level=detail_level))

            # Charging Sessions Performance section
            if 'charging-performance' in content_categories:
                sections.append(self._generate_charging_section(content, detail_level=detail_level))

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
        /* Health Score Styles - PDF optimized */
            .health-score-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin: 15px 0;
                align-items: center;
                page-break-inside: avoid;
            }

            .health-pentagon {
                position: relative;
                width: 100%;
                margin: 0 auto;
                text-align: center;
            }

            .health-details {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }

            .health-component {
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 5px 0;
            }

            .health-component-label {
                min-width: 100px;
                font-weight: 600;
                color: #495057;
                font-size: 10px;
            }

            .health-component-bar {
                flex: 1;
                height: 12px;
                background: #e9ecef;
                border-radius: 6px;
                overflow: hidden;
                position: relative;
            }

            .health-component-fill {
                height: 100%;
                transition: none; /* No transitions in PDF */
                border-radius: 6px;
            }

            .health-excellent { background: linear-gradient(90deg, #28a745, #20c997); }
            .health-good { background: linear-gradient(90deg, #17a2b8, #3498db); }
            .health-fair { background: linear-gradient(90deg, #ffc107, #f39c12); }
            .health-poor { background: linear-gradient(90deg, #dc3545, #c0392b); }

            .health-component-value {
                min-width: 40px;
                text-align: right;
                font-weight: bold;
                color: #2c3e50;
                font-size: 10px;
            }

            /* Utilization breakdown styles */
            .utilization-breakdown {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 10px;
                margin: 15px 0;
                page-break-inside: avoid;
            }

            .utilization-card {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 5px;
                padding: 10px;
                text-align: center;
                page-break-inside: avoid;
            }

            .utilization-label {
                font-size: 9px;
                color: #6c757d;
                margin-bottom: 5px;
            }

            .utilization-value {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
            }

            .utilization-bar-container {
                margin-top: 8px;
                height: 6px;
                background: #e9ecef;
                border-radius: 3px;
                overflow: hidden;
            }

            .utilization-bar-fill {
                height: 100%;
            }

            .working-time { background: #28a745; }
            .idle-time { background: #ffc107; }
            .charging-time { background: #17a2b8; }
            .downtime { background: #dc3545; }

            /* Metric definition boxes */
            .metric-definition-box {
                background: #e3f2fd;
                padding: 12px;
                border-radius: 5px;
                margin: 15px 0;
                border-left: 4px solid #2196f3;
                page-break-inside: avoid;
                font-size: 10px;
            }

            .metric-definition-box h4 {
                color: #1976d2;
                margin-top: 0;
                font-size: 12px;
                margin-bottom: 8px;
            }

            .metric-definition-box p {
                margin: 3px 0;
                font-size: 10px;
            }

            /* Time distribution chart containers */
            .time-chart-container {
                margin: 8px 0;
                page-break-inside: avoid;
            }

            .time-chart-title {
                margin: 5px 0;
                font-size: 10px;
                color: #495057;
                font-weight: 600;
            }

            .time-metrics-summary {
                background: #e9ecef;
                padding: 8px;
                border-radius: 3px;
                font-size: 9px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 5px;
            }

            .time-metrics-summary div {
                white-space: nowrap;
            }

            @media print {
                .health-score-container {
                    page-break-inside: avoid;
                }
                .utilization-breakdown {
                    page-break-inside: avoid;
                }
                .metric-definition-box {
                    page-break-inside: avoid;
                }
                .time-chart-container {
                    page-break-inside: avoid;
                }
            }
        </style>"""

    def _generate_executive_summary(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
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
                return '#28a745' # Green for increased savings (good)
            elif value.startswith('-'):
                return '#dc3545'
            else:
                return '#6c757d'

        # Get days with tasks ratio format
        days_ratio = fleet_data.get('days_ratio', fleet_data.get('days_with_tasks', 0))

        # Generate robot performance table with NEW COLUMNS including health score and utilization
        robot_rows = ""
        robot_health_scores = content.get('robot_health_scores', {})

        if individual_robots:
            for robot in individual_robots[:10]:
                robot_id = robot.get('robot_id', 'Unknown')

                # Get health data if available
                has_health_data = robot_health_scores and robot_id in robot_health_scores
                if has_health_data:
                    health_data = robot_health_scores.get(robot_id, {})
                    health_score = health_data.get('overall_health_score', 0)
                    health_rating = health_data.get('overall_health_rating', 'N/A')

                    # Color code health rating
                    if health_rating == 'Excellent':
                        health_color = '#28a745'
                    elif health_rating == 'Good':
                        health_color = '#17a2b8'
                    elif health_rating == 'Fair':
                        health_color = '#ffc107'
                    else:
                        health_color = '#dc3545'

                    health_display = f'<span style="color: {health_color}; font-weight: bold;">{health_score:.1f} ({health_rating})</span>'
                else:
                    health_display = '<span style="color: #6c757d;">N/A</span>'

                # Get utilization
                utilization = robot.get('utilization_score', robot.get('working_ratio', 0))

                robot_rows += f"""
                <tr>
                    <td>{robot_id}</td>
                    <td>{robot.get('location', 'Unknown Location')}</td>
                    <td>{robot.get('total_tasks', 0)}</td>
                    <td>{robot.get('tasks_completed', 0)}</td>
                    <td>{robot.get('total_area_cleaned', 0):,.0f} sq ft</td>
                    <td>{robot.get('average_coverage', 0):.1f}%</td>
                    <td>{robot.get('days_with_tasks', 0)}</td>
                    <td>{robot.get('running_hours', 0):.1f} hrs</td>
                    <td>{utilization:.1f}%</td>
                    <td>{health_display}</td>
                </tr>"""

        if not robot_rows:
            robot_rows = '<tr><td colspan="10">No robot data available</td></tr>'

        roi_breakdown_rows = ""
        robot_roi_breakdown = cost_data.get('robot_roi_breakdown', {})
        if robot_roi_breakdown:
            for robot_sn, roi_data in list(robot_roi_breakdown.items())[:10]:  # Top 10 robots
                roi_breakdown_rows += f'''
                <tr>
                    <td>{robot_sn}</td>
                    <td>{roi_data.get('months_elapsed', 0)}</td>
                    <td>${roi_data.get('investment', 0):,.2f}</td>
                    <td>${roi_data.get('savings', 0):,.2f}</td>
                    <td>{roi_data.get('roi_percent', 0):.1f}%</td>
                </tr>'''

        if not roi_breakdown_rows:
            roi_breakdown_rows = '<tr><td colspan="5">No ROI breakdown data available</td></tr>'

        # Base content always included
        base_html = f"""
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
                    <div class="metric-label">Avg Daily Running Hours per Robot (hrs/robot)</div>
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
        """

        # Conditional content
        robot_performance_html = ""
        if detail_level in ['detailed', 'in-depth']:
            robot_performance_html = f"""
            <h3>🤖 Individual Robot Performance</h3>

            <!-- Metric Definitions for Table -->
            <div style="background: #e3f2fd; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #2196f3; font-size: 9px; page-break-inside: avoid;">
                <strong style="color: #1976d2;">Key Metrics:</strong>
                <span style="margin-left: 10px;"><strong>Utilization:</strong> Working hours / Uptime hours × 100. Measures productive time efficiency.</span>
                <span style="margin-left: 10px;"><strong>Health Score:</strong> Overall robot health (0-100) based on availability (40%), task success (20%), efficiency (20%), mode performance (10%), and battery health (10%).</span>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Robot ID</th>
                        <th>Location</th>
                        <th>Total Tasks</th>
                        <th>Tasks Completed</th>
                        <th>Total Area Cleaned</th>
                        <th>Average Coverage</th>
                        <th>Days with Tasks</th>
                        <th>Running Hours</th>
                        <th>Utilization</th>
                        <th>Health Score</th>
                    </tr>
                </thead>
                <tbody>
                    {robot_rows}
                </tbody>
            </table>
            """

        roi_breakdown_html = ""
        if detail_level == 'in-depth':
            roi_breakdown_html = f"""
            <h3>💰 Individual Robot ROI Breakdown</h3>
            <p>Investment and ROI analysis per robot based on lease model and operational savings.</p>
            <table>
                <thead>
                    <tr>
                        <th>Robot ID</th>
                        <th>Months Deployed</th>
                        <th>Total Investment</th>
                        <th>Cumulative Savings</th>
                        <th>ROI</th>
                    </tr>
                </thead>
                <tbody>
                    {roi_breakdown_rows}
                </tbody>
            </table>
            """

        return base_html + robot_performance_html + roi_breakdown_html + "</section>"

    def _generate_task_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate task performance section (PDF version - shows weekly averages)"""
        task_data = content.get('task_performance', {})
        facilities = content.get('facility_performance', {}).get('facilities', {})
        comparisons = content.get('period_comparisons', {})
        facility_comparisons = comparisons.get('facility_comparisons', {})
        daily_location_efficiency = content.get('daily_location_efficiency', {})

        # Get real calculated values
        weekend_completion = task_data.get('weekend_schedule_completion', 0)
        avg_duration = task_data.get('avg_task_duration_minutes', 0)

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

        # Base Task Management Efficiency (always included)
        base_html = f"""
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

            <div class="chart-row" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                <div class="chart-small">
                    {self._get_chart_image_html('task_status_chart', 'Task Status Distribution', max_height=200)}
                </div>
                <div class="chart-small">
                    {self._get_chart_image_html('task_mode_chart', 'Task Mode Distribution', max_height=200)}
                </div>
            </div>
        """

        # Generate location-based efficiency section conditionally
        location_efficiency_section = ""
        facility_task_metrics = content.get('facility_task_metrics', {})
        facility_breakdown_metrics = content.get('facility_breakdown_metrics', {})
        facility_efficiency = content.get('facility_efficiency_metrics', {})

        if detail_level == 'overview':
            # For OVERVIEW: Omit location efficiency section
            pass
        elif daily_location_efficiency:
            location_efficiency_section = """
            <h3>Task Efficiency by Location</h3>
            <p>Daily task performance showing running hours and coverage efficiency patterns for each location. Each chart displays actual operational data to identify location-specific performance trends.</p>

            <div class="location-efficiency-single-column">"""

            for location_name, efficiency_data in daily_location_efficiency.items():
                # Safe access to facility data with proper fallbacks
                facility_comp = facility_comparisons.get(location_name, {}) if isinstance(facility_comparisons, dict) else {}
                facility_task_data = facility_task_metrics.get(location_name, {}) if isinstance(facility_task_metrics, dict) else {}
                facility_breakdown = facility_breakdown_metrics.get(location_name, {}) if isinstance(facility_breakdown_metrics, dict) else {}
                facility_eff = facility_efficiency.get(location_name, {}) if isinstance(facility_efficiency, dict) else {}

                # Use facility-specific duration if available, otherwise use global average
                facility_avg_duration = facility_task_data.get('avg_duration_minutes', avg_duration) if facility_task_data else avg_duration
                primary_mode = facility_task_data.get('primary_mode', 'Mixed tasks') if facility_task_data else 'Mixed tasks'

                # Get coverage by day info
                highest_coverage_day = facility_breakdown.get('highest_coverage_day', 'N/A') if facility_breakdown else 'N/A'
                lowest_coverage_day = facility_breakdown.get('lowest_coverage_day', 'N/A') if facility_breakdown else 'N/A'

                # Get the comparison data correctly
                coverage_comparison_high = facility_comp.get('highest_coverage_day', 'N/A') if facility_comp else 'N/A'
                coverage_comparison_low = facility_comp.get('lowest_coverage_day', 'N/A') if facility_comp else 'N/A'

                # Get days ratio safely
                days_ratio = facility_eff.get('days_ratio', 'N/A') if facility_eff else 'N/A'

                if detail_level in ['detailed', 'in-depth']:
                    location_efficiency_section += f"""
                    <div class="location-efficiency-single-line">
                        <h4>{location_name}</h4>
                        <div class="location-single-line-content">
                            <div class="location-chart-compact">
                                {self._get_chart_image_html(f'taskEfficiencyChart_{location_name.replace(" ", "_")}', f'{location_name} Task Efficiency', max_height=200)}
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
            # Fallback if no location-specific efficiency data
            facility_patterns = ""
            for facility_name, metrics in facilities.items():
                facility_comp = facility_comparisons.get(facility_name, {}) if isinstance(facility_comparisons, dict) else {}
                facility_task_data = facility_task_metrics.get(facility_name, {}) if isinstance(facility_task_metrics, dict) else {}
                facility_breakdown = facility_breakdown_metrics.get(facility_name, {}) if isinstance(facility_breakdown_metrics, dict) else {}

                # Use facility-specific duration if available, otherwise use global average
                facility_avg_duration = facility_task_data.get('avg_duration_minutes', avg_duration) if facility_task_data else avg_duration
                primary_mode = facility_task_data.get('primary_mode', 'Mixed tasks') if facility_task_data else 'Mixed tasks'

                # Get coverage by day info
                highest_coverage_day = facility_breakdown.get('highest_coverage_day', 'N/A') if facility_breakdown else 'N/A'
                lowest_coverage_day = facility_breakdown.get('lowest_coverage_day', 'N/A') if facility_breakdown else 'N/A'

                # Get the comparison data correctly
                coverage_comparison_high = facility_comp.get('highest_coverage_day', 'N/A') if facility_comp else 'N/A'
                coverage_comparison_low = facility_comp.get('lowest_coverage_day', 'N/A') if facility_comp else 'N/A'

                if detail_level in ['detailed', 'in-depth']:
                    facility_patterns += f"""
                    <div>
                        <h4>{facility_name} Task Patterns</h4>
                        <ul>
                            <li><strong>Task Mode:</strong> {primary_mode}</li>
                            <li><strong>Average Task Duration:</strong> {facility_avg_duration:.1f} minutes (vs last period: <span style="color: {get_comparison_color(facility_comp.get('avg_task_duration', 'N/A') if facility_comp else 'N/A')};">{format_comparison(facility_comp.get('avg_task_duration', 'N/A') if facility_comp else 'N/A')}</span>)</li>
                            <li><strong>Day with Highest Coverage:</strong> {highest_coverage_day} (vs last period: {coverage_comparison_high})</li>
                            <li><strong>Day with Lowest Coverage:</strong> {lowest_coverage_day} (vs last period: {coverage_comparison_low})</li>
                        </ul>
                    </div>"""

            if not facility_patterns:
                facility_patterns = f"""
                <div>
                    <h4>Overall Task Patterns</h4>
                    <ul>
                        <li><strong>Average Task Duration:</strong> {avg_duration:.1f} minutes (vs last period: <span style="color: {get_comparison_color(comparisons.get('avg_duration', 'N/A'))};">{format_comparison(comparisons.get('avg_duration', 'N/A'))}</span>)</li>
                        <li><strong>Weekend schedule performance:</strong> {weekend_completion:.1f}% completion</li>
                    </ul>
                </div>"""

            location_efficiency_section = f"""
            <h3>Task Performance by Location</h3>
            <div class="two-column">
                {facility_patterns}
            </div>"""

        return base_html + location_efficiency_section + "</section>"

    def _generate_facility_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
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

        # Generate facility performance tables with REAL efficiency metrics - Time Efficiency moved above Power Efficiency
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

        # Generate map-specific performance section conditionally
        map_sections = ""
        if detail_level != 'overview':
            if map_performance_by_building:
                map_sections = """
                <h3>Map-Specific Performance</h3>
                <p>Coverage: (actual area / planned area) × 100. Area Cleaned: sum of actual cleaned area converted to sq ft. Running Hours: sum of task durations converted from seconds. Power Efficiency: area cleaned / energy consumption. Time Efficiency: area cleaned / running hours. Water Efficiency: area cleaned / water consumption. Days with Tasks: unique dates when tasks occurred.</p>"""

                for building_name, maps in map_performance_by_building.items():
                    if maps and len(maps) > 0:
                        # Maps are already sorted by coverage % in descending order from calculator
                        map_sections += f"""
                        <div class="map-section">
                            <h4>{building_name} Maps</h4>
                            <div class="building-maps">"""

                        if detail_level == 'detailed':
                            # DETAILED: Simple table with coverage only
                            map_sections += """
                            <table>
                                <thead>
                                    <tr>
                                        <th>Map Name</th>
                                        <th>Coverage %</th>
                                        <th>vs Last Period</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                            for map_data in maps:
                                map_name = map_data.get('map_name', 'Unknown Map')
                                coverage = map_data.get('coverage_percentage', 0)
                                map_comp = map_comparisons.get(building_name, {}).get(map_name, {})
                                map_sections += f"""
                                <tr>
                                    <td>{map_name}</td>
                                    <td>{coverage:.1f}%</td>
                                    <td style="color: {get_comparison_color(map_comp.get('coverage_percentage', 'N/A'))};">
                                        {format_comparison(map_comp.get('coverage_percentage', 'N/A'))}
                                    </td>
                                </tr>"""
                            map_sections += "</tbody></table>"
                        elif detail_level == 'in-depth':
                            # IN_DEPTH: Full detailed
                            for map_data in maps:
                                map_name = map_data.get('map_name', 'Unknown Map')
                                coverage = map_data.get('coverage_percentage', 0)

                                # Get comparison data for this map
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
                                            <div style="font-size: 9px; color: #6c757d;">Time Efficiency (sq ft/hr)</div>
                                            <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('time_efficiency', 'N/A'))};">
                                                vs last: {format_comparison(map_comp.get('time_efficiency', 'N/A'))}
                                            </div>
                                        </div>
                                        <div class="map-metric">
                                            <div style="font-weight: bold;">{map_data.get('power_efficiency', 0):.0f}</div>
                                            <div style="font-size: 9px; color: #6c757d;">Power Efficiency (sq ft/kWh)</div>
                                            <div style="font-size: 8px; color: {get_comparison_color(map_comp.get('power_efficiency', 'N/A'))};">
                                                vs last: {format_comparison(map_comp.get('power_efficiency', 'N/A'))}
                                            </div>
                                        </div>
                                        <div class="map-metric">
                                            <div style="font-weight: bold;">{map_data.get('water_efficiency', 0):.1f}</div>
                                            <div style="font-size: 9px; color: #6c757d;">Water Efficiency (sq ft/fl oz)</div>
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

    def _generate_resource_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate resource utilization section (PDF version) with health scores and utilization"""
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

        # Calculate resource usage by facility using facility-specific data
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

        # Conditional chart
        chart_html = ""
        if detail_level != 'overview':
            chart_html = self._get_chart_image_html('resource_chart', 'Weekly Resource Utilization', max_height=200)

        # Add robot health scores and utilization for in-depth reports
        robot_health_utilization = ""
        if detail_level == 'in-depth':
            robot_health_utilization = self._generate_robot_health_utilization_pdf(content)

        return f"""
        <section id="resource-utilization" class="section">
            <h2>⚡ Resource Utilization & Efficiency</h2>
            <h3>Resource Performance</h3>
            <p>Resource utilization: {resource_data.get('total_energy_consumption_kwh', 0):.2f} kWh total energy consumption, {resource_data.get('total_water_consumption_floz', 0):.0f} fl oz total water usage, {resource_data.get('area_per_kwh', 0):.0f} sq ft per kWh energy efficiency, and {resource_data.get('area_per_gallon', 0):.0f} sq ft per gallon water efficiency.</p>

            {chart_html}

            {facility_breakdown}

            {robot_health_utilization}
        </section>"""

    def _generate_robot_health_utilization_pdf(self, content: Dict[str, Any]) -> str:
        """Generate robot health and utilization section for PDF (static version with metric definitions)"""
        robot_health_scores = content.get('robot_health_scores', {})
        individual_robots = content.get('individual_robots', [])

        # Only show if we have actual health score data
        if not robot_health_scores or not isinstance(robot_health_scores, dict) or len(robot_health_scores) == 0:
            return ""

        # Filter out empty health scores
        valid_health_scores = {k: v for k, v in robot_health_scores.items() if v and len(v) > 0}
        if not valid_health_scores:
            return ""

        html = """
        <h3>🤖 Robot Health & Utilization Analysis</h3>
        <p>Comprehensive health and utilization metrics for each robot, including uptime/downtime analysis and component-level health scores.</p>

        <!-- Metric Definitions Box -->
        <div style="background: #e3f2fd; padding: 12px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #2196f3; page-break-inside: avoid;">
            <h4 style="color: #1976d2; margin-top: 0; font-size: 12px;">📘 Metric Definitions</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 10px;">
                <div>
                    <p style="margin: 3px 0;"><strong>Utilization:</strong> Working hours / Uptime hours × 100. Indicates how efficiently the robot's available time is used for productive tasks.</p>
                    <p style="margin: 3px 0;"><strong>Availability:</strong> Percentage of time robot is online and available (weight: 40%)</p>
                    <p style="margin: 3px 0;"><strong>Task Success:</strong> Percentage of successfully completed tasks (weight: 20%)</p>
                </div>
                <div>
                    <p style="margin: 3px 0;"><strong>Efficiency:</strong> Task efficiency score based on performance metrics (weight: 20%)</p>
                    <p style="margin: 3px 0;"><strong>Mode Performance:</strong> Performance in different cleaning modes like sweeping/scrubbing (weight: 10%)</p>
                    <p style="margin: 3px 0;"><strong>Battery Health:</strong> Battery State of Health (SOH) percentage (weight: 10%)</p>
                </div>
            </div>
        </div>
        """

        # Process each robot (up to 5 for PDF)
        for robot in individual_robots[:5]:
            robot_id = robot.get('robot_id', 'Unknown')
            robot_name = robot.get('robot_name', robot_id)
            health_data = valid_health_scores.get(robot_id, {})

            if not health_data:
                continue

            component_scores = health_data.get('component_scores', {})
            overall_score = health_data.get('overall_health_score', 0)
            overall_rating = health_data.get('overall_health_rating', 'N/A')

            # Determine color
            if overall_rating == 'Excellent':
                rating_color = '#28a745'
            elif overall_rating == 'Good':
                rating_color = '#17a2b8'
            elif overall_rating == 'Fair':
                rating_color = '#ffc107'
            else:
                rating_color = '#dc3545'

            # Get utilization metrics
            uptime_hours = robot.get('uptime_hours', 0)
            uptime_hours_perc = robot.get('uptime_ratio', 0)
            downtime_hours = robot.get('downtime_hours', 0)
            downtime_hours_perc = 100 - uptime_hours_perc

            working_hours = robot.get('working_hours', 0)
            working_hours_perc = robot.get('working_ratio', 0)
            idle_hours = robot.get('idle_hours', 0)
            idle_hours_perc = robot.get('idle_ratio', 0)
            charging_hours = robot.get('charging_hours', 0)
            charging_hours_perc = robot.get('charging_ratio', 0)

            utilization_score = robot.get('utilization_score', 0)

            # Check if all 5 components are present
            expected_components = ['Availability', 'Task Success', 'Efficiency', 'Mode Performance', 'Battery Health']
            has_all_components = all(comp in component_scores and component_scores[comp] is not None for comp in expected_components)

            html += f"""
            <div style="background: #f8f9fa; border-radius: 5px; padding: 15px; margin: 15px 0; border-left: 4px solid {rating_color}; page-break-inside: avoid;">
                <h4 style="margin-top: 0; color: #2c3e50; font-size: 13px;">
                    Robot {robot_id} ({robot_name}) -
                    <span style="color: {rating_color};">Health: {overall_score:.1f} ({overall_rating})</span> |
                    <span style="color: #3498db;">Utilization: {utilization_score:.1f}%</span>
                </h4>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 10px;">
                    <!-- Left: Health Score Breakdown -->
                    <div>
                        <h5 style="color: #2c3e50; margin-bottom: 8px; font-size: 11px;">Health Score Breakdown</h5>
            """

            if has_all_components:
                # Show pentagon chart - generate it as base64 image
                safe_robot_id = robot_id.replace('-', '_')

                # Create radar chart data for this robot
                radar_labels = list(component_scores.keys())
                radar_values = list(component_scores.values())

                # Generate the radar chart image inline
                radar_chart_html = self._generate_health_radar_chart_inline(
                    robot_id, radar_labels, radar_values
                )

                html += f"""
                        <div style="text-align: center; margin: 10px 0;">
                            {radar_chart_html}
                        </div>
                """
            else:
                # Show text-based component breakdown
                html += """
                        <div style="font-size: 10px;">
                """

                for component_name, component_score in component_scores.items():
                    if component_score is None:
                        continue

                    # Determine color
                    if component_score >= 90:
                        bar_color = '#28a745'
                    elif component_score >= 80:
                        bar_color = '#17a2b8'
                    elif component_score >= 60:
                        bar_color = '#ffc107'
                    else:
                        bar_color = '#dc3545'

                    html += f"""
                            <div style="margin: 8px 0;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                                    <span style="font-weight: 600;">{component_name}</span>
                                    <span style="font-weight: bold;">{component_score:.1f}</span>
                                </div>
                                <div style="width: 100%; height: 10px; background: #e9ecef; border-radius: 5px; overflow: hidden;">
                                    <div style="width: {component_score}%; height: 100%; background: {bar_color};"></div>
                                </div>
                            </div>
                    """

                html += """
                        </div>
                """

            html += f"""
                    </div>

                    <!-- Right: Time Distribution -->
                    <div>
                        <h5 style="color: #2c3e50; margin-bottom: 8px; font-size: 11px;">Time Distribution</h5>

                        <!-- Uptime vs Downtime Chart -->
                        <div style="margin-bottom: 10px;">
                            <h6 style="margin: 5px 0; font-size: 10px; color: #495057;">Uptime vs Downtime</h6>
                            {self._generate_bar_chart_inline(
                                ['Uptime', 'Downtime'],
                                [uptime_hours, downtime_hours],
                                ['#28a745', '#dc3545'],
                                width=4, height=1.5
                            )}
                        </div>

                        <!-- Working vs Idle vs Charging Chart -->
                        <div style="margin-bottom: 10px;">
                            <h6 style="margin: 5px 0; font-size: 10px; color: #495057;">Working vs Idle vs Charging</h6>
                            {self._generate_bar_chart_inline(
                                ['Working', 'Idle', 'Charging'],
                                [working_hours, idle_hours, charging_hours],
                                ['#28a745', '#ffc107', '#17a2b8'],
                                width=4, height=1.8
                            )}
                        </div>

                        <!-- Time Metrics Summary -->
                        <div style="background: #e9ecef; padding: 8px; border-radius: 3px; font-size: 9px;">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
                                <div><strong>Uptime:</strong> {uptime_hours:.1f}h ({uptime_hours_perc:.1f}%)</div>
                                <div><strong>Downtime:</strong> {downtime_hours:.1f}h ({downtime_hours_perc:.1f}%)</div>
                                <div><strong>Working:</strong> {working_hours:.1f}h ({working_hours_perc:.1f}%)</div>
                                <div><strong>Idle:</strong> {idle_hours:.1f}h ({idle_hours_perc:.1f}%)</div>
                                <div><strong>Charging:</strong> {charging_hours:.1f}h ({charging_hours_perc:.1f}%)</div>
                                <div><strong>Utilization:</strong> {utilization_score:.1f}%</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """

        return html

    def _generate_health_radar_chart_inline(self, robot_id: str, labels: list, values: list) -> str:
        """Generate a health radar chart as base64 inline image for PDF"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from io import BytesIO
            import base64

            # Create figure
            fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(projection='polar'))

            # Number of variables
            num_vars = len(labels)

            # Compute angle for each axis
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

            # Close the plot
            values_plot = values + [values[0]]
            angles_plot = angles + [angles[0]]

            # Plot
            ax.plot(angles_plot, values_plot, 'o-', linewidth=2, color='#3498db')
            ax.fill(angles_plot, values_plot, alpha=0.25, color='#3498db')

            # Fix axis to go in the right order and start at 12 o'clock
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)

            # Set labels
            ax.set_xticks(angles)
            ax.set_xticklabels(labels, size=8)

            # Set y-axis limits
            ax.set_ylim(0, 100)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.set_yticklabels(['20', '40', '60', '80', '100'], size=7)

            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)

            # Title
            ax.set_title(f'Health Score: {np.mean(values):.1f}', size=10, pad=20)

            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return f'<img src="data:image/png;base64,{image_base64}" alt="{robot_id} Health Radar" style="max-width: 90%; height: auto; max-height: 250px;">'

        except Exception as e:
            logger.error(f"Error generating health radar chart for {robot_id}: {e}")
            # Fallback to text if chart generation fails
            return f'<p style="font-size: 10px; color: #6c757d; text-align: center;">Health radar chart unavailable</p>'

    def _generate_bar_chart_inline(self, labels: list, values: list, colors: list, width: float = 4, height: float = 2) -> str:
        """Generate a horizontal bar chart as base64 inline image for PDF"""
        try:
            import matplotlib.pyplot as plt
            from io import BytesIO
            import base64

            # Create figure
            fig, ax = plt.subplots(figsize=(width, height))

            # Create horizontal bar chart
            y_pos = range(len(labels))
            ax.barh(y_pos, values, color=colors, alpha=0.8)

            # Customize
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, size=8)
            ax.set_xlabel('Hours', size=8)
            ax.set_xlim(0, max(values) * 1.1 if max(values) > 0 else 1)

            # Add value labels
            for i, (label, value) in enumerate(zip(labels, values)):
                ax.text(value + max(values) * 0.02, i, f'{value:.1f}h',
                       va='center', size=7, fontweight='bold')

            # Remove top and right spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            # Grid
            ax.grid(axis='x', linestyle='--', alpha=0.3)

            # Tight layout
            plt.tight_layout()

            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return f'<img src="data:image/png;base64,{image_base64}" alt="Bar Chart" style="max-width: 100%; height: auto;">'

        except Exception as e:
            logger.error(f"Error generating bar chart: {e}")
            return '<p style="font-size: 9px; color: #6c757d;">Chart unavailable</p>'

    def _generate_financial_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate financial performance section (PDF version)"""
        cost_data = content.get('cost_analysis', {})
        comparisons = content.get('period_comparisons', {})

        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value, metric_type):
            if value == 'N/A' or not value:
                return '#6c757d'
            if any([i in str(metric_type).lower() for i in ['cost', 'investment']]) and 'efficiency' not in str(metric_type).lower():
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

        # Base content
        base_html = f"""
        <section id="financial-performance" class="section">
            <h2>💰 Financial Performance</h2>

            <p>Financial analysis based on actual resource usage: {safe_format(cost_data.get('cost_per_sqft', 0), '$', '/sq ft')} average cost per square foot, {safe_format(cost_data.get('total_cost', 0))} total operational cost, {cost_data.get('hours_saved', 0):.1f} hours saved compared to manual cleaning, and {safe_format(cost_data.get('savings', 0))} in realized savings.</p>

            <table>
                <thead>
                    <tr>
                        <th>Operational Metric</th>
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
                        <td>Operational efficiency (water + energy cost per area)</td>
                    </tr>
                    <tr>
                        <td>Total Operational Cost</td>
                        <td>{safe_format(cost_data.get('total_cost', 0))}</td>
                        <td style="color: {get_comparison_color(comparisons.get('total_cost', 'N/A'), 'total_cost')};">{format_comparison(comparisons.get('total_cost', 'N/A'))}</td>
                        <td>Robot operational cost this period</td>
                    </tr>
                    <tr>
                        <td>ROI</td>
                        <td>{cost_data.get('roi_improvement', 'N/A')}</td>
                        <td style="color: {get_comparison_color(comparisons.get('roi_improvement', 'N/A'), 'roi')};">{format_comparison(comparisons.get('roi_improvement', 'N/A'))}</td>
                        <td>Return on Investment (cumulative savings ÷ total investment × 100)</td>
                    </tr>
                    <tr>
                        <td>Total Investment</td>
                        <td>{safe_format(cost_data.get('total_investment', 0))}</td>
                        <td style="color: {get_comparison_color(comparisons.get('total_investment', 'N/A'), 'total_investment')};">{format_comparison(comparisons.get('total_investment', 'N/A'))}</td>
                        <td>Cumulative lease investment (${cost_data.get('monthly_lease_price', 1500)}/month per robot)</td>
                    </tr>
                    <tr>
                        <td>Cost Efficiency Improvement</td>
                        <td>{cost_data.get('cost_efficiency_improvement', 0):.1f}%</td>
                        <td style="color: {get_comparison_color(comparisons.get('cost_efficiency_improvement', 'N/A'), 'cost_efficiency')};">{format_comparison(comparisons.get('cost_efficiency_improvement', 'N/A'))}</td>
                        <td>Efficiency improvement vs manual cleaning</td>
                    </tr>
                    <tr>
                        <td>Water Cost</td>
                        <td>{safe_format(cost_data.get('water_cost', 0))}</td>
                        <td style="color: {get_comparison_color(comparisons.get('water_cost', 'N/A'), 'water_cost')};">{format_comparison(comparisons.get('water_cost', 'N/A'))}</td>
                        <td>Water resource cost component</td>
                    </tr>
                    <tr>
                        <td>Energy Cost</td>
                        <td>{safe_format(cost_data.get('energy_cost', 0))}</td>
                        <td style="color: {get_comparison_color(comparisons.get('energy_cost', 'N/A'), 'energy_cost')};">{format_comparison(comparisons.get('energy_cost', 'N/A'))}</td>
                        <td>Energy resource cost component</td>
                    </tr>
                </tbody>
            </table>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #17a2b8;">
                <h4 style="color: #17a2b8; margin-top: 0;">💡 ROI Calculation Method</h4>
                <p><strong>ROI Formula:</strong> Cumulative Savings ÷ Total Investment × 100</p>
                <p><strong>Investment:</strong> $1,500/month per robot × months elapsed (rounded up for billing)</p>
                <p><strong>Cumulative Savings:</strong> All-time savings from first robot task to end of reporting period</p>
            </div>
            """

        # Conditional chart
        chart_html = ""
        if detail_level != 'overview':
            chart_html = self._get_chart_image_html('financial_chart', 'Weekly Financial Performance', max_height=200)

        # Highlight box always
        highlight_html = f"""
            <div class="highlight-box">
                <h3>💡 Financial Impact Summary</h3>
                <div class="metrics-grid">
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('human_cost', 0))}</strong></div>
                        <div>Manual Cleaning Cost</div>
                        <div style="color: {get_comparison_color(comparisons.get('human_cost', 'N/A'), 'human_cost')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('human_cost', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('savings', 0))}</strong></div>
                        <div>Savings Realized</div>
                        <div style="color: {get_comparison_color(comparisons.get('savings', 'N/A'), 'savings')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{cost_data.get('hours_saved', 0):.1f} hrs</strong></div>
                        <div>Hours Saved vs Manual</div>
                        <div style="color: {get_comparison_color(comparisons.get('hours_saved', 'N/A'), 'hours_saved')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('hours_saved', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('annual_projected_savings', 0))}</strong></div>
                        <div>Annual Projected Savings</div>
                        <div style="color: {get_comparison_color(comparisons.get('annual_projected_savings', 'N/A'), 'annual_projected_savings')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('annual_projected_savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('cumulative_savings', 0))}</strong></div>
                        <div>Cumulative Savings</div>
                        <div style="color: {get_comparison_color(comparisons.get('cumulative_savings', 'N/A'), 'cumulative_savings')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('cumulative_savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{cost_data.get('payback_period', 'N/A')}</strong></div>
                        <div>Payback Period</div>
                        <div style="color: {get_comparison_color(comparisons.get('payback_months', 'N/A'), 'payback_months')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('payback_months', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 16px; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('monthly_savings_rate', 0), '$', '/month')}</strong></div>
                        <div>Monthly Savings Rate</div>
                        <div style="color: {get_comparison_color(comparisons.get('monthly_savings_rate', 'N/A'), 'monthly_savings_rate')}; font-size: 9px;">
                            vs last: {format_comparison(comparisons.get('monthly_savings_rate', 'N/A'))}
                        </div>
                    </div>
                </div>
                <p style="margin-top: 15px; font-size: 10px; opacity: 0.8;">
                    {cost_data.get('note', 'Financial calculations based on actual resource usage, lease model, and human cleaning speed benchmarks.')}
                </p>
            </div>

        </section>"""

        return base_html + chart_html + highlight_html

    def _generate_charging_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
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

        # Base metrics grid
        base_html = f"""
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
        """

        # Conditional chart
        chart_html = ""
        if detail_level != 'overview':
            chart_html = self._get_chart_image_html('charging_chart', 'Weekly Charging Performance', max_height=200)

        # Charging by location
        charging_by_location = ""
        facility_charging_metrics = content.get('facility_charging_metrics', {})

        if facility_charging_metrics:
            charging_by_location = """
            <h3>Charging Patterns by Location</h3>
            <table>
                <thead>
                    <tr>
                        <th>Location</th>
                        <th>Total Sessions</th>
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

        return base_html + chart_html + charging_by_location + "</section>"

    def _generate_conclusion(self, content: Dict[str, Any]) -> str:
        """Generate conclusion section (PDF version)"""
        fleet_data = content.get('fleet_performance', {})
        task_data = content.get('task_performance', {})
        resource_data = content.get('resource_utilization', {})
        charging_data = content.get('charging_performance', {})
        cost_data = content.get('cost_analysis', {})

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
                and {cost_data.get('roi_improvement', 'N/A')} return on investment.</p>
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