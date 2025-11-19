from typing import Dict, Any, List
from datetime import datetime
import json
import logging
from ..core.report_config import ReportConfig
from ..calculators.chart_data_formatter import ChartDataFormatter

logger = logging.getLogger(__name__)

class RobotPerformanceTemplate:
    """Enhanced HTML template generator using actual database metrics"""

    def __init__(self):
        self.chart_formatter = ChartDataFormatter()

    def generate_comprehensive_report(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate comprehensive HTML report using real data with conditional sections"""
        try:
            detail_level = config.detail_level.value.lower()
            chart_js_data = self._generate_chart_data(content)
            content_categories = config.content_categories

            # Always include executive summary (now includes individual robot performance)
            sections = [self._generate_executive_summary(content, detail_level=detail_level)]

            # Task Performance section (now includes facility efficiency charts by location)
            if any(cat in content_categories for cat in ['executive-summary', 'fleet-management', 'facility-performance', 'task-performance', 'cleaning-performance']):
                sections.append(self._generate_task_section(content, detail_level=detail_level))

            # Facility-Specific Performance section (moved after task section)
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
            sections.append(self._generate_footer(content, config))

            html_content = f"""<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{content.get('title', config.report_name or 'Robot Performance Report')} - {content.get('period', 'Latest Period')}</title>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
                <style>
                    /* Modern CSS Reset & Base Styles */
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}

                    :root {{
                        /* Color Palette */
                        --primary-color: #2563eb;
                        --primary-dark: #1e40af;
                        --secondary-color: #7c3aed;
                        --accent-color: #06b6d4;
                        --success-color: #10b981;
                        --warning-color: #f59e0b;
                        --error-color: #ef4444;
                        --info-color: #3b82f6;

                        /* Neutrals */
                        --bg-primary: #ffffff;
                        --bg-secondary: #f8fafc;
                        --bg-tertiary: #f1f5f9;
                        --text-primary: #0f172a;
                        --text-secondary: #475569;
                        --text-tertiary: #94a3b8;
                        --border-color: #e2e8f0;
                        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);

                        /* Spacing */
                        --space-xs: 0.25rem;
                        --space-sm: 0.5rem;
                        --space-md: 1rem;
                        --space-lg: 1.5rem;
                        --space-xl: 2rem;
                        --space-2xl: 3rem;

                        /* Typography */
                        --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        --font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Courier New', monospace;
                    }}

                    body {{
                        font-family: var(--font-sans);
                        line-height: 1.6;
                        color: var(--text-primary);
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        background-attachment: fixed;
                        padding: var(--space-xl) var(--space-md);
                        min-height: 100vh;
                    }}

                    .container {{
                        max-width: 1400px;
                        margin: 0 auto;
                        background: var(--bg-primary);
                        border-radius: 24px;
                        box-shadow: var(--shadow-xl);
                        overflow: visible;  /* Changed from hidden to visible */
                        padding: 30px;
                    }}

                    h1 {{
                        color: #2c3e50;
                        text-align: center;
                        margin-bottom: 10px;
                        font-size: 2.5em;
                        font-weight: 700;
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
                        font-size: 1.875rem;
                        font-weight: 700;
                    }}

                    h3 {{
                        color: #2980b9;
                        margin-top: 30px;
                        font-size: 1.5rem;
                        font-weight: 600;
                    }}

                    h4 {{
                        font-size: 1.25rem;
                        font-weight: 600;
                        color: var(--text-secondary);
                        margin-bottom: var(--space-md);
                    }}

                    h5 {{
                        font-size: 1.125rem;
                        font-weight: 600;
                        color: var(--text-secondary);
                        margin-bottom: var(--space-md);
                    }}

                    p {{
                        color: var(--text-secondary);
                        margin-bottom: var(--space-md);
                        line-height: 1.7;
                    }}

                    ul {{
                        margin: var(--space-md) 0;
                        padding-left: var(--space-xl);
                    }}

                    ul li {{
                        margin-bottom: var(--space-sm);
                        color: var(--text-secondary);
                        line-height: 1.7;
                    }}

                    .highlight-box {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: var(--space-xl);
                        border-radius: 16px;
                        margin: var(--space-lg) 0;
                        box-shadow: var(--shadow-lg);
                    }}

                    .highlight-box p {{
                        color: white;
                        font-size: 1.125rem;
                        margin: 0;
                        line-height: 1.8;
                    }}

                    .highlight-box h3 {{
                        color: white;
                        margin-top: 0;
                    }}

                    .metrics-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                        gap: var(--space-lg);
                        margin: var(--space-xl) 0;
                    }}

                    .metric-card {{
                        background: var(--bg-secondary);
                        border: 2px solid var(--border-color);
                        border-radius: 12px;
                        padding: var(--space-lg);
                        text-align: center;
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        position: relative;
                        overflow: visible;  /* Changed from hidden to visible */
                    }}

                    .metric-card::before {{
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        height: 4px;
                        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
                        opacity: 0;
                        transition: opacity 0.3s ease;
                    }}

                    .metric-card:hover {{
                        transform: translateY(-4px);
                        box-shadow: var(--shadow-lg);
                        border-color: var(--primary-color);
                    }}

                    .metric-card:hover::before {{
                        opacity: 1;
                    }}

                    .metric-value {{
                        font-size: 2.25rem;
                        font-weight: 700;
                        color: var(--primary-color);
                        margin-bottom: var(--space-sm);
                        display: block;
                    }}

                    .metric-label {{
                        color: var(--text-secondary);
                        font-size: 0.95rem;
                        font-weight: 500;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}

                    .metric-card > div[style*="font-size: 0.8em"] {{
                        margin-top: var(--space-md);
                        padding-top: var(--space-md);
                        border-top: 1px solid var(--border-color);
                        font-size: 0.875rem !important;
                    }}

                    .chart-toggle-container {{
                        text-align: center;
                        margin-bottom: 15px;
                    }}

                    .chart-toggle-btn {{
                        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 0.9rem;
                        font-weight: 600;
                        transition: all 0.3s ease;
                        box-shadow: var(--shadow-sm);
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}

                    .chart-toggle-btn:hover {{
                        transform: translateY(-2px);
                        box-shadow: var(--shadow-md);
                    }}

                    .chart-toggle-btn:active {{
                        transform: translateY(0);
                    }}

                    .chart-toggle-btn.active {{
                        background: linear-gradient(135deg, var(--success-color) 0%, var(--accent-color) 100%);
                    }}

                    .chart-container {{
                        position: relative;
                        height: 400px;
                        margin: 30px 0;
                        background: white;
                        border-radius: 16px;
                        padding: 20px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        border: 1px solid var(--border-color);
                    }}

                    .location-efficiency-single-column {{
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                        margin: 30px 0;
                    }}

                    .location-efficiency-single-line {{
                        background: #f8f9fa;
                        border-radius: 16px;
                        padding: 20px;
                        border: 1px solid #e9ecef;
                        margin: 15px 0;
                        box-shadow: var(--shadow-sm);
                    }}

                    .location-single-line-content {{
                        display: grid;
                        grid-template-columns: 1fr 350px;
                        gap: 40px;
                        align-items: flex-start;
                    }}

                    .location-chart-compact {{
                        position: relative;
                        height: 280px;
                        background: white;
                        border-radius: 12px;
                        padding: 15px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        width: 100%;
                        overflow: hidden;
                        margin-right: 20px;
                    }}

                    .location-stats-compact {{
                        display: flex;
                        flex-direction: column;
                        gap: 12px;
                        min-width: 350px;
                        max-width: 350px;
                        padding-left: 15px;
                        border-left: 1px solid #e9ecef;
                        background: var(--bg-primary);
                        padding: var(--space-lg);
                        border-radius: 12px;
                        box-shadow: var(--shadow-sm);
                        border: 1px solid var(--border-color);
                    }}

                    .location-chart-compact canvas {{
                        width: 100% !important;
                        height: 220px !important;
                        max-width: 100%;
                        display: block;
                    }}

                    .location-chart-compact .chart-toggle-container {{
                        margin-bottom: 10px;
                        text-align: center;
                    }}

                    .location-chart-compact .chart-toggle-btn {{
                        padding: 6px 12px;
                        font-size: 0.8em;
                    }}

                    .stat-row {{
                        display: flex;
                        align-items: flex-start;
                        gap: 10px;
                        padding: 8px 0;
                        border-bottom: 1px solid #e9ecef;
                        flex-wrap: wrap;
                    }}

                    .stat-row:last-child {{
                        border-bottom: none;
                    }}

                    .stat-label {{
                        font-weight: 600;
                        color: #495057;
                        min-width: 90px;
                        font-size: 0.9em;
                        flex-shrink: 0;
                    }}

                    .stat-value {{
                        font-weight: bold;
                        color: #2c3e50;
                        font-size: 0.95em;
                        flex-shrink: 0;
                    }}

                    .stat-comparison {{
                        font-size: 0.85em;
                        font-style: italic;
                        margin-left: 5px;
                        flex-shrink: 0;
                    }}

                    .location-chart-container {{
                        position: relative;
                        height: 350px;
                        margin: 20px 0;
                        background: white;
                        border-radius: 8px;
                        padding: 15px;
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
                        background: var(--bg-primary);
                        border-radius: 12px;
                        padding: var(--space-lg);
                        box-shadow: var(--shadow-md);
                        border: 1px solid var(--border-color);
                    }}

                    .location-efficiency-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                        gap: 30px;
                        margin: 30px 0;
                    }}

                    .location-efficiency-item {{
                        background: #f8f9fa;
                        border-radius: 8px;
                        padding: 20px;
                        border: 1px solid #e9ecef;
                    }}

                    table {{
                        width: 100%;
                        border-collapse: separate;
                        border-spacing: 0;
                        margin: 20px 0;
                        background: white;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        border: 1px solid var(--border-color);
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
                        font-size: 0.95rem;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}

                    tr:hover {{
                        background: #f8f9fa;
                    }}

                    tbody tr:last-child td {{
                        border-bottom: none;
                    }}

                    .progress-container {{
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        margin: 10px 0;
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
                        border-radius: 6px;
                        position: relative;
                        overflow: hidden;
                    }}

                    .progress-fill::after {{
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background: linear-gradient(
                            90deg,
                            transparent,
                            rgba(255,255,255,0.3),
                            transparent
                        );
                        animation: shimmer 2s infinite;
                    }}

                    @keyframes shimmer {{
                        0% {{ transform: translateX(-100%); }}
                        100% {{ transform: translateX(100%); }}
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

                    .two-column > div {{
                        background: var(--bg-secondary);
                        padding: var(--space-lg);
                        border-radius: 12px;
                        border: 1px solid var(--border-color);
                    }}

                    /* Universal Tooltip Styles */
                    .tooltip {{
                        position: relative;
                        display: inline-block;
                        cursor: help;
                        color: #3498db;
                        text-decoration: underline dotted;
                        text-underline-offset: 2px;
                    }}

                    .tooltip .tooltiptext {{
                        visibility: hidden;
                        width: 280px;
                        background-color: rgba(0, 0, 0, 0.95);
                        color: #fff;
                        text-align: left;
                        border-radius: 8px;
                        padding: 12px 15px;
                        position: absolute;
                        z-index: 99999;
                        bottom: calc(100% + 10px);
                        left: 50%;
                        transform: translateX(-50%);
                        opacity: 0;
                        transition: opacity 0.3s ease, visibility 0.3s ease;
                        font-size: 0.875rem;
                        line-height: 1.6;
                        box-shadow: 0 8px 16px rgba(0,0,0,0.4);
                        pointer-events: none;
                        white-space: normal;
                        word-wrap: break-word;
                    }}

                    .tooltip .tooltiptext::after {{
                        content: '';
                        position: absolute;
                        top: 100%;
                        left: 50%;
                        margin-left: -6px;
                        border-width: 6px;
                        border-style: solid;
                        border-color: rgba(0, 0, 0, 0.95) transparent transparent transparent;
                    }}

                    .tooltip:hover .tooltiptext {{
                        visibility: visible;
                        opacity: 1;
                    }}

                    /* Metric card tooltips - position relative to metric-value */
                    .metric-value .tooltip .tooltiptext {{
                        bottom: calc(100% + 15px);
                        width: 300px;
                    }}

                    /* Make sure containers allow overflow */
                    .container {{
                        overflow: visible !important;
                    }}

                    .metric-card {{
                        overflow: visible !important;
                        position: relative;
                    }}

                    section {{
                        overflow: visible !important;
                    }}

                    table {{
                        overflow: visible !important;
                    }}

                    .map-section {{
                        overflow: visible !important;
                    }}

                    /* Prevent table overflow from hiding tooltips */
                    table {{
                        width: 100%;
                        border-collapse: separate;
                        border-spacing: 0;
                        margin: 20px 0;
                        background: white;
                        border-radius: 12px;
                        overflow: visible;  /* Changed from hidden */
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        border: 1px solid var(--border-color);
                    }}

                    tbody, thead {{
                        overflow: visible;
                    }}

                    tr {{
                        overflow: visible;
                    }}

                    td {{
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #e9ecef;
                        color: var(--text-primary);
                        position: relative;
                        overflow: visible;
                    }}

                    /* For tooltips that might overflow off-screen */
                    .metric-card .tooltip .tooltiptext {{
                        left: auto;
                        right: -10px;
                        margin-left: 0;
                        bottom: 100%;
                        margin-bottom: 10px;
                    }}

                    .metric-card .tooltip .tooltiptext::after {{
                        left: auto;
                        right: 20px;
                        margin-left: 0;
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
                        .chart-row, .two-column, .location-efficiency-grid, .location-single-line-content {{
                            grid-template-columns: 1fr;
                        }}

                        .location-chart-compact {{
                            height: 220px;
                            margin-bottom: 15px;
                        }}

                        .location-stats-compact {{
                            min-width: unset;
                            max-width: unset;
                        }}

                        .stat-label {{
                            min-width: 80px;
                            font-size: 0.85em;
                        }}

                        .stat-value {{
                            font-size: 0.9em;
                        }}

                        .stat-comparison {{
                            font-size: 0.8em;
                            margin-left: 3px;
                        }}

                        .container {{
                            padding: 15px;
                        }}

                        .progress-bar {{
                            width: 40%;
                        }}
                    }}

                    @media (max-width: 1024px) and (min-width: 769px) {{
                        .location-single-line-content {{
                            grid-template-columns: 1fr 320px;
                            gap: 20px;
                        }}

                        .location-stats-compact {{
                            min-width: 320px;
                            max-width: 320px;
                        }}

                        .stat-label {{
                            min-width: 85px;
                        }}
                    }}

                    .health-score-container {{
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 30px;
                        margin: 20px 0;
                        align-items: center;
                    }}

                    .health-pentagon {{
                        position: relative;
                        width: 300px;
                        height: 300px;
                        margin: 0 auto;
                    }}

                    .health-details {{
                        display: flex;
                        flex-direction: column;
                        gap: 15px;
                    }}

                    .health-component {{
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}

                    .health-component-label {{
                        min-width: 140px;
                        font-weight: 600;
                        color: #495057;
                    }}

                    .health-component-bar {{
                        flex: 1;
                        height: 20px;
                        background: #e9ecef;
                        border-radius: 10px;
                        overflow: hidden;
                        position: relative;
                    }}

                    .health-component-fill {{
                        height: 100%;
                        transition: width 0.3s ease;
                        border-radius: 10px;
                    }}

                    .health-excellent {{ background: linear-gradient(90deg, #28a745, #20c997); }}
                    .health-good {{ background: linear-gradient(90deg, #17a2b8, #3498db); }}
                    .health-fair {{ background: linear-gradient(90deg, #ffc107, #f39c12); }}
                    .health-poor {{ background: linear-gradient(90deg, #dc3545, #c0392b); }}

                    .health-component-value {{
                        min-width: 50px;
                        text-align: right;
                        font-weight: bold;
                        color: #2c3e50;
                    }}

                    .utilization-breakdown {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 15px;
                        margin: 20px 0;
                    }}

                    .utilization-card {{
                        background: #f8f9fa;
                        border: 1px solid #e9ecef;
                        border-radius: 8px;
                        padding: 15px;
                        text-align: center;
                    }}

                    .utilization-label {{
                        font-size: 0.9em;
                        color: #6c757d;
                        margin-bottom: 8px;
                    }}

                    .utilization-value {{
                        font-size: 1.5em;
                        font-weight: bold;
                        color: #2c3e50;
                    }}

                    .utilization-bar-container {{
                        margin-top: 10px;
                        height: 8px;
                        background: #e9ecef;
                        border-radius: 4px;
                        overflow: hidden;
                    }}

                    .utilization-bar-fill {{
                        height: 100%;
                        transition: width 0.3s ease;
                    }}

                    .working-time {{ background: #28a745; }}
                    .idle-time {{ background: #ffc107; }}
                    .charging-time {{ background: #17a2b8; }}
                    .downtime {{ background: #dc3545; }}

                    @media (max-width: 768px) {{
                        .health-score-container {{
                            grid-template-columns: 1fr;
                        }}

                        .health-pentagon {{
                            width: 250px;
                            height: 250px;
                        }}
                    }}

                    .white-text {{
                        color: white !important;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>{config.report_name or 'Robot Performance Report'}</h1>
                    <p class="subtitle">{content.get('period', 'Latest Period')}</p>
                    {''.join(sections)}
                </div>
                {self._generate_javascript(chart_js_data, content.get('robot_health_scores', {}), content.get('individual_robots', []))}
            </body>
            </html>"""

            return html_content

        except Exception as e:
            import traceback
            logger.error(f"Error generating report: {traceback.format_exc()}")
            return f"""<!DOCTYPE html>
            <html><head><title>Error</title></head>
            <body><h1>Report Generation Error</h1><p>{str(e)}</p></body></html>
            """

    def _generate_highlights_and_recommendations(self, content: Dict[str, Any]) -> str:
        """Generate data-driven highlights based on period comparisons"""
        comparisons = content.get('period_comparisons', {})
        task_data = content.get('task_performance', {})
        fleet_data = content.get('fleet_performance', {})
        cost_data = content.get('cost_analysis', {})

        highlights = []

        # Helper to parse comparison value
        def parse_comparison(comp_str):
            """Parse comparison string like '+2.5%' or '-1.2 hrs' to numeric value"""
            if comp_str == 'N/A' or not comp_str:
                return None
            try:
                # Remove units and convert to float
                numeric_part = comp_str.replace('%', '').replace('$', '').replace(',', '')
                numeric_part = numeric_part.split()[0]  # Take first part before units
                return float(numeric_part)
            except:
                return None

        # Coverage efficiency
        coverage_comp = parse_comparison(comparisons.get('coverage_efficiency', 'N/A'))
        if coverage_comp is not None:
            if coverage_comp > 0:
                highlights.append(f"Cleaning coverage increased by {abs(coverage_comp):.1f}%, suggesting improved cleaning performance")
            elif coverage_comp < 0:
                highlights.append(f"Cleaning coverage decreased by {abs(coverage_comp):.1f}%")

        # Running hours per robot
        avg_hours_comp = parse_comparison(comparisons.get('avg_daily_running_hours_per_robot', 'N/A'))
        if avg_hours_comp is not None:
            if avg_hours_comp > 0:
                highlights.append(f"Average daily runtime increased by {abs(avg_hours_comp):.1f} hrs/robot")
            elif avg_hours_comp < 0:
                highlights.append(f"Average daily runtime decreased by {abs(avg_hours_comp):.1f} hrs/robot")

        # Charging sessions (frequency change)
        charging_comp = parse_comparison(comparisons.get('charging_sessions', 'N/A'))
        if charging_comp is not None:
            if abs(charging_comp) >= 10:  # Only mention if significant change
                if charging_comp > 0:
                    highlights.append(f"Charging frequency increased by {abs(charging_comp):.0f} sessions, indicating higher operational activity")
                elif charging_comp < 0:
                    highlights.append(f"Charging frequency decreased by {abs(charging_comp):.0f} sessions")

        # Task completion rate
        completion_comp = parse_comparison(comparisons.get('completion_rate', 'N/A'))
        if completion_comp is not None:
            if completion_comp > 0:
                highlights.append(f"Task completion rate improved by {abs(completion_comp):.1f}%")
            elif completion_comp < 0:
                highlights.append(f"Task completion rate declined by {abs(completion_comp):.1f}%")

        # Savings
        savings_comp = parse_comparison(comparisons.get('savings', 'N/A'))
        if savings_comp is not None:
            if savings_comp > 0:
                highlights.append(f"Cost savings increased by ${abs(savings_comp):,.0f}, demonstrating growing operational efficiency")
            elif savings_comp < 0:
                highlights.append(f"Cost savings decreased by ${abs(savings_comp):,.0f}")

        # Area cleaned
        area_comp = parse_comparison(comparisons.get('total_area_cleaned', 'N/A'))
        if area_comp is not None:
            if area_comp > 0:
                highlights.append(f"Total area cleaned expanded by {abs(area_comp):,.0f} sq ft")
            elif area_comp < 0:
                highlights.append(f"Total area cleaned reduced by {abs(area_comp):,.0f} sq ft")

        # Energy efficiency (area per kWh)
        # Note: This is in resource_data but not in comparisons, so we'll skip unless it's critical

        # If no highlights generated, provide generic summary
        if not highlights:
            highlights.append(f"Processed {task_data.get('total_tasks', 0)} tasks with {task_data.get('completion_rate', 0):.1f}% completion rate")
            highlights.append(f"Achieved {fleet_data.get('total_running_hours', 0):.1f} total running hours across fleet")
            highlights.append(f"Realized ${cost_data.get('savings', 0):,.0f} in operational savings")

        return highlights

    def _generate_executive_summary(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate executive summary section with Individual Robot Performance merged in"""
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

        # Generate robot performance table with NEW COLUMNS including health score
        robot_rows = ""
        if individual_robots:
            robot_health_scores = content.get('robot_health_scores', {})

            for robot in individual_robots[:10]:
                # Extract all values first
                robot_id = robot.get('robot_id', 'Unknown')
                location = robot.get('location', 'Unknown Location')
                total_tasks = robot.get('total_tasks', 0)
                tasks_completed = robot.get('tasks_completed', 0)
                total_area = robot.get('total_area_cleaned', 0)
                avg_coverage = robot.get('average_coverage', 0)
                days_tasks = robot.get('days_with_tasks', 0)
                running_hrs = robot.get('running_hours', 0)
                utilization = robot.get('utilization_score', robot.get('working_ratio', 0))

                # Get health data if available
                has_health_data = robot_health_scores and robot_id in robot_health_scores and len(robot_health_scores.get(robot_id, {})) > 0
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
                else:
                    health_score = 0
                    health_rating = 'N/A'
                    health_color = '#6c757d'

                # Build the row - using regular string concatenation to avoid f-string issues
                robot_rows += "<tr>"
                robot_rows += f"<td>{robot_id}</td>"
                robot_rows += f"<td>{location}</td>"
                robot_rows += f"<td>{total_tasks}</td>"
                robot_rows += f"<td>{tasks_completed}</td>"
                robot_rows += f"<td>{total_area:,.0f} sq ft</td>"
                robot_rows += f"<td>{avg_coverage:.1f}%</td>"
                robot_rows += f"<td>{days_tasks}</td>"
                robot_rows += f"<td>{running_hrs:.1f} hrs</td>"
                robot_rows += "<td>"
                robot_rows += f'<span class="tooltip">{utilization:.1f}%'
                robot_rows += '<span class="tooltiptext">Utilization = Working hours / Uptime hours × 100. Indicates how efficiently the robot\'s available time is being used for productive tasks.</span>'
                robot_rows += '</span>'
                robot_rows += "</td>"
                robot_rows += "<td>"
                if has_health_data and health_score > 0:
                    robot_rows += f'<span class="tooltip" style="color: {health_color}; font-weight: bold;">'
                    robot_rows += f'{health_score:.1f} ({health_rating})'
                    robot_rows += '<span class="tooltiptext">Overall health score (0-100) based on availability (40%), task success (20%), efficiency (20%), mode performance (10%), and battery health (10%).</span>'
                    robot_rows += '</span>'
                else:
                    robot_rows += '<span style="color: #6c757d;">N/A</span>'
                robot_rows += "</td>"
                robot_rows += "</tr>"

        if not robot_rows:
            robot_rows = '<tr><td colspan="10">No robot data available</td></tr>'

        roi_breakdown_rows = ""
        robot_roi_breakdown = cost_data.get('robot_roi_breakdown', {})
        if robot_roi_breakdown:
            for robot_sn, roi_data in robot_roi_breakdown.items():
                months = roi_data.get('months_elapsed', 0)
                investment = roi_data.get('investment', 0)
                savings = roi_data.get('savings', 0)
                roi_pct = roi_data.get('roi_percent', 0)

                roi_breakdown_rows += "<tr>"
                roi_breakdown_rows += f"<td>{robot_sn}</td>"
                roi_breakdown_rows += f"<td>{months}</td>"
                roi_breakdown_rows += f"<td>${investment:,.2f}</td>"
                roi_breakdown_rows += f"<td>${savings:,.2f}</td>"
                roi_breakdown_rows += f"<td>{roi_pct:.1f}%</td>"
                roi_breakdown_rows += "</tr>"

        if not roi_breakdown_rows:
            roi_breakdown_rows = '<tr><td colspan="5">No ROI breakdown data available</td></tr>'

        highlights = self._generate_highlights_and_recommendations(content)
        highlights_html = '<h3>🎯 Highlights and Recommendations</h3>\n<ul style="font-size: 1.1em; color: #2c3e50;">\n'
        for highlight in highlights:
            highlights_html += f'    <li>{highlight}</li>\n'
        highlights_html += '</ul>\n'

        # Base content always included
        base_html = f"""
        <section id="executive-summary">
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
                    <div class="metric-value tooltip">{format_value(resource_data.get('total_area_cleaned_sqft', 0))}
                        <span class="tooltiptext">Total area cleaned in square feet, converted from actual_area field in task data (originally in square meters).</span>
                    </div>
                    <div class="metric-label">Sq Ft Cleaned</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('total_area_cleaned', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('total_area_cleaned', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(task_data.get('coverage_efficiency', 0), '%', 'percent')}
                        <span class="tooltiptext">Coverage efficiency calculated as (actual area cleaned / planned area) × 100 from task performance data.</span>
                    </div>
                    <div class="metric-label">Coverage</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('coverage_efficiency', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('coverage_efficiency', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{format_value(fleet_data.get('total_running_hours', 0))}
                        <span class="tooltiptext">Total running hours from all robots during the reporting period, calculated from task duration data.</span>
                    </div>
                    <div class="metric-label">Total Running Hours</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('running_hours', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('running_hours', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{fleet_data.get('avg_daily_running_hours_per_robot', 0):.1f}
                        <span class="tooltiptext">Average daily running hours per robot calculated as the average of daily running hours of each robot on days when the robot had at least 1 task.</span>
                    </div>
                    <div class="metric-label">Avg Daily Running Hours per Robot (hrs/robot)</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('avg_daily_running_hours_per_robot', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('avg_daily_running_hours_per_robot', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{days_ratio}
                        <span class="tooltiptext">Days with tasks out of total reporting period days. Shows actual operational days vs total period length.</span>
                    </div>
                    <div class="metric-label">Days with Tasks</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('days_with_tasks', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('days_with_tasks', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">{cost_data.get('hours_saved', 0):.1f} hrs
                        <span class="tooltiptext">Hours saved compared to manual cleaning, calculated from area cleaned and human cleaning speed benchmarks.</span>
                    </div>
                    <div class="metric-label">Hours Saved vs Manual</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('hours_saved', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('hours_saved', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">${cost_data.get('savings', 0):,.0f}
                        <span class="tooltiptext">Savings realized from robot operations compared to manual cleaning costs.</span>
                    </div>
                    <div class="metric-label">Savings Realized</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('savings', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('savings', 'N/A'))}
                    </div>
                </div>
            </div>
            {highlights_html}
        """

        # Conditional content
        robot_performance_html = ""
        if detail_level in ['detailed', 'in-depth']:
            robot_performance_html = f"""
            <h3>🤖 Individual Robot Performance</h3>
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
        return base_html + robot_performance_html + roi_breakdown_html  + "</section>"

    def _generate_task_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate task performance section with location-based efficiency charts and task patterns"""
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
        <section id="task-performance">
            <h2>📋 Task & Schedule Performance</h2>

            <h3>Task Management Efficiency</h3>
            <p>Task tracking across all facilities: {task_data.get('total_tasks', 0)} total tasks with {task_data.get('total_area_cleaned', 0):,.0f} sq ft total coverage and {avg_duration:.1f} minutes average task duration.</p>

            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Total</th>
                        <th>Completed</th>
                        <th>Task Completion Rate</th>
                        <th>Average Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>All Facilities</strong></td>
                        <td>{task_data.get('total_tasks', 0)}</td>
                        <td>{task_data.get('completed_tasks', 0)}</td>
                        <td>
                            <span class="tooltip">{task_data.get('completion_rate', 0):.1f}%
                                <span class="tooltiptext">Task completion rate calculated as (completed tasks / total tasks) × 100.</span>
                            </span>
                            <span style="color: {get_comparison_color(comparisons.get('completion_rate', 'N/A'))}; font-size: 0.8em; margin-left: 5px;">
                                (vs last: {format_comparison(comparisons.get('completion_rate', 'N/A'))})
                            </span>
                        </td>
                        <td>
                            <span class="tooltip">{avg_duration:.1f} min
                                <span class="tooltiptext">Average task duration calculated from actual task durations in the database.</span>
                            </span>
                            <span style="color: {get_comparison_color(comparisons.get('avg_duration', 'N/A'))}; font-size: 0.8em; margin-left: 5px;">
                                (vs last: {format_comparison(comparisons.get('avg_duration', 'N/A'))})
                            </span>
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
                                <div class="chart-toggle-container">
                                    <button class="chart-toggle-btn" onclick="toggleLocationView('{location_name.replace(' ', '_')}')" id="locationToggle_{location_name.replace(' ', '_')}">
                                        View Weekly Trend
                                    </button>
                                </div>
                                <canvas id="taskEfficiencyChart_{location_name.replace(' ', '_')}"></canvas>
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
        """Generate facility performance section with efficiency metrics and comparisons"""
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

        # Generate map-specific performance section
        map_sections = ""
        if detail_level != 'overview':
            if map_performance_by_building:
                map_sections = """
                    <h3>Map-Specific Performance</h3>
                    <div class="tooltip" style="margin-bottom: 15px;">
                        <span style="color: #3498db; text-decoration: underline dotted;">How these figures are calculated</span>
                        <span class="tooltiptext">Coverage: (actual area / planned area) × 100. Area Cleaned: sum of actual cleaned area converted to sq ft. Running Hours: sum of task durations converted from seconds. Power Efficiency: area cleaned / energy consumption. Time Efficiency: area cleaned / running hours. Water Efficiency: area cleaned / water consumption. Days with Tasks: unique dates when tasks occurred.</span>
                    </div>"""

                for building_name, maps in map_performance_by_building.items():
                    if maps and len(maps) > 0:
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
                            # IN-DEPTH: Full detailed with target performance
                            for map_data in maps:
                                map_name = map_data.get('map_name', 'Unknown Map')
                                coverage = map_data.get('coverage_percentage', 0)

                                # Get comparison data for this map
                                map_comp = map_comparisons.get(building_name, {}).get(map_name, {})
                                target_comp = map_comp.get('target_performance', {})

                                # Get target performance data
                                target_perf = map_data.get('target_performance')
                                targets = target_perf.get('targets', {}) if target_perf else {}

                                map_sections += f"""
                                    <div style="margin: 15px 0; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px;">
                                        <h5>{map_name}</h5>
                                        <div class="progress-container">
                                            <span>Coverage:</span>
                                            <div class="progress-bar">
                                                <div class="progress-fill" style="width: {min(coverage, 100)}%"></div>
                                            </div>
                                            <span class="progress-text">{coverage:.1f}%</span>
                                            <span style="color: {get_comparison_color(map_comp.get('coverage_percentage', 'N/A'))}; font-size: 0.8em; margin-left: 10px;">
                                                vs last: {format_comparison(map_comp.get('coverage_percentage', 'N/A'))}
                                            </span>
                                        </div>

                                        <!-- First row: Existing metrics -->
                                        <div class="map-metrics">
                                            <div class="map-metric">
                                                <div style="font-weight: bold;">{map_data.get('area_cleaned', 0):,.0f}</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">Area Cleaned (sq ft)</div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(map_comp.get('area_cleaned', 'N/A'))};">
                                                    vs last: {format_comparison(map_comp.get('area_cleaned', 'N/A'))}
                                                </div>
                                            </div>
                                            <div class="map-metric">
                                                <div style="font-weight: bold;">{map_data.get('running_hours', 0):.1f}</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">Running Hours</div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(map_comp.get('running_hours', 'N/A'))};">
                                                    vs last: {format_comparison(map_comp.get('running_hours', 'N/A'))}
                                                </div>
                                            </div>
                                            <div class="map-metric">
                                                <div style="font-weight: bold;">{map_data.get('time_efficiency', 0):.0f}</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">Time Efficiency (sq ft/hr)</div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(map_comp.get('time_efficiency', 'N/A'))};">
                                                    vs last: {format_comparison(map_comp.get('time_efficiency', 'N/A'))}
                                                </div>
                                            </div>
                                            <div class="map-metric">
                                                <div style="font-weight: bold;">{map_data.get('power_efficiency', 0):.0f}</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">Power Efficiency (sq ft/kWh)</div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(map_comp.get('power_efficiency', 'N/A'))};">
                                                    vs last: {format_comparison(map_comp.get('power_efficiency', 'N/A'))}
                                                </div>
                                            </div>
                                            <div class="map-metric">
                                                <div style="font-weight: bold;">{map_data.get('water_efficiency', 0):.1f}</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">Water Efficiency (sq ft/fl oz)</div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(map_comp.get('water_efficiency', 'N/A'))};">
                                                    vs last: {format_comparison(map_comp.get('water_efficiency', 'N/A'))}
                                                </div>
                                            </div>
                                            <div class="map-metric">
                                                <div style="font-weight: bold;">{map_data.get('days_with_tasks', 0)}</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">Days with Tasks</div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(map_comp.get('days_with_tasks', 'N/A'))};">
                                                    vs last: {format_comparison(map_comp.get('days_with_tasks', 'N/A'))}
                                                </div>
                                            </div>
                                        </div>"""

                                # NEW: Second row for target performance metrics (only if target data exists)
                                if target_perf:
                                    map_sections += """
                                        <!-- Second row: Target Performance Metrics -->
                                        <div class="map-metrics" style="margin-top: 10px; border-top: 2px solid #667eea; padding-top: 10px;">"""

                                    # Show efficiency compliance if target exists
                                    if targets.get('efficiency') is not None:
                                        eff_compliance = target_perf.get('efficiency_compliance_rate', 0)
                                        tasks_below_eff = target_perf.get('tasks_below_efficiency_target', 0)
                                        total_tasks = target_perf.get('total_tasks_analyzed', 0)
                                        # CONVERT: efficiency target from sqm/hr to sq ft/hr
                                        target_eff_sqft = targets['efficiency'] * 10.764

                                        map_sections += f"""
                                            <div class="map-metric" style="border-left: 3px solid #667eea;">
                                                <div style="font-weight: bold;">{eff_compliance:.1f}%</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">
                                                    Efficiency Compliance
                                                    <div style="font-size: 0.85em; color: #495057;">({tasks_below_eff}/{total_tasks} below {target_eff_sqft:.0f} sq ft/hr)</div>
                                                </div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(target_comp.get('efficiency_compliance_rate', 'N/A'))};">
                                                    vs last: {format_comparison(target_comp.get('efficiency_compliance_rate', 'N/A'))}
                                                </div>
                                            </div>"""

                                    # Show area compliance if target exists
                                    if targets.get('area_value') is not None or targets.get('area_percentage') is not None:
                                        area_compliance = target_perf.get('area_compliance_rate', 0)
                                        tasks_below_area = target_perf.get('tasks_below_area_target', 0)
                                        total_tasks = target_perf.get('total_tasks_analyzed', 0)

                                        if targets.get('area_value') is not None and targets.get('area_type').lower() == 'value':
                                            # CONVERT: area target from sqm to sq ft
                                            target_area_sqft = targets['area_value'] * 10.764
                                            target_desc = f"{target_area_sqft:.0f} sq ft"
                                        elif targets.get('area_percentage') is not None and targets.get('area_type').lower() == 'percentage':
                                            target_desc = f"{targets['area_percentage']:.0f}%"

                                        map_sections += f"""
                                            <div class="map-metric" style="border-left: 3px solid #667eea;">
                                                <div style="font-weight: bold;">{area_compliance:.1f}%</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">
                                                    Area Compliance
                                                    <div style="font-size: 0.85em; color: #495057;">({tasks_below_area}/{total_tasks} below {target_desc})</div>
                                                </div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(target_comp.get('area_compliance_rate', 'N/A'))};">
                                                    vs last: {format_comparison(target_comp.get('area_compliance_rate', 'N/A'))}
                                                </div>
                                            </div>"""

                                    # Show duration compliance if target exists
                                    if targets.get('duration_seconds') is not None:
                                        dur_compliance = target_perf.get('duration_compliance_rate', 0)
                                        tasks_exceeding = target_perf.get('tasks_exceeding_duration_target', 0)
                                        total_tasks = target_perf.get('total_tasks_analyzed', 0)
                                        target_minutes = targets['duration_seconds'] / 60

                                        map_sections += f"""
                                            <div class="map-metric" style="border-left: 3px solid #667eea;">
                                                <div style="font-weight: bold;">{dur_compliance:.1f}%</div>
                                                <div style="font-size: 0.8em; color: #6c757d;">
                                                    Duration Compliance
                                                    <div style="font-size: 0.85em; color: #495057;">({tasks_exceeding}/{total_tasks} exceed {target_minutes:.0f} min)</div>
                                                </div>
                                                <div style="font-size: 0.7em; color: {get_comparison_color(target_comp.get('duration_compliance_rate', 'N/A'))};">
                                                    vs last: {format_comparison(target_comp.get('duration_compliance_rate', 'N/A'))}
                                                </div>
                                            </div>"""

                                    map_sections += """
                                        </div>"""

                                map_sections += """
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

    def _generate_resource_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate resource utilization section with daily charts and vs Last Period"""
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

        # Conditional chart
        chart_html = ""
        if detail_level != 'overview':
            chart_html = """
            <div class="chart-container">
                <div class="chart-toggle-container">
                    <button class="chart-toggle-btn" onclick="toggleResourceView()" id="resourceToggle">
                        View Weekly Trend
                    </button>
                </div>
                <canvas id="resourceChart"></canvas>
            </div>
            """

        # Add robot health scores and utilization charts for in-depth reports
        robot_health_utilization = ""
        if detail_level == 'in-depth':
            robot_health_scores = content.get('robot_health_scores', {})
            individual_robots = content.get('individual_robots', [])

            # Only show health scores section if we have actual health score data for each robot
            if robot_health_scores and isinstance(robot_health_scores, dict) and len(robot_health_scores) > 0 and len([robot for robot in robot_health_scores.values() if len(robot) > 0]) > 0:
                robot_health_utilization = """
                <h3>🤖 Robot Health & Utilization Analysis</h3>
                <p>Comprehensive health and utilization metrics for each robot, including uptime/downtime analysis and component-level health scores.</p>
                <div style="margin: 20px 0;">
                """

                # Combine health scores with individual robot data
                for robot in individual_robots[:5]:  # Top 5 robots
                    robot_id = robot.get('robot_id', 'Unknown')
                    robot_name = robot.get('robot_name', robot_id)
                    health_data = robot_health_scores.get(robot_id, {})

                    if not health_data or len(health_data) == 0:
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

                    safe_robot_id = robot_id.replace('-', '_')

                    # Check if all 5 components are present
                    expected_components = ['Availability', 'Task Success', 'Efficiency', 'Mode Performance', 'Battery Health']
                    has_all_components = all(comp in component_scores and component_scores[comp] is not None for comp in expected_components)

                    robot_health_utilization += f"""
                    <div style="background: #f8f9fa; border-radius: 8px; padding: 25px; margin: 20px 0; border-left: 4px solid {rating_color};">
                        <h4 style="margin-top: 0; color: #2c3e50;">
                            Robot {robot_id} ({robot_name}) -
                            <span style="color: {rating_color};">Health Score: {overall_score:.1f} ({overall_rating})</span> |
                            <span style="color: #3498db;">Utilization: {utilization_score:.1f}%</span>
                        </h4>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 20px;">
                            <!-- Left side: Health radar and components -->
                            <div>
                                <h5 style="color: #2c3e50; margin-bottom: 15px;">Health Score Breakdown</h5>
                    """

                    if has_all_components:
                        # Show pentagon radar chart when all 5 components are present - LARGER SIZE
                        robot_health_utilization += f"""
                                <div class="health-score-container" style="display: flex; justify-content: center; align-items: center; min-height: 400px;">
                                    <div class="health-pentagon" style="width: 100%; max-width: 450px; height: 450px;">
                                        <canvas id="healthRadar_{safe_robot_id}" width="450" height="450"></canvas>
                                    </div>
                                </div>
                        """
                    else:
                        # Show text-based breakdown when components are missing
                        robot_health_utilization += """
                                <div class="health-details" style="margin-top: 0;">
                        """

                        # Add component bars
                        if component_scores and isinstance(component_scores, dict):
                            component_items = list(component_scores.items())

                            tooltip_texts = {
                                'Availability': 'Percentage of time robot is online and available (weight: 40%)',
                                'Task Success': 'Percentage of successfully completed tasks (weight: 20%)',
                                'Efficiency': 'Task efficiency score based on performance metrics (weight: 20%)',
                                'Mode Performance': 'Performance in different cleaning modes (sweeping/scrubbing) (weight: 10%)',
                                'Battery Health': 'Battery State of Health (SOH) percentage (weight: 10%)'
                            }

                            for component_name, component_score in component_items:
                                if component_score is None:
                                    continue

                                if component_score >= 90:
                                    comp_class = 'health-excellent'
                                elif component_score >= 80:
                                    comp_class = 'health-good'
                                elif component_score >= 60:
                                    comp_class = 'health-fair'
                                else:
                                    comp_class = 'health-poor'

                                tooltip_text = tooltip_texts.get(component_name, '')

                                robot_health_utilization += f"""
                                    <div class="health-component">
                                        <span class="health-component-label tooltip">{component_name}
                                            <span class="tooltiptext">{tooltip_text}</span>
                                        </span>
                                        <div class="health-component-bar">
                                            <div class="health-component-fill {comp_class}" style="width: {component_score}%"></div>
                                        </div>
                                        <span class="health-component-value">{component_score:.1f}</span>
                                    </div>
                                """

                        robot_health_utilization += """
                                </div>
                        """

                    robot_health_utilization += f"""
                            </div>

                            <!-- Right side: Utilization charts -->
                            <div>
                                <h5 style="color: #2c3e50; margin-bottom: 15px;">Time Distribution Analysis</h5>

                                <!-- Uptime vs Downtime Chart -->
                                <div style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); height: 150px;">
                                    <h6 style="margin: 0 0 10px 0; color: #495057; font-size: 0.9em;">Uptime vs Downtime</h6>
                                    <div style="height: 100px; position: relative;">
                                        <canvas id="uptimeChart_{safe_robot_id}"></canvas>
                                    </div>
                                </div>

                                <!-- Working vs Idle vs Charging Chart -->
                                <div style="background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); height: 170px;">
                                    <h6 style="margin: 0 0 10px 0; color: #495057; font-size: 0.9em;">Working vs Idle vs Charging</h6>
                                    <div style="height: 120px; position: relative;">
                                        <canvas id="workingIdleChart_{safe_robot_id}"></canvas>
                                    </div>
                                </div>

                                <!-- Time metrics summary -->
                                <div style="margin-top: 15px; padding: 15px; background: #e9ecef; border-radius: 5px;">
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9em;">
                                        <div><strong>Uptime:</strong> {uptime_hours:.1f} hrs ({uptime_hours_perc:.1f}%)</div>
                                        <div><strong>Downtime:</strong> {downtime_hours:.1f} hrs ({downtime_hours_perc:.1f}%)</div>
                                        <div><strong>Working:</strong> {working_hours:.1f} hrs ({working_hours_perc:.1f}%)</div>
                                        <div><strong>Idle:</strong> {idle_hours:.1f} hrs ({idle_hours_perc:.1f}%)</div>
                                        <div><strong>Charging:</strong> {charging_hours:.1f} hrs ({charging_hours_perc:.1f}%)</div>
                                        <div><strong>Utilization:</strong> {utilization_score:.1f}%</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """

                robot_health_utilization += """
                </div>
                """

        return f"""
        <section id="resource-utilization">
            <h2>⚡ Resource Utilization & Efficiency</h2>
            <h3>Resource Performance</h3>
            <p>Resource utilization: {resource_data.get('total_energy_consumption_kwh', 0):.2f} kWh total energy consumption, {resource_data.get('total_water_consumption_floz', 0):.0f} fl oz total water usage, {resource_data.get('area_per_kwh', 0):.0f} sq ft per kWh energy efficiency, and {resource_data.get('area_per_gallon', 0):.0f} sq ft per gallon water efficiency.</p>

            {chart_html}

            {facility_breakdown}

            {robot_health_utilization}
        </section>"""

    def _generate_financial_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate financial performance section with REAL calculated values and vs Last Period"""
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
        <section id="financial-performance">
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
                <p><strong>Chart Note:</strong> ROI trend shows daily cumulative values (not weekly averages, as ROI is cumulative by nature)</p>
            </div>
            """

        # Conditional chart
        chart_html = ""
        if detail_level != 'overview':
            chart_html = """
            <div class="chart-container">
                <div class="chart-toggle-container">
                    <button class="chart-toggle-btn" onclick="toggleFinancialView()" id="financialToggle">
                        View Weekly Trend
                    </button>
                </div>
                <canvas id="financialChart"></canvas>
            </div>
            """

        # Highlight box always
        highlight_html = f"""
            <div class="highlight-box">
                <h3 class="white-text">💡 Financial Impact Summary</h3>
                <div class="metrics-grid">
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('human_cost', 0))}</strong></div>
                        <div>Manual Cleaning Cost</div>
                        <div style="color: {get_comparison_color(comparisons.get('human_cost', 'N/A'), 'human_cost')}; font-size: 0.8em;">
                            vs last: {format_comparison(comparisons.get('human_cost', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('savings', 0))}</strong></div>
                        <div>Savings Realized</div>
                        <div style="color: {get_comparison_color(comparisons.get('savings', 'N/A'), 'savings')}; font-size: 0.8em;">
                            vs last: {format_comparison(comparisons.get('savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>{cost_data.get('hours_saved', 0):.1f} hrs</strong></div>
                        <div>Hours Saved vs Manual</div>
                        <div style="color: {get_comparison_color(comparisons.get('hours_saved', 'N/A'), 'hours_saved')}; font-size: 0.8em;">
                            vs last: {format_comparison(comparisons.get('hours_saved', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('annual_projected_savings', 0))}</strong></div>
                        <div>Annual Projected Savings</div>
                        <div style="color: {get_comparison_color(comparisons.get('annual_projected_savings', 'N/A'), 'annual_projected_savings')}; font-size: 0.8em;">
                            vs last: {format_comparison(comparisons.get('annual_projected_savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('cumulative_savings', 0))}</strong></div>
                        <div>Cumulative Savings</div>
                        <div style="color: {get_comparison_color(comparisons.get('cumulative_savings', 'N/A'), 'cumulative_savings')}; font-size: 0.8em;">
                            vs last: {format_comparison(comparisons.get('cumulative_savings', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>{cost_data.get('payback_period', 'N/A')}</strong></div>
                        <div>Payback Period</div>
                        <div style="color: {get_comparison_color(comparisons.get('payback_months', 'N/A'), 'payback_months')}; font-size: 0.8em;">
                            vs last: {format_comparison(comparisons.get('payback_months', 'N/A'))}
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5em; margin-bottom: 5px;"><strong>{safe_format(cost_data.get('monthly_savings_rate', 0), '$', '/month')}</strong></div>
                        <div>Monthly Savings Rate</div>
                        <div style="color: {get_comparison_color(comparisons.get('monthly_savings_rate', 'N/A'), 'monthly_savings_rate')}; font-size: 0.8em;">
                            vs last: {format_comparison(comparisons.get('monthly_savings_rate', 'N/A'))}
                        </div>
                    </div>
                </div>
                <p style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">
                    {cost_data.get('note', 'Financial calculations based on actual resource usage, lease model, and human cleaning speed benchmarks.')}
                </p>
            </div>

        </section>"""

        return base_html + chart_html + highlight_html

    def _generate_charging_section(self, content: Dict[str, Any], detail_level: str = 'in-depth') -> str:
        """Generate charging performance section with daily charts and median values + vs Last Period"""
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
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('median_charging_duration', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('median_charging_duration', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">+{charging_data.get('avg_power_gain_percent', 0):.1f}%
                        <span class="tooltiptext">Average power gain per charging session from database records.</span>
                    </div>
                    <div class="metric-label">Avg Power Gain per Session</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('avg_power_gain', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('avg_power_gain', 'N/A'))}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value tooltip">+{charging_data.get('median_power_gain_percent', 0):.1f}%
                        <span class="tooltiptext">Median power gain per charging session - represents typical power increase.</span>
                    </div>
                    <div class="metric-label">Median Power Gain per Session</div>
                    <div style="font-size: 0.8em; margin-top: 5px; color: {get_comparison_color(comparisons.get('median_power_gain', 'N/A'))};">
                        vs last period: {format_comparison(comparisons.get('median_power_gain', 'N/A'))}
                    </div>
                </div>
            </div>
        """

        # Conditional chart
        chart_html = ""
        if detail_level != 'overview':
            chart_html = """
            <div class="chart-container">
                <div class="chart-toggle-container">
                    <button class="chart-toggle-btn" onclick="toggleChargingView()" id="chargingToggle">
                        View Weekly Trend
                    </button>
                </div>
                <canvas id="chargingChart"></canvas>
            </div>
            """

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
                            <div style="font-size: 0.7em; color: {get_comparison_color(facility_comp.get('total_sessions', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('total_sessions', 'N/A'))}
                            </div>
                        </td>
                        <td>{charging_metrics.get('avg_duration_minutes', 0):.1f} min
                            <div style="font-size: 0.7em; color: {get_comparison_color(facility_comp.get('avg_charging_duration', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('avg_charging_duration', 'N/A'))}
                            </div>
                        </td>
                        <td>{charging_metrics.get('median_duration_minutes', 0):.1f} min
                            <div style="font-size: 0.7em; color: {get_comparison_color(facility_comp.get('median_charging_duration', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('median_charging_duration', 'N/A'))}
                            </div>
                        </td>
                        <td>+{charging_metrics.get('avg_power_gain_percent', 0):.1f}%
                            <div style="font-size: 0.7em; color: {get_comparison_color(facility_comp.get('avg_power_gain_facility', 'N/A'))};">
                                vs last: {format_comparison(facility_comp.get('avg_power_gain_facility', 'N/A'))}
                            </div>
                        </td>
                        <td>+{charging_metrics.get('median_power_gain_percent', 0):.1f}%
                            <div style="font-size: 0.7em; color: {get_comparison_color(facility_comp.get('median_power_gain_facility', 'N/A'))};">
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
        """Generate conclusion section with key numbers summary"""
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
        <section id="conclusion">
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

    def _generate_footer(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """Generate footer with metadata"""
        generation_time = content.get('generation_time', datetime.now())
        robots_count = content.get('robots_included', 0)

        return f"""
        <footer style="margin-top: 50px; padding-top: 20px; border-top: 2px solid #e9ecef; text-align: center; color: #7f8c8d;">
            <p><strong>{config.report_name or 'Robot Performance Report'}</strong><br>
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
                'trend_data': content.get('trend_data', {}),
                'event_type_by_location': content.get('event_type_by_location', {}),
                'event_location_mapping': content.get('event_location_mapping', {})
            }

            chart_data = self.chart_formatter.format_all_chart_data(metrics)
            # Add financial trend data for financial chart
            financial_trend_data = content.get('financial_trend_data', {})
            if financial_trend_data:
                chart_data['financial_trend_data'] = financial_trend_data

            # Add location efficiency data for location-specific charts
            daily_location_efficiency = content.get('daily_location_efficiency', {})
            if daily_location_efficiency:
                chart_data['daily_location_efficiency'] = daily_location_efficiency

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

    def _generate_javascript(self, chart_data: Dict[str, Any], robot_health_scores: Dict[str, Any] = None, individual_robots: List[Dict[str, Any]] = None) -> str:
        """Generate JavaScript for charts using real data with daily charts, weekly toggle, and location-specific charts"""
        if robot_health_scores is None:
            robot_health_scores = {}
        if individual_robots is None:
            individual_robots = []
        """Generate JavaScript for charts using real data with daily charts, weekly toggle, and location-specific charts"""
        # Get trend data for daily charts
        trend_data = chart_data.get('trend_data', {})
        dates = trend_data.get('dates', [])
        financial_trend_data = chart_data.get('financial_trend_data', {})
        daily_location_efficiency = chart_data.get('daily_location_efficiency', {})

        return f"""
    <script>
        // Store original daily data
        let originalData = {{
            dates: {json.dumps(dates)},
            charging_sessions: {json.dumps(trend_data.get('charging_sessions_trend', []))},
            charging_durations: {json.dumps(trend_data.get('charging_duration_trend', []))},
            energy_data: {json.dumps(trend_data.get('energy_consumption_trend', []))},
            water_data: {json.dumps(trend_data.get('water_usage_trend', []))},
            hours_saved: {json.dumps(financial_trend_data.get('hours_saved_trend', []))},
            savings_data: {json.dumps(financial_trend_data.get('savings_trend', []))},
            roi_data: {json.dumps(trend_data.get('roi_improvement_trend', []))}
        }};

        // Store location efficiency data
        let locationEfficiencyData = {json.dumps(daily_location_efficiency)};

        // Store chart instances
        let chartInstances = {{}};

        // Helper function to aggregate data by day of week
        function aggregateByDayOfWeek(dates, values) {{
            const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
            const dayTotals = new Array(7).fill(0);
            const dayCounts = new Array(7).fill(0);

            dates.forEach((dateStr, index) => {{
                if (values[index] !== undefined && values[index] !== null) {{
                    // Parse date (format: MM/DD)
                    const [month, day] = dateStr.split('/').map(Number);
                    const currentYear = new Date().getFullYear();
                    const date = new Date(currentYear, month - 1, day);
                    const dayOfWeek = (date.getDay() + 6) % 7; // Convert Sunday=0 to Monday=0

                    dayTotals[dayOfWeek] += values[index] || 0;
                    dayCounts[dayOfWeek]++;
                }}
            }});

            // Calculate averages
            const averages = dayTotals.map((total, index) =>
                dayCounts[index] > 0 ? Math.round((total / dayCounts[index]) * 100) / 100 : 0
            );

            return {{ labels: dayNames, data: averages }};
        }}

        // Common chart options for interactivity
        function getInteractiveChartOptions(yAxisTitle, y1AxisTitle) {{
            return {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    intersect: false,
                    mode: 'index'
                }},
                plugins: {{
                    tooltip: {{
                        enabled: true,
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'rgba(255,255,255,0.2)',
                        borderWidth: 1
                    }},
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: yAxisTitle
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: y1AxisTitle
                        }},
                        grid: {{
                            drawOnChartArea: false,
                        }},
                    }}
                }}
            }};
        }}

        // Toggle functions for global charts
        function toggleChargingView() {{
            const btn = document.getElementById('chargingToggle');
            const isWeekly = btn.textContent === 'View Daily Trend';

            if (isWeekly) {{
                btn.textContent = 'View Weekly Trend';
                btn.classList.remove('active');
                createChargingChart(originalData.dates, originalData.charging_sessions, originalData.charging_durations);
            }} else {{
                btn.textContent = 'View Daily Trend';
                btn.classList.add('active');

                const weeklySessions = aggregateByDayOfWeek(originalData.dates, originalData.charging_sessions);
                const weeklyDurations = aggregateByDayOfWeek(originalData.dates, originalData.charging_durations);

                createChargingChart(weeklySessions.labels, weeklySessions.data, weeklyDurations.data);
            }}
        }}

        function toggleResourceView() {{
            const btn = document.getElementById('resourceToggle');
            const isWeekly = btn.textContent === 'View Daily Trend';

            if (isWeekly) {{
                btn.textContent = 'View Weekly Trend';
                btn.classList.remove('active');
                createResourceChart(originalData.dates, originalData.energy_data, originalData.water_data);
            }} else {{
                btn.textContent = 'View Daily Trend';
                btn.classList.add('active');

                const weeklyEnergy = aggregateByDayOfWeek(originalData.dates, originalData.energy_data);
                const weeklyWater = aggregateByDayOfWeek(originalData.dates, originalData.water_data);

                createResourceChart(weeklyEnergy.labels, weeklyEnergy.data, weeklyWater.data);
            }}
        }}

        function toggleFinancialView() {{
            const btn = document.getElementById('financialToggle');
            const isWeekly = btn.textContent === 'View Daily Trend';

            if (isWeekly) {{
                btn.textContent = 'View Weekly Trend';
                btn.classList.remove('active');
                // ROI always shows daily cumulative data (no aggregation)
                createFinancialChart(
                    originalData.dates,
                    originalData.hours_saved,
                    originalData.savings_data,
                    originalData.roi_data
                );
            }} else {{
                btn.textContent = 'View Daily Trend';
                btn.classList.add('active');

                const weeklyHours = aggregateByDayOfWeek(originalData.dates, originalData.hours_saved);
                const weeklySavings = aggregateByDayOfWeek(originalData.dates, originalData.savings_data);

                // ROI remains daily — don’t aggregate by day of week as it doesn’t make sense
                createFinancialChart(
                    weeklyHours.labels,
                    weeklyHours.data,
                    weeklySavings.data,
                    [0, 0, 0, 0, 0, 0, 0] // ROI = 0 in weekly view
                );
            }}
        }}

        // Toggle function for location-specific charts
        function toggleLocationView(locationName) {{
            const btn = document.getElementById(`locationToggle_${{locationName}}`);
            if (!btn) {{
                console.error(`Button not found: locationToggle_${{locationName}}`);
                return;
            }}

            const isWeekly = btn.textContent === 'View Daily Trend';
            const actualLocationName = locationName.replace(/_/g, ' ');
            const locationData = locationEfficiencyData[actualLocationName];

            if (!locationData || !locationData.dates || !locationData.running_hours || !locationData.coverage_percentages) {{
                console.error(`Invalid data for location: ${{actualLocationName}}`, locationData);
                return;
            }}

            if (isWeekly) {{
                btn.textContent = 'View Weekly Trend';
                btn.classList.remove('active');
                createLocationChart(locationName, locationData.dates, locationData.running_hours, locationData.coverage_percentages);
            }} else {{
                btn.textContent = 'View Daily Trend';
                btn.classList.add('active');

                const weeklyHours = aggregateByDayOfWeek(locationData.dates, locationData.running_hours);
                const weeklyCoverage = aggregateByDayOfWeek(locationData.dates, locationData.coverage_percentages);

                createLocationChart(locationName, weeklyHours.labels, weeklyHours.data, weeklyCoverage.data);
            }}
        }}

        // Chart creation functions with full interactivity
        function createChargingChart(labels, sessions, durations) {{
            if (chartInstances.charging) {{
                chartInstances.charging.destroy();
            }}

            const ctx = document.getElementById('chargingChart');
            if (ctx) {{
                chartInstances.charging = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels.length > 0 ? labels : ['No Data'],
                        datasets: [{{
                            label: 'Charging Sessions',
                            data: sessions.length > 0 ? sessions : [0],
                            backgroundColor: 'rgba(23, 162, 184, 0.6)',
                            borderColor: 'rgba(23, 162, 184, 1)',
                            borderWidth: 1,
                            yAxisID: 'y'
                        }}, {{
                            label: 'Avg Duration (min)',
                            data: durations.length > 0 ? durations : [0],
                            type: 'line',
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            tension: 0.4,
                            yAxisID: 'y1',
                            pointBackgroundColor: '#e74c3c',
                            pointBorderColor: '#e74c3c',
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }}]
                    }},
                    options: getInteractiveChartOptions('Sessions', 'Duration (min)')
                }});
            }}
        }}

        function createResourceChart(labels, energy, water) {{
            if (chartInstances.resource) {{
                chartInstances.resource.destroy();
            }}

            const ctx = document.getElementById('resourceChart');
            if (ctx) {{
                chartInstances.resource = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels.length > 0 ? labels : ['No Data'],
                        datasets: [{{
                            label: 'Energy (kWh)',
                            data: energy.length > 0 ? energy : [0],
                            backgroundColor: 'rgba(231, 76, 60, 0.6)',
                            borderColor: 'rgba(231, 76, 60, 1)',
                            borderWidth: 1,
                            yAxisID: 'y'
                        }}, {{
                            label: 'Water (fl oz)',
                            data: water.length > 0 ? water : [0],
                            backgroundColor: 'rgba(52, 152, 219, 0.6)',
                            borderColor: 'rgba(52, 152, 219, 1)',
                            borderWidth: 1,
                            yAxisID: 'y1'
                        }}]
                    }},
                    options: getInteractiveChartOptions('Energy (kWh)', 'Water (fl oz)')
                }});
            }}
        }}

        function createFinancialChart(labels, hours, savings, roi) {{
            if (chartInstances.financial) {{
                chartInstances.financial.destroy();
            }}

            const ctx = document.getElementById('financialChart');
            if (ctx) {{
                chartInstances.financial = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: labels.length > 0 ? labels : ['No Data'],
                        datasets: [{{
                            label: 'Hours Saved',
                            data: hours.length > 0 ? hours : [0],
                            backgroundColor: 'rgba(40, 167, 69, 0.6)',
                            borderColor: 'rgba(40, 167, 69, 1)',
                            borderWidth: 1,
                            yAxisID: 'y'
                        }}, {{
                            label: 'Savings ($)',
                            data: savings.length > 0 ? savings : [0],
                            backgroundColor: 'rgba(23, 162, 184, 0.6)',
                            borderColor: 'rgba(23, 162, 184, 1)',
                            borderWidth: 1,
                            yAxisID: 'y1'
                        }}, {{
                            label: 'ROI (%) - Daily Cumulative',
                            data: roi.length > 0 ? roi : [0],
                            type: 'line',
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            tension: 0.4,
                            yAxisID: 'y2',
                            pointBackgroundColor: '#28a745',
                            pointBorderColor: '#28a745',
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {{
                            intersect: false,
                            mode: 'index'
                        }},
                        plugins: {{
                            tooltip: {{
                                enabled: true,
                                mode: 'index',
                                intersect: false,
                                backgroundColor: 'rgba(0,0,0,0.8)',
                                titleColor: 'white',
                                bodyColor: 'white',
                                borderColor: 'rgba(255,255,255,0.2)',
                                borderWidth: 1,
                                callbacks: {{
                                    afterLabel: function(context) {{
                                        return context.datasetIndex === 2
                                            ? 'Cumulative ROI based on all-time data'
                                            : '';
                                    }}
                                }}
                            }},
                            legend: {{
                                display: true,
                                position: 'top'
                            }}
                        }},
                        scales: {{
                            y: {{
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {{
                                    display: true,
                                    text: 'Hours Saved'
                                }}
                            }},
                            y1: {{
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {{
                                    display: true,
                                    text: 'Savings ($)'
                                }},
                                grid: {{
                                    drawOnChartArea: false
                                }}
                            }},
                            y2: {{
                                type: 'linear',
                                display: false,
                                position: 'right',
                                title: {{
                                    display: true,
                                    text: 'ROI (%)'
                                }},
                                grid: {{
                                    drawOnChartArea: false
                                }}
                            }}
                        }}
                    }}
                }});
            }}
        }}

        function createLocationChart(locationName, labels, runningHours, coverage) {{
            const chartKey = `taskEfficiency_${{locationName}}`;

            if (chartInstances[chartKey]) {{
                chartInstances[chartKey].destroy();
                delete chartInstances[chartKey];
            }}

            const ctx = document.getElementById(`taskEfficiencyChart_${{locationName}}`);
            if (!ctx) {{
                console.error(`Canvas not found: taskEfficiencyChart_${{locationName}}`);
                return;
            }}

            const validLabels = labels && labels.length > 0 ? labels : ['No Data'];
            const validHours = runningHours && runningHours.length > 0 ? runningHours : [0];
            const validCoverage = coverage && coverage.length > 0 ? coverage : [0];

            chartInstances[chartKey] = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: validLabels,
                    datasets: [{{
                        label: 'Running Hours',
                        data: validHours,
                        backgroundColor: 'rgba(52, 152, 219, 0.6)',
                        borderColor: 'rgba(52, 152, 219, 1)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    }}, {{
                        label: 'Coverage %',
                        data: validCoverage,
                        type: 'line',
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1',
                        pointBackgroundColor: '#e74c3c',
                        pointBorderColor: '#e74c3c',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: getInteractiveChartOptions('Running Hours', 'Coverage %')
            }});
        }}

        function createLocationTaskEfficiencyCharts() {{
            if (!locationEfficiencyData || Object.keys(locationEfficiencyData).length === 0) {{
                console.log('No locationEfficiencyData available');
                return;
            }}

            Object.keys(locationEfficiencyData).forEach(locationName => {{
                const locationData = locationEfficiencyData[locationName];
                const safeName = locationName.replace(/\s+/g, '_');

                if (locationData && locationData.dates && locationData.running_hours && locationData.coverage_percentages) {{
                    console.log(`Creating interactive chart for: ${{locationName}} (ID: ${{safeName}})`);
                    createLocationChart(safeName, locationData.dates, locationData.running_hours, locationData.coverage_percentages);
                }} else {{
                    console.error(`Invalid data structure for location: ${{locationName}}`, locationData);
                }}
            }});
        }}

        // Create health score radar charts
        function createHealthRadarCharts() {{
            const healthScores = {json.dumps(robot_health_scores)};

            Object.keys(healthScores).forEach(robotSn => {{
                const health = healthScores[robotSn];
                const safeId = robotSn.replace(/-/g, '_');
                const ctx = document.getElementById(`healthRadar_${{safeId}}`);

                if (ctx && health.component_scores) {{
                    new Chart(ctx, {{
                        type: 'radar',
                        data: {{
                            labels: Object.keys(health.component_scores),
                            datasets: [{{
                                label: 'Health Score',
                                data: Object.values(health.component_scores),
                                backgroundColor: 'rgba(52, 152, 219, 0.2)',
                                borderColor: 'rgba(52, 152, 219, 1)',
                                pointBackgroundColor: 'rgba(52, 152, 219, 1)',
                                pointBorderColor: '#fff',
                                pointHoverBackgroundColor: '#fff',
                                pointHoverBorderColor: 'rgba(52, 152, 219, 1)',
                                borderWidth: 2,
                                pointRadius: 4,
                                pointHoverRadius: 6
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: true,
                            scales: {{
                                r: {{
                                    beginAtZero: true,
                                    max: 100,
                                    ticks: {{
                                        stepSize: 20,
                                        callback: function(value) {{
                                            return value;
                                        }}
                                    }},
                                    pointLabels: {{
                                        font: {{
                                            size: 11
                                        }}
                                    }}
                                }}
                            }},
                            plugins: {{
                                legend: {{
                                    display: false
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(0,0,0,0.8)',
                                    titleColor: 'white',
                                    bodyColor: 'white',
                                    callbacks: {{
                                        label: function(context) {{
                                            return context.label + ': ' + context.parsed.r.toFixed(1);
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }} else {{
                    console.warn(`Health radar canvas not found or no data: healthRadar_${{safeId}}`);
                }}
            }});
        }}

        // Static charts with interactivity
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
                            text: 'Task Status Distribution'
                        }},
                        tooltip: {{
                            enabled: true,
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white'
                        }},
                        legend: {{
                            display: true,
                            position: 'bottom'
                        }}
                    }}
                }}
            }});
        }}

        const taskModeCtx = document.getElementById('taskModeChart');
        if (taskModeCtx) {{
            const taskModeData = {json.dumps(chart_data.get('taskModeChart', {}))};
            new Chart(taskModeCtx, {{
                type: 'pie',
                data: {{
                    labels: taskModeData.labels || ['No Data'],
                    datasets: [{{
                        data: taskModeData.data || [1],
                        backgroundColor: taskModeData.backgroundColor || ['#6c757d'],
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
                            text: 'Task Mode Distribution'
                        }},
                        tooltip: {{
                            enabled: true,
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white'
                        }},
                        legend: {{
                            display: true,
                            position: 'bottom'
                        }}
                    }}
                }}
            }});
        }}

        // Create uptime vs downtime charts
        function createUptimeCharts() {{
             const individualRobots = {json.dumps(individual_robots)};

            individualRobots.forEach(robot => {{
                const robotId = robot.robot_id;
                const safeId = robotId.replace(/-/g, '_');

                // Uptime vs Downtime chart
                const uptimeCtx = document.getElementById(`uptimeChart_${{safeId}}`);
                if (uptimeCtx) {{
                    new Chart(uptimeCtx, {{
                        type: 'bar',
                        data: {{
                            labels: ['Uptime', 'Downtime'],
                            datasets: [{{
                                label: 'Hours',
                                data: [robot.uptime_hours || 0, robot.downtime_hours || 0],
                                backgroundColor: ['#28a745', '#dc3545'],
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ display: false }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            return context.label + ': ' + context.parsed.x.toFixed(1) + ' hrs';
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                x: {{
                                    beginAtZero: true,
                                    title: {{ display: true, text: 'Hours' }}
                                }}
                            }}
                        }}
                    }});
                }}

                // Working vs Idle vs Charging chart
                const workingIdleCtx = document.getElementById(`workingIdleChart_${{safeId}}`);
                if (workingIdleCtx) {{
                    new Chart(workingIdleCtx, {{
                        type: 'bar',
                        data: {{
                            labels: ['Working', 'Idle', 'Charging'],
                            datasets: [{{
                                label: 'Hours',
                                data: [
                                    robot.working_hours || 0,
                                    robot.idle_hours || 0,
                                    robot.charging_hours || 0
                                ],
                                backgroundColor: ['#28a745', '#ffc107', '#17a2b8'],
                                borderWidth: 1
                            }}]
                        }},
                        options: {{
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ display: false }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            return context.label + ': ' + context.parsed.x.toFixed(1) + ' hrs';
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                x: {{
                                    beginAtZero: true,
                                    title: {{ display: true, text: 'Hours' }}
                                }}
                            }}
                        }}
                    }});
                }}
            }});
        }}

        // Initialize all charts when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('Initializing all charts...');
            console.log('LocationEfficiencyData:', locationEfficiencyData);

            // Global trend charts
            createChargingChart(originalData.dates, originalData.charging_sessions, originalData.charging_durations);
            createResourceChart(originalData.dates, originalData.energy_data, originalData.water_data);
            createFinancialChart(originalData.dates, originalData.hours_saved, originalData.savings_data, originalData.roi_data);

            // Location-specific charts
            createLocationTaskEfficiencyCharts();

            // Health score radar charts
            createHealthRadarCharts();

            // Uptime and utilization charts
            createUptimeCharts();

            console.log('All charts initialized');
        }});


    </script>"""

    def generate_report(self, content: Dict[str, Any], config: ReportConfig) -> str:
        """
        Legacy method for backward compatibility

        This method maintains compatibility with existing code that calls generate_report
        while internally using the enhanced comprehensive report generation logic.

        Args:
            content: Report content data structure
            config: Report configuration object

        Returns:
            str: Generated HTML report content
        """
        return self.generate_comprehensive_report(content, config)