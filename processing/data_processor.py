from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.base_models import Location, Alert, Metric
from models.environment_models import EnvironmentData
from models.occupancy_models import OccupancyData
from models.consumable_models import ConsumableData
from models.task_models import TaskData
from models.insights_models import InsightsData, ProblemHotspot, CleaningPriority


class DataProcessor:
    """Processes and aggregates data for reporting"""

    def __init__(self):
        self.location_hierarchy = ['country', 'city', 'building', 'floor', 'area']

    def aggregate_by_location(self, data: pd.DataFrame,
                            aggregation_level: str = 'building') -> pd.DataFrame:
        """Aggregate data by location hierarchy level"""
        if data.empty:
            return pd.DataFrame()

        # Determine grouping columns based on aggregation level
        level_index = self.location_hierarchy.index(aggregation_level)
        group_cols = self.location_hierarchy[:level_index + 1]

        # Group and aggregate
        available_cols = [col for col in group_cols if col in data.columns]
        if not available_cols:
            return data

        return data.groupby(available_cols).agg({
            'value': ['mean', 'min', 'max', 'std'],
            'timestamp': 'count'
        }).round(2)

    def calculate_trends(self, data: pd.DataFrame,
                        date_column: str = 'timestamp',
                        value_column: str = 'value') -> Dict[str, Any]:
        """Calculate trend information"""
        if data.empty or date_column not in data.columns or value_column not in data.columns:
            return {'trend': 'unknown', 'change_percentage': 0}

        # Sort by date
        data = data.sort_values(date_column)

        # Split into first half and second half
        mid_point = len(data) // 2
        first_half_avg = data[value_column].iloc[:mid_point].mean()
        second_half_avg = data[value_column].iloc[mid_point:].mean()

        # Calculate trend
        if second_half_avg > first_half_avg * 1.05:
            trend = 'up'
        elif second_half_avg < first_half_avg * 0.95:
            trend = 'down'
        else:
            trend = 'stable'

        # Calculate percentage change
        if first_half_avg != 0:
            change_percentage = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        else:
            change_percentage = 0

        return {
            'trend': trend,
            'change_percentage': round(change_percentage, 1),
            'current_value': round(data[value_column].iloc[-1], 2),
            'average_value': round(data[value_column].mean(), 2)
        }

    def identify_problem_hotspots(self, all_alerts: List[Alert],
                                top_n: int = 10) -> List[ProblemHotspot]:
        """Identify locations with most frequent issues"""
        if not all_alerts:
            return []

        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([{
            'location': str(alert.location),
            'severity': alert.severity,
            'category': alert.category,
            'timestamp': alert.timestamp
        } for alert in all_alerts])

        # Group by location
        location_stats = df.groupby('location').agg({
            'severity': 'count',
            'timestamp': 'max'
        }).rename(columns={'severity': 'total_count'})

        # Count by severity
        severity_counts = df.groupby(['location', 'severity']).size().unstack(fill_value=0)

        # Get top issues by location
        top_issues = df.groupby(['location', 'category']).size().reset_index(name='count')

        # Create hotspots
        hotspots = []
        for location in location_stats.nlargest(top_n, 'total_count').index:
            # Parse location string back to Location object
            parts = location.split(' > ')
            loc_obj = Location(
                country=parts[0] if len(parts) > 0 else '',
                city=parts[1] if len(parts) > 1 else '',
                building=parts[2] if len(parts) > 2 else '',
                floor=parts[3] if len(parts) > 3 else '',
                area=parts[4] if len(parts) > 4 else None
            )

            # Get top issues for this location
            loc_issues = top_issues[top_issues['location'] == location].nlargest(3, 'count')
            top_issue_list = [(row['category'], row['count']) for _, row in loc_issues.iterrows()]

            # Calculate trend (simplified - would be more sophisticated in production)
            recent_alerts = df[df['location'] == location].tail(20)
            older_alerts = df[df['location'] == location].head(20)

            if len(recent_alerts) > len(older_alerts):
                trend = 'increasing'
            elif len(recent_alerts) < len(older_alerts):
                trend = 'decreasing'
            else:
                trend = 'stable'

            hotspot = ProblemHotspot(
                location=loc_obj,
                alert_count=int(location_stats.loc[location, 'total_count']),
                critical_count=int(severity_counts.loc[location, 'critical']) if 'critical' in severity_counts.columns else 0,
                warning_count=int(severity_counts.loc[location, 'warning']) if 'warning' in severity_counts.columns else 0,
                top_issues=top_issue_list,
                trend=trend,
                priority_score=self._calculate_priority_score(
                    int(location_stats.loc[location, 'total_count']),
                    int(severity_counts.loc[location, 'critical']) if 'critical' in severity_counts.columns else 0
                )
            )
            hotspots.append(hotspot)

        return sorted(hotspots, key=lambda x: x.priority_score, reverse=True)

    def _calculate_priority_score(self, total_alerts: int, critical_alerts: int) -> float:
        """Calculate priority score for a location"""
        # Weight critical alerts more heavily
        base_score = total_alerts + (critical_alerts * 3)
        # Normalize to 0-100 scale
        return min(100, base_score * 2)

    def calculate_cleaning_priorities(self, environment_data: EnvironmentData,
                                    occupancy_data: OccupancyData,
                                    consumable_data: ConsumableData,
                                    task_data: TaskData) -> List[CleaningPriority]:
        """Calculate cleaning priorities based on multiple factors"""
        priorities = []

        # Get unique locations
        all_locations = set()

        # Collect locations from all data sources
        if environment_data.readings:
            all_locations.update([r.location for r in environment_data.readings])
        if occupancy_data.readings:
            all_locations.update([r.location for r in occupancy_data.readings])
        if consumable_data.consumable_readings:
            all_locations.update([r.location for r in consumable_data.consumable_readings])

        for location in all_locations:
            # Calculate factors
            factors = {}

            # Environment factor (poor air quality increases priority)
            env_scores = [s.value for s in environment_data.scores
                         if s.location == location and s.score_type == 'iaq_score']
            if env_scores:
                avg_iaq = np.mean(env_scores)
                factors['air_quality'] = max(0, 100 - avg_iaq) * 0.3

            # Occupancy factor (high traffic increases priority)
            occ_readings = [r.people_count for r in occupancy_data.readings
                           if r.location == location]
            if occ_readings:
                avg_occupancy = np.mean(occ_readings)
                max_occupancy = max(occ_readings)
                factors['occupancy'] = (avg_occupancy / max_occupancy * 100) * 0.3 if max_occupancy > 0 else 0

            # Alert factor (more alerts increase priority)
            alert_count = len([a for a in environment_data.alerts if a.location == location])
            factors['alerts'] = min(alert_count * 5, 100) * 0.2

            # Consumable factor (low supplies increase priority)
            consumable_levels = [r.remaining_percentage for r in consumable_data.consumable_readings
                               if r.location == location]
            if consumable_levels:
                min_level = min(consumable_levels)
                factors['consumables'] = max(0, 100 - min_level) * 0.2

            # Calculate total priority score
            priority_score = sum(factors.values())

            # Determine recommended frequency
            if priority_score >= 80:
                recommended_freq = "Multiple times daily"
            elif priority_score >= 60:
                recommended_freq = "Twice daily"
            elif priority_score >= 40:
                recommended_freq = "Daily"
            elif priority_score >= 20:
                recommended_freq = "Every other day"
            else:
                recommended_freq = "Twice weekly"

            # Get current frequency from task data
            current_freq = "Daily"  # Default
            location_tasks = [t for t in task_data.work_orders if t.location == location]
            if location_tasks:
                # Simplified logic - would analyze actual task patterns
                current_freq = "Daily"

            priority = CleaningPriority(
                location=location,
                priority_score=priority_score,
                contributing_factors=factors,
                recommended_frequency=recommended_freq,
                current_frequency=current_freq,
                adjustment_needed=recommended_freq != current_freq
            )
            priorities.append(priority)

        return sorted(priorities, key=lambda x: x.priority_score, reverse=True)

    def calculate_time_based_metrics(self, df: pd.DataFrame,
                                   time_column: str = 'timestamp',
                                   value_column: str = 'value',
                                   period: str = 'daily') -> Dict[str, pd.DataFrame]:
        """Calculate time-based metrics (hourly, daily, weekly patterns)"""
        if df.empty or time_column not in df.columns:
            return {}

        df[time_column] = pd.to_datetime(df[time_column])
        results = {}

        if period in ['hourly', 'all']:
            hourly = df.groupby(df[time_column].dt.hour)[value_column].agg(['mean', 'std', 'count'])
            results['hourly'] = hourly

        if period in ['daily', 'all']:
            daily = df.groupby(df[time_column].dt.date)[value_column].agg(['mean', 'min', 'max'])
            results['daily'] = daily

        if period in ['weekly', 'all']:
            weekly = df.groupby(df[time_column].dt.isocalendar().week)[value_column].agg(['mean', 'sum'])
            results['weekly'] = weekly

        if period in ['day_of_week', 'all']:
            dow = df.groupby(df[time_column].dt.day_name())[value_column].agg(['mean', 'count'])
            # Reorder days
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow = dow.reindex([d for d in day_order if d in dow.index])
            results['day_of_week'] = dow

        return results

    def generate_summary_statistics(self, data: Any) -> Dict[str, Any]:
        """Generate summary statistics for any data type"""
        summary = {}

        if isinstance(data, EnvironmentData):
            summary['total_readings'] = len(data.readings)
            summary['unique_sensors'] = len(set(r.sensor_id for r in data.readings))
            summary['alert_count'] = len(data.alerts)
            summary['critical_alerts'] = len([a for a in data.alerts if a.severity == 'critical'])

            if data.scores:
                iaq_scores = [s.value for s in data.scores if s.score_type == 'iaq_score']
                comfort_scores = [s.value for s in data.scores if s.score_type == 'comfort_score']

                if iaq_scores:
                    summary['avg_iaq_score'] = np.mean(iaq_scores)
                    summary['min_iaq_score'] = min(iaq_scores)

                if comfort_scores:
                    summary['avg_comfort_score'] = np.mean(comfort_scores)
                    summary['min_comfort_score'] = min(comfort_scores)

        elif isinstance(data, OccupancyData):
            summary['total_readings'] = len(data.readings)

            if data.readings:
                people_counts = [r.people_count for r in data.readings]
                summary['total_people_count'] = sum(people_counts)
                summary['avg_occupancy'] = np.mean(people_counts)
                summary['peak_occupancy'] = max(people_counts)

                dwell_times = [r.dwell_time_minutes for r in data.readings]
                summary['avg_dwell_time'] = np.mean(dwell_times)

        elif isinstance(data, ConsumableData):
            summary['consumable_types'] = len(set(r.consumable_type for r in data.consumable_readings))
            summary['critical_consumables'] = len(data.get_critical_consumables())
            summary['waste_issues'] = len(data.get_waste_issues())
            summary['sustainability_score'] = data.calculate_sustainability_score()

        elif isinstance(data, TaskData):
            summary['total_work_orders'] = len(data.work_orders)
            summary['completed_orders'] = len([w for w in data.work_orders if w.status == 'completed'])
            summary['overdue_orders'] = len([w for w in data.work_orders if w.status == 'overdue'])

            if data.work_orders:
                completion_rate = summary['completed_orders'] / summary['total_work_orders'] * 100
                summary['completion_rate'] = round(completion_rate, 1)

            summary['total_inspections'] = len(data.inspections)
            if data.inspections:
                summary['avg_inspection_score'] = np.mean([i.overall_score for i in data.inspections])
                summary['inspection_pass_rate'] = len([i for i in data.inspections if i.pass_fail == 'pass']) / len(data.inspections) * 100

        return summary