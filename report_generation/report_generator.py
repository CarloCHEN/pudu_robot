import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from jinja2 import Environment, FileSystemLoader
import pdfkit
import tempfile

from config.report_config import ReportConfiguration, ReportType, REPORT_CONTENT_CATALOG
from models.environment_models import EnvironmentData
from models.occupancy_models import OccupancyData
from models.consumable_models import ConsumableData
from models.task_models import TaskData
from models.insights_models import InsightsData
from processing.data_processor import DataProcessor
from .pdf_builder import PDFBuilder

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Main report generation class"""

    def __init__(self, template_dir: str = None):
        self.template_dir = template_dir or os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir))
        self.data_processor = DataProcessor()
        self.pdf_builder = PDFBuilder()

        # Configure wkhtmltopdf options
        self.wkhtmltopdf_options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }

    def generate_report(self, config: ReportConfiguration,
                       all_data: Dict[str, Any]) -> str:
        """Generate report based on configuration and data"""

        # Select appropriate template based on report type
        template_map = {
            ReportType.CLIENT: 'client_report.html',
            ReportType.PERFORMANCE: 'performance_report.html',
            ReportType.INTERNAL: 'internal_report.html'
        }

        template_name = template_map.get(config.report_type, 'client_report.html')
        template = self.jinja_env.get_template(template_name)

        # Process data based on selected content
        report_data = self._prepare_report_data(config, all_data)

        # Add metadata
        report_data['metadata'] = {
            'report_name': config.report_name,
            'report_type': config.report_type.value,
            'generated_date': datetime.now().strftime('%B %d, %Y'),
            'generated_time': datetime.now().strftime('%I:%M %p'),
            'time_range': config.time_range,
            'locations': self._format_locations(config.locations)
        }

        # Render HTML
        html_content = template.render(**report_data)

        # Generate PDF
        output_path = self._generate_pdf(html_content, config.report_name)

        logger.info(f"Report generated successfully: {output_path}")
        return output_path

    def _prepare_report_data(self, config: ReportConfiguration,
                           all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for report based on selected content"""

        report_data = {
            'sections': [],
            'has_insights': False,
            'has_environment': False,
            'has_occupancy': False,
            'has_consumables': False,
            'has_tasks': False,
            'has_robots': False,
            'has_financial': False
        }

        # Get content definitions
        selected_content = [c for c in REPORT_CONTENT_CATALOG if c.id in config.selected_content]

        # Group by category
        for content in selected_content:
            if content.category.value == 'insights':
                report_data['has_insights'] = True
                self._add_insights_section(report_data, content, all_data)
            elif content.category.value == 'environment':
                report_data['has_environment'] = True
                self._add_environment_section(report_data, content, all_data)
            elif content.category.value == 'occupancy':
                report_data['has_occupancy'] = True
                self._add_occupancy_section(report_data, content, all_data)
            elif content.category.value == 'consumable_waste':
                report_data['has_consumables'] = True
                self._add_consumables_section(report_data, content, all_data)
            elif content.category.value == 'task_management':
                report_data['has_tasks'] = True
                self._add_tasks_section(report_data, content, all_data)
            elif content.category.value == 'autonomous_equipment':
                report_data['has_robots'] = True
                self._add_robots_section(report_data, content, all_data)
            elif content.category.value == 'financial':
                report_data['has_financial'] = True
                self._add_financial_section(report_data, content, all_data)

        # Add summary statistics
        report_data['summary'] = self._generate_executive_summary(all_data, config)

        return report_data

    def _add_insights_section(self, report_data: Dict, content, all_data: Dict):
        """Add insights-related content to report"""
        insights_data: InsightsData = all_data.get('insights')
        if not insights_data:
            return

        section = {
            'id': content.id,
            'title': content.name,
            'type': 'insights',
            'data': {}
        }

        if content.id == 'problem-hotspots':
            hotspots = insights_data.get_top_hotspots(5)
            section['data'] = {
                'hotspots': [{
                    'location': str(h.location),
                    'alert_count': h.alert_count,
                    'critical_count': h.critical_count,
                    'priority_score': h.priority_score,
                    'trend': h.trend,
                    'top_issues': h.top_issues[:3]
                } for h in hotspots]
            }

        elif content.id == 'cleaning-priorities':
            priorities = [p for p in insights_data.cleaning_priorities if p.adjustment_needed][:10]
            section['data'] = {
                'priorities': [{
                    'location': str(p.location),
                    'score': round(p.priority_score, 1),
                    'current_frequency': p.current_frequency,
                    'recommended_frequency': p.recommended_frequency,
                    'factors': p.contributing_factors
                } for p in priorities]
            }

        elif content.id == 'work-performance':
            if 'tasks' in all_data:
                task_data: TaskData = all_data['tasks']
                section['data'] = {
                    'total_tasks': len(task_data.work_orders),
                    'completion_rate': 85.5,  # Would calculate from actual data
                    'avg_quality_score': 92.3,
                    'on_time_rate': 88.0
                }

        elif content.id == 'executive-summary' and insights_data.executive_summary:
            summary = insights_data.executive_summary
            section['data'] = {
                'key_achievements': summary.key_achievements[:5],
                'critical_issues': summary.critical_issues[:3],
                'cost_savings': f"${summary.cost_savings:,.0f}",
                'efficiency_improvement': f"{summary.efficiency_improvements:.1f}%"
            }

        report_data['sections'].append(section)

    def _add_environment_section(self, report_data: Dict, content, all_data: Dict):
        """Add environment-related content to report"""
        env_data: EnvironmentData = all_data.get('environment')
        if not env_data:
            return

        section = {
            'id': content.id,
            'title': content.name,
            'type': 'environment',
            'data': {}
        }

        if content.id == 'critical-conditions':
            critical_alerts = env_data.get_critical_alerts()[:10]
            section['data'] = {
                'alerts': [{
                    'location': str(a.location),
                    'parameter': a.category,
                    'value': a.value,
                    'threshold': a.threshold,
                    'message': a.message,
                    'timestamp': a.timestamp.strftime('%Y-%m-%d %H:%M')
                } for a in critical_alerts]
            }

        elif content.id == 'env-trends':
            # Generate trend data
            df = env_data.to_dataframe()
            if not df.empty:
                trends = self.data_processor.calculate_time_based_metrics(df, period='daily')
                section['data'] = {
                    'has_data': True,
                    'chart_data': self._prepare_chart_data(trends.get('daily', pd.DataFrame()))
                }

        report_data['sections'].append(section)

    def _add_occupancy_section(self, report_data: Dict, content, all_data: Dict):
        """Add occupancy-related content to report"""
        occ_data: OccupancyData = all_data.get('occupancy')
        if not occ_data:
            return

        section = {
            'id': content.id,
            'title': content.name,
            'type': 'occupancy',
            'data': {}
        }

        if content.id == 'people-distribution':
            peak_locations = occ_data.get_peak_locations(10)
            section['data'] = {
                'locations': peak_locations,
                'total_capacity': sum(p.max_capacity for p in occ_data.patterns),
                'utilization_metrics': occ_data.get_utilization_metrics()
            }

        elif content.id == 'occupancy-insights':
            insights = occ_data.insights[:5]
            section['data'] = {
                'insights': [{
                    'location': str(i.location),
                    'type': i.insight_type,
                    'description': i.description,
                    'impact': i.impact_score,
                    'action': i.recommended_action
                } for i in insights]
            }

        report_data['sections'].append(section)

    def _format_locations(self, locations: Dict[str, Any]) -> str:
        """Format location hierarchy for display"""
        parts = []
        if locations.get('country') and locations['country'] != 'All Countries':
            parts.append(locations['country'])
        if locations.get('city') and locations['city'] != 'All Cities':
            parts.append(locations['city'])
        if locations.get('building') and locations['building'] != 'All Buildings':
            parts.append(locations['building'])
        if locations.get('floor') and locations['floor'] != 'All Floors':
            parts.append(locations['floor'])

        return ' > '.join(parts) if parts else 'All Locations'

    def _generate_pdf(self, html_content: str, report_name: str) -> str:
        """Generate PDF from HTML content"""
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_html = f.name

        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = "".join(c for c in report_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_filename = f"{safe_name}_{timestamp}.pdf"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)

        try:
            # Generate PDF using wkhtmltopdf
            pdfkit.from_file(temp_html, output_path, options=self.wkhtmltopdf_options)
        finally:
            # Clean up temporary HTML file
            os.unlink(temp_html)

        return output_path

    def _prepare_chart_data(self, df: pd.DataFrame) -> Dict[str, List]:
        """Prepare data for chart rendering"""
        if df.empty:
            return {'labels': [], 'values': []}

        # Convert index to string labels
        labels = [str(idx) for idx in df.index]

        # Get the first numeric column
        if 'mean' in df.columns:
            values = df['mean'].tolist()
        else:
            values = df.iloc[:, 0].tolist()

        return {
            'labels': labels,
            'values': values
        }

    def _generate_executive_summary(self, all_data: Dict, config: ReportConfiguration) -> Dict[str, Any]:
        """Generate executive summary for the report"""
        summary = {
            'total_locations': len(config.locations),
            'reporting_period': config.time_range,
            'key_metrics': []
        }

        # Add key metrics from each data type
        if 'environment' in all_data:
            env_summary = self.data_processor.generate_summary_statistics(all_data['environment'])
            if 'avg_iaq_score' in env_summary:
                summary['key_metrics'].append({
                    'name': 'Air Quality Score',
                    'value': f"{env_summary['avg_iaq_score']:.1f}",
                    'unit': 'points'
                })

        if 'tasks' in all_data:
            task_summary = self.data_processor.generate_summary_statistics(all_data['tasks'])
            if 'completion_rate' in task_summary:
                summary['key_metrics'].append({
                    'name': 'Task Completion Rate',
                    'value': f"{task_summary['completion_rate']:.1f}",
                    'unit': '%'
                })

        return summary

    def _add_consumables_section(self, report_data: Dict, content, all_data: Dict):
        """Add consumables-related content to report"""
        # Implementation similar to other sections
        pass

    def _add_tasks_section(self, report_data: Dict, content, all_data: Dict):
        """Add tasks-related content to report"""
        # Implementation similar to other sections
        pass

    def _add_robots_section(self, report_data: Dict, content, all_data: Dict):
        """Add robots-related content to report"""
        # Implementation similar to other sections
        pass

    def _add_financial_section(self, report_data: Dict, content, all_data: Dict):
        """Add financial-related content to report"""
        # Implementation similar to other sections
        pass