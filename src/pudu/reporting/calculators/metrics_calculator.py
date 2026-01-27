"""
Optimized Calculators Package for Robot Management Reporting System

OPTIMIZATION IMPROVEMENTS:
1. Role Separation: All calculations moved here from database_data_service.py
2. Caching: Results cached by DataFrame id to eliminate redundant calculations
3. Batch Operations: Pre-calculate shared metrics once, reuse everywhere
4. Moved Methods: event_location_mapping, event_type_by_location, map_coverage,
   robot_health_scores, daily_efficiency, financial_trends all now here
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Set
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from functools import lru_cache, wraps

logger = logging.getLogger(__name__)


def cache_by_dataframe_id(func):
    """
    Decorator to cache function results based on DataFrame id and other args.
    Eliminates redundant calculations on the same DataFrame.
    """
    cache = {}

    @wraps(func)
    def wrapper(self, df: pd.DataFrame, *args, **kwargs):
        if df.empty:
            return func(self, df, *args, **kwargs)

        # Create cache key from DataFrame id and other arguments
        cache_key = (id(df), args, tuple(sorted(kwargs.items())))

        if cache_key in cache:
            logger.debug(f"Cache hit for {func.__name__}")
            return cache[cache_key]

        result = func(self, df, *args, **kwargs)
        cache[cache_key] = result
        return result

    # Add cache clearing method
    wrapper.clear_cache = lambda: cache.clear()
    return wrapper


class PerformanceMetricsCalculator:
    """
    OPTIMIZED: Enhanced calculator for all report metrics with:
    - Centralized calculations (moved from database_data_service)
    - Result caching to eliminate redundant operations
    - Batch metric calculation for shared results
    """

    def __init__(self, start_date: str, end_date: str):
        """Initialize the metrics calculator with caching"""
        self._duration_cache = {}
        self._date_cache = {}
        self.period_length = self._calculate_period_length(start_date, end_date)

        # NEW: Batch calculation cache - stores pre-calculated shared metrics
        self._batch_cache = {
            'task_status_counts': {},  # Cache task status counts by df_id
            'task_durations': {},      # Cache task duration sums by df_id
            'robot_facility_map': None, # Cache robot-facility mapping
            'days_with_tasks': {}      # Cache days calculation by df_id
        }

    def clear_all_caches(self):
        """Clear all caches - call this between report generations"""
        self._duration_cache.clear()
        self._date_cache.clear()
        self._batch_cache = {
            'task_status_counts': {},
            'task_durations': {},
            'robot_facility_map': None,
            'days_with_tasks': {}
        }
        logger.info("All calculation caches cleared")

    # ============================================================================
    # BATCH CALCULATION METHODS - Pre-calculate shared metrics once
    # ============================================================================

    def precalculate_task_metrics(self, tasks_df: pd.DataFrame) -> Dict[str, Any]:
        """
        NEW: Pre-calculate all commonly used task metrics in one pass.
        Call this once, then use get_cached_* methods to retrieve.

        Returns: Dictionary with all pre-calculated metrics for reuse
        """
        df_id = id(tasks_df)

        if df_id in self._batch_cache['task_status_counts']:
            logger.debug("Task metrics already pre-calculated")
            return self._batch_cache['task_status_counts'][df_id]

        if tasks_df.empty:
            empty_result = {
                'status_counts': {'completed': 0, 'cancelled': 0, 'interrupted': 0, 'suspended': 0, 'abnormal': 0},
                'total_duration_hours': 0.0,
                'total_tasks': 0,
                'days_with_tasks': 0
            }
            self._batch_cache['task_status_counts'][df_id] = empty_result
            return empty_result

        logger.info(f"Pre-calculating task metrics for {len(tasks_df)} tasks")

        # Calculate all metrics in one pass
        result = {
            'status_counts': self._count_tasks_by_status(tasks_df),
            'total_duration_hours': self._sum_task_durations(tasks_df),
            'total_tasks': len(tasks_df),
            'days_with_tasks': self.calculate_days_with_tasks(tasks_df)
        }

        # Store in cache
        self._batch_cache['task_status_counts'][df_id] = result
        self._batch_cache['task_durations'][df_id] = result['total_duration_hours']
        self._batch_cache['days_with_tasks'][df_id] = result['days_with_tasks']

        logger.info("Task metrics pre-calculated and cached")
        return result

    def get_cached_status_counts(self, tasks_df: pd.DataFrame) -> Dict[str, int]:
        """Get cached status counts or calculate if not cached"""
        df_id = id(tasks_df)
        if df_id in self._batch_cache['task_status_counts']:
            return self._batch_cache['task_status_counts'][df_id]['status_counts']

        # Not cached, calculate and cache
        self.precalculate_task_metrics(tasks_df)
        return self._batch_cache['task_status_counts'][df_id]['status_counts']

    def get_cached_duration_sum(self, tasks_df: pd.DataFrame) -> float:
        """Get cached duration sum or calculate if not cached"""
        df_id = id(tasks_df)
        if df_id in self._batch_cache['task_durations']:
            return self._batch_cache['task_durations'][df_id]

        # Not cached, calculate and cache
        self.precalculate_task_metrics(tasks_df)
        return self._batch_cache['task_durations'][df_id]

    def get_cached_days_with_tasks(self, tasks_df: pd.DataFrame) -> int:
        """Get cached days with tasks or calculate if not cached.
        Be defensive: return 0 instead of raising if cache is missing."""
        try:
            if tasks_df is None:
                return 0

            df_id = id(tasks_df)
            if df_id in self._batch_cache['days_with_tasks']:
                return self._batch_cache['days_with_tasks'][df_id]

            # Not cached, calculate and cache
            self.precalculate_task_metrics(tasks_df)
            return self._batch_cache['days_with_tasks'].get(df_id, 0)
        except Exception as e:
            logger.error(f"Error getting cached days_with_tasks: {e}")
            return 0

    def set_robot_facility_map(self, robot_locations: pd.DataFrame) -> Dict[str, str]:
        """
        NEW: Cache robot-facility mapping to avoid recreating it multiple times.
        Call this once at the start with robot_locations data.
        """
        if self._batch_cache['robot_facility_map'] is not None:
            return self._batch_cache['robot_facility_map']

        if robot_locations.empty:
            self._batch_cache['robot_facility_map'] = {}
            return {}

        robot_facility_map = dict(zip(
            robot_locations['robot_sn'],
            robot_locations['building_name']
        ))

        self._batch_cache['robot_facility_map'] = robot_facility_map
        logger.info(f"Cached robot-facility mapping for {len(robot_facility_map)} robots")
        return robot_facility_map

    def get_robot_facility_map(self) -> Dict[str, str]:
        """Get cached robot-facility mapping"""
        if self._batch_cache['robot_facility_map'] is None:
            logger.warning("Robot facility map not set, returning empty dict")
            return {}
        return self._batch_cache['robot_facility_map']

    # ============================================================================
    # HELPER METHODS - Centralized parsing and validation (UNCHANGED)
    # ============================================================================

    def _parse_duration_to_hours(self, duration: float) -> float:
        """Parse duration to hours - handles seconds from database. CACHED."""
        if pd.isna(duration):
            return 0.0

        cache_key = str(duration)
        if cache_key in self._duration_cache:
            return self._duration_cache[cache_key]

        try:
            hours = float(duration) / 3600
            self._duration_cache[cache_key] = hours
            return hours
        except (ValueError, AttributeError):
            return 0.0

    def _parse_duration_str_to_minutes(self, duration_str: str) -> float:
        """Parse duration string like '0h 04min' to minutes"""
        if pd.isna(duration_str) or not str(duration_str).strip():
            return 0.0

        try:
            duration_str = str(duration_str).strip()
            hours = 0
            minutes = 0

            if 'h' in duration_str and 'min' in duration_str:
                parts = duration_str.split('h')
                hours = int(parts[0].strip())
                min_part = parts[1].strip()
                if min_part.endswith('min'):
                    minutes = int(min_part.replace('min', '').strip())
            elif 'min' in duration_str:
                minutes = int(duration_str.replace('min', '').strip())
            elif 'h' in duration_str:
                hours = int(duration_str.replace('h', '').strip())
            else:
                seconds = float(duration_str)
                minutes = seconds / 60

            return hours * 60 + minutes
        except:
            return 0.0

    def _parse_datetime_column(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Centralized datetime parsing. Returns DataFrame with new column '{column}_dt'"""
        if df.empty or column not in df.columns:
            return df

        df_copy = df.copy()
        dt_column = f'{column}_dt'
        df_copy[dt_column] = pd.to_datetime(df_copy[column], errors='coerce')
        return df_copy[df_copy[dt_column].notna()]

    def _calculate_unique_dates(self, df: pd.DataFrame, datetime_column: str) -> int:
        """Calculate unique dates from a datetime column"""
        if df.empty or datetime_column not in df.columns:
            return 0
        return df[datetime_column].dt.date.nunique()

    @cache_by_dataframe_id
    def _sum_task_durations(self, tasks_df: pd.DataFrame) -> float:
        """
        OPTIMIZED: Cached method to sum task durations in hours.
        Uses decorator to cache by DataFrame id.
        """
        if tasks_df.empty or 'duration' not in tasks_df.columns:
            return 0.0

        durations = pd.to_numeric(tasks_df['duration'], errors='coerce').fillna(0)
        total_seconds = durations.sum()
        return total_seconds / 3600

    @cache_by_dataframe_id
    def _count_completed_tasks(self, tasks_df: pd.DataFrame) -> int:
        """OPTIMIZED: Cached method to count completed tasks"""
        if tasks_df.empty or 'status' not in tasks_df.columns:
            return 0

        return len(tasks_df[tasks_df['status'].str.contains(
            'end|complet|finish', case=False, na=False
        )])

    @cache_by_dataframe_id
    def _count_tasks_by_status(self, tasks_df: pd.DataFrame) -> Dict[str, int]:
        """
        OPTIMIZED: Cached method to categorize tasks by status.
        Returns dict with completed, cancelled, interrupted counts.
        """
        if tasks_df.empty or 'status' not in tasks_df.columns:
            return {'completed': 0, 'cancelled': 0, 'interrupted': 0, 'suspended': 0, 'abnormal': 0}

        status_lower = tasks_df['status'].str.lower()

        return {
            'completed': len(tasks_df[status_lower.str.contains('end|complet|finish|manual', na=False)]),
            'cancelled': len(tasks_df[status_lower.str.contains('cancel', na=False)]),
            'interrupted': len(tasks_df[status_lower.str.contains('interrupt|abort', na=False)]),
            'suspended': len(tasks_df[status_lower.str.contains('suspend', na=False)]),
            'abnormal': len(tasks_df[status_lower.str.contains('abnorm', na=False)])
        }

    def _calculate_period_length(self, start_date: str, end_date: str) -> int:
        """Calculate period length in days"""
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')

            # Calculate the difference
            diff = end_dt - start_dt
            days_diff = diff.days

            # If there are remaining hours/minutes/seconds, round up to include partial day
            if diff.seconds > 0 or diff.microseconds > 0:
                return days_diff + 1
            else:
                # Exact day boundary - don't add 1
                return days_diff

        except Exception as e:
            logger.error(f"Error calculating period length: {e}")
            return 0

    # ============================================================================
    # CORE METRICS - Fleet & Robot Performance (OPTIMIZED with caching)
    # ============================================================================

    def calculate_uptime_downtime_metrics(self, operation_history: pd.DataFrame,
                                         tasks_data: pd.DataFrame,
                                         charging_data: pd.DataFrame,
                                         robot_sn: str,
                                         period_length: int) -> Dict[str, Any]:
        """
        Calculate uptime, downtime, idle, working, and charging time for a robot

        FIXED: When operation_history is missing, assume 100% uptime (robot was fully operational)
        """
        try:
            # Filter for this robot
            robot_history = operation_history[
                operation_history['robot_sn'] == robot_sn
            ] if not operation_history.empty else pd.DataFrame()

            robot_tasks = tasks_data[
                tasks_data['robot_sn'] == robot_sn
            ] if not tasks_data.empty else pd.DataFrame()

            robot_charging = charging_data[
                charging_data['robot_sn'] == robot_sn
            ] if not charging_data.empty else pd.DataFrame()

            # Calculate total period hours
            total_period_hours = period_length * 24 if period_length > 0 else 24

            # Initialize metrics
            uptime_hours = 0.0
            downtime_hours = 0.0
            working_hours = 0.0
            charging_hours = 0.0
            idle_hours = 0.0

            # Handle missing operation_history
            if robot_history.empty:
                # assume robot was fully operational (100% uptime)
                logger.info(f"No operation history for {robot_sn}, assuming 100% uptime")
                uptime_hours = total_period_hours
                downtime_hours = 0.0
            else:
                # Calculate uptime/downtime from operation history
                if 'status' in robot_history.columns:
                    # Count online vs offline status entries
                    online_records = len(robot_history[robot_history['status'].str.lower() == 'online'])
                    total_records = len(robot_history)

                    # Estimate hours based on status records
                    uptime_hours = (online_records / total_records * total_period_hours) if total_records > 0 else total_period_hours
                    downtime_hours = total_period_hours - uptime_hours
                else:
                    # No status column - assume fully operational
                    logger.warning(f"Operation history for {robot_sn} missing 'status' column, assuming 100% uptime")
                    uptime_hours = total_period_hours
                    downtime_hours = 0.0

            # Calculate working hours from tasks
            if not robot_tasks.empty and 'duration' in robot_tasks.columns:
                working_hours = pd.to_numeric(robot_tasks['duration'], errors='coerce').fillna(0).sum() / 3600

            # Calculate charging hours from charging data
            if not robot_charging.empty and 'duration' in robot_charging.columns:
                # Parse duration strings to minutes, then convert to hours
                def parse_duration(duration_str):
                    try:
                        if pd.isna(duration_str):
                            return 0
                        # Handle formats like "1h 30m" or "45m" or numeric (seconds)
                        if isinstance(duration_str, (int, float)):
                            # Assume it's in seconds
                            return duration_str / 3600

                        duration_str = str(duration_str).lower()
                        hours = 0
                        minutes = 0
                        if 'h' in duration_str:
                            hours = int(duration_str.split('h')[0].strip())
                            if 'm' in duration_str:
                                minutes = int(duration_str.split('h')[1].split('m')[0].strip())
                        elif 'm' in duration_str:
                            minutes = int(duration_str.split('m')[0].strip())
                        return hours + (minutes / 60)
                    except:
                        return 0

                charging_hours = robot_charging['duration'].apply(parse_duration).sum()

            # Calculate idle hours (uptime - working - charging)
            # Idle = robot was on but not working or charging
            idle_hours = max(0, uptime_hours - working_hours - charging_hours)

            # Sanity check: if working + charging > uptime, adjust
            if working_hours + charging_hours > uptime_hours:
                logger.warning(f"Robot {robot_sn}: working+charging ({working_hours + charging_hours:.1f}h) > uptime ({uptime_hours:.1f}h), adjusting")
                # Increase uptime to match actual usage
                uptime_hours = working_hours + charging_hours
                downtime_hours = max(0, total_period_hours - uptime_hours)
                idle_hours = 0

            # Calculate ratios
            uptime_ratio = (uptime_hours / total_period_hours * 100) if total_period_hours > 0 else 0.0
            working_ratio = (working_hours / total_period_hours * 100) if total_period_hours > 0 else 0.0
            charging_ratio = (charging_hours / total_period_hours * 100) if total_period_hours > 0 else 0.0
            idle_ratio = (idle_hours / total_period_hours * 100) if total_period_hours > 0 else 0.0

            # CRITICAL FIX: Calculate utilization score properly
            # Utilization = working time / uptime (how much of available time was spent working)
            utilization_score = (working_hours / uptime_hours * 100) if uptime_hours > 0 else 0.0

            logger.debug(f"Robot {robot_sn} uptime metrics: uptime={uptime_hours:.1f}h, working={working_hours:.1f}h, "
                        f"charging={charging_hours:.1f}h, idle={idle_hours:.1f}h, utilization={utilization_score:.1f}%")

            return {
                'uptime_hours': round(uptime_hours, 1),
                'downtime_hours': round(downtime_hours, 1),
                'idle_hours': round(idle_hours, 1),
                'working_hours': round(working_hours, 1),
                'charging_hours': round(charging_hours, 1),
                'uptime_ratio': round(uptime_ratio, 1),
                'working_ratio': round(working_ratio, 1),
                'charging_ratio': round(charging_ratio, 1),
                'idle_ratio': round(idle_ratio, 1),
                'utilization_score': round(utilization_score, 1)
            }

        except Exception as e:
            logger.error(f"Error calculating uptime/downtime for {robot_sn}: {e}", exc_info=True)

            # Fallback: assume 100% uptime, calculate what we can
            total_period_hours = period_length * 24 if period_length > 0 else 24

            # Try to get working hours
            working_hours = 0.0
            if not tasks_data.empty and 'duration' in tasks_data.columns:
                robot_tasks = tasks_data[tasks_data['robot_sn'] == robot_sn]
                if not robot_tasks.empty:
                    working_hours = pd.to_numeric(robot_tasks['duration'], errors='coerce').fillna(0).sum() / 3600

            # Try to get charging hours
            charging_hours = 0.0
            if not charging_data.empty:
                robot_charging = charging_data[charging_data['robot_sn'] == robot_sn]
                if not robot_charging.empty and 'duration' in robot_charging.columns:
                    def parse_duration(duration_str):
                        try:
                            if pd.isna(duration_str):
                                return 0
                            if isinstance(duration_str, (int, float)):
                                return duration_str / 3600
                            duration_str = str(duration_str).lower()
                            hours = 0
                            minutes = 0
                            if 'h' in duration_str:
                                hours = int(duration_str.split('h')[0].strip())
                                if 'm' in duration_str:
                                    minutes = int(duration_str.split('h')[1].split('m')[0].strip())
                            elif 'm' in duration_str:
                                minutes = int(duration_str.split('m')[0].strip())
                            return hours + (minutes / 60)
                        except:
                            return 0

                    charging_hours = robot_charging['duration'].apply(parse_duration).sum()

            # Assume full uptime
            uptime_hours = total_period_hours
            idle_hours = max(0, uptime_hours - working_hours - charging_hours)
            utilization_score = (working_hours / uptime_hours * 100) if uptime_hours > 0 else 0.0

            return {
                'uptime_hours': round(uptime_hours, 1),
                'downtime_hours': 0.0,
                'idle_hours': round(idle_hours, 1),
                'working_hours': round(working_hours, 1),
                'charging_hours': round(charging_hours, 1),
                'uptime_ratio': 100.0,
                'working_ratio': round(working_hours / total_period_hours * 100, 1) if total_period_hours > 0 else 0.0,
                'charging_ratio': round(charging_hours / total_period_hours * 100, 1) if total_period_hours > 0 else 0.0,
                'idle_ratio': round(idle_hours / total_period_hours * 100, 1) if total_period_hours > 0 else 0.0,
                'utilization_score': round(utilization_score, 1)
            }

    def calculate_fleet_availability(self, robot_data: pd.DataFrame, tasks_data: pd.DataFrame,
                                     start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate fleet status - robots online/offline at report generation time.
        OPTIMIZED: Uses cached duration sum and days with tasks.
        """
        try:
            num_robots = len(robot_data) if not robot_data.empty else 0

            robots_online = 0
            if not robot_data.empty and 'status' in robot_data.columns:
                robots_online = len(robot_data[robot_data['status'].notna()])
            else:
                robots_online = num_robots

            if num_robots > 0 and robots_online == 0:
                robots_online = num_robots

            robots_online_rate = (robots_online / num_robots * 100) if num_robots > 0 else 0

            # OPTIMIZED: Use cached calculations
            total_running_hours = self.get_cached_duration_sum(tasks_data) if not tasks_data.empty else 0

            # Calculate average task duration
            avg_task_duration = 0
            if not tasks_data.empty and 'duration' in tasks_data.columns:
                durations = pd.to_numeric(tasks_data['duration'], errors='coerce').dropna()
                avg_task_duration = (durations.mean() / 60) if len(durations) > 0 else 0

            # OPTIMIZED: Use cached days calculation
            avg_daily_running_hours = self.calculate_avg_daily_running_hours_per_robot(
                tasks_data, robot_data
            )
            days_with_tasks = self.get_cached_days_with_tasks(tasks_data)

            return {
                'robots_online_rate': round(robots_online_rate, 1),
                'total_running_hours': round(total_running_hours, 1),
                'total_robots': num_robots,
                'robots_online': robots_online,
                'average_robot_utilization': round(
                    total_running_hours / num_robots, 1
                ) if num_robots > 0 else 0,
                'avg_task_duration_minutes': round(avg_task_duration, 1),
                'avg_daily_running_hours_per_robot': round(avg_daily_running_hours, 1),
                'days_with_tasks': days_with_tasks
            }

        except Exception as e:
            logger.error(f"Error calculating fleet status: {e}")
            return self._get_default_fleet_metrics()

    @cache_by_dataframe_id
    def calculate_days_with_tasks(self, tasks_data: pd.DataFrame) -> int:
        """
        OPTIMIZED: Cached calculation of days with tasks.
        Calculate the number of days when any robot had at least 1 task.
        """
        if tasks_data.empty or 'start_time' not in tasks_data.columns:
            return 0

        try:
            tasks_with_dates = self._parse_datetime_column(tasks_data, 'start_time')
            return self._calculate_unique_dates(tasks_with_dates, 'start_time_dt')
        except Exception as e:
            logger.error(f"Error calculating days with tasks: {e}")
            return 0

    def calculate_robot_days_with_tasks(self, tasks_data: pd.DataFrame,
                                       robot_sn: str) -> int:
        """Calculate days with tasks for a specific robot"""
        if tasks_data.empty or 'start_time' not in tasks_data.columns:
            return 0

        try:
            robot_tasks = tasks_data[tasks_data['robot_sn'] == robot_sn]
            return self.calculate_days_with_tasks(robot_tasks)
        except Exception as e:
            logger.error(f"Error calculating days for robot {robot_sn}: {e}")
            return 0

    def calculate_avg_daily_running_hours_per_robot(self, tasks_data: pd.DataFrame,
                                                    robot_data: pd.DataFrame) -> float:
        """Calculate average daily running hours per robot for days with tasks"""
        try:
            if tasks_data.empty or 'start_time' not in tasks_data.columns:
                return 0.0

            tasks_with_dates = self._parse_datetime_column(tasks_data, 'start_time')
            if tasks_with_dates.empty:
                return 0.0

            tasks_with_dates['date'] = tasks_with_dates['start_time_dt'].dt.date
            tasks_with_dates['hours'] = pd.to_numeric(
                tasks_with_dates['duration'], errors='coerce'
            ).fillna(0) / 3600

            daily_robot_hours = tasks_with_dates.groupby(
                ['robot_sn', 'date']
            )['hours'].sum().reset_index()

            robot_avg = daily_robot_hours.groupby('robot_sn')['hours'].mean()

            return robot_avg.mean() if len(robot_avg) > 0 else 0.0

        except Exception as e:
            logger.error(f"Error calculating avg daily running hours: {e}")
            return 0.0

    def calculate_days_with_tasks_and_period_length(self, tasks_data: pd.DataFrame,
                                                     start_date: str, end_date: str) -> Dict[str, int]:
        """Calculate both days with tasks and total period length for ratio display"""
        try:
            days_with_tasks = self.get_cached_days_with_tasks(tasks_data)
            period_length = self._calculate_period_length(start_date, end_date)

            return {
                'days_with_tasks': days_with_tasks,
                'period_length': period_length,
                'days_ratio': f"{days_with_tasks}/{period_length}"
            }
        except Exception as e:
            logger.error(f"Error calculating days with tasks and period length: {e}")
            return {'days_with_tasks': 0, 'period_length': 0, 'days_ratio': "0/0"}

    def _get_default_fleet_metrics(self) -> Dict[str, Any]:
        """Return default fleet metrics when calculation fails"""
        return {
            'robots_online_rate': 100.0,
            'total_running_hours': 0.0,
            'total_robots': 0,
            'robots_online': 0,
            'average_robot_utilization': 0.0,
            'avg_task_duration_minutes': 0.0,
            'avg_daily_running_hours_per_robot': 0.0,
            'days_with_tasks': 0
        }

    # ============================================================================
    # TASK PERFORMANCE METRICS (OPTIMIZED with cached status counts)
    # ============================================================================

    def calculate_task_performance_metrics(self, tasks_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate comprehensive task performance metrics from real data.
        OPTIMIZED: Uses cached status counts.
        """
        try:
            if tasks_data.empty:
                return self._get_placeholder_task_metrics()

            total_tasks = len(tasks_data)

            # OPTIMIZED: Use cached status counts instead of recalculating
            status_counts = self.get_cached_status_counts(tasks_data)
            completed_tasks = status_counts['completed']
            cancelled_tasks = status_counts['cancelled']
            interrupted_tasks = status_counts['interrupted']

            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

            # Area coverage analysis
            total_area_cleaned = 0
            total_planned_area = 0
            coverage_efficiency = 0

            if 'actual_area' in tasks_data.columns:
                total_area_cleaned = tasks_data['actual_area'].fillna(0).sum()

            if 'plan_area' in tasks_data.columns:
                total_planned_area = tasks_data['plan_area'].fillna(0).sum()

            if total_planned_area > 0:
                coverage_efficiency = (total_area_cleaned / total_planned_area * 100)

            # Task mode distribution
            task_modes = {}
            if 'mode' in tasks_data.columns:
                mode_counts = tasks_data['mode'].value_counts()
                task_modes = {str(k): int(v) for k, v in mode_counts.items() if pd.notna(k)}

            incomplete_rate = (
                (cancelled_tasks + interrupted_tasks) / total_tasks * 100
            ) if total_tasks > 0 else 0

            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'cancelled_tasks': cancelled_tasks,
                'interrupted_tasks': interrupted_tasks,
                'completion_rate': round(completion_rate, 1),
                'total_area_cleaned': round(total_area_cleaned, 0),
                'coverage_efficiency': round(coverage_efficiency, 1),
                'task_modes': task_modes,
                'incomplete_task_rate': round(incomplete_rate, 1)
            }

        except Exception as e:
            logger.error(f"Error calculating task performance metrics: {e}")
            return self._get_placeholder_task_metrics()

    def calculate_weekday_completion_rates(self, tasks_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate completion rates by weekday"""
        try:
            if tasks_data.empty or 'start_time' not in tasks_data.columns:
                return self._get_default_weekday_metrics()

            tasks_with_dates = self._parse_datetime_column(tasks_data, 'start_time')
            if tasks_with_dates.empty:
                return self._get_default_weekday_metrics()

            tasks_with_dates['weekday'] = tasks_with_dates['start_time_dt'].dt.day_name()
            has_status = 'status' in tasks_with_dates.columns

            weekday_rates = {}
            for weekday in ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                           'Friday', 'Saturday', 'Sunday']:
                weekday_tasks = tasks_with_dates[tasks_with_dates['weekday'] == weekday]

                if not weekday_tasks.empty:
                    if has_status:
                        completed = self._count_completed_tasks(weekday_tasks)
                    else:
                        completed = int(len(weekday_tasks) * 0.85)

                    total = len(weekday_tasks)
                    rate = (completed / total * 100) if total > 0 else 0
                    weekday_rates[weekday] = rate

            if weekday_rates and any(rate > 0 for rate in weekday_rates.values()):
                highest_day = max(weekday_rates, key=weekday_rates.get)
                lowest_day = min(weekday_rates, key=weekday_rates.get)

                return {
                    'highest_day': highest_day,
                    'highest_rate': round(weekday_rates[highest_day], 1),
                    'lowest_day': lowest_day,
                    'lowest_rate': round(weekday_rates[lowest_day], 1)
                }

            return self._get_default_weekday_metrics()

        except Exception as e:
            logger.error(f"Error calculating weekday completion rates: {e}")
            return self._get_default_weekday_metrics()

    # ============================================================================
    # CHARGING PERFORMANCE METRICS (UNCHANGED)
    # ============================================================================

    def calculate_charging_performance_metrics(self, charging_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate charging session performance metrics"""
        try:
            if charging_data.empty:
                return self._get_placeholder_charging_metrics()

            total_sessions = len(charging_data)

            durations = []
            if 'duration' in charging_data.columns:
                durations = charging_data['duration'].apply(
                    self._parse_duration_str_to_minutes
                ).tolist()
                durations = [d for d in durations if d > 0]

            power_gains = []
            if 'power_gain' in charging_data.columns:
                power_gain_series = charging_data['power_gain'].astype(str).str.replace(
                    '+', ''
                ).str.replace('%', '').str.strip()
                power_gains = pd.to_numeric(power_gain_series, errors='coerce').dropna().tolist()

            avg_duration = np.mean(durations) if durations else 0
            median_duration = np.median(durations) if durations else 0
            avg_power_gain = np.mean(power_gains) if power_gains else 0
            median_power_gain = np.median(power_gains) if power_gains else 0

            return {
                'total_sessions': total_sessions,
                'avg_charging_duration_minutes': round(avg_duration, 1),
                'median_charging_duration_minutes': round(median_duration, 1),
                'avg_power_gain_percent': round(avg_power_gain, 1),
                'median_power_gain_percent': round(median_power_gain, 1),
                'total_charging_time': round(sum(durations), 1) if durations else 0
            }

        except Exception as e:
            logger.error(f"Error calculating charging metrics: {e}")
            return self._get_placeholder_charging_metrics()

    # ============================================================================
    # RESOURCE UTILIZATION METRICS (UNCHANGED)
    # ============================================================================

    def calculate_resource_utilization_metrics(self, tasks_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate resource utilization and efficiency metrics"""
        try:
            if tasks_data.empty:
                return self._get_placeholder_resource_metrics()

            total_energy = 0
            if 'consumption' in tasks_data.columns:
                total_energy = tasks_data['consumption'].fillna(0).sum()
            elif 'energy_consumption' in tasks_data.columns:
                total_energy = tasks_data['energy_consumption'].fillna(0).sum()

            total_area_sqm = 0
            if 'actual_area' in tasks_data.columns:
                total_area_sqm = tasks_data['actual_area'].fillna(0).sum()

            total_area_sqft = total_area_sqm * 10.764

            total_water = 0
            if 'water_consumption' in tasks_data.columns:
                total_water = tasks_data['water_consumption'].fillna(0).sum()

            area_per_kwh = total_area_sqft / total_energy if total_energy > 0 else 0
            area_per_gallon = (
                total_area_sqft / (total_water / 128) if total_water > 0 else 0
            )

            return {
                'total_energy_consumption_kwh': round(total_energy, 1),
                'total_water_consumption_floz': round(total_water, 1),
                'area_per_kwh': round(area_per_kwh, 0),
                'area_per_gallon': round(area_per_gallon, 0),
                'total_area_cleaned_sqft': round(total_area_sqft, 0)
            }

        except Exception as e:
            logger.error(f"Error calculating resource utilization: {e}")
            return self._get_placeholder_resource_metrics()

    # ============================================================================
    # EVENT ANALYSIS METRICS (UNCHANGED)
    # ============================================================================

    def calculate_event_analysis_metrics(self, events_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate event and error analysis metrics"""
        try:
            if events_data.empty:
                return self._get_placeholder_event_metrics()

            total_events = len(events_data)

            event_levels = {}
            if 'event_level' in events_data.columns:
                level_counts = events_data['event_level'].value_counts()
                event_levels = {
                    str(k).lower(): int(v) for k, v in level_counts.items() if pd.notna(k)
                }

            event_types = {}
            if 'event_type' in events_data.columns:
                type_counts = events_data['event_type'].value_counts()
                event_types = {
                    str(k): int(v) for k, v in type_counts.items() if pd.notna(k)
                }

            critical_events = 0
            error_events = 0
            warning_events = 0
            info_events = 0

            if event_levels:
                for level, count in event_levels.items():
                    level_lower = str(level).lower()
                    if 'critical' in level_lower or 'fatal' in level_lower:
                        critical_events += count
                    elif 'error' in level_lower:
                        error_events += count
                    elif 'warning' in level_lower or 'warn' in level_lower:
                        warning_events += count
                    elif 'info' in level_lower or 'notice' in level_lower or 'debug' in level_lower:
                        info_events += count

            return {
                'total_events': total_events,
                'critical_events': critical_events,
                'error_events': error_events,
                'warning_events': warning_events,
                'info_events': info_events,
                'event_types': event_types,
                'event_levels': event_levels
            }

        except Exception as e:
            logger.error(f"Error calculating event metrics: {e}")
            return self._get_placeholder_event_metrics()

    # ============================================================================
    # MOVED FROM DATABASE_DATA_SERVICE: Event Location Methods
    # ============================================================================

    def calculate_event_location_mapping(self, events_data: pd.DataFrame,
                                        robot_locations: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        MOVED FROM database_data_service.py
        Map events to building locations.
        OPTIMIZED: Uses cached robot-building map.
        """
        try:
            if events_data.empty or robot_locations.empty:
                return {}

            # OPTIMIZED: Use cached robot-building mapping
            robot_building_map = self.get_robot_facility_map()
            if not robot_building_map:
                # If not cached, create it
                robot_building_map = self.set_robot_facility_map(robot_locations)

            # Add building column
            events_with_building = events_data.copy()
            events_with_building['building'] = events_with_building['robot_sn'].map(
                robot_building_map
            ).fillna('Unknown Building')

            # Vectorized level extraction
            events_with_building['level_lower'] = events_with_building['event_level'].astype(
                str
            ).str.lower()

            building_events = {}

            # Count events by building
            for building, building_group in events_with_building.groupby('building'):
                level_counts = building_group['level_lower'].value_counts()

                building_events[building] = {
                    'total_events': len(building_group),
                    'critical_events': 0,
                    'error_events': 0,
                    'warning_events': 0,
                    'info_events': 0
                }

                # Categorize events
                for level, count in level_counts.items():
                    if 'fatal' in level or 'critical' in level:
                        building_events[building]['critical_events'] += count
                    elif 'error' in level:
                        building_events[building]['error_events'] += count
                    elif 'warning' in level or 'warn' in level:
                        building_events[building]['warning_events'] += count
                    else:
                        building_events[building]['info_events'] += count

            logger.info(f"Mapped events to {len(building_events)} locations")
            return building_events

        except Exception as e:
            logger.error(f"Error mapping events to locations: {e}")
            return {}

    def calculate_event_type_by_location(self, events_data: pd.DataFrame,
                                        robot_locations: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        MOVED FROM database_data_service.py
        Calculate event type breakdown by location.
        OPTIMIZED: Uses cached robot-building map.
        """
        try:
            if events_data.empty or robot_locations.empty:
                return {}

            # OPTIMIZED: Use cached robot-building mapping
            robot_building_map = self.get_robot_facility_map()
            if not robot_building_map:
                robot_building_map = self.set_robot_facility_map(robot_locations)

            # Add building column
            events_with_building = events_data.copy()
            events_with_building['building'] = events_with_building['robot_sn'].map(
                robot_building_map
            ).fillna('Unknown Building')

            event_type_location_breakdown = {}

            # Two-level groupby
            for event_type, type_group in events_with_building.groupby('event_type'):
                if pd.isna(event_type):
                    continue

                event_type_location_breakdown[event_type] = {}

                # Count by building for this event type
                building_counts = type_group['building'].value_counts()

                for building, count in building_counts.items():
                    event_type_location_breakdown[event_type][building] = int(count)

            logger.info(f"Calculated event types for {len(event_type_location_breakdown)} types")
            return event_type_location_breakdown

        except Exception as e:
            logger.error(f"Error calculating event type by location: {e}")
            return {}

    # ============================================================================
    # MOVED FROM DATABASE_DATA_SERVICE: Map Coverage Methods
    # ============================================================================

    def calculate_map_coverage_metrics(self, tasks_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        MOVED FROM database_data_service.py
        Calculate detailed map coverage metrics.
        OPTIMIZED: Uses cached completed task counts.
        """
        logger.info("Calculating map coverage metrics")

        try:
            if tasks_data.empty or 'map_name' not in tasks_data.columns:
                logger.warning("No map data available")
                return []

            map_metrics = []

            # Single groupby
            for map_name, map_tasks in tasks_data.groupby('map_name'):
                if pd.isna(map_name):
                    continue

                # Vectorized calculations
                total_actual_area = map_tasks['actual_area'].fillna(0).sum() if 'actual_area' in map_tasks.columns else 0
                total_planned_area = map_tasks['plan_area'].fillna(0).sum() if 'plan_area' in map_tasks.columns else 0

                coverage_percentage = (total_actual_area / total_planned_area * 100) if total_planned_area > 0 else 0

                # OPTIMIZED: Use cached method for completed tasks
                completed_tasks = self._count_completed_tasks(map_tasks)
                total_tasks = len(map_tasks)

                map_metrics.append({
                    'map_name': map_name,
                    'coverage_percentage': round(coverage_percentage, 1),
                    'actual_area': round(total_actual_area, 0),
                    'planned_area': round(total_planned_area, 0),
                    'completed_tasks': completed_tasks,
                    'total_tasks': total_tasks,
                    'completion_rate': round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
                })

            # Sort by coverage
            map_metrics.sort(key=lambda x: x['coverage_percentage'], reverse=True)

            logger.info(f"Calculated coverage for {len(map_metrics)} maps")
            return map_metrics

        except Exception as e:
            logger.error(f"Error calculating map coverage: {e}")
            return []

    # ============================================================================
    # MOVED FROM DATABASE_DATA_SERVICE: Robot Health Scores
    # ============================================================================

    def calculate_robot_health_scores(self, operation_history: pd.DataFrame,
                                    tasks_data: pd.DataFrame,
                                    target_robots: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        MOVED FROM database_data_service.py
        Calculate health scores for all robots based on the reporting period data.
        OPTIMIZED: Uses cached status counts.
        """
        logger.info(f"Calculating health scores for {len(target_robots)} robots")

        try:
            health_scores = {}

            for robot_sn in target_robots:
                # Filter data for this robot
                robot_history = operation_history[
                    operation_history['robot_sn'] == robot_sn
                ] if not operation_history.empty else pd.DataFrame()

                robot_tasks = tasks_data[
                    tasks_data['robot_sn'] == robot_sn
                ] if not tasks_data.empty else pd.DataFrame()

                if robot_history.empty and robot_tasks.empty:
                    logger.warning(f"No data available for robot {robot_sn}, skipping health score")
                    health_scores[robot_sn] = {}
                    continue

                # === AVAILABILITY SCORE ===
                if not robot_history.empty and 'status' in robot_history.columns:
                    online_count = len(robot_history[robot_history['status'].str.lower() == 'online'])
                    total_count = len(robot_history)
                    availability_score = (online_count / total_count * 100) if total_count > 0 else 100.0
                else:
                    availability_score = 100.0

                # === TASK SUCCESS SCORE ===
                task_success_score = None
                if not robot_tasks.empty and 'status' in robot_tasks.columns:
                    # OPTIMIZED: Use cached status counts
                    status_counts = self.get_cached_status_counts(robot_tasks)
                    total_tasks = len(robot_tasks)
                    task_success_score = (status_counts['completed'] / total_tasks * 100) if total_tasks > 0 else 0

                # === EFFICIENCY SCORE ===
                efficiency_score = None
                if not robot_tasks.empty and 'efficiency' in robot_tasks.columns and not robot_tasks['efficiency'].isna().all():
                    avg_efficiency = robot_tasks['efficiency'].fillna(0).mean()
                    # Map efficiency to 0-100 scale
                    if avg_efficiency >= 700:
                        efficiency_score = 100
                    elif avg_efficiency >= 600:
                        efficiency_score = 95
                    elif avg_efficiency >= 500:
                        efficiency_score = 85
                    elif avg_efficiency >= 400:
                        efficiency_score = 75
                    elif avg_efficiency >= 300:
                        efficiency_score = 60
                    elif avg_efficiency >= 200:
                        efficiency_score = 50
                    elif avg_efficiency >= 100:
                        efficiency_score = 30
                    else:
                        efficiency_score = 10

                # === BATTERY SOH SCORE ===
                battery_soh_score = None
                if not robot_history.empty and 'battery_soh' in robot_history.columns and not robot_history['battery_soh'].isna().all():
                    battery_soh = robot_history['battery_soh'].dropna()
                    if not battery_soh.empty:
                        try:
                            soh_values = battery_soh.astype(str).str.replace(
                                '+', ''
                            ).str.replace('%', '').str.strip()
                            soh_numeric = pd.to_numeric(soh_values, errors='coerce').dropna()
                            if not soh_numeric.empty:
                                battery_soh_score = soh_numeric.mean()
                        except Exception as e:
                            logger.warning(f"Error parsing battery SOH for {robot_sn}: {e}")

                # === MODE PERFORMANCE SCORE ===
                mode_performance_score = None
                if not robot_tasks.empty and 'mode' in robot_tasks.columns and 'battery_usage' in robot_tasks.columns and 'actual_area' in robot_tasks.columns:
                    if not robot_tasks['actual_area'].isna().all() and not robot_tasks['battery_usage'].isna().all():
                        mode_performance_score = 100

                        for mode in robot_tasks['mode'].unique():
                            if pd.isna(mode):
                                continue

                            mode_tasks = robot_tasks[robot_tasks['mode'] == mode]
                            mode_tasks_filtered = mode_tasks[mode_tasks['battery_usage'] > 0]

                            if mode_tasks_filtered.empty:
                                continue

                            max_area = (mode_tasks_filtered['actual_area'] * (100 / mode_tasks_filtered['battery_usage'])).max()

                            if mode.lower() == 'sweeping':
                                if max_area >= 2700:
                                    mode_performance_score = max(mode_performance_score, 100)
                                elif max_area >= 2400:
                                    mode_performance_score = max(mode_performance_score, 90)
                                elif max_area >= 2100:
                                    mode_performance_score = max(mode_performance_score, 80)
                                elif max_area >= 1800:
                                    mode_performance_score = max(mode_performance_score, 70)
                                elif max_area >= 1500:
                                    mode_performance_score = max(mode_performance_score, 60)
                                elif max_area >= 1200:
                                    mode_performance_score = max(mode_performance_score, 50)
                                elif max_area >= 900:
                                    mode_performance_score = max(mode_performance_score, 40)
                                elif max_area >= 600:
                                    mode_performance_score = max(mode_performance_score, 30)
                                elif max_area >= 300:
                                    mode_performance_score = max(mode_performance_score, 20)
                                elif max_area > 0:
                                    mode_performance_score = max(mode_performance_score, 10)

                            elif mode.lower() == 'scrubbing':
                                if max_area >= 1800:
                                    mode_performance_score = max(mode_performance_score, 100)
                                elif max_area >= 1600:
                                    mode_performance_score = max(mode_performance_score, 90)
                                elif max_area >= 1400:
                                    mode_performance_score = max(mode_performance_score, 80)
                                elif max_area >= 1200:
                                    mode_performance_score = max(mode_performance_score, 70)
                                elif max_area >= 1000:
                                    mode_performance_score = max(mode_performance_score, 60)
                                elif max_area >= 800:
                                    mode_performance_score = max(mode_performance_score, 50)
                                elif max_area >= 600:
                                    mode_performance_score = max(mode_performance_score, 40)
                                elif max_area >= 400:
                                    mode_performance_score = max(mode_performance_score, 30)
                                elif max_area >= 200:
                                    mode_performance_score = max(mode_performance_score, 20)
                                elif max_area > 0:
                                    mode_performance_score = max(mode_performance_score, 10)

                # === CALCULATE OVERALL HEALTH SCORE ===
                base_weights = {
                    'availability': 0.4,
                    'task_success': 0.2,
                    'efficiency': 0.2,
                    'mode_performance': 0.1,
                    'battery_soh': 0.1
                }

                component_scores = {}
                active_components = {}
                total_weight = 0

                # Availability is always available
                component_scores['Availability'] = availability_score
                active_components['availability'] = availability_score
                total_weight += base_weights['availability']

                # Add optional components if available
                if task_success_score is not None:
                    component_scores['Task Success'] = task_success_score
                    active_components['task_success'] = task_success_score
                    total_weight += base_weights['task_success']

                if efficiency_score is not None:
                    component_scores['Efficiency'] = efficiency_score
                    active_components['efficiency'] = efficiency_score
                    total_weight += base_weights['efficiency']

                if mode_performance_score is not None:
                    component_scores['Mode Performance'] = mode_performance_score
                    active_components['mode_performance'] = mode_performance_score
                    total_weight += base_weights['mode_performance']

                if battery_soh_score is not None:
                    component_scores['Battery Health'] = battery_soh_score
                    active_components['battery_soh'] = battery_soh_score
                    total_weight += base_weights['battery_soh']

                # Calculate weighted average
                overall_health_score = 0
                for component_key, component_value in active_components.items():
                    weight = base_weights[component_key]
                    normalized_weight = weight / total_weight
                    overall_health_score += component_value * normalized_weight

                # Determine rating
                if overall_health_score >= 90:
                    rating = 'Excellent'
                elif overall_health_score >= 80:
                    rating = 'Good'
                elif overall_health_score >= 60:
                    rating = 'Fair'
                else:
                    rating = 'Poor'

                health_scores[robot_sn] = {
                    'robot_sn': robot_sn,
                    'overall_health_score': round(overall_health_score, 1),
                    'overall_health_rating': rating,
                    'availability_score': round(availability_score, 1),
                    'task_success_score': round(task_success_score, 1) if task_success_score is not None else None,
                    'efficiency_score': round(efficiency_score, 1) if efficiency_score is not None else None,
                    'mode_performance_score': round(mode_performance_score, 1) if mode_performance_score is not None else None,
                    'battery_soh_score': round(battery_soh_score, 1) if battery_soh_score is not None else None,
                    'component_scores': {k: round(v, 1) for k, v in component_scores.items()}
                }

            logger.info(f"Calculated health scores for {len(health_scores)} robots")
            return health_scores

        except Exception as e:
            logger.error(f"Error calculating robot health scores: {e}", exc_info=True)
            return {}

    # ============================================================================
    # MOVED FROM DATABASE_DATA_SERVICE: Daily Efficiency Trends
    # ============================================================================

    def calculate_daily_task_efficiency_by_location(self, tasks_data: pd.DataFrame,
                                                    robot_locations: pd.DataFrame,
                                                    start_date: str, end_date: str) -> Dict[str, Dict[str, List]]:
        """
        MOVED FROM database_data_service.py
        Calculate daily efficiency by location.
        OPTIMIZED: Uses cached robot-facility map.
        """
        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create date range
            date_range = [
                start_dt + timedelta(days=i)
                for i in range((end_dt - start_dt).days + 1)
            ]

            # OPTIMIZED: Use cached robot-facility map
            robot_facility_map = self.get_robot_facility_map()
            if not robot_facility_map:
                robot_facility_map = self.set_robot_facility_map(robot_locations)

            # Add facility and date columns
            tasks_with_context = tasks_data.copy()
            tasks_with_context['facility'] = tasks_with_context['robot_sn'].map(
                robot_facility_map
            )
            tasks_with_context['start_time_dt'] = pd.to_datetime(
                tasks_with_context['start_time'], errors='coerce'
            )
            tasks_with_context = tasks_with_context[
                tasks_with_context['start_time_dt'].notna()
            ]

            # Filter date range
            tasks_filtered = tasks_with_context[
                (tasks_with_context['start_time_dt'].dt.date >= start_dt.date()) &
                (tasks_with_context['start_time_dt'].dt.date <= end_dt.date())
            ]

            if tasks_filtered.empty:
                return {}

            # Add calculated columns - VECTORIZED
            tasks_filtered['date_str'] = tasks_filtered['start_time_dt'].dt.strftime('%m/%d')
            tasks_filtered['hours'] = pd.to_numeric(
                tasks_filtered['duration'], errors='coerce'
            ).fillna(0) / 3600
            tasks_filtered['actual_area'] = pd.to_numeric(
                tasks_filtered['actual_area'], errors='coerce'
            ).fillna(0)
            tasks_filtered['plan_area'] = pd.to_numeric(
                tasks_filtered['plan_area'], errors='coerce'
            ).fillna(0)

            location_efficiency = {}

            # Multi-level groupby
            for facility, facility_group in tasks_filtered.groupby('facility'):
                if pd.isna(facility):
                    continue

                # Aggregate by date
                daily_agg = facility_group.groupby('date_str').agg({
                    'hours': 'sum',
                    'actual_area': 'sum',
                    'plan_area': 'sum'
                }).reset_index()

                # Initialize with zeros for all dates
                daily_data = {date.strftime('%m/%d'): {
                    'running_hours': 0,
                    'coverage_percentage': 0
                } for date in date_range}

                # Fill in actual data
                for _, row in daily_agg.iterrows():
                    date_str = row['date_str']
                    if date_str in daily_data:
                        coverage = (row['actual_area'] / row['plan_area'] * 100) if row['plan_area'] > 0 else 0
                        daily_data[date_str]['running_hours'] = row['hours']
                        daily_data[date_str]['coverage_percentage'] = min(coverage, 100)

                # Convert to lists
                dates = list(daily_data.keys())
                location_efficiency[facility] = {
                    'dates': dates,
                    'running_hours': [round(daily_data[d]['running_hours'], 2) for d in dates],
                    'coverage_percentages': [round(daily_data[d]['coverage_percentage'], 1) for d in dates]
                }

            logger.info(f"Calculated daily efficiency for {len(location_efficiency)} locations")
            return location_efficiency

        except Exception as e:
            logger.error(f"Error calculating daily task efficiency: {e}")
            return {}

    # ============================================================================
    # MOVED FROM DATABASE_DATA_SERVICE: Financial Trends
    # ============================================================================

    def calculate_daily_financial_trends(self, tasks_data: pd.DataFrame,
                                        start_date: str, end_date: str) -> Dict[str, List]:
        """
        MOVED FROM database_data_service.py
        Calculate daily financial trends.
        """
        try:
            logger.info("Calculating daily financial trends")

            # Constants
            HOURLY_WAGE = 25.0
            HUMAN_CLEANING_SPEED = 1000.0

            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create date range
            date_range = [
                start_dt + timedelta(days=i)
                for i in range((end_dt - start_dt).days + 1)
            ]

            daily_data = {
                date.strftime('%m/%d'): {'area_cleaned': 0}
                for date in date_range
            }

            # Process tasks
            if not tasks_data.empty and 'start_time' in tasks_data.columns:
                tasks_with_dates = tasks_data.copy()
                tasks_with_dates['start_time_dt'] = pd.to_datetime(
                    tasks_with_dates['start_time'], errors='coerce'
                )
                tasks_filtered = tasks_with_dates[
                    (tasks_with_dates['start_time_dt'].dt.date >= start_dt.date()) &
                    (tasks_with_dates['start_time_dt'].dt.date <= end_dt.date())
                ]

                if not tasks_filtered.empty:
                    # Vectorized calculations
                    tasks_filtered['date_str'] = tasks_filtered['start_time_dt'].dt.strftime('%m/%d')
                    tasks_filtered['area_sqft'] = pd.to_numeric(
                        tasks_filtered['actual_area'], errors='coerce'
                    ).fillna(0) * 10.764

                    # Aggregate by date
                    daily_agg = tasks_filtered.groupby('date_str')['area_sqft'].sum()

                    for date_str, area in daily_agg.items():
                        if date_str in daily_data:
                            daily_data[date_str]['area_cleaned'] = area

            # Calculate trends - VECTORIZED
            dates = list(daily_data.keys())
            hours_saved_trend = []
            savings_trend = []

            for date in dates:
                area_cleaned = daily_data[date]['area_cleaned']
                hours_saved = area_cleaned / HUMAN_CLEANING_SPEED if HUMAN_CLEANING_SPEED > 0 else 0
                human_cost = hours_saved * HOURLY_WAGE
                savings = human_cost  # Robot cost is 0

                hours_saved_trend.append(round(hours_saved, 1))
                savings_trend.append(round(savings, 2))

            logger.info(f"Calculated financial trends for {len(dates)} days")
            return {
                'dates': dates,
                'hours_saved_trend': hours_saved_trend,
                'savings_trend': savings_trend
            }

        except Exception as e:
            logger.error(f"Error calculating daily financial trends: {e}")
            return {'dates': [], 'hours_saved_trend': [], 'savings_trend': []}

    # ============================================================================
    # FACILITY-SPECIFIC METRICS (OPTIMIZED with cached mappings)
    # ============================================================================

    def calculate_facility_efficiency_metrics(self, tasks_data: pd.DataFrame,
                                             robot_locations: pd.DataFrame,
                                             start_date: str, end_date: str) -> Dict[str, Dict[str, Any]]:
        """
        Calculate water/time efficiency for facilities.
        OPTIMIZED: Uses cached robot-facility map and duration sums.
        """
        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            # OPTIMIZED: Use cached robot-facility mapping
            robot_facility_map = self.get_robot_facility_map()
            if not robot_facility_map:
                robot_facility_map = self.set_robot_facility_map(robot_locations)

            # Add facility column to tasks
            tasks_with_facility = tasks_data.copy()
            tasks_with_facility['facility'] = tasks_with_facility['robot_sn'].map(
                robot_facility_map
            )

            facility_metrics = {}

            # Group by facility once
            for building_name, facility_tasks in tasks_with_facility.groupby('facility'):
                if pd.isna(building_name):
                    continue

                # Vectorized calculations
                total_area_sqm = facility_tasks['actual_area'].fillna(0).sum() if 'actual_area' in facility_tasks.columns else 0
                total_area_sqft = total_area_sqm * 10.764

                water_consumption = facility_tasks['water_consumption'].fillna(0).sum() if 'water_consumption' in facility_tasks.columns else 0
                water_efficiency = total_area_sqft / water_consumption if water_consumption > 0 else 0

                # OPTIMIZED: Use cached duration sum
                total_time_hours = self.get_cached_duration_sum(facility_tasks)
                time_efficiency = total_area_sqft / total_time_hours if total_time_hours > 0 else 0

                # OPTIMIZED: Use cached days calculation
                facility_days_info = self.calculate_facility_days_with_tasks_and_period(
                    facility_tasks, start_date, end_date
                )

                facility_metrics[building_name] = {
                    'water_efficiency': round(water_efficiency, 1),
                    'time_efficiency': round(time_efficiency, 1),
                    'total_area_cleaned': round(total_area_sqft, 0),
                    'total_time_hours': round(total_time_hours, 1),
                    'days_with_tasks': facility_days_info['days_with_tasks'],
                    'period_length': facility_days_info['period_length'],
                    'days_ratio': facility_days_info['days_ratio']
                }

            return facility_metrics

        except Exception as e:
            logger.error(f"Error calculating facility efficiency metrics: {e}")
            return {}

    def calculate_facility_days_with_tasks_and_period(self, facility_tasks: pd.DataFrame,
                                                      start_date: str, end_date: str) -> Dict[str, Any]:
        """Calculate facility-specific days with tasks and period length"""
        try:
            # OPTIMIZED: Use cached days calculation
            facility_days = self.get_cached_days_with_tasks(facility_tasks)
            period_length = self._calculate_period_length(start_date, end_date)

            return {
                'days_with_tasks': facility_days,
                'period_length': period_length,
                'days_ratio': f"{facility_days}/{period_length}"
            }
        except Exception as e:
            logger.error(f"Error calculating facility days: {e}")
            return {'days_with_tasks': 0, 'period_length': 0, 'days_ratio': "0/0"}

    def calculate_facility_coverage_by_day(self, tasks_data: pd.DataFrame,
                                       robot_locations: pd.DataFrame,
                                       facility_name: str,
                                       start_date: str, end_date: str) -> Dict[str, str]:
        """
        Calculate highest/lowest coverage days for a facility.
        Coverage is calculated per day first (sum(actual_area)/sum(plan_area)),
        then averaged by weekday to get weekday coverage. Days without tasks are treated as 0 coverage.
        """
        try:
            if tasks_data.empty or robot_locations.empty:
                return {'highest_coverage_day': 'N/A', 'lowest_coverage_day': 'N/A'}

            # Use cached robot-facility map if available
            robot_facility_map = self.get_robot_facility_map()
            if not robot_facility_map:
                robot_facility_map = self.set_robot_facility_map(robot_locations)

            # Get facility robots
            facility_robots = [
                robot_sn for robot_sn, building in robot_facility_map.items()
                if building == facility_name
            ]
            facility_tasks = tasks_data[tasks_data['robot_sn'].isin(facility_robots)]

            if facility_tasks.empty or 'start_time' not in facility_tasks.columns:
                return {'highest_coverage_day': 'N/A', 'lowest_coverage_day': 'N/A'}

            # Parse dates
            tasks_with_dates = self._parse_datetime_column(facility_tasks, 'start_time')
            if tasks_with_dates.empty:
                return {'highest_coverage_day': 'N/A', 'lowest_coverage_day': 'N/A'}

            # Fill missing areas
            tasks_with_dates['actual_area'] = tasks_with_dates.get('actual_area', 0).fillna(0)
            tasks_with_dates['plan_area'] = tasks_with_dates.get('plan_area', 0).fillna(0)

            # Aggregate coverage per day
            tasks_with_dates['date'] = tasks_with_dates['start_time_dt'].dt.date
            daily_coverage = tasks_with_dates.groupby('date').apply(
                lambda df: (df['actual_area'].sum() / df['plan_area'].sum() * 100)
                if df['plan_area'].sum() > 0 else 0
            ).reset_index(name='daily_coverage')

            # Create complete date range and merge
            full_dates = pd.DataFrame({'date': pd.date_range(start=start_date, end=end_date)})
            full_dates['date'] = full_dates['date'].dt.date
            daily_coverage = pd.merge(full_dates, daily_coverage, on='date', how='left').fillna(0)

            # Add weekday
            daily_coverage['weekday'] = pd.to_datetime(daily_coverage['date']).dt.day_name()

            # Average daily coverage by weekday
            weekday_coverage = daily_coverage.groupby('weekday')['daily_coverage'].mean().to_dict()

            if not weekday_coverage:
                return {'highest_coverage_day': 'N/A', 'lowest_coverage_day': 'N/A'}

            highest_day = max(weekday_coverage, key=weekday_coverage.get)
            lowest_day = min(weekday_coverage, key=weekday_coverage.get)

            return {
                'highest_coverage_day': highest_day,
                'lowest_coverage_day': lowest_day
            }

        except Exception as e:
            logger.error(f"Error calculating facility coverage by day: {e}")
            return {'highest_coverage_day': 'N/A', 'lowest_coverage_day': 'N/A'}

    def calculate_facility_breakdown_metrics(self, tasks_data: pd.DataFrame,
                                           robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Calculate comprehensive facility breakdown.
        OPTIMIZED: Uses cached robot-facility map, status counts, and duration sums.
        """
        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            # OPTIMIZED: Use cached robot-facility mapping
            robot_facility_map = self.get_robot_facility_map()
            if not robot_facility_map:
                robot_facility_map = self.set_robot_facility_map(robot_locations)

            tasks_with_facility = tasks_data.copy()
            tasks_with_facility['facility'] = tasks_with_facility['robot_sn'].map(
                robot_facility_map
            )

            facility_metrics = {}

            # Single groupby for all facilities
            for building_name, facility_tasks in tasks_with_facility.groupby('facility'):
                if pd.isna(building_name):
                    continue

                # Basic metrics - OPTIMIZED with cached calculations
                total_tasks = len(facility_tasks)
                status_counts = self.get_cached_status_counts(facility_tasks)

                # Area calculations
                actual_area = facility_tasks['actual_area'].fillna(0).sum() if 'actual_area' in facility_tasks.columns else 0
                planned_area = facility_tasks['plan_area'].fillna(0).sum() if 'plan_area' in facility_tasks.columns else 0

                coverage_efficiency = (actual_area / planned_area * 100) if planned_area > 0 else 0
                completion_rate = (status_counts['completed'] / total_tasks * 100) if total_tasks > 0 else 0

                # OPTIMIZED: Use cached duration sum
                running_hours = self.get_cached_duration_sum(facility_tasks)

                # Resource consumption
                energy = facility_tasks['consumption'].fillna(0).sum() if 'consumption' in facility_tasks.columns else 0
                water = facility_tasks['water_consumption'].fillna(0).sum() if 'water_consumption' in facility_tasks.columns else 0

                power_efficiency = actual_area / energy if energy > 0 else 0

                # Primary mode
                primary_mode = "Mixed"
                if 'mode' in facility_tasks.columns:
                    mode_counts = facility_tasks['mode'].value_counts()
                    if not mode_counts.empty:
                        primary_mode = mode_counts.index[0]

                # Average duration
                avg_duration = 0
                if 'duration' in facility_tasks.columns:
                    durations = pd.to_numeric(facility_tasks['duration'], errors='coerce').dropna()
                    avg_duration = (durations.mean() / 60) if len(durations) > 0 else 0

                # Coverage by day
                coverage_by_day = self.calculate_facility_coverage_by_day(
                    tasks_data, robot_locations, building_name
                )

                facility_metrics[building_name] = {
                    'total_tasks': total_tasks,
                    'completed_tasks': status_counts['completed'],
                    'cancelled_tasks': status_counts['cancelled'],
                    'completion_rate': round(completion_rate, 1),
                    'area_cleaned': round(actual_area, 0),
                    'planned_area': round(planned_area, 0),
                    'coverage_efficiency': round(coverage_efficiency, 1),
                    'running_hours': round(running_hours, 1),
                    'energy_consumption': round(energy, 1),
                    'water_consumption': round(water, 1),
                    'power_efficiency': round(power_efficiency, 0),
                    'robot_count': len(robot_locations[robot_locations['building_name'] == building_name]),
                    'primary_mode': primary_mode,
                    'avg_task_duration': round(avg_duration, 1),
                    'cancellation_rate': round((status_counts['cancelled'] / total_tasks * 100), 1) if total_tasks > 0 else 0,
                    'highest_coverage_day': coverage_by_day['highest_coverage_day'],
                    'lowest_coverage_day': coverage_by_day['lowest_coverage_day']
                }

            return facility_metrics

        except Exception as e:
            logger.error(f"Error calculating facility breakdown: {e}")
            return {}

    # ============================================================================
    # MAP PERFORMANCE METRICS (OPTIMIZED with cached mappings)
    # ============================================================================

    def calculate_map_performance_by_building(self, tasks_data: pd.DataFrame,
                                         robot_locations: pd.DataFrame,
                                         performance_targets: pd.DataFrame = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate map performance organized by building.
        OPTIMIZED: Uses cached robot-building map and duration sums.
        UPDATED: Includes performance target analysis when targets are provided.
        """
        try:
            if tasks_data.empty or 'map_name' not in tasks_data.columns:
                return {}

            # OPTIMIZED: Use cached robot-building mapping
            robot_building_map = self.get_robot_facility_map()
            if not robot_building_map:
                robot_building_map = self.set_robot_facility_map(robot_locations)

            tasks_with_building = tasks_data.copy()
            tasks_with_building['building'] = tasks_with_building['robot_sn'].map(
                robot_building_map
            ).fillna('Unknown Building')

            # Analyze tasks against targets (if provided)
            target_analysis_by_map = {}
            if performance_targets is not None and not performance_targets.empty:
                target_analysis_by_map = self._analyze_tasks_against_targets(tasks_data, performance_targets)
                logger.info(f"Performance target analysis completed for {len(target_analysis_by_map)} maps")

            result = {}

            # Two-level groupby
            for building_name, building_tasks in tasks_with_building.groupby('building'):
                result[building_name] = []

                for map_name, map_tasks in building_tasks.groupby('map_name'):
                    if pd.isna(map_name):
                        continue

                    # Vectorized calculations
                    total_actual_area = map_tasks['actual_area'].fillna(0).sum() if 'actual_area' in map_tasks.columns else 0
                    total_planned_area = map_tasks['plan_area'].fillna(0).sum() if 'plan_area' in map_tasks.columns else 0
                    coverage_percentage = (total_actual_area / total_planned_area * 100) if total_planned_area > 0 else 0

                    # Task completion - OPTIMIZED with cached method
                    completed_tasks = self._count_completed_tasks(map_tasks)
                    total_tasks = len(map_tasks)
                    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                    # OPTIMIZED: Use cached duration sum
                    running_hours = self.get_cached_duration_sum(map_tasks)

                    # Efficiency metrics
                    area_sqft = total_actual_area * 10.764
                    energy = map_tasks['consumption'].fillna(0).sum() if 'consumption' in map_tasks.columns else 0
                    water = map_tasks['water_consumption'].fillna(0).sum() if 'water_consumption' in map_tasks.columns else 0

                    power_efficiency = area_sqft / energy if energy > 0 else 0
                    time_efficiency = area_sqft / running_hours if running_hours > 0 else 0
                    water_efficiency = area_sqft / water if water > 0 else 0

                    # OPTIMIZED: Use cached days calculation
                    map_days_with_tasks = self.get_cached_days_with_tasks(map_tasks)

                    # Base map performance data
                    map_data = {
                        'map_name': map_name,
                        'coverage_percentage': round(coverage_percentage, 1),
                        'area_cleaned': round(area_sqft, 0),
                        'completion_rate': round(completion_rate, 1),
                        'running_hours': round(running_hours, 1),
                        'power_efficiency': round(power_efficiency, 1),
                        'time_efficiency': round(time_efficiency, 1),
                        'water_efficiency': round(water_efficiency, 1),
                        'days_with_tasks': map_days_with_tasks,
                        'total_tasks': total_tasks
                    }

                    # NEW: Add target performance analysis if available for this map
                    if map_name in target_analysis_by_map:
                        analysis = target_analysis_by_map[map_name]
                        map_data['target_performance'] = {
                            'tasks_below_efficiency_target': analysis['tasks_below_efficiency_target'],
                            'tasks_below_area_target': analysis['tasks_below_area_target'],
                            'tasks_exceeding_duration_target': analysis['tasks_exceeding_duration_target'],
                            'total_tasks_analyzed': analysis['total_tasks'],
                            'efficiency_compliance_rate': analysis['efficiency_compliance_rate'],
                            'area_compliance_rate': analysis['area_compliance_rate'],
                            'duration_compliance_rate': analysis['duration_compliance_rate'],
                            'targets': analysis['targets']
                        }

                    result[building_name].append(map_data)

                # Sort by coverage
                result[building_name].sort(key=lambda x: x['coverage_percentage'], reverse=True)

            return result

        except Exception as e:
            logger.error(f"Error calculating map performance: {e}", exc_info=True)
            return {}


    def _analyze_tasks_against_targets(self, tasks_data: pd.DataFrame,
                                       performance_targets: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Analyze tasks against performance targets by map_name.
        Helper method for calculate_map_performance_by_building.

        Returns:
        {
            'map_name_1': {
                'tasks_below_efficiency_target': 5,
                'tasks_below_area_target': 3,
                'tasks_exceeding_duration_target': 2,
                'total_tasks': 10,
                'efficiency_compliance_rate': 50.0,
                'area_compliance_rate': 70.0,
                'duration_compliance_rate': 80.0,
                'targets': {...}
            }
        }
        """
        try:
            if tasks_data.empty or performance_targets.empty:
                return {}

            # Ensure required columns exist
            required_task_cols = ['map_name', 'efficiency', 'actual_area', 'duration']
            missing_cols = [col for col in required_task_cols if col not in tasks_data.columns]
            if missing_cols:
                logger.warning(f"Missing columns for target analysis: {missing_cols}")
                return {}

            target_analysis = {}

            # Group tasks by map_name
            for map_name, map_tasks in tasks_data.groupby('map_name'):
                if pd.isna(map_name) or map_name == '':
                    continue

                # Check if we have targets for this map
                map_targets = performance_targets[performance_targets['map_name'] == map_name]

                if map_targets.empty:
                    # No targets defined for this map - skip
                    continue

                # Get the target values (first row if multiple)
                target = map_targets.iloc[0]

                total_tasks = len(map_tasks)
                below_efficiency = 0
                below_area = 0
                exceeding_duration = 0

                # Analyze each task
                for _, task in map_tasks.iterrows():
                    # 1. Check efficiency target
                    if pd.notna(target.get('target_efficiency')):
                        task_efficiency = pd.to_numeric(task['efficiency'], errors='coerce')
                        if pd.notna(task_efficiency) and task_efficiency < target['target_efficiency']:
                            below_efficiency += 1

                    # 2. Check area target (depends on area_storage_type)
                    actual_area_sqm = pd.to_numeric(task['actual_area'], errors='coerce')
                    if pd.notna(actual_area_sqm):
                        actual_area_sqft = actual_area_sqm * 10.764  # Convert to sqft

                        area_storage_type = target.get('area_storage_type', '').lower()

                        if area_storage_type == 'value':
                            # Compare against absolute value in sqft
                            target_area_value = pd.to_numeric(target.get('target_area_value'), errors='coerce')
                            if pd.notna(target_area_value) and actual_area_sqm < target_area_value:
                                below_area += 1

                        elif area_storage_type == 'percentage':
                            # Compare against percentage of plan_area
                            if 'plan_area' in task.index and pd.notna(task['plan_area']):
                                plan_area_sqm = pd.to_numeric(task['plan_area'], errors='coerce')
                                if pd.notna(plan_area_sqm) and plan_area_sqm > 0:
                                    plan_area_sqft = plan_area_sqm * 10.764
                                    actual_percentage = (actual_area_sqft / plan_area_sqft * 100)

                                    target_area_pct = pd.to_numeric(target.get('target_area_percentage'), errors='coerce')
                                    if pd.notna(target_area_pct) and actual_percentage < target_area_pct:
                                        below_area += 1

                    # 3. Check duration target (tasks exceeding target are below performance)
                    target_duration = pd.to_numeric(target.get('target_duration'), errors='coerce')
                    if pd.notna(target_duration):
                        task_duration = pd.to_numeric(task['duration'], errors='coerce')
                        if pd.notna(task_duration):
                            # Duration in tasks is in seconds, target_duration is also in seconds
                            # Tasks EXCEEDING target duration are considered poor performance
                            if task_duration > target_duration:
                                exceeding_duration += 1

                # Calculate compliance rates
                efficiency_compliance = round((total_tasks - below_efficiency) / total_tasks * 100, 1) if total_tasks > 0 else 0
                area_compliance = round((total_tasks - below_area) / total_tasks * 100, 1) if total_tasks > 0 else 0
                duration_compliance = round((total_tasks - exceeding_duration) / total_tasks * 100, 1) if total_tasks > 0 else 0

                # Store results
                target_analysis[map_name] = {
                    'tasks_below_efficiency_target': below_efficiency,
                    'tasks_below_area_target': below_area,
                    'tasks_exceeding_duration_target': exceeding_duration,
                    'total_tasks': total_tasks,
                    'efficiency_compliance_rate': efficiency_compliance,
                    'area_compliance_rate': area_compliance,
                    'duration_compliance_rate': duration_compliance,
                    'targets': {
                        'efficiency': float(target['target_efficiency']) if pd.notna(target.get('target_efficiency')) else None,
                        'area_value': float(target['target_area_value']) if pd.notna(target.get('target_area_value')) else None,
                        'area_percentage': float(target['target_area_percentage']) if pd.notna(target.get('target_area_percentage')) else None,
                        'area_type': str(target['area_storage_type']) if pd.notna(target.get('area_storage_type')) else None,
                        'duration_seconds': int(target['target_duration']) if pd.notna(target.get('target_duration')) else None
                    }
                }

                logger.debug(f"Map '{map_name}': {below_efficiency}/{total_tasks} below efficiency, "
                            f"{below_area}/{total_tasks} below area, {exceeding_duration}/{total_tasks} exceeding duration")

            return target_analysis

        except Exception as e:
            logger.error(f"Error analyzing tasks against targets: {e}", exc_info=True)
            return {}

    def calculate_map_days_with_tasks(self, map_df: pd.DataFrame) -> int:
        """Calculate days with tasks for a specific map - uses cached calculation"""
        return self.get_cached_days_with_tasks(map_df)

    def calculate_facility_days_with_tasks(self, facility_tasks: pd.DataFrame) -> int:
        """Calculate days with tasks for a specific facility - uses cached calculation"""
        return self.get_cached_days_with_tasks(facility_tasks)

    # ============================================================================
    # INDIVIDUAL ROBOT PERFORMANCE (OPTIMIZED with cached calculations)
    # ============================================================================

    def calculate_individual_robot_performance(self, tasks_data: pd.DataFrame,
                                           charging_data: pd.DataFrame,
                                           robot_status: pd.DataFrame,
                                           operation_history: pd.DataFrame = None,
                                           period_length: int = 0) -> List[Dict[str, Any]]:
        """
        Calculate detailed performance for individual robots
        FIXED: Proper error handling and empty data handling
        """
        try:
            # Check if we have robot data
            if robot_status.empty:
                logger.warning("No robot status data available for individual robot performance")
                return []

            robot_metrics = []

            # Pre-group tasks and charging by robot (may be empty)
            robot_tasks_groups = {}
            if not tasks_data.empty and 'robot_sn' in tasks_data.columns:
                try:
                    for robot_sn, robot_tasks in tasks_data.groupby('robot_sn'):
                        robot_tasks_groups[robot_sn] = robot_tasks
                except Exception as e:
                    logger.error(f"Error grouping tasks by robot: {e}")

            robot_charging_groups = {}
            if not charging_data.empty and 'robot_sn' in charging_data.columns:
                try:
                    for robot_sn, robot_charging in charging_data.groupby('robot_sn'):
                        robot_charging_groups[robot_sn] = robot_charging
                except Exception as e:
                    logger.error(f"Error grouping charging by robot: {e}")

            # Process each robot
            for idx, robot in robot_status.iterrows():
                try:
                    robot_sn = robot.get('robot_sn')
                    if not robot_sn or pd.isna(robot_sn):
                        logger.warning(f"Skipping robot with missing serial number at index {idx}")
                        continue

                    # Get data for this robot (may be empty)
                    robot_tasks = robot_tasks_groups.get(robot_sn, pd.DataFrame())
                    robot_charging = robot_charging_groups.get(robot_sn, pd.DataFrame())

                    # Handle robot with NO TASKS
                    if robot_tasks.empty:
                        logger.info(f"Robot {robot_sn} has no tasks in this period")

                        # Calculate uptime/downtime even without tasks
                        try:
                            uptime_metrics = self.calculate_uptime_downtime_metrics(
                                operation_history if operation_history is not None else pd.DataFrame(),
                                robot_tasks,  # Empty, but still pass it
                                robot_charging,
                                robot_sn,
                                period_length
                            )
                        except Exception as e:
                            logger.warning(f"Error calculating uptime for robot {robot_sn} without tasks: {e}")
                            uptime_metrics = {
                                'uptime_hours': 0.0,
                                'downtime_hours': 0.0,
                                'idle_hours': 0.0,
                                'working_hours': 0.0,
                                'charging_hours': 0.0,
                                'charging_ratio': 0.0,
                                'uptime_ratio': 0.0,
                                'working_ratio': 0.0,
                                'idle_ratio': 0.0,
                                'utilization_score': 0.0
                            }

                        robot_metrics.append({
                            'robot_id': robot_sn,
                            'robot_name': robot.get('robot_name', f'Robot {robot_sn}'),
                            'location': self._get_robot_location_name(robot),
                            'total_tasks': 0,
                            'tasks_completed': 0,
                            'total_area_cleaned': 0,
                            'average_coverage': 0.0,
                            'days_with_tasks': 0,
                            'completion_rate': 0.0,
                            'running_hours': 0.0,
                            'avg_efficiency': 0.0,
                            'charging_sessions': len(robot_charging) if not robot_charging.empty else 0,
                            'battery_level': robot.get('battery_level', 0),
                            'water_level': robot.get('water_level', 0),
                            'sewage_level': robot.get('sewage_level', 0),
                            # Use uptime metrics calculated in the try block
                            'uptime_hours': uptime_metrics.get('uptime_hours', 0.0),
                            'downtime_hours': uptime_metrics.get('downtime_hours', 0.0),
                            'idle_hours': uptime_metrics.get('idle_hours', 0.0),
                            'working_hours': 0.0,  # Correctly 0 since no tasks
                            'charging_hours': uptime_metrics.get('charging_hours', 0.0),
                            'charging_ratio': uptime_metrics.get('charging_ratio', 0.0),
                            'uptime_ratio': uptime_metrics.get('uptime_ratio', 0.0),
                            'working_ratio': 0.0,  # Correctly 0 since no tasks
                            'idle_ratio': uptime_metrics.get('idle_ratio', 0.0),
                            'utilization_score': uptime_metrics.get('utilization_score', 0.0)
                        })
                        continue

                    # Normal calculation for robots WITH tasks
                    total_tasks = len(robot_tasks)

                    # Use cached calculations if available
                    try:
                        status_counts = self.get_cached_status_counts(robot_tasks)
                        completed_tasks = status_counts['completed']
                    except Exception as e:
                        logger.warning(f"Cache miss for robot {robot_sn} status counts: {e}")
                        # Fallback: count manually
                        completed_tasks = len(robot_tasks[robot_tasks['status'].str.lower().str.contains('complet', na=False)])

                    try:
                        running_hours = self.get_cached_duration_sum(robot_tasks)
                    except Exception as e:
                        logger.warning(f"Cache miss for robot {robot_sn} duration sum: {e}")
                        # Fallback: calculate manually
                        running_hours = pd.to_numeric(robot_tasks['duration'], errors='coerce').fillna(0).sum() / 3600

                    # Area calculations
                    total_area_cleaned = 0
                    total_planned_area = 0
                    if 'actual_area' in robot_tasks.columns:
                        total_area_cleaned = robot_tasks['actual_area'].fillna(0).sum() * 10.764
                    if 'plan_area' in robot_tasks.columns:
                        total_planned_area = robot_tasks['plan_area'].fillna(0).sum() * 10.764

                    average_coverage = (total_area_cleaned / total_planned_area * 100) if total_planned_area > 0 else 0

                    # Days with tasks
                    try:
                        robot_days_with_tasks = self.get_cached_days_with_tasks(robot_tasks)
                    except Exception as e:
                        logger.warning(f"Cache miss for robot {robot_sn} days: {e}")
                        # Fallback
                        if 'start_time' in robot_tasks.columns:
                            dates = pd.to_datetime(robot_tasks['start_time'], errors='coerce').dt.date
                            robot_days_with_tasks = dates.nunique()
                        else:
                            robot_days_with_tasks = 0

                    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                    location_name = self._get_robot_location_name(robot)

                    # Average efficiency
                    avg_efficiency = 0
                    if 'efficiency' in robot_tasks.columns:
                        avg_efficiency = robot_tasks['efficiency'].fillna(0).mean()

                    # Calculate uptime metrics
                    try:
                        uptime_metrics = self.calculate_uptime_downtime_metrics(
                            operation_history if operation_history is not None else pd.DataFrame(),
                            robot_tasks,
                            robot_charging,
                            robot_sn,
                            period_length
                        )
                    except Exception as e:
                        logger.warning(f"Error calculating uptime for {robot_sn}: {e}")
                        uptime_metrics = {
                            'uptime_hours': 0.0,
                            'downtime_hours': 0.0,
                            'idle_hours': 0.0,
                            'working_hours': 0.0,
                            'charging_hours': 0.0,
                            'charging_ratio': 0.0,
                            'uptime_ratio': 0.0,
                            'working_ratio': 0.0,
                            'idle_ratio': 0.0,
                            'utilization_score': 0.0
                        }

                    robot_metrics.append({
                        'robot_id': robot_sn,
                        'robot_name': robot.get('robot_name', f'Robot {robot_sn}'),
                        'location': location_name,
                        'total_tasks': total_tasks,
                        'tasks_completed': completed_tasks,
                        'total_area_cleaned': round(total_area_cleaned, 0),
                        'average_coverage': round(average_coverage, 1),
                        'days_with_tasks': robot_days_with_tasks,
                        'completion_rate': round(completion_rate, 1),
                        'running_hours': round(running_hours, 1),
                        'avg_efficiency': round(avg_efficiency, 1),
                        'charging_sessions': len(robot_charging) if not robot_charging.empty else 0,
                        'battery_level': robot.get('battery_level', 0),
                        'water_level': robot.get('water_level', 0),
                        'sewage_level': robot.get('sewage_level', 0),
                        'uptime_hours': uptime_metrics.get('uptime_hours', 0.0),
                        'downtime_hours': uptime_metrics.get('downtime_hours', 0.0),
                        'idle_hours': uptime_metrics.get('idle_hours', 0.0),
                        'working_hours': uptime_metrics.get('working_hours', 0.0),
                        'charging_hours': uptime_metrics.get('charging_hours', 0.0),
                        'charging_ratio': uptime_metrics.get('charging_ratio', 0.0),
                        'uptime_ratio': uptime_metrics.get('uptime_ratio', 0.0),
                        'working_ratio': uptime_metrics.get('working_ratio', 0.0),
                        'idle_ratio': uptime_metrics.get('idle_ratio', 0.0),
                        'utilization_score': uptime_metrics.get('utilization_score', 0.0)
                    })

                except Exception as e:
                    logger.error(f"Error processing robot {robot.get('robot_sn', 'unknown')}: {e}", exc_info=True)
                    continue

            # Sort by running hours
            robot_metrics.sort(key=lambda x: x['running_hours'], reverse=True)

            logger.info(f"Calculated performance for {len(robot_metrics)} robots")
            return robot_metrics

        except Exception as e:
            logger.error(f"Critical error in calculate_individual_robot_performance: {e}", exc_info=True)
            return []


    def _get_robot_location_name(self, robot: pd.Series) -> str:
        """
        Extract location name from robot data
        FIXED: Better error handling for missing data
        """
        try:
            location_fields = ['building_name', 'location_id', 'city']

            for field in location_fields:
                if field in robot and pd.notna(robot[field]):
                    location = str(robot[field]).strip()
                    if location and location.lower() not in ['unknown', 'none', 'nan']:
                        return location

            return 'Unknown Location'

        except Exception as e:
            logger.warning(f"Error extracting location name: {e}")
            return 'Unknown Location'

    # ============================================================================
    # ROI & COST ANALYSIS METRICS (UNCHANGED but included for completeness)
    # ============================================================================

    def calculate_roi_metrics(self, all_time_tasks: pd.DataFrame, target_robots: List[str], 
                             current_period_end: str, monthly_lease_price: float = 1500.0) -> Dict[str, Any]:
        """Calculate ROI metrics using all-time task data"""
        try:
            logger.info(f"Calculating ROI for {len(target_robots)} robots")

            if all_time_tasks.empty:
                return self._get_placeholder_roi_metrics()

            end_date = datetime.strptime(current_period_end.split(' ')[0], '%Y-%m-%d')

            # Pre-group tasks by robot
            robot_task_groups = {}
            if not all_time_tasks.empty:
                for robot_sn, robot_tasks in all_time_tasks.groupby('robot_sn'):
                    if robot_sn in target_robots:
                        robot_task_groups[robot_sn] = robot_tasks

            # Calculate per-robot metrics
            robot_roi_breakdown = {}
            total_investment = 0
            total_savings = 0

            for robot_sn in target_robots:
                robot_tasks = robot_task_groups.get(robot_sn, pd.DataFrame())

                if robot_tasks.empty:
                    robot_roi_breakdown[robot_sn] = {
                        'months_elapsed': 0,
                        'investment': 0,
                        'savings': 0,
                        'roi_percent': 0
                    }
                    continue

                # Find first task date
                first_task_date = pd.to_datetime(robot_tasks['start_time']).min().date()
                months_elapsed = self._calculate_months_elapsed(first_task_date, end_date.date())

                # Calculate investment
                robot_investment = monthly_lease_price * months_elapsed

                # Calculate cumulative savings
                robot_savings = self._calculate_cumulative_savings_vectorized(
                    robot_tasks, end_date.date()
                )

                # Calculate ROI
                robot_roi = (robot_savings / robot_investment * 100) if robot_investment > 0 else 0

                robot_roi_breakdown[robot_sn] = {
                    'months_elapsed': months_elapsed,
                    'investment': robot_investment,
                    'savings': round(robot_savings, 2),
                    'roi_percent': round(robot_roi, 1)
                }

                total_investment += robot_investment
                total_savings += robot_savings

            # Calculate aggregate metrics
            total_roi = (total_savings / total_investment * 100) if total_investment > 0 else 0

            max_months_elapsed = max(
                [rb['months_elapsed'] for rb in robot_roi_breakdown.values()],
                default=1
            )

            monthly_savings_rate = total_savings / max_months_elapsed if max_months_elapsed > 0 else 0

            # Calculate payback period
            payback_period = self._calculate_payback_period(
                total_investment, monthly_savings_rate
            )

            logger.info(f"ROI calculation complete: {total_roi:.1f}%")

            return {
                'total_roi_percent': round(total_roi, 1),
                'total_investment': round(total_investment, 2),
                'total_savings': round(total_savings, 2),
                'monthly_lease_price': monthly_lease_price,
                'robot_count': len(target_robots),
                'robot_breakdown': robot_roi_breakdown,
                'monthly_savings_rate': round(monthly_savings_rate, 2),
                'payback_period': payback_period
            }

        except Exception as e:
            logger.error(f"Error calculating ROI metrics: {e}")
            return self._get_placeholder_roi_metrics()

    def _calculate_cumulative_savings_vectorized(self, robot_tasks: pd.DataFrame,
                                                 end_date: datetime.date) -> float:
        """Calculate cumulative savings using vectorized operations"""
        try:
            HOURLY_WAGE = 25.0
            HUMAN_CLEANING_SPEED = 8000.0

            # Filter tasks up to end_date
            tasks_with_dates = self._parse_datetime_column(robot_tasks, 'start_time')
            tasks_filtered = tasks_with_dates[
                tasks_with_dates['start_time_dt'].dt.date <= end_date
            ]

            if tasks_filtered.empty:
                return 0.0

            # Vectorized area calculation
            area_sqm = pd.to_numeric(tasks_filtered['actual_area'], errors='coerce').fillna(0)
            area_sqft = area_sqm * 10.764

            # Vectorized cost calculations
            total_area_sqft = area_sqft.sum()

            # Human cost calculation
            human_hours = total_area_sqft / HUMAN_CLEANING_SPEED
            human_cost = human_hours * HOURLY_WAGE

            # Robot costs (currently 0 for water and energy)
            total_robot_cost = 0

            cumulative_savings = human_cost - total_robot_cost

            return max(0, cumulative_savings)

        except Exception as e:
            logger.error(f"Error calculating cumulative savings: {e}")
            return 0.0

    def _calculate_months_elapsed(self, first_date: datetime.date,
                                  end_date: datetime.date) -> int:
        """Calculate months elapsed, rounded up for lease billing"""
        try:
            years_diff = end_date.year - first_date.year
            months_diff = end_date.month - first_date.month
            total_months = years_diff * 12 + months_diff

            # Round up for partial months
            if end_date.day >= first_date.day:
                total_months += 1
            else:
                total_months += 1

            return max(1, total_months)

        except Exception as e:
            logger.error(f"Error calculating months elapsed: {e}")
            return 1

    def _calculate_payback_period(self, total_investment: float,
                                  monthly_savings_rate: float) -> str:
        """Calculate payback period string"""
        if monthly_savings_rate <= 0:
            return "Not yet profitable"

        payback_months = total_investment / monthly_savings_rate

        if payback_months <= 0:
            return "Already profitable"
        elif payback_months < 24:
            return f"{payback_months:.1f} months"
        else:
            payback_years = payback_months / 12
            return f"{payback_years:.1f} years"

    def calculate_daily_roi_trends(self, tasks_data: pd.DataFrame,
                                  all_time_tasks: pd.DataFrame,
                                  target_robots: List[str], start_date: str,
                                  end_date: str,
                                  monthly_lease_price: float = 1500.0) -> Dict[str, List]:
        """Calculate daily ROI trends"""
        try:
            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create daily buckets
            date_range = [
                start_dt + timedelta(days=i)
                for i in range((end_dt - start_dt).days + 1)
            ]

            daily_data = {
                date.strftime('%m/%d'): {'daily_savings': 0}
                for date in date_range
            }

            # Calculate total investment once
            total_investment = self._calculate_total_investment(
                target_robots, all_time_tasks, end_dt, monthly_lease_price
            )

            # Process daily savings
            if not tasks_data.empty and 'start_time' in tasks_data.columns:
                tasks_with_dates = self._parse_datetime_column(tasks_data, 'start_time')
                tasks_filtered = tasks_with_dates[
                    (tasks_with_dates['start_time_dt'].dt.date >= start_dt.date()) &
                    (tasks_with_dates['start_time_dt'].dt.date <= end_dt.date())
                ]

                if not tasks_filtered.empty:
                    # Vectorized savings calculation
                    tasks_filtered['date_str'] = tasks_filtered['start_time_dt'].dt.strftime('%m/%d')
                    tasks_filtered['area_sqft'] = pd.to_numeric(
                        tasks_filtered['actual_area'], errors='coerce'
                    ).fillna(0) * 10.764
                    tasks_filtered['task_savings'] = (tasks_filtered['area_sqft'] / 8000.0) * 25.0

                    # Group by date and sum
                    daily_savings = tasks_filtered.groupby('date_str')['task_savings'].sum()

                    for date_str, savings in daily_savings.items():
                        if date_str in daily_data:
                            daily_data[date_str]['daily_savings'] = savings

            # Calculate cumulative savings up to period start
            running_total_savings = 0
            if not all_time_tasks.empty:
                pre_period_tasks = all_time_tasks[
                    pd.to_datetime(all_time_tasks['start_time']).dt.date < start_dt.date()
                ]
                running_total_savings = self._calculate_total_savings_from_tasks_vectorized(
                    pre_period_tasks
                )

            # Build final trends
            dates = list(daily_data.keys())
            daily_savings_trend = []
            roi_trend = []

            for date in dates:
                running_total_savings += daily_data[date]['daily_savings']
                roi_percent = (running_total_savings / total_investment * 100) if total_investment > 0 else 0

                daily_savings_trend.append(round(daily_data[date]['daily_savings'], 2))
                roi_trend.append(round(roi_percent, 1))

            logger.info(f"Calculated daily ROI trends for {len(dates)} days")

            return {
                'dates': dates,
                'daily_savings_trend': daily_savings_trend,
                'roi_trend': roi_trend
            }

        except Exception as e:
            logger.error(f"Error calculating daily ROI trends: {e}")
            return {'dates': [], 'daily_savings_trend': [], 'roi_trend': []}

    def _calculate_total_investment(self, target_robots: List[str],
                                   all_time_tasks: pd.DataFrame,
                                   end_dt: datetime,
                                   monthly_lease_price: float) -> float:
        """Calculate total investment for all robots"""
        total_investment = 0

        if all_time_tasks.empty:
            return 0

        # Group by robot once
        for robot_sn, robot_tasks in all_time_tasks.groupby('robot_sn'):
            if robot_sn in target_robots:
                first_task_date = pd.to_datetime(robot_tasks['start_time']).min().date()
                months_elapsed = self._calculate_months_elapsed(first_task_date, end_dt.date())
                total_investment += monthly_lease_price * months_elapsed

        return total_investment

    def _calculate_total_savings_from_tasks_vectorized(self, tasks_df: pd.DataFrame) -> float:
        """Calculate total savings using vectorized operations"""
        if tasks_df.empty:
            return 0

        # Vectorized calculation
        area_sqm = pd.to_numeric(tasks_df['actual_area'], errors='coerce').fillna(0)
        area_sqft = area_sqm * 10.764
        human_hours = area_sqft / 8000.0
        human_cost = human_hours * 25.0

        return max(0, human_cost.sum())

    def calculate_cost_analysis_metrics(self, tasks_data: pd.DataFrame,
                                       resource_metrics: Dict[str, Any],
                                       roi_improvement: str = 'N/A') -> Dict[str, Any]:
        """Calculate cost analysis metrics"""
        try:
            # Constants
            HOURLY_WAGE = 25
            COST_PER_FL_OZ_WATER = 0.0
            COST_PER_KWH = 0.0
            HUMAN_CLEANING_SPEED = 8000.0

            # Get resource usage from metrics
            total_area_sqft = resource_metrics.get('total_area_cleaned_sqft', 0)
            total_energy_kwh = resource_metrics.get('total_energy_consumption_kwh', 0)
            total_water_floz = resource_metrics.get('total_water_consumption_floz', 0)

            # Calculate costs
            water_cost = total_water_floz * COST_PER_FL_OZ_WATER
            energy_cost = total_energy_kwh * COST_PER_KWH
            total_cost = water_cost + energy_cost

            cost_per_sqft = total_cost / total_area_sqft if total_area_sqft > 0 else 0

            # Calculate savings
            hours_saved = total_area_sqft / HUMAN_CLEANING_SPEED if HUMAN_CLEANING_SPEED > 0 else 0
            human_cost = hours_saved * HOURLY_WAGE
            savings = human_cost - total_cost

            return {
                'cost_per_sqft': round(cost_per_sqft, 4),
                'total_cost': round(total_cost, 2),
                'hours_saved': round(hours_saved, 1),
                'savings': round(savings, 2),
                'annual_projected_savings': round(savings * 12, 2) if savings > 0 else 0,
                'cost_efficiency_improvement': round((savings / human_cost * 100), 1) if human_cost > 0 else 0,
                'roi_improvement': roi_improvement,
                'human_cost': round(human_cost, 2),
                'water_cost': round(water_cost, 2),
                'energy_cost': round(energy_cost, 2),
                'hourly_wage': HOURLY_WAGE,
            }

        except Exception as e:
            logger.error(f"Error calculating cost analysis: {e}")
            return self._get_placeholder_cost_metrics(roi_improvement)

    # ============================================================================
    # TREND DATA CALCULATION (UNCHANGED)
    # ============================================================================

    def calculate_daily_trends(self, tasks_data: pd.DataFrame,
                              charging_data: pd.DataFrame,
                              start_date: str, end_date: str) -> Dict[str, List]:
        """Calculate daily trend data with REAL savings"""
        try:
            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create daily buckets
            date_range = [
                start_dt + timedelta(days=i)
                for i in range((end_dt - start_dt).days + 1)
            ]

            daily_data = {
                date.strftime('%m/%d'): {
                    'charging_sessions': 0,
                    'charging_duration_total': 0,
                    'charging_session_count': 0,
                    'energy_consumption': 0,
                    'water_usage': 0,
                    'daily_savings': 0
                }
                for date in date_range
            }

            # Process tasks data
            if not tasks_data.empty and 'start_time' in tasks_data.columns:
                tasks_with_dates = self._parse_datetime_column(tasks_data, 'start_time')
                tasks_filtered = tasks_with_dates[
                    (tasks_with_dates['start_time_dt'].dt.date >= start_dt.date()) &
                    (tasks_with_dates['start_time_dt'].dt.date <= end_dt.date())
                ]

                if not tasks_filtered.empty:
                    # Add calculated columns
                    tasks_filtered['date_str'] = tasks_filtered['start_time_dt'].dt.strftime('%m/%d')
                    tasks_filtered['energy'] = pd.to_numeric(
                        tasks_filtered['consumption'], errors='coerce'
                    ).fillna(0)
                    tasks_filtered['water'] = pd.to_numeric(
                        tasks_filtered['water_consumption'], errors='coerce'
                    ).fillna(0)
                    tasks_filtered['area_sqft'] = pd.to_numeric(
                        tasks_filtered['actual_area'], errors='coerce'
                    ).fillna(0) * 10.764
                    tasks_filtered['task_savings'] = (tasks_filtered['area_sqft'] / 8000.0) * 25.0

                    # Group and aggregate
                    daily_agg = tasks_filtered.groupby('date_str').agg({
                        'energy': 'sum',
                        'water': 'sum',
                        'task_savings': 'sum'
                    })

                    for date_str, row in daily_agg.iterrows():
                        if date_str in daily_data:
                            daily_data[date_str]['energy_consumption'] = row['energy']
                            daily_data[date_str]['water_usage'] = row['water']
                            daily_data[date_str]['daily_savings'] = row['task_savings']

            # Process charging data
            if not charging_data.empty and 'start_time' in charging_data.columns:
                charging_with_dates = self._parse_datetime_column(charging_data, 'start_time')
                charging_filtered = charging_with_dates[
                    (charging_with_dates['start_time_dt'].dt.date >= start_dt.date()) &
                    (charging_with_dates['start_time_dt'].dt.date <= end_dt.date())
                ]

                if not charging_filtered.empty:
                    charging_filtered['date_str'] = charging_filtered['start_time_dt'].dt.strftime('%m/%d')
                    charging_filtered['duration_min'] = charging_filtered['duration'].apply(
                        self._parse_duration_str_to_minutes
                    )

                    # Group and count
                    for date_str, date_charges in charging_filtered.groupby('date_str'):
                        if date_str in daily_data:
                            daily_data[date_str]['charging_sessions'] = len(date_charges)
                            valid_durations = date_charges['duration_min'][date_charges['duration_min'] > 0]
                            if len(valid_durations) > 0:
                                daily_data[date_str]['charging_duration_total'] = valid_durations.sum()
                                daily_data[date_str]['charging_session_count'] = len(valid_durations)

            # Convert to lists
            dates = list(daily_data.keys())

            charging_sessions = [daily_data[d]['charging_sessions'] for d in dates]

            charging_durations = [
                round(daily_data[d]['charging_duration_total'] / daily_data[d]['charging_session_count'], 1)
                if daily_data[d]['charging_session_count'] > 0 else 0
                for d in dates
            ]

            energy_consumption = [round(daily_data[d]['energy_consumption'], 1) for d in dates]
            water_usage = [round(daily_data[d]['water_usage'], 0) for d in dates]
            cost_savings_trend = [round(daily_data[d]['daily_savings'], 2) for d in dates]

            return {
                'dates': dates,
                'charging_sessions_trend': charging_sessions,
                'charging_duration_trend': charging_durations,
                'energy_consumption_trend': energy_consumption,
                'water_usage_trend': water_usage,
                'cost_savings_trend': cost_savings_trend,
                'roi_improvement_trend': [0] * len(dates)
            }

        except Exception as e:
            logger.error(f"Error calculating daily trends: {e}")
            return {
                'dates': [],
                'charging_sessions_trend': [],
                'charging_duration_trend': [],
                'energy_consumption_trend': [],
                'water_usage_trend': [],
                'cost_savings_trend': [],
                'roi_improvement_trend': []
            }

    # ============================================================================
    # PERIOD COMPARISON METRICS (UNCHANGED - large method)
    # ============================================================================

    def calculate_period_comparison_metrics(self, current_metrics: Dict[str, Any],
                                            previous_metrics: Dict[str, Any]) -> Dict[str, str]:
        """Calculate period comparisons for all metrics"""
        try:
            comparisons = {}

            # Helper function
            def calc_change(current, previous, format_type="number", suffix=""):
                """Calculate and format change between periods"""
                if current == 'N/A' or previous == 'N/A' or current is None or previous is None:
                    return "N/A"

                try:
                    if isinstance(current, str) and current.endswith('%'):
                        current = float(current.replace('%', ''))
                    else:
                        current = float(current)

                    if isinstance(previous, str) and previous.endswith('%'):
                        previous = float(previous.replace('%', ''))
                    else:
                        previous = float(previous)

                    if previous == 0:
                        if current == 0:
                            return "0" + suffix
                        return f"+{current:.1f}{suffix if format_type != 'percent' else '%'}"

                    change = current - previous
                    sign = '+' if change >= 0 else ''

                    if format_type == "percent":
                        return f"{sign}{change:.1f}%"
                    else:
                        return f"{sign}{change:.1f}{suffix}"

                except (ValueError, TypeError):
                    return "N/A"

            # Extract metric groups
            task_curr = current_metrics.get('task_performance', {})
            task_prev = previous_metrics.get('task_performance', {})

            fleet_curr = current_metrics.get('fleet_performance', {})
            fleet_prev = previous_metrics.get('fleet_performance', {})

            resource_curr = current_metrics.get('resource_utilization', {})
            resource_prev = previous_metrics.get('resource_utilization', {})

            charging_curr = current_metrics.get('charging_performance', {})
            charging_prev = previous_metrics.get('charging_performance', {})

            cost_curr = current_metrics.get('cost_analysis', {})
            cost_prev = previous_metrics.get('cost_analysis', {})

            # Task performance comparisons
            task_comparisons = {
                'completion_rate': ('completion_rate', 'percent'),
                'total_tasks': ('total_tasks', 'number', ' tasks'),
                'total_area_cleaned': ('total_area_cleaned', 'number', ' sq ft'),
                'coverage_efficiency': ('coverage_efficiency', 'percent'),
                'avg_duration': ('avg_task_duration_minutes', 'number', ' min')
            }

            for comp_key, (metric_key, *format_args) in task_comparisons.items():
                comparisons[comp_key] = calc_change(
                    task_curr.get(metric_key, 0),
                    task_prev.get(metric_key, 0),
                    *format_args
                )

            # Fleet performance comparisons
            comparisons['fleet_availability'] = 'N/A'
            comparisons['running_hours'] = calc_change(
                fleet_curr.get('total_running_hours', 0),
                fleet_prev.get('total_running_hours', 0),
                'number', ' hrs'
            )
            comparisons['days_with_tasks'] = calc_change(
                fleet_curr.get('days_with_tasks', 0),
                fleet_prev.get('days_with_tasks', 0),
                'number', ' days'
            )
            comparisons['avg_daily_running_hours_per_robot'] = calc_change(
                fleet_curr.get('avg_daily_running_hours_per_robot', 0),
                fleet_prev.get('avg_daily_running_hours_per_robot', 0),
                'number', ' hrs/robot'
            )

            # Resource utilization comparisons
            comparisons['energy_consumption'] = calc_change(
                resource_curr.get('total_energy_consumption_kwh', 0),
                resource_prev.get('total_energy_consumption_kwh', 0),
                'number', ' kWh'
            )
            comparisons['water_consumption'] = calc_change(
                resource_curr.get('total_water_consumption_floz', 0),
                resource_prev.get('total_water_consumption_floz', 0),
                'number', ' fl oz'
            )

            # Charging performance comparisons
            charging_comparisons = {
                'charging_sessions': ('total_sessions', 'number', ' sessions'),
                'avg_charging_duration': ('avg_charging_duration_minutes', 'number', ' min'),
                'median_charging_duration': ('median_charging_duration_minutes', 'number', ' min'),
                'avg_power_gain': ('avg_power_gain_percent', 'number', '%'),
                'median_power_gain': ('median_power_gain_percent', 'number', '%')
            }

            for comp_key, (metric_key, *format_args) in charging_comparisons.items():
                comparisons[comp_key] = calc_change(
                    charging_curr.get(metric_key, 0),
                    charging_prev.get(metric_key, 0),
                    *format_args
                )

            # Cost analysis comparisons
            cost_comparisons = {
                'cost_per_sqft': ('cost_per_sqft', 'number', ''),
                'total_cost': ('total_cost', 'number', ''),
                'savings': ('savings', 'number', ''),
                'hours_saved': ('hours_saved', 'number', ' hrs'),
                'annual_projected_savings': ('annual_projected_savings', 'number', ''),
                'human_cost': ('human_cost', 'number', ''),
                'roi_improvement': ('roi_improvement', 'percent'),
                'cost_efficiency_improvement': ('cost_efficiency_improvement', 'percent'),
                'water_cost': ('water_cost', 'number', ''),
                'energy_cost': ('energy_cost', 'number', ''),
                'cumulative_savings': ('cumulative_savings', 'number', ''),
                'monthly_savings_rate': ('monthly_savings_rate', 'number', ''),
                'payback_months': ('payback_months', 'number', ' months')
            }

            for comp_key, (metric_key, *format_args) in cost_comparisons.items():
                comparisons[comp_key] = calc_change(
                    cost_curr.get(metric_key, 0),
                    cost_prev.get(metric_key, 0),
                    *format_args
                )

            # Facility comparisons
            comparisons['facility_comparisons'] = self._calculate_facility_comparisons(
                current_metrics, previous_metrics, calc_change
            )

            # Map comparisons
            comparisons['map_comparisons'] = self._calculate_map_comparisons(
                current_metrics, previous_metrics, calc_change
            )

            logger.info(f"Calculated {len(comparisons)} period comparisons")
            return comparisons

        except Exception as e:
            logger.error(f"Error calculating period comparisons: {e}")
            return {}

    def _calculate_facility_comparisons(self, current_metrics: Dict[str, Any],
                                       previous_metrics: Dict[str, Any],
                                       calc_change) -> Dict[str, Dict[str, str]]:
        """Calculate facility-level comparisons"""
        facility_curr = current_metrics.get('facility_performance', {}).get('facilities', {})
        facility_prev = previous_metrics.get('facility_performance', {}).get('facilities', {})

        facility_eff_curr = current_metrics.get('facility_efficiency_metrics', {})
        facility_eff_prev = previous_metrics.get('facility_efficiency_metrics', {})

        facility_task_curr = current_metrics.get('facility_task_metrics', {})
        facility_task_prev = previous_metrics.get('facility_task_metrics', {})

        facility_resource_curr = current_metrics.get('facility_resource_metrics', {})
        facility_resource_prev = previous_metrics.get('facility_resource_metrics', {})

        facility_charging_curr = current_metrics.get('facility_charging_metrics', {})
        facility_charging_prev = previous_metrics.get('facility_charging_metrics', {})

        facility_breakdown_curr = current_metrics.get('facility_breakdown_metrics', {})
        facility_breakdown_prev = previous_metrics.get('facility_breakdown_metrics', {})

        comparisons = {}

        for facility_name in facility_curr.keys():
            if facility_name not in facility_prev:
                comparisons[facility_name] = self._get_default_facility_comparison()
                continue

            fc = facility_curr[facility_name]
            fp = facility_prev[facility_name]

            # Basic comparisons
            comp = {
                'area_cleaned': calc_change(fc.get('area_cleaned', 0), fp.get('area_cleaned', 0), 'number', ' sq ft'),
                'completion_rate': calc_change(fc.get('completion_rate', 0), fp.get('completion_rate', 0), 'percent'),
                'running_hours': calc_change(fc.get('running_hours', 0), fp.get('running_hours', 0), 'number', ' hrs'),
                'coverage_efficiency': calc_change(fc.get('coverage_efficiency', 0), fp.get('coverage_efficiency', 0), 'percent'),
                'power_efficiency': calc_change(fc.get('power_efficiency', 0), fp.get('power_efficiency', 0), 'number', ' sq ft/kWh')
            }

            # Efficiency metrics
            if facility_name in facility_eff_curr and facility_name in facility_eff_prev:
                comp['water_efficiency'] = calc_change(
                    facility_eff_curr[facility_name].get('water_efficiency', 0),
                    facility_eff_prev[facility_name].get('water_efficiency', 0),
                    'number', ' sq ft/fl oz'
                )
                comp['time_efficiency'] = calc_change(
                    facility_eff_curr[facility_name].get('time_efficiency', 0),
                    facility_eff_prev[facility_name].get('time_efficiency', 0),
                    'number', ' sq ft/hr'
                )
                comp['days_with_tasks'] = calc_change(
                    facility_eff_curr[facility_name].get('days_with_tasks', 0),
                    facility_eff_prev[facility_name].get('days_with_tasks', 0),
                    'number', ' days'
                )
            else:
                comp.update({'water_efficiency': 'N/A', 'time_efficiency': 'N/A', 'days_with_tasks': 'N/A'})

            # Task metrics
            if facility_name in facility_task_curr and facility_name in facility_task_prev:
                comp['avg_task_duration'] = calc_change(
                    facility_task_curr[facility_name].get('avg_duration_minutes', 0),
                    facility_task_prev[facility_name].get('avg_duration_minutes', 0),
                    'number', ' min'
                )
                comp['total_tasks'] = calc_change(
                    facility_task_curr[facility_name].get('total_tasks', 0),
                    facility_task_prev[facility_name].get('total_tasks', 0),
                    'number', ' tasks'
                )
            else:
                comp.update({'avg_task_duration': 'N/A', 'total_tasks': 'N/A'})

            # Resource metrics
            if facility_name in facility_resource_curr and facility_name in facility_resource_prev:
                comp['energy_consumption_facility'] = calc_change(
                    facility_resource_curr[facility_name].get('energy_consumption_kwh', 0),
                    facility_resource_prev[facility_name].get('energy_consumption_kwh', 0),
                    'number', ' kWh'
                )
                comp['water_consumption_facility'] = calc_change(
                    facility_resource_curr[facility_name].get('water_consumption_floz', 0),
                    facility_resource_prev[facility_name].get('water_consumption_floz', 0),
                    'number', ' fl oz'
                )
            else:
                comp.update({'energy_consumption_facility': 'N/A', 'water_consumption_facility': 'N/A'})

            # Charging metrics
            if facility_name in facility_charging_curr and facility_name in facility_charging_prev:
                comp['total_sessions'] = calc_change(
                    facility_charging_curr[facility_name].get('total_sessions', 0),
                    facility_charging_prev[facility_name].get('total_sessions', 0),
                    'number', ' sessions'
                )
                comp['avg_charging_duration'] = calc_change(
                    facility_charging_curr[facility_name].get('avg_duration_minutes', 0),
                    facility_charging_prev[facility_name].get('avg_duration_minutes', 0),
                    'number', ' min'
                )
                comp['median_charging_duration'] = calc_change(
                    facility_charging_curr[facility_name].get('median_duration_minutes', 0),
                    facility_charging_prev[facility_name].get('median_duration_minutes', 0),
                    'number', ' min'
                )
                comp['avg_power_gain_facility'] = calc_change(
                    facility_charging_curr[facility_name].get('avg_power_gain_percent', 0),
                    facility_charging_prev[facility_name].get('avg_power_gain_percent', 0),
                    'number', '%'
                )
                comp['median_power_gain_facility'] = calc_change(
                    facility_charging_curr[facility_name].get('median_power_gain_percent', 0),
                    facility_charging_prev[facility_name].get('median_power_gain_percent', 0),
                    'number', '%'
                )
            else:
                comp.update({
                    'total_sessions': 'N/A',
                    'avg_charging_duration': 'N/A',
                    'median_charging_duration': 'N/A',
                    'avg_power_gain_facility': 'N/A',
                    'median_power_gain_facility': 'N/A'
                })

            # Coverage by day
            if facility_name in facility_breakdown_curr and facility_name in facility_breakdown_prev:
                comp['highest_coverage_day'] = facility_breakdown_prev[facility_name].get('highest_coverage_day', 'N/A')
                comp['lowest_coverage_day'] = facility_breakdown_prev[facility_name].get('lowest_coverage_day', 'N/A')
            else:
                comp.update({'highest_coverage_day': 'N/A', 'lowest_coverage_day': 'N/A'})

            comparisons[facility_name] = comp

        return comparisons

    def _calculate_map_comparisons(self, current_metrics: Dict[str, Any],
                               previous_metrics: Dict[str, Any],
                               calc_change) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Calculate map-level comparisons
        UPDATED: Now includes target performance comparisons
        """
        current_map_perf = current_metrics.get('map_performance_by_building', {})
        previous_map_perf = previous_metrics.get('map_performance_by_building', {})

        comparisons = {}

        for building_name, maps in current_map_perf.items():
            if building_name not in previous_map_perf:
                continue

            comparisons[building_name] = {}

            # Create map lookup
            previous_maps = {m['map_name']: m for m in previous_map_perf[building_name]}

            for map_data in maps:
                map_name = map_data['map_name']
                if map_name not in previous_maps:
                    continue

                prev_map = previous_maps[map_name]

                # Base comparisons
                map_comparisons = {
                    'coverage_percentage': calc_change(
                        map_data.get('coverage_percentage', 0),
                        prev_map.get('coverage_percentage', 0),
                        'percent'
                    ),
                    'area_cleaned': calc_change(
                        map_data.get('area_cleaned', 0),
                        prev_map.get('area_cleaned', 0),
                        'number', ' sq ft'
                    ),
                    'running_hours': calc_change(
                        map_data.get('running_hours', 0),
                        prev_map.get('running_hours', 0),
                        'number', ' hrs'
                    ),
                    'power_efficiency': calc_change(
                        map_data.get('power_efficiency', 0),
                        prev_map.get('power_efficiency', 0),
                        'number', ' sq ft/kWh'
                    ),
                    'time_efficiency': calc_change(
                        map_data.get('time_efficiency', 0),
                        prev_map.get('time_efficiency', 0),
                        'number', ' sq ft/hr'
                    ),
                    'water_efficiency': calc_change(
                        map_data.get('water_efficiency', 0),
                        prev_map.get('water_efficiency', 0),
                        'number', ' sq ft/fl oz'
                    ),
                    'days_with_tasks': calc_change(
                        map_data.get('days_with_tasks', 0),
                        prev_map.get('days_with_tasks', 0),
                        'number', ' days'
                    )
                }

                # NEW: Add target performance comparisons if both periods have target data
                current_target_perf = map_data.get('target_performance')
                prev_target_perf = prev_map.get('target_performance')

                if current_target_perf and prev_target_perf:
                    # Helper function for reverse logic (fewer tasks below target = better)
                    def calc_reverse_change(current, previous, suffix=''):
                        """Calculate change where negative is good (fewer tasks failing)"""
                        if previous == 0 and current == 0:
                            return 'N/A'

                        change = current - previous

                        if abs(change) < 0.01:
                            return f'±0{suffix}'

                        # Add sign
                        sign = '+' if change > 0 else ''
                        return f'{sign}{int(change)}{suffix}'

                    map_comparisons['target_performance'] = {
                        'tasks_below_efficiency': calc_reverse_change(
                            current_target_perf.get('tasks_below_efficiency_target', 0),
                            prev_target_perf.get('tasks_below_efficiency_target', 0),
                            ' tasks'
                        ),
                        'tasks_below_area': calc_reverse_change(
                            current_target_perf.get('tasks_below_area_target', 0),
                            prev_target_perf.get('tasks_below_area_target', 0),
                            ' tasks'
                        ),
                        'tasks_exceeding_duration': calc_reverse_change(
                            current_target_perf.get('tasks_exceeding_duration_target', 0),
                            prev_target_perf.get('tasks_exceeding_duration_target', 0),
                            ' tasks'
                        ),
                        'efficiency_compliance_rate': calc_change(
                            current_target_perf.get('efficiency_compliance_rate', 0),
                            prev_target_perf.get('efficiency_compliance_rate', 0),
                            'percent'
                        ),
                        'area_compliance_rate': calc_change(
                            current_target_perf.get('area_compliance_rate', 0),
                            prev_target_perf.get('area_compliance_rate', 0),
                            'percent'
                        ),
                        'duration_compliance_rate': calc_change(
                            current_target_perf.get('duration_compliance_rate', 0),
                            prev_target_perf.get('duration_compliance_rate', 0),
                            'percent'
                        )
                    }

                comparisons[building_name][map_name] = map_comparisons

        return comparisons

    def _get_default_facility_comparison(self) -> Dict[str, str]:
        """Return default N/A comparison for new facilities"""
        return {
            'area_cleaned': 'N/A',
            'completion_rate': 'N/A',
            'running_hours': 'N/A',
            'coverage_efficiency': 'N/A',
            'power_efficiency': 'N/A',
            'water_efficiency': 'N/A',
            'time_efficiency': 'N/A',
            'days_with_tasks': 'N/A',
            'avg_task_duration': 'N/A',
            'total_tasks': 'N/A',
            'energy_consumption_facility': 'N/A',
            'water_consumption_facility': 'N/A',
            'total_sessions': 'N/A',
            'avg_charging_duration': 'N/A',
            'median_charging_duration': 'N/A',
            'avg_power_gain_facility': 'N/A',
            'median_power_gain_facility': 'N/A',
            'highest_coverage_day': 'N/A',
            'lowest_coverage_day': 'N/A'
        }

    def analyze_tasks_against_targets(self, tasks_data: pd.DataFrame,
                                  performance_targets: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Analyze tasks against performance targets by map_name

        Returns:
        {
            'map_name_1': {
                'tasks_below_efficiency_target': 5,
                'tasks_below_area_target': 3,
                'tasks_below_duration_target': 2,
                'total_tasks': 10
            },
            'map_name_2': {...}
        }
        """
        try:
            if tasks_data.empty or performance_targets.empty:
                logger.info("No tasks or targets available for target analysis")
                return {}

            # Ensure required columns exist
            required_task_cols = ['map_name', 'efficiency', 'actual_area', 'duration']
            if not all(col in tasks_data.columns for col in required_task_cols):
                logger.warning(f"Missing required columns in tasks_data for target analysis")
                return {}

            target_analysis = {}

            # Group tasks by map_name
            for map_name, map_tasks in tasks_data.groupby('map_name'):
                # Check if we have targets for this map
                map_targets = performance_targets[performance_targets['map_name'] == map_name]

                if map_targets.empty:
                    # No targets defined for this map - skip
                    logger.debug(f"No performance targets found for map: {map_name}")
                    continue

                # Get the target values (first row if multiple)
                target = map_targets.iloc[0]

                total_tasks = len(map_tasks)
                below_efficiency = 0
                below_area = 0
                below_duration = 0

                # Analyze each task
                for _, task in map_tasks.iterrows():
                    # 1. Check efficiency target
                    if pd.notna(target['target_efficiency']):
                        task_efficiency = pd.to_numeric(task['efficiency'], errors='coerce')
                        if pd.notna(task_efficiency) and task_efficiency < target['target_efficiency']:
                            below_efficiency += 1

                    # 2. Check area target (depends on area_storage_type)
                    actual_area_sqm = pd.to_numeric(task['actual_area'], errors='coerce')
                    if pd.notna(actual_area_sqm):
                        actual_area_sqft = actual_area_sqm * 10.764  # Convert to sqft

                        if target['area_storage_type'] == 'value':
                            # Compare against absolute value
                            if pd.notna(target['target_area_value']) and actual_area_sqft < target['target_area_value']:
                                below_area += 1

                        elif target['area_storage_type'] == 'percentage':
                            # Compare against percentage of plan_area
                            if 'plan_area' in task and pd.notna(task['plan_area']):
                                plan_area_sqm = pd.to_numeric(task['plan_area'], errors='coerce')
                                if pd.notna(plan_area_sqm):
                                    plan_area_sqft = plan_area_sqm * 10.764
                                    actual_percentage = (actual_area_sqft / plan_area_sqft * 100) if plan_area_sqft > 0 else 0

                                    if pd.notna(target['target_area_percentage']) and actual_percentage < target['target_area_percentage']:
                                        below_area += 1

                    # 3. Check duration target
                    if pd.notna(target['target_duration']):
                        task_duration = pd.to_numeric(task['duration'], errors='coerce')
                        if pd.notna(task_duration):
                            # Duration in tasks is in seconds, target_duration is also in seconds
                            # Tasks EXCEEDING target duration are considered "below target"
                            if task_duration > target['target_duration']:
                                below_duration += 1

                # Store results only if we have targets
                target_analysis[map_name] = {
                    'tasks_below_efficiency_target': below_efficiency,
                    'tasks_below_area_target': below_area,
                    'tasks_exceeding_duration_target': below_duration,  # Exceeding = worse performance
                    'total_tasks': total_tasks,
                    'efficiency_compliance_rate': round((total_tasks - below_efficiency) / total_tasks * 100, 1) if total_tasks > 0 else 0,
                    'area_compliance_rate': round((total_tasks - below_area) / total_tasks * 100, 1) if total_tasks > 0 else 0,
                    'duration_compliance_rate': round((total_tasks - below_duration) / total_tasks * 100, 1) if total_tasks > 0 else 0,
                    # Include target values for reference
                    'targets': {
                        'efficiency': target.get('target_efficiency'),
                        'area_value': target.get('target_area_value'),
                        'area_percentage': target.get('target_area_percentage'),
                        'area_type': target.get('area_storage_type'),
                        'duration_seconds': target.get('target_duration')
                    }
                }

                logger.info(f"Map '{map_name}': {below_efficiency}/{total_tasks} below efficiency, "
                           f"{below_area}/{total_tasks} below area, {below_duration}/{total_tasks} exceeding duration")

            return target_analysis

        except Exception as e:
            logger.error(f"Error analyzing tasks against targets: {e}", exc_info=True)
            return {}

    # ============================================================================
    # ADDITIONAL UTILITY METRICS (UNCHANGED)
    # ============================================================================

    def calculate_weekend_schedule_completion(self, tasks_data: pd.DataFrame) -> float:
        """Calculate weekend completion rate"""
        try:
            if tasks_data.empty or 'start_time' not in tasks_data.columns:
                return 0.0

            tasks_with_dates = self._parse_datetime_column(tasks_data, 'start_time')

            # Filter weekend tasks (Saturday=5, Sunday=6)
            weekend_tasks = tasks_with_dates[
                tasks_with_dates['start_time_dt'].dt.weekday.isin([5, 6])
            ]

            if weekend_tasks.empty:
                return 0.0

            total_weekend = len(weekend_tasks)
            completed_weekend = self._count_completed_tasks(weekend_tasks)

            weekend_rate = (completed_weekend / total_weekend * 100) if total_weekend > 0 else 0

            return round(weekend_rate, 1)

        except Exception as e:
            logger.error(f"Error calculating weekend completion: {e}")
            return 0.0

    def calculate_average_task_duration(self, tasks_data: pd.DataFrame) -> float:
        """Calculate average task duration in minutes"""
        try:
            if tasks_data.empty or 'duration' not in tasks_data.columns:
                return 0.0

            durations = pd.to_numeric(tasks_data['duration'], errors='coerce').dropna()
            avg_duration = (durations.mean() / 60) if len(durations) > 0 else 0.0

            return round(avg_duration, 1)

        except Exception as e:
            logger.error(f"Error calculating average task duration: {e}")
            return 0.0

    # ============================================================================
    # PLACEHOLDER METRICS (UNCHANGED)
    # ============================================================================

    def _get_placeholder_task_metrics(self) -> Dict[str, Any]:
        """Return placeholder task metrics"""
        return {
            'total_tasks': 0,
            'completed_tasks': 0,
            'cancelled_tasks': 0,
            'interrupted_tasks': 0,
            'completion_rate': 0.0,
            'total_area_cleaned': 0.0,
            'coverage_efficiency': 0.0,
            'task_modes': {},
            'incomplete_task_rate': 0.0
        }

    def _get_placeholder_charging_metrics(self) -> Dict[str, Any]:
        """Return placeholder charging metrics"""
        return {
            'total_sessions': 0,
            'avg_charging_duration_minutes': 0.0,
            'median_charging_duration_minutes': 0.0,
            'avg_power_gain_percent': 0.0,
            'median_power_gain_percent': 0.0,
            'total_charging_time': 0.0
        }

    def _get_placeholder_resource_metrics(self) -> Dict[str, Any]:
        """Return placeholder resource metrics"""
        return {
            'total_energy_consumption_kwh': 0.0,
            'total_water_consumption_floz': 0.0,
            'area_per_kwh': 0,
            'area_per_gallon': 0,
            'total_area_cleaned_sqft': 0.0
        }

    def _get_placeholder_event_metrics(self) -> Dict[str, Any]:
        """Return placeholder event metrics"""
        return {
            'total_events': 0,
            'critical_events': 0,
            'error_events': 0,
            'warning_events': 0,
            'info_events': 0,
            'event_types': {},
            'event_levels': {}
        }

    def _get_default_weekday_metrics(self) -> Dict[str, Any]:
        """Return default weekday metrics"""
        return {
            'highest_day': 'N/A',
            'highest_rate': 0.0,
            'lowest_day': 'N/A',
            'lowest_rate': 0.0
        }

    def _get_placeholder_roi_metrics(self) -> Dict[str, Any]:
        """Return placeholder ROI metrics"""
        return {
            'total_roi_percent': 0.0,
            'total_investment': 0.0,
            'total_savings': 0.0,
            'monthly_lease_price': 1500.0,
            'robot_count': 0,
            'robot_breakdown': {},
            'monthly_savings_rate': 0.0,
            'payback_period': 'Not yet profitable'
        }

    def _get_placeholder_cost_metrics(self, roi_improvement: str = 'N/A') -> Dict[str, Any]:
        """Return placeholder cost metrics"""
        return {
            'cost_per_sqft': 0.0,
            'total_cost': 0.0,
            'hours_saved': 0.0,
            'savings': 0.0,
            'annual_projected_savings': 0.0,
            'cost_efficiency_improvement': 0.0,
            'roi_improvement': roi_improvement,
            'human_cost': 0.0,
            'water_cost': 0.0,
            'energy_cost': 0.0,
            'hourly_wage': 25.0
        }