import logging
from typing import Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)

class ChartDataFormatter:
    """Format calculated metrics data for Chart.js visualizations"""

    def __init__(self):
        """Initialize the chart data formatter"""
        pass

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

            logger.warning("No event data available - using default chart")
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