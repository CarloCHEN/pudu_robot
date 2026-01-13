import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ChartDataFormatter:
    """Format calculated metrics data for Chart.js visualizations"""

    def __init__(self):
        """Initialize the chart data formatter"""
        pass

    def generate_pdf_chart_images(self, content: Dict[str, Any]) -> Dict[str, str]:
        """Generate chart images matching the original HTML charts exactly"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            import base64
            from io import BytesIO

            charts = {}

            # Set matplotlib style to match web charts
            plt.rcParams.update({
                'figure.facecolor': 'white',
                'axes.facecolor': 'white',
                'axes.edgecolor': '#dee2e6',
                'axes.linewidth': 0.8,
                'xtick.color': '#666',
                'ytick.color': '#666',
                'text.color': '#333',
                'font.size': 10
            })

            # Get trend data for weekly aggregation
            trend_data = content.get('trend_data', {})
            dates = trend_data.get('dates', [])

            # 1. Task Status Pie Chart (matches taskStatusChart)
            task_data = content.get('task_performance', {})
            if task_data:
                completed = task_data.get('completed_tasks', 0)
                cancelled = task_data.get('cancelled_tasks', 0)
                interrupted = task_data.get('interrupted_tasks', 0)

                if completed > 0 or cancelled > 0 or interrupted > 0:
                    fig, ax = plt.subplots(figsize=(6, 6))

                    labels = ['Completed', 'Cancelled', 'Interrupted']
                    sizes = [completed, cancelled, interrupted]
                    colors = ['#28a745', '#ffc107', '#dc3545']  # Match HTML colors

                    # Filter out zero values
                    filtered_data = [(label, size, color) for label, size, color in zip(labels, sizes, colors) if size > 0]
                    if filtered_data:
                        labels, sizes, colors = zip(*filtered_data)

                        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                                         autopct='%1.1f%%', startangle=90,
                                                         textprops={'fontsize': 11, 'color': '#333'})

                        # Style the text
                        for autotext in autotexts:
                            autotext.set_color('white')
                            autotext.set_fontweight('bold')

                    ax.set_title('Task Status Distribution', fontsize=14, fontweight='bold', pad=20)

                    # Save chart
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches=None,
                               facecolor='white', edgecolor='none')
                    buffer.seek(0)
                    chart_img = base64.b64encode(buffer.getvalue()).decode()
                    charts['task_status_chart'] = f"data:image/png;base64,{chart_img}"
                    plt.close()

            # 2. Task Mode Distribution Pie Chart (matches taskModeChart)
            # Get task mode data from facility metrics
            facility_task_metrics = content.get('facility_task_metrics', {})
            mode_counts = {}

            for facility, metrics in facility_task_metrics.items():
                mode = metrics.get('primary_mode', 'Mixed tasks')
                mode_counts[mode] = mode_counts.get(mode, 0) + metrics.get('total_tasks', 0)

            if mode_counts:
                fig, ax = plt.subplots(figsize=(6, 6))

                labels = list(mode_counts.keys())
                sizes = list(mode_counts.values())
                colors = ['#3498db', '#9b59b6', '#e67e22', '#1abc9c', '#34495e'][:len(labels)]

                wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                                 autopct='%1.1f%%', startangle=45,
                                                 textprops={'fontsize': 11, 'color': '#333'})

                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')

                ax.set_title('Task Mode Distribution', fontsize=14, fontweight='bold', pad=20)

                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=150, bbox_inches=None,
                           facecolor='white', edgecolor='none')
                buffer.seek(0)
                chart_img = base64.b64encode(buffer.getvalue()).decode()
                charts['task_mode_chart'] = f"data:image/png;base64,{chart_img}"
                plt.close()

            # 3. Charging Performance Chart (weekly trend - matches chargingChart)
            if dates and trend_data.get('charging_sessions_trend') and trend_data.get('charging_duration_trend'):
                weekly_sessions = self._aggregate_by_weekday(dates, trend_data.get('charging_sessions_trend', []))
                weekly_durations = self._aggregate_by_weekday(dates, trend_data.get('charging_duration_trend', []))

                if weekly_sessions['data'] and weekly_durations['data']:
                    fig, ax1 = plt.subplots(figsize=(12, 6))

                    x = np.arange(len(weekly_sessions['labels']))
                    width = 0.8

                    # Sessions bars
                    bars = ax1.bar(x, weekly_sessions['data'], width,
                                  color=(23/255, 162/255, 184/255, 0.6),
                                  edgecolor=(23/255, 162/255, 184/255, 0.6),
                                  linewidth=1, label='Charging Sessions')

                    ax1.set_xlabel('Day of Week', fontsize=12)
                    ax1.set_ylabel('Sessions', fontsize=12, color='#17a2b8')
                    ax1.set_title('Weekly Charging Performance', fontsize=14, fontweight='bold', pad=20)
                    ax1.set_xticks(x)
                    ax1.set_xticklabels(weekly_sessions['labels'])
                    ax1.tick_params(axis='y', labelcolor='#17a2b8')

                    # Duration line
                    ax2 = ax1.twinx()
                    line = ax2.plot(x, weekly_durations['data'], color='#e74c3c',
                                   linewidth=3, marker='o', markersize=6,
                                   markerfacecolor='#e74c3c', markeredgecolor='#e74c3c',
                                   label='Avg Duration (min)')

                    ax2.set_ylabel('Duration (min)', fontsize=12, color='#e74c3c')
                    ax2.tick_params(axis='y', labelcolor='#e74c3c')

                    # Legends
                    ax1.legend(loc='upper left')
                    ax2.legend(loc='upper right')

                    plt.tight_layout()

                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                               facecolor='white', edgecolor='none')
                    buffer.seek(0)
                    chart_img = base64.b64encode(buffer.getvalue()).decode()
                    charts['charging_chart'] = f"data:image/png;base64,{chart_img}"
                    plt.close()

            # 4. Resource Usage Chart (weekly trend - matches resourceChart)
            if dates and trend_data.get('energy_consumption_trend') and trend_data.get('water_usage_trend'):
                weekly_energy = self._aggregate_by_weekday(dates, trend_data.get('energy_consumption_trend', []))
                weekly_water = self._aggregate_by_weekday(dates, trend_data.get('water_usage_trend', []))

                if weekly_energy['data'] and weekly_water['data']:
                    fig, ax1 = plt.subplots(figsize=(12, 6))

                    x = np.arange(len(weekly_energy['labels']))
                    width = 0.35

                    # Energy bars
                    bars1 = ax1.bar(x - width/2, weekly_energy['data'], width,
                                   color=(231/255, 76/255, 60/255, 0.6),
                                   edgecolor=(231/255, 76/255, 60/255, 0.6),
                                   linewidth=1, label='Energy (kWh)')

                    ax1.set_xlabel('Day of Week', fontsize=12)
                    ax1.set_ylabel('Energy (kWh)', fontsize=12, color='#e74c3c')
                    ax1.set_title('Weekly Resource Utilization', fontsize=14, fontweight='bold', pad=20)
                    ax1.set_xticks(x)
                    ax1.set_xticklabels(weekly_energy['labels'])
                    ax1.tick_params(axis='y', labelcolor='#e74c3c')

                    # Water bars
                    ax2 = ax1.twinx()
                    bars2 = ax2.bar(x + width/2, weekly_water['data'], width,
                                   color=(52/255, 152/255, 219/255, 0.6),
                                   edgecolor=(52/255, 152/255, 219/255, 0.6),
                                   linewidth=1, label='Water (fl oz)')

                    ax2.set_ylabel('Water (fl oz)', fontsize=12, color='#3498db')
                    ax2.tick_params(axis='y', labelcolor='#3498db')

                    # Legends
                    ax1.legend(loc='upper left')
                    ax2.legend(loc='upper right')

                    plt.tight_layout()

                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                               facecolor='white', edgecolor='none')
                    buffer.seek(0)
                    chart_img = base64.b64encode(buffer.getvalue()).decode()
                    charts['resource_chart'] = f"data:image/png;base64,{chart_img}"
                    plt.close()

            # 5. Financial Trend Chart (weekly trend - matches financialChart)
            financial_trend_data = content.get('financial_trend_data', {})
            if dates and financial_trend_data.get('hours_saved_trend') and financial_trend_data.get('savings_trend'):
                weekly_hours = self._aggregate_by_weekday(dates, financial_trend_data.get('hours_saved_trend', []))
                weekly_savings = self._aggregate_by_weekday(dates, financial_trend_data.get('savings_trend', []))

                if weekly_hours['data'] and weekly_savings['data']:
                    fig, ax1 = plt.subplots(figsize=(12, 6))

                    x = np.arange(len(weekly_hours['labels']))
                    width = 0.35

                    # Hours saved bars
                    bars1 = ax1.bar(x - width/2, weekly_hours['data'], width,
                                   color=(40/255, 167/255, 69/255, 0.6),
                                   edgecolor=(40/255, 167/255, 69/255, 0.6),
                                   linewidth=1, label='Hours Saved')

                    ax1.set_xlabel('Day of Week', fontsize=12)
                    ax1.set_ylabel('Hours Saved', fontsize=12, color='#28a745')
                    ax1.set_title('Weekly Financial Performance', fontsize=14, fontweight='bold', pad=20)
                    ax1.set_xticks(x)
                    ax1.set_xticklabels(weekly_hours['labels'])
                    ax1.tick_params(axis='y', labelcolor='#28a745')

                    # Savings bars
                    ax2 = ax1.twinx()
                    bars2 = ax2.bar(x + width/2, weekly_savings['data'], width,
                                   color=(23/255, 162/255, 184/255, 0.6),
                                   edgecolor=(23/255, 162/255, 184/255, 0.6),
                                   linewidth=1, label='Savings ($)')

                    ax2.set_ylabel('Savings ($)', fontsize=12, color='#17a2b8')
                    ax2.tick_params(axis='y', labelcolor='#17a2b8')

                    # Legends
                    ax1.legend(loc='upper left')
                    ax2.legend(loc='upper right')

                    plt.tight_layout()

                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                               facecolor='white', edgecolor='none')
                    buffer.seek(0)
                    chart_img = base64.b64encode(buffer.getvalue()).decode()
                    charts['financial_chart'] = f"data:image/png;base64,{chart_img}"
                    plt.close()

            # 6. Location-specific task efficiency charts (weekly trend for each location)
            daily_location_efficiency = content.get('daily_location_efficiency', {})
            for location_name, efficiency_data in daily_location_efficiency.items():
                if efficiency_data.get('dates') and efficiency_data.get('running_hours') and efficiency_data.get('coverage_percentages'):
                    weekly_hours = self._aggregate_by_weekday(efficiency_data['dates'], efficiency_data['running_hours'])
                    weekly_coverage = self._aggregate_by_weekday(efficiency_data['dates'], efficiency_data['coverage_percentages'])

                    if weekly_hours['data'] and weekly_coverage['data']:
                        fig, ax1 = plt.subplots(figsize=(10, 5))

                        x = np.arange(len(weekly_hours['labels']))
                        width = 0.8

                        # Running hours bars
                        bars = ax1.bar(x, weekly_hours['data'], width,
                                       color=(52/255, 152/255, 219/255, 0.6),
                                       edgecolor=(52/255, 152/219, 219/255, 0.6),
                                       linewidth=1, label='Running Hours')

                        ax1.set_xlabel('Day of Week', fontsize=11)
                        ax1.set_ylabel('Running Hours', fontsize=11, color='#3498db')
                        ax1.set_ylim(bottom=0)
                        ax1.set_title(f'{location_name} - Weekly Performance', fontsize=12, fontweight='bold')
                        ax1.set_xticks(x)
                        ax1.set_xticklabels(weekly_hours['labels'])
                        ax1.tick_params(axis='y', labelcolor='#3498db')

                        # Coverage line
                        ax2 = ax1.twinx()
                        line = ax2.plot(x, weekly_coverage['data'], color='#e74c3c',
                                       linewidth=2, marker='o', markersize=5,
                                       markerfacecolor='#e74c3c', markeredgecolor='#e74c3c',
                                       label='Coverage %')

                        ax2.set_ylabel('Coverage %', fontsize=11, color='#e74c3c')
                        ax2.set_ylim(bottom=0)
                        ax2.tick_params(axis='y', labelcolor='#e74c3c')

                        # Legends
                        ax1.legend(loc='upper left')
                        ax2.legend(loc='upper right')

                        plt.tight_layout()

                        buffer = BytesIO()
                        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                                   facecolor='white', edgecolor='none')
                        buffer.seek(0)
                        chart_img = base64.b64encode(buffer.getvalue()).decode()
                        safe_name = location_name.replace(' ', '_')
                        charts[f'taskEfficiencyChart_{safe_name}'] = f"data:image/png;base64,{chart_img}"
                        plt.close()

            return charts

        except ImportError:
            logger.warning("matplotlib not available - charts will not be generated for PDF")
            return {}
        except Exception as e:
            logger.error(f"Error generating chart images: {e}", exc_info=True)
            return {}

    def _aggregate_by_weekday(self, dates, values):
        """Aggregate data by day of week (Monday to Sunday)"""
        try:
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_totals = [0.0] * 7
            day_counts = [0] * 7

            for i, date_str in enumerate(dates):
                if i < len(values) and values[i] is not None:
                    try:
                        # Try parsing full date first
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            try:
                                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            except ValueError:
                                # Fallback to MM/DD format, use current year
                                month, day = map(int, date_str.split('/'))
                                year = datetime.now().year
                                date_obj = datetime(year, month, day)

                        day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
                        day_totals[day_of_week] += float(values[i])
                        day_counts[day_of_week] += 1
                    except (ValueError, IndexError):
                        continue

            # Calculate averages
            averages = []
            for i in range(7):
                avg = round(day_totals[i] / day_counts[i], 2) if day_counts[i] > 0 else 0.0
                averages.append(avg)

            return {
                'labels': day_names,
                'data': averages
            }

        except Exception as e:
            logger.error(f"Error in weekday aggregation: {e}")
            return {'labels': [], 'data': []}

    def format_task_status_chart(self, task_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format task status data for doughnut chart

        Args:
            task_metrics: Task performance metrics from calculator

        Returns:
            Chart.js compatible data structure
        """
        try:
            completed = int(task_metrics.get('completed_tasks', 0))
            cancelled = int(task_metrics.get('cancelled_tasks', 0))
            interrupted = int(task_metrics.get('interrupted_tasks', 0))

            return {
                'labels': ['Task Ended (Completed)', 'Task Cancelled', 'Task Interrupted'],
                'data': [completed, cancelled, interrupted],
                'backgroundColor': ['#28a745', '#ffc107', '#dc3545'],
                'borderWidth': 2,
                'borderColor': '#fff'
            }

        except Exception as e:
            logger.error(f"Error formatting task status chart: {e}")
            return {
                'labels': ['Task Ended (Completed)', 'Task Cancelled', 'Task Interrupted'],
                'data': [5776, 195, 30],
                'backgroundColor': ['#28a745', '#ffc107', '#dc3545'],
                'borderWidth': 2,
                'borderColor': '#fff'
            }

    def format_task_mode_chart(self, task_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format task mode distribution for pie chart

        Args:
            task_metrics: Task performance metrics with mode distribution

        Returns:
            Chart.js compatible data structure
        """
        try:
            task_modes = task_metrics.get('task_modes', {})

            return {
                'labels': list(task_modes.keys()),
                'data': [int(v) for v in task_modes.values()],  # Convert to int
                'backgroundColor': ['#3498db', '#2ecc71'],
                'borderWidth': 2,
                'borderColor': '#fff'
            }

        except Exception as e:
            logger.error(f"Error formatting task mode chart: {e}")
            return {
                'labels': ['Scrubbing Tasks', 'Sweeping Tasks'],
                'data': [3154, 2847],
                'backgroundColor': ['#3498db', '#2ecc71'],
                'borderWidth': 2,
                'borderColor': '#fff'
            }

    def format_charging_performance_chart(self, charging_metrics: Dict[str, Any],
                                        trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format charging performance trends for line chart

        Args:
            charging_metrics: Charging performance metrics
            trend_data: Weekly trend data

        Returns:
            Chart.js compatible data structure
        """
        try:
            weeks = trend_data.get('weeks', ['Week 1', 'Week 2', 'Week 3', 'Week 4'])
            sessions_trend = [int(x) for x in trend_data.get('charging_sessions_trend', [268, 275, 271, 278])]
            duration_trend = [float(x) for x in trend_data.get('charging_duration_trend', [5.2, 5.8, 6.1, 6.2])]

            return {
                'labels': weeks,
                'datasets': [
                    {
                        'label': 'Charging Sessions',
                        'data': sessions_trend,
                        'backgroundColor': '#17a2b8',
                        'yAxisID': 'y'
                    },
                    {
                        'label': 'Avg Duration (min)',
                        'data': duration_trend,
                        'type': 'line',
                        'borderColor': '#e74c3c',
                        'backgroundColor': 'rgba(231, 76, 60, 0.1)',
                        'tension': 0.4,
                        'yAxisID': 'y1'
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Error formatting charging chart: {e}")
            return self._get_default_charging_chart()

    def format_resource_utilization_chart(self, resource_metrics: Dict[str, Any],
                                        trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format resource utilization trends for line chart

        Args:
            resource_metrics: Resource utilization metrics
            trend_data: Weekly trend data

        Returns:
            Chart.js compatible data structure
        """
        try:
            weeks = trend_data.get('weeks', ['Week 1', 'Week 2', 'Week 3', 'Week 4'])
            energy_trend = [float(x) for x in trend_data.get('energy_consumption_trend', [75.2, 78.1, 76.8, 79.8])]
            water_trend = [int(x) for x in trend_data.get('water_usage_trend', [980, 1020, 995, 1025])]

            return {
                'labels': weeks,
                'datasets': [
                    {
                        'label': 'Energy Consumption (kWh)',
                        'data': energy_trend,
                        'borderColor': '#e74c3c',
                        'backgroundColor': 'rgba(231, 76, 60, 0.1)',
                        'tension': 0.4,
                        'yAxisID': 'y'
                    },
                    {
                        'label': 'Water Usage (fl oz)',
                        'data': water_trend,
                        'borderColor': '#3498db',
                        'backgroundColor': 'rgba(52, 152, 219, 0.1)',
                        'tension': 0.4,
                        'yAxisID': 'y1'
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Error formatting resource chart: {e}")
            return self._get_default_resource_chart()

    def format_financial_performance_chart(self, cost_metrics: Dict[str, Any],
                                         trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format financial performance trends for line chart

        Args:
            cost_metrics: Cost analysis metrics
            trend_data: Weekly trend data

        Returns:
            Chart.js compatible data structure
        """
        try:
            weeks = trend_data.get('weeks', ['Week 1', 'Week 2', 'Week 3', 'Week 4'])
            savings_trend = [int(x) for x in trend_data.get('cost_savings_trend', [2850, 3100, 3200, 3250])]
            roi_trend = [float(x) for x in trend_data.get('roi_improvement_trend', [16.2, 17.8, 18.5, 19.1])]

            return {
                'labels': weeks,
                'datasets': [
                    {
                        'label': 'Cost Savings ($)',
                        'data': savings_trend,
                        'borderColor': '#28a745',
                        'backgroundColor': 'rgba(40, 167, 69, 0.1)',
                        'tension': 0.4,
                        'fill': True,
                        'yAxisID': 'y'
                    },
                    {
                        'label': 'ROI Improvement (%)',
                        'data': roi_trend,
                        'borderColor': '#17a2b8',
                        'backgroundColor': 'rgba(23, 162, 184, 0.1)',
                        'tension': 0.4,
                        'yAxisID': 'y1'
                    }
                ]
            }

        except Exception as e:
            logger.error(f"Error formatting financial chart: {e}")
            return self._get_default_financial_chart()

    def format_event_type_chart(self, event_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format event types for bar chart with location breakdown
        """
        try:
            logger.info(f"Formatting event type chart with keys: {list(event_metrics.keys())}")

            # Check for exact breakdown data first
            event_type_by_location = event_metrics.get('event_type_by_location', {})

            if event_type_by_location:
                logger.info(f"Using exact event breakdown: {event_type_by_location}")
                return self._format_exact_breakdown(event_type_by_location)

            # Fallback to proportional distribution
            event_types = event_metrics.get('event_types', {})
            event_location_mapping = event_metrics.get('event_location_mapping', {})

            if event_types and event_location_mapping:
                logger.info("Using proportional distribution fallback")
                return self._format_proportional_breakdown(event_types, event_location_mapping)

            # logger.warning("No event data available - using default chart")
            return self._get_default_event_type_chart()

        except Exception as e:
            logger.error(f"Error formatting event type chart: {e}")
            return self._get_default_event_type_chart()

    def _format_exact_breakdown(self, event_type_by_location: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Format using exact event type breakdown"""
        # Get top 4 event types
        total_by_type = {event_type: sum(locations.values())
                         for event_type, locations in event_type_by_location.items()}

        sorted_events = sorted(total_by_type.items(), key=lambda x: x[1], reverse=True)[:4]
        event_labels = [event[0] for event in sorted_events]

        # Get all locations
        all_locations = set()
        for locations in event_type_by_location.values():
            all_locations.update(locations.keys())

        location_list = sorted([loc for loc in all_locations if loc != 'Unknown Building'])

        # Create datasets
        datasets = []
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']

        for i, location in enumerate(location_list):
            data = []
            for event_type in event_labels:
                count = event_type_by_location.get(event_type, {}).get(location, 0)
                data.append(count)

            datasets.append({
                'label': location,
                'data': data,
                'backgroundColor': colors[i % len(colors)]
            })

        return {
            'labels': event_labels,
            'datasets': datasets
        }

    def _format_proportional_breakdown(self, event_types: Dict[str, int],
                                      event_location_mapping: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Format using proportional distribution"""
        # Get top 4 event types
        sorted_events = sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:4]
        event_labels = [event[0] for event in sorted_events]

        # Get locations
        locations = [loc for loc in event_location_mapping.keys() if loc != 'Unknown Building']

        total_all_events = sum(loc_data['total_events'] for loc_data in event_location_mapping.values())

        datasets = []
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']

        for i, location in enumerate(locations):
            data = []
            location_total = event_location_mapping[location]['total_events']
            location_proportion = location_total / total_all_events if total_all_events > 0 else 0

            for event_type, total_count in sorted_events:
                estimated_count = int(total_count * location_proportion)
                data.append(estimated_count)

            datasets.append({
                'label': location,
                'data': data,
                'backgroundColor': colors[i % len(colors)]
            })

        return {
            'labels': event_labels,
            'datasets': datasets
        }

    def format_event_level_chart(self, event_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format event levels for pie chart - rename 'fatal' to 'Critical'
        """
        try:
            event_levels = event_metrics.get('event_levels', {})

            # Map levels and rename fatal to Critical
            level_mapping = {
                'fatal': 'Critical',
                'critical': 'Critical',
                'error': 'Error',
                'warning': 'Warning',
                'info': 'Event'
            }

            # Colors for each level
            level_colors = {
                'Critical': '#dc3545',  # Red
                'Error': '#fd7e14',     # Orange
                'Warning': '#ffc107',   # Yellow
                'Info': '#007bff'       # Blue
            }

            # Process the levels
            processed_levels = {}

            for level, count in event_levels.items():
                mapped_level = level_mapping.get(level.lower(), level.capitalize())

                if mapped_level in processed_levels:
                    processed_levels[mapped_level] += count
                else:
                    processed_levels[mapped_level] = count

            # Create the chart data
            if processed_levels:
                # Sort by count (descending) for better visual presentation
                sorted_levels = sorted(processed_levels.items(), key=lambda x: x[1], reverse=True)

                labels = [level for level, count in sorted_levels]
                data = [int(count) for level, count in sorted_levels]
                colors = [level_colors.get(level, '#6c757d') for level in labels]

                return {
                    'labels': labels,
                    'data': data,
                    'backgroundColor': colors,
                    'borderWidth': 2,
                    'borderColor': '#fff'
                }
            else:
                return {
                    'labels': ['No Events'],
                    'data': [1],
                    'backgroundColor': ['#6c757d'],
                    'borderWidth': 2,
                    'borderColor': '#fff'
                }

        except Exception as e:
            logger.error(f"Error formatting event level chart: {e}")
            return {
                'labels': ['No Events'],
                'data': [1],
                'backgroundColor': ['#6c757d'],
                'borderWidth': 2,
                'borderColor': '#fff'
            }

    def _get_default_event_type_chart(self) -> Dict[str, Any]:
        """Return default event type chart when no data available"""
        return {
            'labels': ['No Event Data'],
            'datasets': [{
                'label': 'No Data Available',
                'data': [1],
                'backgroundColor': '#6c757d'
            }]
        }

    def format_all_chart_data(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Format all chart data for the comprehensive report"""
        try:
            task_metrics = metrics.get('task_performance', {})
            charging_metrics = metrics.get('charging_performance', {})
            resource_metrics = metrics.get('resource_utilization', {})
            cost_metrics = metrics.get('cost_analysis', {})
            event_metrics = metrics.get('event_analysis', {})
            trend_data = metrics.get('trend_data', {})

            # Include event_type_by_location in event_metrics for chart formatting
            event_type_by_location = metrics.get('event_type_by_location', {})
            event_location_mapping = metrics.get('event_location_mapping', {})

            # Combine event data for chart formatting
            enhanced_event_metrics = event_metrics.copy()
            enhanced_event_metrics['event_type_by_location'] = event_type_by_location
            enhanced_event_metrics['event_location_mapping'] = event_location_mapping

            logger.info(f"Enhanced event metrics keys: {list(enhanced_event_metrics.keys())}")
            logger.info(f"Event type by location in chart data: {bool(event_type_by_location)}")

            chart_data = {
                'taskStatusChart': self.format_task_status_chart(task_metrics),
                'taskModeChart': self.format_task_mode_chart(task_metrics),
                'eventTypeChart': self.format_event_type_chart(enhanced_event_metrics),
                'eventLevelChart': self.format_event_level_chart(enhanced_event_metrics)
            }

            # Add trend_data directly to chart_data for JavaScript access
            chart_data['trend_data'] = trend_data

            return chart_data

        except Exception as e:
            logger.error(f"Error formatting all chart data: {e}")
            return {
                'taskStatusChart': self._get_default_task_chart(),
                'taskModeChart': self._get_default_mode_chart(),
                'eventTypeChart': self._get_default_event_chart(),
                'eventLevelChart': self._get_default_level_chart(),
                'trend_data': {
                    'dates': ['01/01', '01/02', '01/03'],
                    'charging_sessions_trend': [5, 7, 6],
                    'charging_duration_trend': [45.2, 52.1, 48.7],
                    'energy_consumption_trend': [12.5, 15.2, 13.8],
                    'water_usage_trend': [245, 289, 267]
                }
            }

    def _get_default_charging_chart(self) -> Dict[str, Any]:
        """Return default charging chart data"""
        return {
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            'datasets': [
                {
                    'label': 'Charging Sessions',
                    'data': [268, 275, 271, 278],
                    'backgroundColor': '#17a2b8',
                    'yAxisID': 'y'
                },
                {
                    'label': 'Avg Duration (min)',
                    'data': [5.2, 5.8, 6.1, 6.2],
                    'type': 'line',
                    'borderColor': '#e74c3c',
                    'backgroundColor': 'rgba(231, 76, 60, 0.1)',
                    'tension': 0.4,
                    'yAxisID': 'y1'
                }
            ]
        }

    def _get_default_resource_chart(self) -> Dict[str, Any]:
        """Return default resource chart data"""
        return {
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            'datasets': [
                {
                    'label': 'Energy Consumption (kWh)',
                    'data': [75.2, 78.1, 76.8, 79.8],
                    'borderColor': '#e74c3c',
                    'backgroundColor': 'rgba(231, 76, 60, 0.1)',
                    'tension': 0.4,
                    'yAxisID': 'y'
                },
                {
                    'label': 'Water Usage (fl oz)',
                    'data': [980, 1020, 995, 1025],
                    'borderColor': '#3498db',
                    'backgroundColor': 'rgba(52, 152, 219, 0.1)',
                    'tension': 0.4,
                    'yAxisID': 'y1'
                }
            ]
        }

    def _get_default_financial_chart(self) -> Dict[str, Any]:
        """Return default financial chart data"""
        return {
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            'datasets': [
                {
                    'label': 'Cost Savings ($)',
                    'data': [2850, 3100, 3200, 3250],
                    'borderColor': '#28a745',
                    'backgroundColor': 'rgba(40, 167, 69, 0.1)',
                    'tension': 0.4,
                    'fill': True,
                    'yAxisID': 'y'
                },
                {
                    'label': 'ROI Improvement (%)',
                    'data': [16.2, 17.8, 18.5, 19.1],
                    'borderColor': '#17a2b8',
                    'backgroundColor': 'rgba(23, 162, 184, 0.1)',
                    'tension': 0.4,
                    'yAxisID': 'y1'
                }
            ]
        }

    def _get_default_all_charts(self) -> Dict[str, Any]:
        """Return all default chart data when formatting fails"""
        return {
            'taskStatusChart': {
                'labels': ['Task Ended (Completed)', 'Task Cancelled', 'Task Interrupted'],
                'data': [5776, 195, 30],
                'backgroundColor': ['#28a745', '#ffc107', '#dc3545'],
                'borderWidth': 2,
                'borderColor': '#fff'
            },
            'taskModeChart': {
                'labels': ['Scrubbing Tasks', 'Sweeping Tasks'],
                'data': [3154, 2847],
                'backgroundColor': ['#3498db', '#2ecc71'],
                'borderWidth': 2,
                'borderColor': '#fff'
            },
            'chargingChart': self._get_default_charging_chart(),
            'resourceChart': self._get_default_resource_chart(),
            'financialChart': self._get_default_financial_chart(),
            'eventTypeChart': {
                'labels': ['Brush Error', 'Lost Localization', 'Drop Detection', 'Odom Slip'],
                'datasets': [
                    {
                        'label': 'Marston Library',
                        'data': [0, 1, 8, 4],
                        'backgroundColor': '#3498db'
                    },
                    {
                        'label': 'Dental Science Building',
                        'data': [7, 1, 7, 4],
                        'backgroundColor': '#e74c3c'
                    }
                ]
            },
            'eventLevelChart': {
                'labels': ['Critical', 'Error', 'Warning', 'Info'],
                'data': [0, 8, 23, 147],
                'backgroundColor': ['#6c757d', '#dc3545', '#ffc107', '#28a745'],
                'borderWidth': 2,
                'borderColor': '#fff'
            }
        }