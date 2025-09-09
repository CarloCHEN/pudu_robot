from typing import Dict, Any
from datetime import datetime
import json
import logging
from ..core.report_config import ReportConfig, ReportDetailLevel
from ..calculators.chart_data_formatter import ChartDataFormatter

logger = logging.getLogger(__name__)

class RobotPerformanceTemplate:
    """Enhanced HTML template generator using actual database metrics"""

    def __init__(self):
        self.chart_formatter = ChartDataFormatter()

    def generate_comprehensive_report(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate comprehensive HTML report using real data"""
        try:
            chart_js_data = self._generate_chart_data(content)

            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robot Performance Report - {content.get('period', 'Latest Period')}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}

        .subtitle {{
            text-align: center;
            color: #7f8c8d;
            font-size: 1.2em;
            margin-bottom: 30px;
        }}

        h2 {{
            color: #34495e;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
        }}

        h3 {{
            color: #2980b9;
            margin-top: 30px;
        }}

        .highlight-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .metric-card {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}

        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}

        .metric-label {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 5px;
        }}

        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .chart-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }}

        .chart-small {{
            position: relative;
            height: 300px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}

        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .progress-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 10px 0;
        }}

        .progress-bar {{
            flex: 1;
            min-width: 100px;
            height: 15px;
            background: #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }}

        .progress-text {{
            font-weight: bold;
            color: #2c3e50;
            white-space: nowrap;
            min-width: 60px;
            text-align: right;
        }}

        .progress-bar {{
            width: 60%;
            height: 15px;
            background: #e9ecef;
            border-radius: 8px;
            overflow: hidden;
            margin: 3px 0;
            display: inline-block;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}

        .progress-text {{
            display: inline-block;
            margin-left: 10px;
            font-weight: bold;
            color: #2c3e50;
        }}

        .status-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}

        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}

        .status-excellent {{ background: #28a745; }}
        .status-good {{ background: #17a2b8; }}
        .status-warning {{ background: #ffc107; }}
        .status-error {{ background: #dc3545; }}

        .two-column {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 20px 0;
        }}

        .tooltip {{
            position: relative;
            display: inline-block;
            cursor: help;
            color: #3498db;
            text-decoration: underline dotted;
        }}

        .tooltip .tooltiptext {{
            visibility: hidden;
            width: 300px;
            background-color: #555;
            color: #fff;
            text-align: left;
            border-radius: 6px;
            padding: 10px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -150px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 0.9em;
        }}

        .tooltip:hover .tooltiptext {{
            visibility: visible;
            opacity: 1;
        }}

        .map-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}

        .building-maps {{
            margin: 15px 0;
        }}

        .map-metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 10px 0;
        }}

        .map-metric {{
            background: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            border: 1px solid #dee2e6;
        }}

        @media (max-width: 768px) {{
            .chart-row, .two-column {{
                grid-template-columns: 1fr;
            }}

            .container {{
                padding: 15px;
            }}

            .progress-bar {{
                width: 40%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Robot Performance Report</h1>
        <p class="subtitle">{content.get('period', 'Latest Period')}</p>

        {self._generate_executive_summary(content)}
        {self._generate_fleet_section(content)}
        {self._generate_facility_section(content)}
        {self._generate_task_section(content)}
        {self._generate_charging_section(content)}
        {self._generate_resource_section(content)}
        {self._generate_financial_section(content)}
        {self._generate_event_section(content)}
        {self._generate_conclusion(content)}
        {self._generate_footer(content)}
    </div>
    {self._generate_javascript(chart_js_data)}
</body>
</html>"""

            return html_content

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"""<!DOCTYPE html>
<html><head><title>Error</title></head>
<body><h1>Report Generation Error</h1><p>{str(e)}</p></body></html>"""

    def _generate_executive_summary(self, content: Dict[str, Any]) -> str:
        """Generate executive summary section with real data and tooltips"""
        exec_data = content.get('executive_summary', {})
        period_desc = content.get('period', 'the reporting period')

        # Handle N/A values gracefully
        def format_value(value, suffix="", format_type="number"):
            if value == 'N/A' or value is None:
                return 'N/A'
            if format_type == "number":
                return f"{value:,.0f}{suffix}" if isinstance(value, (int, float)) else f"{value}{suffix}"
            elif format_type == "percent":
                return f"{value}%" if isinstance(value, (int, float)) else f"{value}"
            return str(value)

        # Get robots online rate instead of fleet availability
        robots_online_rate = exec_data.get('robots_online_rate', exec_data.get('fleet_availability_rate', 0))

        return f"""
        <section id="executive-summary">
            <h2>📊 Executive Summary</h2>
            <div class="highlight-box">
                <p>Robot deployment during {period_desc} achieved {format_value(robots_online_rate, '%', 'percent')} robots online status
                with {format_value(exec_data.get('task_completion_rate', 0), '%', 'percent')} task completion rate,
                covering {format_value(exec_data.get('total_area_cleaned', 0), ' square feet')}.</p>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(robots_online_rate, '%', 'percent')}
                        <span class="tooltiptext">Percentage of robots with online status at the time of report generation. Calculated from robot status data in the management system.</span>
                    </div>
                    <div class="metric-label">Robots Online</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(exec_data.get('monthly_cost_savings', 'N/A'), '', 'number')}
                        <span class="tooltiptext">Monthly cost savings compared to traditional cleaning methods. Currently not available - requires cost configuration and baseline data.</span>
                    </div>
                    <div class="metric-label">Monthly Cost Savings</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(exec_data.get('energy_saved_kwh', 0), ' kWh')}
                        <span class="tooltiptext">Total energy consumption calculated from task data consumption field during the reporting period.</span>
                    </div>
                    <div class="metric-label">Energy Used</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(exec_data.get('coverage_efficiency', 0), '%', 'percent')}
                        <span class="tooltiptext">Coverage efficiency calculated as (actual area cleaned / planned area) × 100 from task performance data.</span>
                    </div>
                    <div class="metric-label">Coverage</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(exec_data.get('task_completion_rate', 0), '%', 'percent')}
                        <span class="tooltiptext">Percentage of tasks with 'completed' or 'ended' status from total tasks during the reporting period.</span>
                    </div>
                    <div class="metric-label">Task Completion</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(exec_data.get('total_area_cleaned', 0))}
                        <span class="tooltiptext">Total area cleaned in square feet, converted from actual_area field in task data (originally in square meters).</span>
                    </div>
                    <div class="metric-label">Sq Ft Cleaned</div>
                </div>
            </div>

            <h3>🎯 Key Achievements</h3>
            <ul style="font-size: 1.1em; color: #2c3e50;">
                <li>{format_value(exec_data.get('total_tasks', 0))} total tasks processed during reporting period</li>
                <li>{format_value(exec_data.get('total_area_cleaned', 0))} square feet cleaned across all locations</li>
                <li>{format_value(exec_data.get('total_robots', 0))} robots actively deployed and monitored</li>
                <li>{format_value(exec_data.get('total_charging_sessions', 0))} charging sessions during the period</li>
            </ul>
        </section>"""

    def _generate_fleet_section(self, content: Dict[str, Any]) -> str:
        """Generate fleet management section with tooltips and online/offline status"""
        fleet_data = content.get('fleet_management', {})
        individual_robots = content.get('individual_robots', [])
        comparisons = content.get('period_comparisons', {})

        # Get robots online rate instead of fleet availability
        robots_online_rate = fleet_data.get('robots_online_rate', 0)
        total_running_hours = fleet_data.get('total_running_hours', fleet_data.get('total_operational_hours', 0))

        # Format comparison values with color coding
        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value):
            if value == 'N/A' or not value:
                return '#6c757d'
            elif value.startswith('+'):
                return '#28a745'  # Green for positive
            elif value.startswith('-'):
                return '#dc3545'  # Red for negative
            else:
                return '#6c757d'  # Gray for neutral

        # Generate robot performance table
        robot_rows = ""
        if individual_robots:
            for robot in individual_robots[:10]:  # Show top 10 robots
                status_text = robot.get('status', 'Unknown')
                status_class = robot.get('status_class', 'status-error')
                running_hours = robot.get('running_hours', robot.get('operational_hours', 0))

                robot_rows += f"""
                <tr>
                    <td>{robot.get('robot_id', 'Unknown')}</td>
                    <td>{robot.get('location', 'Unknown Location')}</td>
                    <td>{robot.get('tasks_completed', 0)}</td>
                    <td>{running_hours} hrs</td>
                    <td><span class="status-indicator"><span class="status-dot {status_class}"></span>{status_text}</span></td>
                </tr>"""

        if not robot_rows:
            robot_rows = '<tr><td colspan="5">No robot data available</td></tr>'

        # Summarize key performance metrics instead of generic statements
        performance_summary = f"Fleet includes {fleet_data.get('total_robots', 0)} robots with {robots_online_rate}% currently online, completing {fleet_data.get('completed_tasks', 0) if 'completed_tasks' in fleet_data else 'N/A'} tasks and accumulating {total_running_hours:,.0f} total running hours."

        return f"""
        <section id="fleet-management">
            <h2>🤖 Fleet Management Performance</h2>

            <h3>System Performance Overview</h3>
            <p>{performance_summary}</p>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{fleet_data.get('total_robots', 0)}</div>
                    <div class="metric-label">Total Robots</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{robots_online_rate}%
                        <span class="tooltiptext">Percentage of robots with online/operational status at report generation time. Based on current robot status from management system.</span>
                    </div>
                    <div class="metric-label">Robots Online</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{total_running_hours:,.0f}
                        <span class="tooltiptext">Total running hours calculated from task duration data (converted from seconds to hours) across all robots during the reporting period.</span>
                    </div>
                    <div class="metric-label">Total Running Hours</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('running_hours', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('running_hours', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{fleet_data.get('average_robot_utilization', 0):.1f}
                        <span class="tooltiptext">Average running hours per robot calculated as total running hours divided by number of robots.</span>
                    </div>
                    <div class="metric-label">Avg Utilization (hrs/robot)</div>
                </div>
            </div>

            <h3>Individual Robot Performance</h3>
            <table>
                <thead>
                    <tr>
                        <th>Robot ID</th>
                        <th>Location</th>
                        <th>Tasks Completed</th>
                        <th>Running Hours</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {robot_rows}
                </tbody>
            </table>
        </section>"""

    def _generate_facility_section(self, content: Dict[str, Any]) -> str:
        """Generate facility performance section with efficiency metrics and map-specific performance"""
        facilities = content.get('facility_performance', {}).get('facilities', {})
        facility_efficiency = content.get('facility_efficiency_metrics', {})
        map_performance_by_building = content.get('map_performance_by_building', {})
        comparisons = content.get('period_comparisons', {})
        facility_comparisons = comparisons.get('facility_comparisons', {})

        # Format comparison values with color coding
        def format_comparison(value):
            return value if value != 'N/A' else 'N/A'

        def get_comparison_color(value):
            if value == 'N/A' or not value:
                return '#6c757d'
            elif value.startswith('+'):
                return '#28a745'  # Green for positive
            elif value.startswith('-'):
                return '#dc3545'  # Red for negative
            else:
                return '#6c757d'  # Gray for neutral

        # Generate facility performance tables with new metrics
        facility_sections = ""
        for facility_name, metrics in facilities.items():
            facility_comp = facility_comparisons.get(facility_name, {})
            facility_eff = facility_efficiency.get(facility_name, {})

            # Calculate coverage (average if multiple tasks)
            total_tasks = metrics.get('total_tasks', 0)
            coverage_eff = metrics.get('coverage_efficiency', 0)
            # For display, show as average coverage since it's calculated from multiple tasks
            avg_coverage = coverage_eff  # This is already an average from the calculation

            facility_sections += f"""
            <div>
                <h3>{facility_name}</h3>
                <p>Performance metrics for {facility_name}: {total_tasks} total tasks, {metrics.get('area_cleaned', 0):,.0f} sq ft total area cleaned, {avg_coverage:.1f}% average coverage, {facility_eff.get('water_efficiency', 0):.1f} sq ft/fl oz water efficiency, and {facility_eff.get('time_efficiency', 0):.1f} sq ft/hour time efficiency.</p>

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
                            <td>{avg_coverage:.1f}%</td>
                            <td style="color: {get_comparison_color(facility_comp.get('coverage_efficiency', 'N/A'))};">{format_comparison(facility_comp.get('coverage_efficiency', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Task Completion Rate</td>
                            <td>{metrics.get('completion_rate', 0):.1f}%</td>
                            <td style="color: {get_comparison_color(facility_comp.get('completion_rate', 'N/A'))};">{format_comparison(facility_comp.get('completion_rate', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Running Hours</td>
                            <td>{metrics.get('running_hours', metrics.get('operating_hours', 0)):.1f} hours</td>
                            <td style="color: {get_comparison_color(facility_comp.get('running_hours', 'N/A'))};">{format_comparison(facility_comp.get('running_hours', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Power Efficiency</td>
                            <td>{metrics.get('power_efficiency', 0):,.0f} sq ft/kWh</td>
                            <td style="color: {get_comparison_color(facility_comp.get('power_efficiency', 'N/A'))};">{format_comparison(facility_comp.get('power_efficiency', 'N/A'))}</td>
                        </tr>
                        <tr>
                            <td>Water Efficiency</td>
                            <td>{facility_eff.get('water_efficiency', 0):.1f} sq ft/fl oz</td>
                            <td>N/A</td>
                        </tr>
                        <tr>
                            <td>Time Efficiency</td>
                            <td>{facility_eff.get('time_efficiency', 0):.1f} sq ft/hour</td>
                            <td>N/A</td>
                        </tr>
                    </tbody>
                </table>
            </div>"""

        if not facility_sections:
            facility_sections = '<div><p>No facility-specific data available</p></div>'

        # Generate map-specific performance section
        map_sections = ""
        if map_performance_by_building:
            map_sections = """
            <h3>Map-Specific Performance</h3>
            <div class="tooltip" style="margin-bottom: 15px;">
                <span style="color: #3498db; text-decoration: underline dotted;">How these figures are calculated</span>
                <span class="tooltiptext">Coverage: (actual area / planned area) × 100. Area Cleaned: sum of actual_area converted to sq ft. Task Completion: completed tasks / total tasks × 100. Running Hours: sum of task durations converted from seconds. Power Efficiency: area cleaned / energy consumption. Time Efficiency: area cleaned / running hours.</span>
            </div>"""

            for building_name, maps in map_performance_by_building.items():
                if maps:  # Only show buildings that have maps
                    map_sections += f"""
                    <div class="map-section">
                        <h4>{building_name} Maps</h4>
                        <div class="building-maps">"""

                    for map_data in maps:
                        map_name = map_data.get('map_name', 'Unknown Map')
                        coverage = map_data.get('coverage_percentage', 0)

                        map_sections += f"""
                        <div style="margin: 15px 0; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px;">
                            <h5>{map_name}</h5>
                            <div class="progress-container">
                                <span>Coverage:</span>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {min(coverage, 100)}%"></div>
                                </div>
                                <span class="progress-text">{coverage:.1f}%</span>
                            </div>
                            <div class="map-metrics">
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('area_cleaned', 0):,.0f}</div>
                                    <div style="font-size: 0.8em; color: #6c757d;">Area Cleaned (sq ft)</div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('completion_rate', 0):.1f}%</div>
                                    <div style="font-size: 0.8em; color: #6c757d;">Task Completion</div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('running_hours', 0):.1f}</div>
                                    <div style="font-size: 0.8em; color: #6c757d;">Running Hours</div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('power_efficiency', 0):.0f}</div>
                                    <div style="font-size: 0.8em; color: #6c757d;">Power Efficiency</div>
                                </div>
                                <div class="map-metric">
                                    <div style="font-weight: bold;">{map_data.get('time_efficiency', 0):.0f}</div>
                                    <div style="font-size: 0.8em; color: #6c757d;">Time Efficiency</div>
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
        <section id="facility-performance">
            <h2>🏢 Facility-Specific Performance</h2>

            <div class="two-column">
                {facility_sections}
            </div>

            {map_sections}
        </section>"""

    def _generate_task_section(self, content: Dict[str, Any]) -> str:
        """Generate task performance section with weekday completion rates"""
        task_data = content.get('task_performance', {})
        facilities = content.get('facility_performance', {}).get('facilities', {})
        comparisons = content.get('period_comparisons', {})
        facility_comparisons = comparisons.get('facility_comparisons', {})
        weekday_data = content.get('weekday_completion', {})

        # Get real calculated values
        weekend_completion = task_data.get('weekend_schedule_completion', 0)
        avg_duration = task_data.get('avg_task_duration_minutes', 0)

        # Get weekday completion data
        highest_day = weekday_data.get('highest_day', 'Monday')
        highest_rate = weekday_data.get('highest_rate', 0)
        lowest_day = weekday_data.get('lowest_day', 'Sunday')
        lowest_rate = weekday_data.get('lowest_rate', 0)

        # Format comparison values
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

        # Calculate new metrics for facility patterns
        facility_patterns = ""
        facility_task_metrics = content.get('facility_task_metrics', {})
        for facility_name, metrics in facilities.items():
            facility_comp = facility_comparisons.get(facility_name, {})
            facility_task_data = facility_task_metrics.get(facility_name, {})

            # Use facility-specific duration if available, otherwise use global average
            facility_avg_duration = facility_task_data.get('avg_duration_minutes', avg_duration)
            primary_mode = facility_task_data.get('primary_mode', 'Mixed tasks')

            # New metrics for this facility
            completion_efficiency = metrics.get('completion_rate', 0)
            total_area = metrics.get('area_cleaned', 0)

            facility_patterns += f"""
            <div>
                <h4>{facility_name} Task Patterns</h4>
                <ul>
                    <li><strong>Task completion efficiency:</strong> {completion_efficiency:.1f}% (vs last period: <span style="color: {get_comparison_color(facility_comp.get('completion_rate', 'N/A'))};">{format_comparison(facility_comp.get('completion_rate', 'N/A'))}</span>)</li>
                    <li><strong>Area productivity:</strong> {total_area:,.0f} sq ft coverage (vs last period: <span style="color: {get_comparison_color(facility_comp.get('area_cleaned', 'N/A'))};">{format_comparison(facility_comp.get('area_cleaned', 'N/A'))}</span>)</li>
                    <li><strong>Task pattern:</strong> {primary_mode}</li>
                    <li><strong>Operation rhythm:</strong> {facility_avg_duration:.1f} minutes average task duration</li>
                    <li><strong>Scheduling effectiveness:</strong> {facility_task_data.get('completed_tasks', metrics.get('completed_tasks', 0))} of {facility_task_data.get('total_tasks', metrics.get('total_tasks', 0))} tasks completed</li>
                </ul>
            </div>"""

        if not facility_patterns:
            facility_patterns = f"""
            <div>
                <h4>Overall Task Patterns</h4>
                <ul>
                    <li><strong>Task volume:</strong> {task_data.get('total_tasks', 0)} total tasks (vs last period: <span style="color: {get_comparison_color(comparisons.get('total_tasks', 'N/A'))};">{format_comparison(comparisons.get('total_tasks', 'N/A'))}</span>)</li>
                    <li><strong>Completion effectiveness:</strong> {task_data.get('completion_rate', 0):.1f}% rate (vs last period: <span style="color: {get_comparison_color(comparisons.get('completion_rate', 'N/A'))};">{format_comparison(comparisons.get('completion_rate', 'N/A'))}</span>)</li>
                    <li><strong>Operational timing:</strong> {avg_duration:.1f} minutes average duration</li>
                    <li><strong>Weekend schedule performance:</strong> {weekend_completion:.1f}% completion</li>
                </ul>
            </div>"""

        return f"""
        <section id="task-performance">
            <h2>📋 Task & Schedule Performance</h2>

            <h3>Task Management Efficiency</h3>
            <p>Task tracking across all facilities: {task_data.get('total_tasks', 0)} total tasks with {task_data.get('completion_rate', 0):.1f}% completion rate, {task_data.get('total_area_cleaned', 0):,.0f} sq ft total coverage, and {avg_duration:.1f} minutes average task duration.</p>

            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Total</th>
                        <th>Completed</th>
                        <th>In Progress</th>
                        <th>Completion Rate</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>All Facilities</strong></td>
                        <td>{task_data.get('total_tasks', 0)}</td>
                        <td>{task_data.get('completed_tasks', 0)}</td>
                        <td>0</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {task_data.get('completion_rate', 0)}%"></div>
                            </div>
                            <span class="progress-text">{task_data.get('completion_rate', 0):.1f}%</span>
                        </td>
                    </tr>
                </tbody>
            </table>

            <div class="chart-row">
                <div class="chart-small">
                    <canvas id="taskStatusChart"></canvas>
                </div>
                <div class="chart-small">
                    <canvas id="taskModeChart"></canvas>
                </div>
            </div>

            <h3>Task Efficiency Analysis</h3>
            <p>Schedule performance analysis based on actual task data showing weekday completion patterns and weekend performance.</p>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{highest_day}</div>
                    <div class="metric-label">Highest Performance Day</div>
                    <div style="font-size: 0.9em; margin-top: 5px; color: #28a745;">
                        {highest_rate:.1f}% completion rate
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{lowest_day}</div>
                    <div class="metric-label">Lowest Performance Day</div>
                    <div style="font-size: 0.9em; margin-top: 5px; color: #dc3545;">
                        {lowest_rate:.1f}% completion rate
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{task_data.get('incomplete_task_rate', 0):.1f}%
                        <span class="tooltiptext">Percentage of tasks that were cancelled or interrupted based on task status.</span>
                    </div>
                    <div class="metric-label">Incomplete Task Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{weekend_completion:.1f}%
                        <span class="tooltiptext">Task completion rate specifically for weekend schedules, calculated from actual task timestamps.</span>
                    </div>
                    <div class="metric-label">Weekend Schedule Completion</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{avg_duration:.1f} min
                        <span class="tooltiptext">Average task duration calculated from actual task durations in the database.</span>
                    </div>
                    <div class="metric-label">Average Task Duration</div>
                </div>
            </div>

            <h3>Task Performance by Location</h3>
            <div class="two-column">
                {facility_patterns}
            </div>
        </section>"""

    def _generate_charging_section(self, content: Dict[str, Any]) -> str:
        """Generate charging performance section with daily charts and median values"""
        charging_data = content.get('charging_performance', {})
        comparisons = content.get('period_comparisons', {})

        # Format comparison values with color coding
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

        # Calculate charging patterns by location using facility-specific data
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
                charging_by_location += f"""
                    <tr>
                        <td>{facility_name}</td>
                        <td>{charging_metrics.get('total_sessions', 0)}</td>
                        <td>{charging_metrics.get('avg_duration_minutes', 0):.1f} min</td>
                        <td>{charging_metrics.get('median_duration_minutes', 0):.1f} min</td>
                        <td>+{charging_metrics.get('avg_power_gain_percent', 0):.1f}%</td>
                        <td>+{charging_metrics.get('median_power_gain_percent', 0):.1f}%</td>
                    </tr>"""

            charging_by_location += """
                </tbody>
            </table>"""
        else:
            # Fallback if no facility-specific charging data
            facilities = content.get('facility_performance', {}).get('facilities', {})
            if facilities:
                total_sessions = charging_data.get('total_sessions', 0)
                facility_count = len(facilities)

                if facility_count > 0:
                    sessions_per_facility = total_sessions // facility_count
                    remaining_sessions = total_sessions % facility_count

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

                    for i, facility_name in enumerate(facilities.keys()):
                        sessions = sessions_per_facility + (1 if i < remaining_sessions else 0)
                        avg_duration = charging_data.get('avg_charging_duration_minutes', 0)
                        median_duration = charging_data.get('median_charging_duration_minutes', 0)
                        avg_power_gain = charging_data.get('avg_power_gain_percent', 0)
                        median_power_gain = charging_data.get('median_power_gain_percent', 0)

                        charging_by_location += f"""
                            <tr>
                                <td>{facility_name}</td>
                                <td>{sessions}</td>
                                <td>{avg_duration:.1f} min</td>
                                <td>{median_duration:.1f} min</td>
                                <td>+{avg_power_gain:.1f}%</td>
                                <td>+{median_power_gain:.1f}%</td>
                            </tr>"""

                    charging_by_location += """
                        </tbody>
                    </table>"""

        if not charging_by_location:
            charging_by_location = "<h3>Charging Patterns by Location</h3><p>Location-specific charging data not available</p>"

        return f"""
        <section id="charging-performance">
            <h2>🔋 Charging Sessions Performance</h2>

            <p>Charging patterns and battery management during the reporting period: {charging_data.get('total_sessions', 0)} total sessions, {charging_data.get('avg_charging_duration_minutes', 0):.1f} minutes average duration, and {charging_data.get('avg_power_gain_percent', 0):.1f}% average power gain per session.</p>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{charging_data.get('total_sessions', 0)}</div>
                    <div class="metric-label">Total Charging Sessions</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('charging_sessions', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('charging_sessions', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{charging_data.get('avg_charging_duration_minutes', 0):.1f} min
                        <span class="tooltiptext">Average charging duration calculated from actual charging session data.</span>
                    </div>
                    <div class="metric-label">Avg Charging Duration</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('avg_charging_duration', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('avg_charging_duration', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{charging_data.get('median_charging_duration_minutes', 0):.1f} min
                        <span class="tooltiptext">Median charging duration from actual charging session data - represents typical session length.</span>
                    </div>
                    <div class="metric-label">Median Charging Duration</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">+{charging_data.get('avg_power_gain_percent', 0):.1f}%
                        <span class="tooltiptext">Average power gain per charging session from database records.</span>
                    </div>
                    <div class="metric-label">Avg Power Gain per Session</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">+{charging_data.get('median_power_gain_percent', 0):.1f}%
                        <span class="tooltiptext">Median power gain per charging session - represents typical power increase.</span>
                    </div>
                    <div class="metric-label">Median Power Gain per Session</div>
                </div>
            </div>

            <div class="chart-container">
                <canvas id="chargingChart"></canvas>
            </div>

            {charging_by_location}
        </section>"""

    def _generate_resource_section(self, content: Dict[str, Any]) -> str:
        """Generate resource utilization section with daily charts"""
        resource_data = content.get('resource_utilization', {})
        comparisons = content.get('period_comparisons', {})

        # Format comparison values with color coding
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
                facility_breakdown += f"<li><strong>{facility_name}:</strong> {resource_metrics.get('energy_consumption_kwh', 0):.1f} kWh</li>"

            facility_breakdown += """
                    </ul>
                </div>
                <div>
                    <h4>Water Usage by Facility</h4>
                    <ul>"""

            for facility_name, resource_metrics in facility_resource_metrics.items():
                facility_breakdown += f"<li><strong>{facility_name}:</strong> {resource_metrics.get('water_consumption_floz', 0):.0f} fl oz</li>"

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
                        <li><strong>Total consumption:</strong> {total_energy:.1f} kWh
                            <span style="color: {get_comparison_color(comparisons.get('energy_consumption', 'N/A'))};">
                                (vs last period: {format_comparison(comparisons.get('energy_consumption', 'N/A'))})
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
                                (vs last period: {format_comparison(comparisons.get('water_consumption', 'N/A'))})
                            </span>
                        </li>
                        <li><strong>Efficiency:</strong> {resource_data.get('area_per_gallon', 0):.0f} sq ft per gallon</li>
                    </ul>
                </div>
            </div>"""

        return f"""
        <section id="resource-utilization">
            <h2>⚡ Resource Utilization & Efficiency</h2>

            <div class="chart-container">
                <canvas id="resourceChart"></canvas>
            </div>

            <h3>Resource Performance</h3>
            <p>Resource utilization: {resource_data.get('total_energy_consumption_kwh', 0):.1f} kWh total energy consumption, {resource_data.get('total_water_consumption_floz', 0):.0f} fl oz total water usage, {resource_data.get('area_per_kwh', 0):.0f} sq ft per kWh energy efficiency, and {resource_data.get('area_per_gallon', 0):.0f} sq ft per gallon water efficiency.</p>

            {facility_breakdown}
        </section>"""

    def _generate_financial_section(self, content: Dict[str, Any]) -> str:
        """Generate financial performance section with N/A placeholders"""
        cost_data = content.get('cost_analysis', {})

        return f"""
        <section id="financial-performance">
            <h2>💰 Financial Performance</h2>

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
                        <td>N/A</td>
                        <td>N/A</td>
                        <td>Requires cost configuration</td>
                    </tr>
                    <tr>
                        <td>Monthly Total</td>
                        <td>N/A</td>
                        <td>N/A</td>
                        <td>Requires cost configuration</td>
                    </tr>
                    <tr>
                        <td>Cost Savings</td>
                        <td>N/A</td>
                        <td>N/A</td>
                        <td>Requires baseline cost data</td>
                    </tr>
                    <tr>
                        <td>ROI Impact</td>
                        <td>N/A</td>
                        <td>N/A</td>
                        <td>Requires investment data</td>
                    </tr>
                </tbody>
            </table>

            <div class="chart-container">
                <canvas id="financialChart"></canvas>
            </div>

            <div class="highlight-box">
                <h3>💡 Financial Impact Summary</h3>
                <div class="metrics-grid">
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>N/A</strong></div>
                        <div>Monthly operational cost</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>N/A</strong></div>
                        <div>Traditional cleaning estimated cost</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>N/A</strong></div>
                        <div>Monthly savings realized</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>N/A</strong></div>
                        <div>Annual projected savings</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>N/A</strong></div>
                        <div>Cost efficiency improvement</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>N/A</strong></div>
                        <div>Monthly ROI</div>
                    </div>
                </div>
                <p style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">
                    {cost_data.get('note', 'Financial metrics require cost configuration and baseline data to calculate accurate savings and ROI figures.')}
                </p>
            </div>
        </section>"""

    def _generate_event_section(self, content: Dict[str, Any]) -> str:
        # ... existing code until location_analysis = ""

        # REPLACE the location_analysis section with:
        location_analysis = ""
        event_location_mapping = content.get('event_location_mapping', {})

        if event_location_mapping:
            location_analysis = """
            <h3>Event Analysis by Location</h3>
            <div class="two-column">"""

            for building_name, building_events in event_location_mapping.items():
                if building_name != 'Unknown Building':  # Skip unknown buildings
                    location_analysis += f"""
                    <div>
                        <h4>{building_name} Events</h4>
                        <ul>
                            <li><strong>Total Events:</strong> {building_events['total_events']} events</li>
                            <li><strong>Critical Events:</strong> {building_events['critical_events']}</li>
                            <li><strong>Error Events:</strong> {building_events['error_events']}</li>
                            <li><strong>Warning Events:</strong> {building_events['warning_events']}</li>
                            <li><strong>Info Events:</strong> {building_events['info_events']}</li>
                        </ul>
                    </div>"""

            location_analysis += """
            </div>"""
        else:
            location_analysis = """
            <h3>Event Analysis by Location</h3>
            <p>No location-specific event data available</p>"""

    def _generate_conclusion(self, content: Dict[str, Any]) -> str:
        """Generate conclusion section with key numbers summary"""
        exec_data = content.get('executive_summary', {})
        period = content.get('period', 'the reporting period')

        def format_value(value, suffix=""):
            if value == 'N/A' or value is None:
                return 'N/A'
            return f"{value:,.0f}{suffix}" if isinstance(value, (int, float)) else f"{value}{suffix}"

        # Get robots online rate instead of fleet availability
        robots_online_rate = exec_data.get('robots_online_rate', exec_data.get('fleet_availability_rate', 0))

        return f"""
        <section id="conclusion">
            <h2>🎯 Conclusion</h2>

            <div class="highlight-box">
                <p>{period.title()} performance summary: {format_value(robots_online_rate, '%')} robots online,
                {format_value(exec_data.get('task_completion_rate', 0), '%')} task completion rate across
                {format_value(exec_data.get('total_robots', 0))} robot(s),
                {format_value(exec_data.get('total_tasks', 0))} tasks completed,
                {format_value(exec_data.get('total_area_cleaned', 0))} sq ft cleaned,
                {format_value(exec_data.get('total_charging_sessions', 0))} charging sessions,
                {format_value(exec_data.get('energy_saved_kwh', 0))} kWh energy consumption,
                and {format_value(exec_data.get('water_consumption', 0))} fl oz water usage.</p>
            </div>
        </section>"""

    def _generate_footer(self, content: Dict[str, Any]) -> str:
        """Generate footer with metadata"""
        generation_time = content.get('generation_time', datetime.now())
        robots_count = content.get('robots_included', 0)

        return f"""
        <footer style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #e9ecef; text-align: center; color: #7f8c8d;">
            <p><strong>Robot Performance Report</strong><br>
            Period: {content.get('period', 'N/A')}<br>
            Robots Included: {robots_count}<br>
            Generated: {generation_time.strftime('%B %d, %Y at %I:%M %p') if hasattr(generation_time, 'strftime') else str(generation_time)}</p>
        </footer>"""

    def _generate_chart_data(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data from real metrics"""
        try:
            metrics = {
                'task_performance': content.get('task_performance', {}),
                'charging_performance': content.get('charging_performance', {}),
                'resource_utilization': content.get('resource_utilization', {}),
                'cost_analysis': content.get('cost_analysis', {}),
                'event_analysis': content.get('event_analysis', {}),
                'trend_data': content.get('trend_data', {})
            }

            chart_data = self.chart_formatter.format_all_chart_data(metrics)
            return self._convert_numpy_types(chart_data)
        except Exception as e:
            logger.error(f"Chart data error: {e}")
            return {}

    def _convert_numpy_types(self, obj):
        """Convert numpy types to Python types"""
        import numpy as np

        if isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    def _generate_javascript(self, chart_data: Dict[str, Any]) -> str:
        """Generate JavaScript for charts using real data with daily charts"""
        # Get trend data for daily charts
        trend_data = chart_data.get('trend_data', {})
        dates = trend_data.get('dates', [])

        return f"""
    <script>
        // Task Status Chart
        const taskStatusCtx = document.getElementById('taskStatusChart');
        if (taskStatusCtx) {{
            const taskStatusData = {json.dumps(chart_data.get('taskStatusChart', {}))};
            new Chart(taskStatusCtx, {{
                type: 'doughnut',
                data: {{
                    labels: taskStatusData.labels || ['Completed', 'Cancelled', 'Interrupted'],
                    datasets: [{{
                        data: taskStatusData.data || [0, 0, 0],
                        backgroundColor: taskStatusData.backgroundColor || ['#28a745', '#ffc107', '#dc3545'],
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Task Status Distribution'
                        }}
                    }}
                }}
            }});
        }}

        // Task Mode Chart
        const taskModeCtx = document.getElementById('taskModeChart');
        if (taskModeCtx) {{
            const taskModeData = {json.dumps(chart_data.get('taskModeChart', {}))};
            new Chart(taskModeCtx, {{
                type: 'pie',
                data: {{
                    labels: taskModeData.labels || ['No Data'],
                    datasets: [{{
                        data: taskModeData.data || [1],
                        backgroundColor: taskModeData.backgroundColor || ['#6c757d']
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Task Mode Distribution'
                        }}
                    }}
                }}
            }});
        }}

        // Event Type Chart
        const eventTypeCtx = document.getElementById('eventTypeChart');
        if (eventTypeCtx) {{
            const eventData = {json.dumps(chart_data.get('eventTypeChart', {}))};
            new Chart(eventTypeCtx, {{
                type: 'bar',
                data: eventData.datasets ? eventData : {{
                    labels: ['No Events'],
                    datasets: [{{
                        label: 'Events',
                        data: [0],
                        backgroundColor: '#6c757d'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Event Types'
                        }}
                    }}
                }}
            }});
        }}

        // Event Level Chart - Fixed to include all levels
        const eventLevelCtx = document.getElementById('eventLevelChart');
        if (eventLevelCtx) {{
            const eventLevelData = {json.dumps(chart_data.get('eventLevelChart', {}))};
            new Chart(eventLevelCtx, {{
                type: 'doughnut',
                data: {{
                    labels: eventLevelData.labels || ['No Events'],
                    datasets: [{{
                        data: eventLevelData.data || [1],
                        backgroundColor: eventLevelData.backgroundColor || ['#6c757d']
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Event Level Distribution'
                        }}
                    }}
                }}
            }});
        }}

        // Charging Chart - Daily bars instead of weekly lines
        const chargingCtx = document.getElementById('chargingChart');
        if (chargingCtx) {{
            const chargingDates = {json.dumps(dates)};
            const chargingSessions = {json.dumps(trend_data.get('charging_sessions_trend', []))};
            const chargingDurations = {json.dumps(trend_data.get('charging_duration_trend', []))};

            new Chart(chargingCtx, {{
                type: 'bar',
                data: {{
                    labels: chargingDates.length > 0 ? chargingDates : ['No Data'],
                    datasets: [{{
                        label: 'Charging Sessions',
                        data: chargingSessions.length > 0 ? chargingSessions : [0],
                        backgroundColor: '#17a2b8',
                        yAxisID: 'y'
                    }}, {{
                        label: 'Avg Duration (min)',
                        data: chargingDurations.length > 0 ? chargingDurations : [0],
                        type: 'line',
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Daily Charging Performance'
                        }}
                    }},
                    scales: {{
                        y: {{
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {{
                                display: true,
                                text: 'Sessions'
                            }}
                        }},
                        y1: {{
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {{
                                display: true,
                                text: 'Duration (min)'
                            }},
                            grid: {{
                                drawOnChartArea: false,
                            }},
                        }}
                    }}
                }}
            }});
        }}

        // Resource Chart - Daily bars instead of weekly lines
        const resourceCtx = document.getElementById('resourceChart');
        if (resourceCtx) {{
            const resourceDates = {json.dumps(dates)};
            const energyData = {json.dumps(trend_data.get('energy_consumption_trend', []))};
            const waterData = {json.dumps(trend_data.get('water_usage_trend', []))};

            new Chart(resourceCtx, {{
                type: 'bar',
                data: {{
                    labels: resourceDates.length > 0 ? resourceDates : ['No Data'],
                    datasets: [{{
                        label: 'Energy (kWh)',
                        data: energyData.length > 0 ? energyData : [0],
                        backgroundColor: '#e74c3c',
                        yAxisID: 'y'
                    }}, {{
                        label: 'Water (fl oz)',
                        data: waterData.length > 0 ? waterData : [0],
                        backgroundColor: '#3498db',
                        yAxisID: 'y1'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Daily Resource Usage'
                        }}
                    }},
                    scales: {{
                        y: {{
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {{
                                display: true,
                                text: 'Energy (kWh)'
                            }}
                        }},
                        y1: {{
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {{
                                display: true,
                                text: 'Water (fl oz)'
                            }},
                            grid: {{
                                drawOnChartArea: false,
                            }},
                        }}
                    }}
                }}
            }});
        }}

        // Financial Chart - N/A data
        const financialCtx = document.getElementById('financialChart');
        if (financialCtx) {{
            new Chart(financialCtx, {{
                type: 'line',
                data: {{
                    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    datasets: [{{
                        label: 'Cost Data Not Available',
                        data: [0, 0, 0, 0],
                        borderColor: '#6c757d',
                        backgroundColor: 'rgba(108, 117, 125, 0.1)',
                        fill: true
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Financial Performance (Data Not Available)'
                        }}
                    }},
                    scales: {{
                        y: {{
                            display: false
                        }}
                    }}
                }}
            }});
        }}
    </script>"""

    # Legacy method for backward compatibility
    def generate_report(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Legacy method - redirects to comprehensive report generation"""
        return self.generate_comprehensive_report(content, config)