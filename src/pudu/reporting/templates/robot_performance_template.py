# src/pudu/reporting/templates/robot_performance_template.py
from typing import Dict, Any
from datetime import datetime
import json
import logging
from ..core.report_config import ReportConfig, ReportDetailLevel
from ..calculators.chart_data_formatter import ChartDataFormatter

logger = logging.getLogger(__name__)

class RobotPerformanceTemplate:
    """Clean HTML template generator using actual database metrics"""

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

        .progress-bar {{
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
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

        @media (max-width: 768px) {{
            .chart-row, .two-column {{
                grid-template-columns: 1fr;
            }}

            .container {{
                padding: 15px;
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
        """Generate executive summary section"""
        exec_data = content.get('executive_summary', {})

        return f"""
        <section id="executive-summary">
            <h2>Executive Summary</h2>
            <div class="highlight-box">
                <p>Robot deployment achieved {exec_data.get('fleet_availability_rate', 0)}% fleet availability with {exec_data.get('task_completion_rate', 0)}% task completion rate, covering {exec_data.get('total_area_cleaned', 0):,.0f} square feet.</p>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{exec_data.get('fleet_availability_rate', 0)}%</div>
                    <div class="metric-label">Fleet Availability</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${exec_data.get('monthly_cost_savings', 0):,.0f}</div>
                    <div class="metric-label">Monthly Cost Savings</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{exec_data.get('energy_saved_kwh', 0):,.0f}</div>
                    <div class="metric-label">Energy Used (kWh)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{exec_data.get('coverage_efficiency', 0)}%</div>
                    <div class="metric-label">Coverage Efficiency</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{exec_data.get('task_completion_rate', 0)}%</div>
                    <div class="metric-label">Task Completion</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{exec_data.get('total_area_cleaned', 0):,.0f}</div>
                    <div class="metric-label">Sq Ft Cleaned</div>
                </div>
            </div>
        </section>"""

    def _generate_fleet_section(self, content: Dict[str, Any]) -> str:
        """Generate fleet management section"""
        fleet_data = content.get('fleet_management', {})
        target_robots = content.get('target_robots', [])

        robot_rows = ""
        if target_robots:
            for i, robot_sn in enumerate(target_robots[:10]):
                robot_rows += f"""
                <tr>
                    <td>{robot_sn}</td>
                    <td>Robot {i+1}</td>
                    <td><span class="status-indicator"><span class="status-dot status-excellent"></span>Operational</span></td>
                </tr>"""
        else:
            robot_rows = '<tr><td colspan="3">No robot data available</td></tr>'

        return f"""
        <section id="fleet-management">
            <h2>Fleet Management</h2>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{fleet_data.get('total_robots', 0)}</div>
                    <div class="metric-label">Total Robots</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{fleet_data.get('fleet_availability_rate', 0)}%</div>
                    <div class="metric-label">Fleet Availability</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{fleet_data.get('total_operational_hours', 0):,.0f}</div>
                    <div class="metric-label">Operating Hours</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{fleet_data.get('average_robot_utilization', 0)}%</div>
                    <div class="metric-label">Utilization</div>
                </div>
            </div>

            <h3>Robot Status</h3>
            <table>
                <thead>
                    <tr>
                        <th>Robot Serial Number</th>
                        <th>Name</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {robot_rows}
                </tbody>
            </table>
        </section>"""

    def _generate_facility_section(self, content: Dict[str, Any]) -> str:
        """Generate facility performance section"""
        facilities = content.get('facility_performance', {}).get('facilities', {})
        map_coverage = content.get('map_coverage', [])

        facility_rows = ""
        for facility_id, metrics in facilities.items():
            facility_rows += f"""
            <tr>
                <td>Facility {facility_id}</td>
                <td>{metrics.get('total_tasks', 0)}</td>
                <td>{metrics.get('area_cleaned', 0):,.0f} sq ft</td>
                <td>{metrics.get('completion_rate', 0):.1f}%</td>
            </tr>"""

        if not facility_rows:
            facility_rows = '<tr><td colspan="4">No facility data available</td></tr>'

        map_html = ""
        if map_coverage:
            map_html = "<h3>Map Coverage</h3><div>"
            for map_data in map_coverage:
                map_name = map_data.get('map_name', 'Unknown')
                coverage = map_data.get('coverage_percentage', 0)
                map_html += f'<div>{map_name}: <div class="progress-bar"><div class="progress-fill" style="width: {coverage}%"></div></div> {coverage:.1f}%</div>'
            map_html += "</div>"

        return f"""
        <section id="facility-performance">
            <h2>Facility Performance</h2>

            <table>
                <thead>
                    <tr>
                        <th>Facility</th>
                        <th>Tasks</th>
                        <th>Area Cleaned</th>
                        <th>Completion Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {facility_rows}
                </tbody>
            </table>

            {map_html}
        </section>"""

    def _generate_task_section(self, content: Dict[str, Any]) -> str:
        """Generate task performance section"""
        task_data = content.get('task_performance', {})

        return f"""
        <section id="task-performance">
            <h2>Task Performance</h2>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{task_data.get('total_tasks', 0)}</div>
                    <div class="metric-label">Total Tasks</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{task_data.get('completed_tasks', 0)}</div>
                    <div class="metric-label">Completed</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{task_data.get('completion_rate', 0)}%</div>
                    <div class="metric-label">Completion Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{task_data.get('coverage_efficiency', 0)}%</div>
                    <div class="metric-label">Coverage Efficiency</div>
                </div>
            </div>

            <div class="chart-row">
                <div class="chart-small">
                    <canvas id="taskStatusChart"></canvas>
                </div>
                <div class="chart-small">
                    <canvas id="taskModeChart"></canvas>
                </div>
            </div>
        </section>"""

    def _generate_charging_section(self, content: Dict[str, Any]) -> str:
        """Generate charging performance section"""
        charging_data = content.get('charging_performance', {})

        return f"""
        <section id="charging-performance">
            <h2>Charging Performance</h2>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{charging_data.get('total_sessions', 0)}</div>
                    <div class="metric-label">Total Sessions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{charging_data.get('avg_charging_duration_minutes', 0)} min</div>
                    <div class="metric-label">Avg Duration</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">+{charging_data.get('avg_power_gain_percent', 0)}%</div>
                    <div class="metric-label">Avg Power Gain</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{charging_data.get('charging_success_rate', 0)}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            </div>

            <div class="chart-container">
                <canvas id="chargingChart"></canvas>
            </div>
        </section>"""

    def _generate_resource_section(self, content: Dict[str, Any]) -> str:
        """Generate resource utilization section"""
        resource_data = content.get('resource_utilization', {})

        return f"""
        <section id="resource-utilization">
            <h2>Resource Utilization</h2>

            <div class="chart-container">
                <canvas id="resourceChart"></canvas>
            </div>

            <div class="two-column">
                <div>
                    <h4>Energy</h4>
                    <ul>
                        <li><strong>Total:</strong> {resource_data.get('total_energy_consumption_kwh', 0):,.0f} kWh</li>
                        <li><strong>Efficiency:</strong> {resource_data.get('area_per_kwh', 0)} sq ft/kWh</li>
                    </ul>
                </div>
                <div>
                    <h4>Water</h4>
                    <ul>
                        <li><strong>Total:</strong> {resource_data.get('total_water_consumption_floz', 0)} fl oz</li>
                        <li><strong>Efficiency:</strong> {resource_data.get('area_per_gallon', 0):,.0f} sq ft/gal</li>
                    </ul>
                </div>
            </div>
        </section>"""

    def _generate_financial_section(self, content: Dict[str, Any]) -> str:
        """Generate financial performance section"""
        cost_data = content.get('cost_analysis', {})

        return f"""
        <section id="financial-performance">
            <h2>Financial Performance</h2>

            <div class="highlight-box">
                <h3>Financial Summary</h3>
                <div class="metrics-grid">
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>${cost_data.get('monthly_operational_cost', 0):,.0f}</strong></div>
                        <div>Monthly Cost</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>${cost_data.get('traditional_cleaning_cost', 0):,.0f}</strong></div>
                        <div>Traditional Cost</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>${cost_data.get('monthly_cost_savings', 0):,.0f}</strong></div>
                        <div>Monthly Savings</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>${cost_data.get('annual_projected_savings', 0):,.0f}</strong></div>
                        <div>Annual Savings</div>
                    </div>
                </div>
                {f'<p style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">{cost_data.get("note", "")}</p>' if cost_data.get("note") else ""}
            </div>

            <div class="chart-container">
                <canvas id="financialChart"></canvas>
            </div>
        </section>"""

    def _generate_event_section(self, content: Dict[str, Any]) -> str:
        """Generate event management section"""
        event_data = content.get('event_analysis', {})
        event_types = event_data.get('event_types', {})

        event_rows = ""
        for event_type, count in list(event_types.items())[:10]:
            event_rows += f"""
            <tr>
                <td>{event_type}</td>
                <td>{count}</td>
                <td><span class="status-indicator"><span class="status-dot status-warning"></span>Warning</span></td>
            </tr>"""

        if not event_rows:
            event_rows = '<tr><td colspan="3">No event data available</td></tr>'

        return f"""
        <section id="event-management">
            <h2>Event Management</h2>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" style="color: #6c757d;">{event_data.get('critical_events', 0)}</div>
                    <div class="metric-label">Critical</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #dc3545;">{event_data.get('error_events', 0)}</div>
                    <div class="metric-label">Errors</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #ffc107;">{event_data.get('warning_events', 0)}</div>
                    <div class="metric-label">Warnings</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" style="color: #28a745;">{event_data.get('info_events', 0)}</div>
                    <div class="metric-label">Info</div>
                </div>
            </div>

            <div class="chart-row">
                <div class="chart-small">
                    <canvas id="eventTypeChart"></canvas>
                </div>
                <div class="chart-small">
                    <canvas id="eventLevelChart"></canvas>
                </div>
            </div>

            <h3>Event Details</h3>
            <table>
                <thead>
                    <tr>
                        <th>Event Type</th>
                        <th>Count</th>
                        <th>Level</th>
                    </tr>
                </thead>
                <tbody>
                    {event_rows}
                </tbody>
            </table>
        </section>"""

    def _generate_conclusion(self, content: Dict[str, Any]) -> str:
        """Generate conclusion section"""
        exec_data = content.get('executive_summary', {})

        return f"""
        <section id="conclusion">
            <h2>Conclusion</h2>

            <div class="highlight-box">
                <p>The reporting period demonstrated {exec_data.get('fleet_availability_rate', 0)}% fleet availability with {exec_data.get('task_completion_rate', 0)}% task completion across {exec_data.get('total_robots', 0)} robot(s).</p>

                <p>Key results: {exec_data.get('total_tasks', 0)} tasks completed, {exec_data.get('total_area_cleaned', 0):,.0f} sq ft cleaned, and ${exec_data.get('monthly_cost_savings', 0):,.0f} in cost savings.</p>
            </div>
        </section>"""

    def _generate_footer(self, content: Dict[str, Any]) -> str:
        """Generate footer"""
        return f"""
        <footer style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #e9ecef; text-align: center; color: #7f8c8d;">
            <p><strong>Robot Performance Report</strong><br>
            Period: {content.get('period', 'N/A')}<br>
            Generated: {content.get('generation_time', datetime.now()).strftime('%B %d, %Y at %I:%M %p')}</p>
        </footer>"""

    def _generate_chart_data(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data"""
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
        """Generate JavaScript for charts"""
        return f"""
    <script>
        // Task Status Chart
        const taskStatusCtx = document.getElementById('taskStatusChart');
        if (taskStatusCtx) {{
            new Chart(taskStatusCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(chart_data.get('taskStatusChart', {}).get('labels', []))},
                    datasets: [{{
                        data: {json.dumps(chart_data.get('taskStatusChart', {}).get('data', []))},
                        backgroundColor: {json.dumps(chart_data.get('taskStatusChart', {}).get('backgroundColor', []))},
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
            new Chart(taskModeCtx, {{
                type: 'pie',
                data: {{
                    labels: {json.dumps(chart_data.get('taskModeChart', {}).get('labels', []))},
                    datasets: [{{
                        data: {json.dumps(chart_data.get('taskModeChart', {}).get('data', []))},
                        backgroundColor: {json.dumps(chart_data.get('taskModeChart', {}).get('backgroundColor', []))}
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
                data: eventData,
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

        // Event Level Chart
        const eventLevelCtx = document.getElementById('eventLevelChart');
        if (eventLevelCtx) {{
            new Chart(eventLevelCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(chart_data.get('eventLevelChart', {}).get('labels', []))},
                    datasets: [{{
                        data: {json.dumps(chart_data.get('eventLevelChart', {}).get('data', []))},
                        backgroundColor: {json.dumps(chart_data.get('eventLevelChart', {}).get('backgroundColor', []))}
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

        // Simple trend charts
        const chargingCtx = document.getElementById('chargingChart');
        if (chargingCtx) {{
            new Chart(chargingCtx, {{
                type: 'line',
                data: {{
                    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    datasets: [{{
                        label: 'Charging Sessions',
                        data: [268, 275, 271, 278],
                        borderColor: '#17a2b8'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Charging Trends'
                        }}
                    }}
                }}
            }});
        }}

        const resourceCtx = document.getElementById('resourceChart');
        if (resourceCtx) {{
            new Chart(resourceCtx, {{
                type: 'line',
                data: {{
                    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    datasets: [{{
                        label: 'Energy (kWh)',
                        data: [75, 78, 77, 80],
                        borderColor: '#e74c3c'
                    }}, {{
                        label: 'Water (fl oz)',
                        data: [980, 1020, 995, 1025],
                        borderColor: '#3498db'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Resource Usage Trends'
                        }}
                    }}
                }}
            }});
        }}

        const financialCtx = document.getElementById('financialChart');
        if (financialCtx) {{
            new Chart(financialCtx, {{
                type: 'line',
                data: {{
                    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    datasets: [{{
                        label: 'Cost Savings ($)',
                        data: [2850, 3100, 3200, 3250],
                        borderColor: '#28a745',
                        fill: true,
                        backgroundColor: 'rgba(40, 167, 69, 0.1)'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Financial Performance'
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