# src/pudu/reporting/templates/robot_performance_template.py
from typing import Dict, Any
from datetime import datetime
import json
import logging
from ..core.report_config import ReportConfig, ReportDetailLevel

logger = logging.getLogger(__name__)

class RobotPerformanceTemplate:
    """HTML template generator for robot performance reports"""

    def __init__(self):
        """Initialize template with reusable components"""
        pass

    def generate_report(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """
        Generate complete HTML report

        Args:
            content: Processed report content from ReportGenerator
            config: Report configuration

        Returns:
            Complete HTML report as string
        """
        logger.info(f"Generating HTML report with detail level: {config.detail_level.value}")

        html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{content['title']}</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
            {self._generate_styles()}
        </head>
        <body>
            <div class="container">
                {self._generate_header(content, config)}
                {self._generate_executive_summary(content, config)}
                {self._generate_content_sections(content, config)}
                {self._generate_footer(content)}
            </div>
            {self._generate_javascript(content, config)}
        </body>
        </html>
        """

        return html_content

    def _generate_styles(self) -> str:
        """Generate CSS styles for the report"""
        return '''
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }

        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }

        .subtitle {
            text-align: center;
            color: #7f8c8d;
            font-size: 1.2em;
            margin-bottom: 30px;
        }

        h2 {
            color: #34495e;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
        }

        h3 {
            color: #2980b9;
            margin-top: 30px;
        }

        .highlight-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .metric-card {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }

        .metric-label {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 5px;
        }

        .chart-container {
            position: relative;
            height: 400px;
            margin: 30px 0;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .chart-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin: 30px 0;
        }

        .chart-small {
            position: relative;
            height: 300px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }

        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
        }

        tr:hover {
            background: #f8f9fa;
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        .status-excellent { background: #28a745; }
        .status-good { background: #17a2b8; }
        .status-warning { background: #ffc107; }
        .status-error { background: #dc3545; }

        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e9ecef;
            text-align: center;
            color: #7f8c8d;
        }

        .summary-section {
            margin-bottom: 30px;
        }

        .data-section {
            margin-bottom: 40px;
        }

        @media (max-width: 768px) {
            .chart-row {
                grid-template-columns: 1fr;
            }

            .container {
                padding: 15px;
            }
        }
    </style>'''

    def _generate_header(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate report header"""
        generation_time = content['generation_time'].strftime('%B %d, %Y at %I:%M %p')

        return f'''
        <h1>{content['title']}</h1>
        <p class="subtitle">Generated on {generation_time}</p>
        <p class="subtitle">Report Period: {content['period']}</p>
        '''

    def _generate_executive_summary(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate executive summary section"""
        sections = content.get('sections', {})

        # Calculate summary metrics
        total_robots = 0
        total_tasks = 0
        total_sessions = 0

        if 'robot_status' in sections:
            total_robots = sections['robot_status'].get('total_robots', 0)
        if 'cleaning_tasks' in sections:
            total_tasks = sections['cleaning_tasks'].get('total_tasks', 0)
        if 'charging_tasks' in sections:
            total_sessions = sections['charging_tasks'].get('total_sessions', 0)

        return f'''
        <section id="executive-summary">
            <h2>Executive Summary</h2>
            <div class="highlight-box">
                <p>This report provides {config.detail_level.value} analysis of robot management system performance for the specified period.</p>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{total_robots}</div>
                    <div class="metric-label">Total Robots</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_tasks}</div>
                    <div class="metric-label">Cleaning Tasks</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_sessions}</div>
                    <div class="metric-label">Charging Sessions</div>
                </div>
            </div>
        </section>
        '''

    def _generate_content_sections(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate main content sections based on selected categories"""
        sections_html = ""
        sections = content.get('sections', {})

        if 'robot_status' in sections:
            sections_html += self._generate_robot_status_section(sections['robot_status'], config)

        if 'cleaning_tasks' in sections:
            sections_html += self._generate_cleaning_tasks_section(sections['cleaning_tasks'], config)

        if 'charging_tasks' in sections:
            sections_html += self._generate_charging_section(sections['charging_tasks'], config)

        if 'performance' in sections:
            sections_html += self._generate_performance_section(sections['performance'], config)

        if 'cost_analysis' in sections:
            sections_html += self._generate_cost_section(sections['cost_analysis'], config)

        return sections_html

    def _generate_robot_status_section(self, robot_data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate robot status section"""
        html = f'''
        <section id="robot-status" class="data-section">
            <h2>Robot Status & Management</h2>
            <p>{robot_data.get('summary', 'No robot status data available')}</p>
        '''

        if config.detail_level in [ReportDetailLevel.DETAILED, ReportDetailLevel.COMPREHENSIVE]:
            status_dist = robot_data.get('status_distribution', {})
            if status_dist:
                html += '''
                <h3>Status Distribution</h3>
                <div class="chart-row">
                    <div class="chart-small">
                        <canvas id="robotStatusChart"></canvas>
                    </div>
                </div>
                '''

        html += '</section>'
        return html

    def _generate_cleaning_tasks_section(self, tasks_data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate cleaning tasks section"""
        html = f'''
        <section id="cleaning-tasks" class="data-section">
            <h2>Cleaning Tasks Performance</h2>
            <p>{tasks_data.get('summary', 'No cleaning tasks data available')}</p>
        '''

        if config.detail_level in [ReportDetailLevel.DETAILED, ReportDetailLevel.COMPREHENSIVE]:
            completion_rate = tasks_data.get('completion_rate', 0)
            html += f'''
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{completion_rate}%</div>
                    <div class="metric-label">Task Completion Rate</div>
                </div>
            </div>
            '''

            if 'task_status_distribution' in tasks_data:
                html += '''
                <h3>Task Status Analysis</h3>
                <div class="chart-row">
                    <div class="chart-small">
                        <canvas id="taskStatusChart"></canvas>
                    </div>
                </div>
                '''

        html += '</section>'
        return html

    def _generate_charging_section(self, charging_data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate charging section"""
        html = f'''
        <section id="charging-performance" class="data-section">
            <h2>Charging Performance</h2>
            <p>{charging_data.get('summary', 'No charging data available')}</p>
        '''

        if config.detail_level in [ReportDetailLevel.DETAILED, ReportDetailLevel.COMPREHENSIVE]:
            avg_duration = charging_data.get('average_charging_duration', 0)
            avg_power_gain = charging_data.get('average_power_gain', '0%')

            html += f'''
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{avg_duration}</div>
                    <div class="metric-label">Avg Charging Duration</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{avg_power_gain}</div>
                    <div class="metric-label">Avg Power Gain</div>
                </div>
            </div>
            '''

        html += '</section>'
        return html

    def _generate_performance_section(self, performance_data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate performance analysis section"""
        html = f'''
        <section id="performance-analysis" class="data-section">
            <h2>Performance Analysis</h2>
            <p>{performance_data.get('summary', 'No performance data available')}</p>
        '''

        if config.detail_level in [ReportDetailLevel.DETAILED, ReportDetailLevel.COMPREHENSIVE]:
            error_events = performance_data.get('error_events', 0)
            warning_events = performance_data.get('warning_events', 0)

            html += f'''
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{error_events}</div>
                    <div class="metric-label">Error Events</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{warning_events}</div>
                    <div class="metric-label">Warning Events</div>
                </div>
            </div>
            '''

        html += '</section>'
        return html

    def _generate_cost_section(self, cost_data: Dict[str, Any], config: ReportConfig) -> str:
        """Generate cost analysis section"""
        return f'''
        <section id="cost-analysis" class="data-section">
            <h2>Cost Analysis</h2>
            <p>{cost_data.get('summary', 'No cost data available')}</p>
            <div class="highlight-box">
                <p>{cost_data.get('note', 'Cost analysis requires additional configuration')}</p>
            </div>
        </section>
        '''

    def _generate_footer(self, content: Dict[str, Any]) -> str:
        """Generate report footer"""
        generation_time = content['generation_time'].strftime('%Y-%m-%d %H:%M:%S')

        return f'''
        <footer class="footer">
            <p><strong>Robot Management Report</strong><br>
            Generated: {generation_time}<br>
            Report Period: {content['period']}</p>
        </footer>
        '''

    def _generate_javascript(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate JavaScript for interactive charts"""
        sections = content.get('sections', {})
        js_code = '''
    <script>
        // Chart.js configurations and data
        '''

        # Robot Status Chart
        if 'robot_status' in sections and 'status_distribution' in sections['robot_status']:
            status_data = sections['robot_status']['status_distribution']
            js_code += f'''
        // Robot Status Chart
        const robotStatusCtx = document.getElementById('robotStatusChart');
        if (robotStatusCtx) {{
            new Chart(robotStatusCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(list(status_data.keys()))},
                    datasets: [{{
                        data: {json.dumps(list(status_data.values()))},
                        backgroundColor: ['#28a745', '#17a2b8', '#ffc107', '#dc3545'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Robot Status Distribution',
                            font: {{ size: 16, weight: 'bold' }}
                        }}
                    }}
                }}
            }});
        }}
        '''

        # Task Status Chart
        if 'cleaning_tasks' in sections and 'task_status_distribution' in sections['cleaning_tasks']:
            task_data = sections['cleaning_tasks']['task_status_distribution']
            js_code += f'''
        // Task Status Chart
        const taskStatusCtx = document.getElementById('taskStatusChart');
        if (taskStatusCtx) {{
            new Chart(taskStatusCtx, {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(list(task_data.keys()))},
                    datasets: [{{
                        label: 'Tasks',
                        data: {json.dumps(list(task_data.values()))},
                        backgroundColor: ['#3498db', '#e74c3c', '#f39c12'],
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        title: {{
                            display: true,
                            text: 'Task Status Distribution',
                            font: {{ size: 16, weight: 'bold' }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
        }}
        '''

        js_code += '''
        </script>'''

        return js_code