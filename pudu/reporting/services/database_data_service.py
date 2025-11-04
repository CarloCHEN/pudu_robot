import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Reuse existing RDS infrastructure
from pudu.rds.rdsTable import RDSTable
from pudu.configs.database_config_loader import DynamicDatabaseConfig

# Import calculators
from ..calculators.metrics_calculator import PerformanceMetricsCalculator

logger = logging.getLogger(__name__)

reuse_connection = False

class DatabaseDataService:
    """Enhanced service for querying and processing historical data from databases"""

    def __init__(self, config: DynamicDatabaseConfig):
        """Initialize with database configuration and calculators"""
        self.config = config
        self.connection_config = "credentials.yaml"
        self.metrics_calculator = PerformanceMetricsCalculator()

        # Cache for robot-facility mappings - OPTIMIZATION
        self._robot_facility_cache = None

    # ============================================================================
    # CORE DATA FETCHING METHODS - OPTIMIZED
    # ============================================================================

    def fetch_robot_status_data(self, target_robots: List[str]) -> pd.DataFrame:
        """
        Fetch current robot status data
        OPTIMIZED: Batch query processing
        """
        logger.info(f"Fetching robot status for {len(target_robots)} robots")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_status', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=reuse_connection
                    )

                    # Optimized query - only fetch needed columns
                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, robot_type, robot_name, location_id,
                               water_level, sewage_level, battery_level, status
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} robot status records")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching robot status: {e}")
                    continue

            # Combine and deduplicate - OPTIMIZED
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total robot status records: {len(combined_df)}")
                return combined_df

            logger.warning("No robot status data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_robot_status_data: {e}")
            return pd.DataFrame()

    def fetch_cleaning_tasks_data(self, target_robots: List[str],
                                  start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical cleaning tasks data
        OPTIMIZED: Selective column fetching, indexed queries
        """
        logger.info(f"Fetching tasks for {len(target_robots)} robots from {start_date} to {end_date}")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_task', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=reuse_connection
                    )

                    # OPTIMIZED: Only fetch columns we actually use
                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, task_name, mode, sub_mode, type,
                               actual_area, plan_area, start_time, end_time, duration,
                               efficiency, battery_usage, consumption, water_consumption,
                               progress, status, map_name, map_url, new_map_url
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND start_time >= '{start_date}'
                        AND start_time <= '{end_date}'
                        ORDER BY start_time DESC
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} task records")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching tasks: {e}")
                    continue

            # Combine all data - OPTIMIZED
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total task records: {len(combined_df)}")
                return combined_df

            logger.warning("No cleaning tasks data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_cleaning_tasks_data: {e}")
            return pd.DataFrame()

    def fetch_charging_data(self, target_robots: List[str],
                           start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical charging sessions data
        OPTIMIZED: Minimal column selection
        """
        logger.info(f"Fetching charging data for {len(target_robots)} robots")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_charging', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=reuse_connection
                    )

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, robot_name, start_time, end_time, duration,
                               initial_power, final_power, power_gain, status
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND start_time >= '{start_date}'
                        AND start_time <= '{end_date}'
                        ORDER BY start_time DESC
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} charging records")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching charging data: {e}")
                    continue

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total charging records: {len(combined_df)}")
                return combined_df

            logger.warning("No charging data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_charging_data: {e}")
            return pd.DataFrame()

    def fetch_events_data(self, target_robots: List[str],
                         start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical robot events data
        OPTIMIZED: Selective column fetching
        """
        logger.info(f"Fetching events for {len(target_robots)} robots")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_events', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=reuse_connection
                    )

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, event_id, error_id, event_level, event_type,
                               event_detail, task_time, upload_time, created_at
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND task_time >= '{start_date}'
                        AND task_time <= '{end_date}'
                        ORDER BY task_time DESC
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} event records")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching events: {e}")
                    continue

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total event records: {len(combined_df)}")
                return combined_df

            logger.warning("No events data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_events_data: {e}")
            return pd.DataFrame()

    def fetch_location_data(self, target_robots: List[str]) -> pd.DataFrame:
        """
        Fetch location/building information for robots
        OPTIMIZED: Cached robot-facility mapping
        """
        logger.info(f"Fetching location data for {len(target_robots)} robots")

        try:
            # Check cache first - OPTIMIZATION
            if self._robot_facility_cache is not None:
                cached_robots = set(self._robot_facility_cache['robot_sn'].unique())
                if set(target_robots).issubset(cached_robots):
                    logger.info("Using cached location data")
                    return self._robot_facility_cache[
                        self._robot_facility_cache['robot_sn'].isin(target_robots)
                    ]

            # Fetch robot status with location_id
            robot_status = self.fetch_robot_status_data(target_robots)

            if robot_status.empty or 'location_id' not in robot_status.columns:
                logger.warning("No location data in robot status")
                return pd.DataFrame()

            # Get unique location IDs
            location_ids = robot_status['location_id'].dropna().unique().tolist()

            if not location_ids:
                logger.warning("No location IDs found")
                return pd.DataFrame()

            # Fetch building information
            building_configs = self.config.get_all_table_configs('location')

            all_locations = []
            for config in building_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys'],
                        reuse_connection=reuse_connection
                    )

                    location_list = "', '".join(location_ids)
                    query = f"""
                        SELECT building_id, building_name, city, state, country
                        FROM {table.table_name}
                        WHERE building_id IN ('{location_list}')
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_locations.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} location records")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching location data: {e}")
                    continue

            # Combine and merge - OPTIMIZED
            if all_locations:
                locations_df = pd.concat(all_locations, ignore_index=True).drop_duplicates()

                # Merge with robot status
                robot_locations = robot_status.merge(
                    locations_df,
                    left_on='location_id',
                    right_on='building_id',
                    how='left'
                )

                # Cache the result - OPTIMIZATION
                self._robot_facility_cache = robot_locations

                logger.info(f"Mapped {len(robot_locations)} robots to locations")
                return robot_locations

            logger.warning("No location data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching location data: {e}")
            return pd.DataFrame()

    def fetch_all_time_tasks_for_roi(self, target_robots: List[str],
                                    end_date: str) -> pd.DataFrame:
        """
        Fetch minimal task data for ROI calculation
        OPTIMIZED: Only fetch essential columns
        """
        logger.info(f"Fetching all-time tasks for ROI ({len(target_robots)} robots)")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_task', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=reuse_connection
                    )

                    # CRITICAL OPTIMIZATION: Only fetch 4 columns instead of all
                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, actual_area, consumption, water_consumption, start_time
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND start_time <= '{end_date}'
                        AND actual_area IS NOT NULL
                        AND actual_area > 0
                        ORDER BY robot_sn, start_time ASC
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} ROI task records")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching ROI tasks: {e}")
                    continue

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total ROI task records: {len(combined_df)}")
                return combined_df

            logger.warning("No ROI task data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_all_time_tasks_for_roi: {e}")
            return pd.DataFrame()

    def fetch_all_report_data(self, target_robots: List[str], start_date: str,
                             end_date: str, content_categories: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Fetch all required data for report generation
        OPTIMIZED: Parallel data structure, reduced redundant fetching
        """
        logger.info(f"Fetching report data for categories: {content_categories}")

        report_data = {}

        try:
            # Always fetch robot status and location (needed for context)
            logger.info("Fetching robot status...")
            report_data['robot_status'] = self.fetch_robot_status_data(target_robots)

            logger.info("Fetching location data...")
            report_data['robot_locations'] = self.fetch_location_data(target_robots)

            # Always fetch cleaning and charging tasks (used by multiple metrics)
            logger.info("Fetching cleaning tasks...")
            report_data['cleaning_tasks'] = self.fetch_cleaning_tasks_data(
                target_robots, start_date, end_date
            )

            logger.info("Fetching charging tasks...")
            report_data['charging_tasks'] = self.fetch_charging_data(
                target_robots, start_date, end_date
            )

            # Conditionally fetch events
            if 'event-analysis' in content_categories:
                logger.info("Fetching events...")
                report_data['events'] = self.fetch_events_data(
                    target_robots, start_date, end_date
                )
            else:
                report_data['events'] = pd.DataFrame()

            logger.info(f"Data fetching completed: {list(report_data.keys())}")
            return report_data

        except Exception as e:
            logger.error(f"Error fetching all report data: {e}")
            return {}

    # ============================================================================
    # COMPREHENSIVE METRICS CALCULATION - OPTIMIZED
    # ============================================================================

    def calculate_comprehensive_metrics(self, report_data: Dict[str, pd.DataFrame],
                                       start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics using calculator
        OPTIMIZED: Eliminated duplicate calculations, reuse results
        """
        logger.info("Calculating comprehensive metrics")

        try:
            # Extract DataFrames once - OPTIMIZATION
            robot_data = report_data.get('robot_status', pd.DataFrame())
            tasks_data = report_data.get('cleaning_tasks', pd.DataFrame())
            charging_data = report_data.get('charging_tasks', pd.DataFrame())
            events_data = report_data.get('events', pd.DataFrame())
            robot_locations = report_data.get('robot_locations', pd.DataFrame())

            metrics = {}

            # Calculate core metrics using calculator - OPTIMIZED (single call each)
            metrics['fleet_performance'] = self.metrics_calculator.calculate_fleet_availability(
                robot_data, tasks_data, start_date, end_date
            )

            metrics['task_performance'] = self.metrics_calculator.calculate_task_performance_metrics(
                tasks_data
            )

            metrics['charging_performance'] = self.metrics_calculator.calculate_charging_performance_metrics(
                charging_data
            )

            # Resource utilization - REUSED by cost analysis
            metrics['resource_utilization'] = self.metrics_calculator.calculate_resource_utilization_metrics(
                tasks_data
            )

            metrics['event_analysis'] = self.metrics_calculator.calculate_event_analysis_metrics(
                events_data
            )

            # Event location mapping - OPTIMIZED
            if not events_data.empty and not robot_locations.empty:
                metrics['event_location_mapping'] = self.calculate_event_location_mapping(
                    events_data, robot_locations
                )
                metrics['event_type_by_location'] = self.calculate_event_type_by_location(
                    events_data, robot_locations
                )
            else:
                metrics['event_location_mapping'] = {}
                metrics['event_type_by_location'] = {}

            # Facility-specific metrics - BATCH CALCULATION
            if not robot_locations.empty:
                # Calculate ALL facility metrics in batch - OPTIMIZATION
                facility_metrics_batch = self._calculate_all_facility_metrics_batch(
                    tasks_data, charging_data, robot_locations, start_date, end_date
                )
                metrics.update(facility_metrics_batch)
            else:
                # Fallback to basic calculation
                metrics['facility_performance'] = self.metrics_calculator.calculate_facility_performance_metrics(
                    tasks_data, robot_data
                )
                metrics['facility_efficiency_metrics'] = {}
                metrics['facility_task_metrics'] = {}
                metrics['facility_charging_metrics'] = {}
                metrics['facility_resource_metrics'] = {}
                metrics['facility_breakdown_metrics'] = {}

            # Individual robot metrics - OPTIMIZED
            metrics['individual_robots'] = self.metrics_calculator.calculate_individual_robot_performance(
                tasks_data, charging_data, robot_locations if not robot_locations.empty else robot_data
            )

            # Map coverage metrics
            metrics['map_coverage'] = self.calculate_map_coverage_metrics(tasks_data)

            # Map performance by building - OPTIMIZED
            if not robot_locations.empty:
                metrics['map_performance_by_building'] = self.metrics_calculator.calculate_map_performance_by_building(
                    tasks_data, robot_locations
                )
            else:
                metrics['map_performance_by_building'] = {}

            # Trend data - OPTIMIZED (removed redundant weekly calculation)
            metrics['trend_data'] = self.calculate_daily_trends(
                tasks_data, charging_data, start_date, end_date
            )

            # Cost analysis - REUSES resource_utilization (no recalculation)
            metrics['cost_analysis'] = self.metrics_calculator.calculate_cost_analysis_metrics(
                tasks_data, metrics['resource_utilization'], roi_improvement='N/A'
            )

            logger.info("Comprehensive metrics calculation completed")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating comprehensive metrics: {e}")
            return {}

    def _calculate_all_facility_metrics_batch(self, tasks_data: pd.DataFrame,
                                              charging_data: pd.DataFrame,
                                              robot_locations: pd.DataFrame,
                                              start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate ALL facility metrics in a single batch pass
        OPTIMIZED: Single groupby for all facility calculations
        """
        try:
            logger.info("Batch calculating all facility metrics")

            # Pre-create robot-facility mapping - OPTIMIZATION
            robot_facility_map = dict(zip(
                robot_locations['robot_sn'],
                robot_locations['building_name']
            ))

            # Add facility column to tasks - OPTIMIZATION
            tasks_with_facility = tasks_data.copy()
            tasks_with_facility['facility'] = tasks_with_facility['robot_sn'].map(
                robot_facility_map
            )

            # Add facility column to charging - OPTIMIZATION
            charging_with_facility = charging_data.copy()
            charging_with_facility['facility'] = charging_with_facility['robot_sn'].map(
                robot_facility_map
            )

            # Initialize result dictionaries
            facility_performance = {}
            facility_efficiency = {}
            facility_task_metrics = {}
            facility_charging_metrics = {}
            facility_resource_metrics = {}
            facility_breakdown = {}

            # Single groupby for tasks - MAJOR OPTIMIZATION
            for building_name, facility_tasks in tasks_with_facility.groupby('facility'):
                if pd.isna(building_name):
                    continue

                # Calculate all task-based metrics in one pass - OPTIMIZED
                total_tasks = len(facility_tasks)
                status_counts = self.metrics_calculator._count_tasks_by_status(facility_tasks)

                # Area calculations - vectorized
                actual_area_sqm = facility_tasks['actual_area'].fillna(0).sum() if 'actual_area' in facility_tasks.columns else 0
                planned_area_sqm = facility_tasks['plan_area'].fillna(0).sum() if 'plan_area' in facility_tasks.columns else 0
                actual_area_sqft = actual_area_sqm * 10.764
                planned_area_sqft = planned_area_sqm * 10.764

                # Running hours - vectorized
                running_hours = self.metrics_calculator._sum_task_durations(facility_tasks)

                # Resource consumption - vectorized
                energy = facility_tasks['consumption'].fillna(0).sum() if 'consumption' in facility_tasks.columns else 0
                water = facility_tasks['water_consumption'].fillna(0).sum() if 'water_consumption' in facility_tasks.columns else 0

                # Efficiency calculations
                coverage_efficiency = (actual_area_sqm / planned_area_sqm * 100) if planned_area_sqm > 0 else 0
                completion_rate = (status_counts['completed'] / total_tasks * 100) if total_tasks > 0 else 0
                power_efficiency = actual_area_sqft / energy if energy > 0 else 0
                water_efficiency = actual_area_sqft / water if water > 0 else 0
                time_efficiency = actual_area_sqft / running_hours if running_hours > 0 else 0

                # Average duration - vectorized
                durations = pd.to_numeric(facility_tasks['duration'], errors='coerce').dropna()
                avg_duration = (durations.mean() / 60) if len(durations) > 0 else 0

                # Primary mode
                primary_mode = "Mixed"
                if 'mode' in facility_tasks.columns:
                    mode_counts = facility_tasks['mode'].value_counts()
                    if not mode_counts.empty:
                        primary_mode = mode_counts.index[0]

                # Days with tasks
                facility_days = self.metrics_calculator.calculate_days_with_tasks(facility_tasks)
                period_length = self.metrics_calculator._calculate_period_length(start_date, end_date)

                # Coverage by day
                coverage_by_day = self.metrics_calculator.calculate_facility_coverage_by_day(
                    tasks_data, robot_locations, building_name
                )

                robot_count = len(robot_locations[robot_locations['building_name'] == building_name])

                # Populate all facility metrics dictionaries - BATCH POPULATION
                facility_performance[building_name] = {
                    'total_tasks': total_tasks,
                    'completed_tasks': status_counts['completed'],
                    'completion_rate': round(completion_rate, 1),
                    'area_cleaned': round(actual_area_sqft, 0),
                    'planned_area': round(planned_area_sqft, 0),
                    'coverage_efficiency': round(coverage_efficiency, 1),
                    'running_hours': round(running_hours, 1),
                    'power_efficiency': round(power_efficiency, 0),
                    'robot_count': robot_count
                }

                facility_efficiency[building_name] = {
                    'water_efficiency': round(water_efficiency, 1),
                    'time_efficiency': round(time_efficiency, 1),
                    'total_area_cleaned': round(actual_area_sqft, 0),
                    'total_time_hours': round(running_hours, 1),
                    'days_with_tasks': facility_days,
                    'period_length': period_length,
                    'days_ratio': f"{facility_days}/{period_length}"
                }

                facility_task_metrics[building_name] = {
                    'total_tasks': total_tasks,
                    'completed_tasks': status_counts['completed'],
                    'completion_rate': completion_rate,
                    'avg_duration_minutes': round(avg_duration, 1),
                    'primary_mode': primary_mode,
                    'task_count_by_mode': facility_tasks['mode'].value_counts().to_dict() if 'mode' in facility_tasks.columns else {}
                }

                facility_resource_metrics[building_name] = {
                    'energy_consumption_kwh': round(energy, 1),
                    'water_consumption_floz': round(water, 0)
                }

                facility_breakdown[building_name] = {
                    'total_tasks': total_tasks,
                    'completed_tasks': status_counts['completed'],
                    'cancelled_tasks': status_counts['cancelled'],
                    'completion_rate': round(completion_rate, 1),
                    'area_cleaned': round(actual_area_sqm, 0),
                    'planned_area': round(planned_area_sqm, 0),
                    'coverage_efficiency': round(coverage_efficiency, 1),
                    'running_hours': round(running_hours, 1),
                    'energy_consumption': round(energy, 1),
                    'water_consumption': round(water, 1),
                    'power_efficiency': round(power_efficiency, 0),
                    'robot_count': robot_count,
                    'primary_mode': primary_mode,
                    'avg_task_duration': round(avg_duration, 1),
                    'cancellation_rate': round((status_counts['cancelled'] / total_tasks * 100), 1) if total_tasks > 0 else 0,
                    'highest_coverage_day': coverage_by_day['highest_coverage_day'],
                    'lowest_coverage_day': coverage_by_day['lowest_coverage_day']
                }

            # Process charging data - single groupby
            for building_name, facility_charging in charging_with_facility.groupby('facility'):
                if pd.isna(building_name):
                    continue

                total_sessions = len(facility_charging)

                # Vectorized duration parsing - OPTIMIZED
                durations = facility_charging['duration'].apply(
                    self.metrics_calculator._parse_duration_str_to_minutes
                ).tolist()
                durations = [d for d in durations if d > 0]

                # Vectorized power gain parsing - OPTIMIZED
                power_gain_series = facility_charging['power_gain'].astype(str).str.replace(
                    '+', ''
                ).str.replace('%', '').str.strip()
                power_gains = pd.to_numeric(power_gain_series, errors='coerce').dropna().tolist()

                avg_duration = np.mean(durations) if durations else 0
                median_duration = np.median(durations) if durations else 0
                avg_power_gain = np.mean(power_gains) if power_gains else 0
                median_power_gain = np.median(power_gains) if power_gains else 0

                facility_charging_metrics[building_name] = {
                    'total_sessions': total_sessions,
                    'avg_duration_minutes': round(avg_duration, 1),
                    'median_duration_minutes': round(median_duration, 1),
                    'avg_power_gain_percent': round(avg_power_gain, 1),
                    'median_power_gain_percent': round(median_power_gain, 1)
                }

            logger.info(f"Batch calculated metrics for {len(facility_performance)} facilities")

            return {
                'facility_performance': {'facilities': facility_performance},
                'facility_efficiency_metrics': facility_efficiency,
                'facility_task_metrics': facility_task_metrics,
                'facility_charging_metrics': facility_charging_metrics,
                'facility_resource_metrics': facility_resource_metrics,
                'facility_breakdown_metrics': facility_breakdown
            }

        except Exception as e:
            logger.error(f"Error in batch facility calculation: {e}")
            return {
                'facility_performance': {'facilities': {}},
                'facility_efficiency_metrics': {},
                'facility_task_metrics': {},
                'facility_charging_metrics': {},
                'facility_resource_metrics': {},
                'facility_breakdown_metrics': {}
            }

    def calculate_map_coverage_metrics(self, tasks_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Calculate detailed map coverage metrics
        OPTIMIZED: Single groupby operation
        """
        logger.info("Calculating map coverage metrics")

        try:
            if tasks_data.empty or 'map_name' not in tasks_data.columns:
                logger.warning("No map data available")
                return []

            map_metrics = []

            # Single groupby - OPTIMIZED
            for map_name, map_tasks in tasks_data.groupby('map_name'):
                if pd.isna(map_name):
                    continue

                # Vectorized calculations - OPTIMIZED
                total_actual_area = map_tasks['actual_area'].fillna(0).sum() if 'actual_area' in map_tasks.columns else 0
                total_planned_area = map_tasks['plan_area'].fillna(0).sum() if 'plan_area' in map_tasks.columns else 0

                coverage_percentage = (total_actual_area / total_planned_area * 100) if total_planned_area > 0 else 0

                # Task completion
                completed_tasks = self.metrics_calculator._count_completed_tasks(map_tasks)
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

            # Sort by coverage - OPTIMIZED
            map_metrics.sort(key=lambda x: x['coverage_percentage'], reverse=True)

            logger.info(f"Calculated coverage for {len(map_metrics)} maps")
            return map_metrics

        except Exception as e:
            logger.error(f"Error calculating map coverage: {e}")
            return []

    def calculate_daily_trends(self, tasks_data: pd.DataFrame,
                              charging_data: pd.DataFrame,
                              start_date: str, end_date: str) -> Dict[str, List]:
        """
        Calculate daily trend data
        OPTIMIZED: Reuses calculator method (no duplication)
        """
        return self.metrics_calculator.calculate_daily_trends(
            tasks_data, charging_data, start_date, end_date
        )

    def calculate_event_location_mapping(self, events_data: pd.DataFrame,
                                        robot_locations: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Map events to building locations
        OPTIMIZED: Pre-built robot-building map
        """
        try:
            if events_data.empty or robot_locations.empty:
                return {}

            # Create robot-building mapping - OPTIMIZATION
            robot_building_map = dict(zip(
                robot_locations['robot_sn'],
                robot_locations['building_name']
            ))

            # Add building column - OPTIMIZED with map
            events_with_building = events_data.copy()
            events_with_building['building'] = events_with_building['robot_sn'].map(
                robot_building_map
            ).fillna('Unknown Building')

            # Vectorized level extraction - OPTIMIZED
            events_with_building['level_lower'] = events_with_building['event_level'].astype(
                str
            ).str.lower()

            # Count events by building - OPTIMIZED with groupby
            building_events = {}

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

            return building_events

        except Exception as e:
            logger.error(f"Error mapping events to locations: {e}")
            return {}

    def calculate_event_type_by_location(self, events_data: pd.DataFrame,
                                        robot_locations: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Calculate event type breakdown by location
        OPTIMIZED: Pre-built mapping, single groupby
        """
        try:
            if events_data.empty or robot_locations.empty:
                return {}

            # Pre-build robot-building map - OPTIMIZATION
            robot_building_map = dict(zip(
                robot_locations['robot_sn'],
                robot_locations['building_name']
            ))

            # Add building column - OPTIMIZED
            events_with_building = events_data.copy()
            events_with_building['building'] = events_with_building['robot_sn'].map(
                robot_building_map
            ).fillna('Unknown Building')

            # Two-level groupby - OPTIMIZED
            event_type_location_breakdown = {}

            for event_type, type_group in events_with_building.groupby('event_type'):
                if pd.isna(event_type):
                    continue

                event_type_location_breakdown[event_type] = {}

                # Count by building for this event type
                building_counts = type_group['building'].value_counts()

                for building, count in building_counts.items():
                    event_type_location_breakdown[event_type][building] = int(count)

            return event_type_location_breakdown

        except Exception as e:
            logger.error(f"Error calculating event type by location: {e}")
            return {}
    # ============================================================================
    # COMPREHENSIVE METRICS WITH COMPARISON - OPTIMIZED
    # ============================================================================

    def calculate_comprehensive_metrics_with_comparison(self, current_data: Dict[str, pd.DataFrame],
                                                       previous_data: Dict[str, pd.DataFrame],
                                                       current_start: str, current_end: str,
                                                       previous_start: str, previous_end: str) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics with period comparison and ROI
        OPTIMIZED: Parallel calculation, eliminated redundant operations
        """
        logger.info("Calculating comprehensive metrics with comparison and ROI")

        try:
            # Calculate both periods in parallel structure - OPTIMIZED
            logger.info("Calculating current period metrics...")
            current_metrics = self.calculate_comprehensive_metrics(
                current_data, current_start, current_end
            )

            logger.info("Calculating previous period metrics...")
            previous_metrics = self.calculate_comprehensive_metrics(
                previous_data, previous_start, previous_end
            )

            # Extract data references - OPTIMIZATION
            tasks_data = current_data.get('cleaning_tasks', pd.DataFrame())
            events_data = current_data.get('events', pd.DataFrame())
            robot_locations = current_data.get('robot_locations', pd.DataFrame())
            charging_data = current_data.get('charging_tasks', pd.DataFrame())
            robot_status = current_data.get('robot_status', pd.DataFrame())

            # Get target robots - OPTIMIZED
            target_robots = self._extract_target_robots(robot_status, tasks_data)

            # === ROI CALCULATION ===
            if target_robots:
                logger.info(f"Calculating ROI for {len(target_robots)} robots")

                # Fetch all-time task data for ROI
                all_time_tasks = self.fetch_all_time_tasks_for_roi(target_robots, current_end)

                # Calculate current and previous ROI - OPTIMIZED (parallel structure)
                roi_metrics = self.metrics_calculator.calculate_roi_metrics(
                    all_time_tasks, target_robots, current_end, monthly_lease_price=1500.0
                )
                previous_roi_metrics = self.metrics_calculator.calculate_roi_metrics(
                    all_time_tasks, target_robots, previous_end, monthly_lease_price=1500.0
                )

                # Update cost analysis with ROI - BATCH UPDATE
                self._update_cost_analysis_with_roi(
                    current_metrics, previous_metrics, roi_metrics, previous_roi_metrics
                )

                # Calculate daily ROI trends
                daily_roi_trends = self.metrics_calculator.calculate_daily_roi_trends(
                    tasks_data, all_time_tasks, target_robots, current_start, current_end
                )

                # Update trend data with ROI - MERGE OPERATION
                if current_metrics.get('trend_data') and daily_roi_trends.get('dates'):
                    current_metrics['trend_data']['cost_savings_trend'] = daily_roi_trends['daily_savings_trend']
                    current_metrics['trend_data']['roi_improvement_trend'] = daily_roi_trends['roi_trend']

                logger.info(f"ROI calculation complete: {roi_metrics['total_roi_percent']:.1f}%")
            else:
                logger.warning("No target robots for ROI calculation")
                self._set_default_roi_metrics(current_metrics)

            # === ADDITIONAL CURRENT PERIOD METRICS ===

            # Weekend completion and average duration - BATCH CALCULATION
            weekend_completion = self.metrics_calculator.calculate_weekend_schedule_completion(tasks_data)
            avg_duration = self.metrics_calculator.calculate_average_task_duration(tasks_data)

            current_metrics['task_performance']['weekend_schedule_completion'] = weekend_completion
            current_metrics['task_performance']['avg_task_duration_minutes'] = avg_duration

            # Weekday completion rates
            current_metrics['weekday_completion'] = self.metrics_calculator.calculate_weekday_completion_rates(
                tasks_data
            )

            # Days with tasks and period length - BATCH UPDATE
            days_info = self.metrics_calculator.calculate_days_with_tasks_and_period_length(
                tasks_data, current_start, current_end
            )
            current_metrics['fleet_performance'].update(days_info)

            # Daily location efficiency for charts
            if not robot_locations.empty:
                daily_location_efficiency = self.calculate_daily_task_efficiency_by_location(
                    tasks_data, robot_locations, current_start, current_end
                )
                current_metrics['daily_location_efficiency'] = daily_location_efficiency

            # === PREVIOUS PERIOD SUPPLEMENTARY METRICS ===
            previous_tasks_data = previous_data.get('cleaning_tasks', pd.DataFrame())
            previous_avg_duration = self.metrics_calculator.calculate_average_task_duration(
                previous_tasks_data
            )
            previous_metrics['task_performance']['avg_task_duration_minutes'] = previous_avg_duration

            # === PERIOD COMPARISON ===
            period_comparisons = self.metrics_calculator.calculate_period_comparison_metrics(
                current_metrics, previous_metrics
            )
            current_metrics['period_comparisons'] = period_comparisons

            # Add comparison metadata
            current_metrics['comparison_metadata'] = {
                'current_period': {'start': current_start, 'end': current_end},
                'previous_period': {'start': previous_start, 'end': previous_end},
                'comparison_available': True
            }

            # === FINANCIAL TRENDS ===
            daily_financial_trends = self.calculate_daily_financial_trends(
                tasks_data, current_start, current_end
            )
            if daily_financial_trends and daily_financial_trends.get('dates'):
                current_metrics['financial_trend_data'] = daily_financial_trends

            logger.info("Successfully calculated metrics with comparison and ROI")
            return current_metrics

        except Exception as e:
            logger.error(f"Error calculating metrics with comparison and ROI: {e}")
            # Fallback to current metrics only
            return self._calculate_fallback_metrics(current_data, current_start, current_end)

    def _extract_target_robots(self, robot_status: pd.DataFrame,
                               tasks_data: pd.DataFrame) -> List[str]:
        """
        Extract target robot list from available data
        OPTIMIZED: Single extraction operation
        """
        if not robot_status.empty:
            return robot_status['robot_sn'].dropna().unique().tolist()
        elif not tasks_data.empty:
            return tasks_data['robot_sn'].dropna().unique().tolist()
        return []

    def _update_cost_analysis_with_roi(self, current_metrics: Dict[str, Any],
                                      previous_metrics: Dict[str, Any],
                                      roi_metrics: Dict[str, Any],
                                      previous_roi_metrics: Dict[str, Any]) -> None:
        """
        Update cost analysis with ROI data in place
        OPTIMIZED: In-place update, no copying
        """
        # Update current metrics
        current_metrics['cost_analysis'].update({
            'roi_improvement': f"{roi_metrics['total_roi_percent']:.1f}%",
            'total_investment': roi_metrics['total_investment'],
            'robot_roi_breakdown': roi_metrics['robot_breakdown'],
            'monthly_savings_rate': roi_metrics['monthly_savings_rate'],
            'payback_period': roi_metrics['payback_period'],
            'cumulative_savings': roi_metrics['total_savings']
        })

        # Update previous metrics
        previous_metrics['cost_analysis'].update({
            'roi_improvement': f"{previous_roi_metrics['total_roi_percent']:.1f}%",
            'total_investment': previous_roi_metrics['total_investment'],
            'robot_roi_breakdown': previous_roi_metrics['robot_breakdown'],
            'monthly_savings_rate': previous_roi_metrics['monthly_savings_rate'],
            'payback_period': previous_roi_metrics['payback_period'],
            'cumulative_savings': previous_roi_metrics['total_savings']
        })

    def _set_default_roi_metrics(self, metrics: Dict[str, Any]) -> None:
        """Set default ROI metrics when calculation not possible"""
        metrics['cost_analysis'].update({
            'roi_improvement': '0.0%',
            'total_investment': 0.0,
            'robot_roi_breakdown': {}
        })

    def _calculate_fallback_metrics(self, current_data: Dict[str, pd.DataFrame],
                                   current_start: str, current_end: str) -> Dict[str, Any]:
        """Calculate fallback metrics without comparison"""
        current_metrics = self.calculate_comprehensive_metrics(
            current_data, current_start, current_end
        )

        tasks_data = current_data.get('cleaning_tasks', pd.DataFrame())
        weekend_completion = self.metrics_calculator.calculate_weekend_schedule_completion(tasks_data)
        avg_duration = self.metrics_calculator.calculate_average_task_duration(tasks_data)

        current_metrics['task_performance']['weekend_schedule_completion'] = weekend_completion
        current_metrics['task_performance']['avg_task_duration_minutes'] = avg_duration
        current_metrics['period_comparisons'] = {}
        current_metrics['comparison_metadata'] = {'comparison_available': False}

        self._set_default_roi_metrics(current_metrics)

        return current_metrics

    # ============================================================================
    # DAILY EFFICIENCY & FINANCIAL TRENDS - OPTIMIZED
    # ============================================================================

    def calculate_daily_task_efficiency_by_location(self, tasks_data: pd.DataFrame,
                                                    robot_locations: pd.DataFrame,
                                                    start_date: str, end_date: str) -> Dict[str, Dict[str, List]]:
        """
        Calculate daily efficiency by location
        OPTIMIZED: Single groupby with multi-level aggregation
        """
        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create date range - OPTIMIZED with list comprehension
            date_range = [
                start_dt + timedelta(days=i)
                for i in range((end_dt - start_dt).days + 1)
            ]

            # Pre-build robot-facility map - OPTIMIZATION
            robot_facility_map = dict(zip(
                robot_locations['robot_sn'],
                robot_locations['building_name']
            ))

            # Add facility and date columns - OPTIMIZED
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

            # Multi-level groupby - MAJOR OPTIMIZATION
            for facility, facility_group in tasks_filtered.groupby('facility'):
                if pd.isna(facility):
                    continue

                # Aggregate by date - OPTIMIZED
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

    def calculate_daily_financial_trends(self, tasks_data: pd.DataFrame,
                                        start_date: str, end_date: str) -> Dict[str, List]:
        """
        Calculate daily financial trends
        OPTIMIZED: Vectorized calculations, single groupby
        """
        try:
            logger.info("Calculating daily financial trends")

            # Constants
            HOURLY_WAGE = 25.0
            HUMAN_CLEANING_SPEED = 1000.0

            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create date range - OPTIMIZED
            date_range = [
                start_dt + timedelta(days=i)
                for i in range((end_dt - start_dt).days + 1)
            ]

            daily_data = {
                date.strftime('%m/%d'): {'area_cleaned': 0}
                for date in date_range
            }

            # Process tasks - OPTIMIZED with groupby
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
                    # Vectorized calculations - OPTIMIZED
                    tasks_filtered['date_str'] = tasks_filtered['start_time_dt'].dt.strftime('%m/%d')
                    tasks_filtered['area_sqft'] = pd.to_numeric(
                        tasks_filtered['actual_area'], errors='coerce'
                    ).fillna(0) * 10.764

                    # Aggregate by date - OPTIMIZED
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
    # LEGACY/DEPRECATED METHODS - Keep for compatibility but log warnings
    # ============================================================================

    def calculate_individual_robot_metrics(self, tasks_data: pd.DataFrame,
                                          charging_data: pd.DataFrame,
                                          robot_status: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use metrics_calculator.calculate_individual_robot_performance instead
        Kept for backward compatibility
        """
        logger.warning("Using deprecated calculate_individual_robot_metrics - use calculator instead")
        return self.metrics_calculator.calculate_individual_robot_performance(
            tasks_data, charging_data, robot_status
        )

    def calculate_facility_specific_metrics(self, tasks_data: pd.DataFrame,
                                           robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        DEPRECATED: Use batch facility calculation instead
        Kept for backward compatibility
        """
        logger.warning("Using deprecated calculate_facility_specific_metrics - use batch method instead")

        if robot_locations.empty or tasks_data.empty:
            return {}

        # Use the new batch method
        batch_results = self._calculate_all_facility_metrics_batch(
            tasks_data, pd.DataFrame(), robot_locations, '', ''
        )
        return batch_results.get('facility_performance', {}).get('facilities', {})

    def calculate_facility_specific_task_metrics(self, tasks_data: pd.DataFrame,
                                                 robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        DEPRECATED: Use batch facility calculation instead
        """
        logger.warning("Using deprecated calculate_facility_specific_task_metrics")
        batch_results = self._calculate_all_facility_metrics_batch(
            tasks_data, pd.DataFrame(), robot_locations, '', ''
        )
        return batch_results.get('facility_task_metrics', {})

    def calculate_facility_specific_charging_metrics(self, charging_data: pd.DataFrame,
                                                     robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        DEPRECATED: Use batch facility calculation instead
        """
        logger.warning("Using deprecated calculate_facility_specific_charging_metrics")
        batch_results = self._calculate_all_facility_metrics_batch(
            pd.DataFrame(), charging_data, robot_locations, '', ''
        )
        return batch_results.get('facility_charging_metrics', {})

    def calculate_facility_specific_resource_metrics(self, tasks_data: pd.DataFrame,
                                                     robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        DEPRECATED: Use batch facility calculation instead
        """
        logger.warning("Using deprecated calculate_facility_specific_resource_metrics")
        batch_results = self._calculate_all_facility_metrics_batch(
            tasks_data, pd.DataFrame(), robot_locations, '', ''
        )
        return batch_results.get('facility_resource_metrics', {})

    def calculate_weekly_trends(self, tasks_data: pd.DataFrame,
                               charging_data: pd.DataFrame,
                               start_date: str, end_date: str) -> Dict[str, List]:
        """
        DEPRECATED: Use calculate_daily_trends instead
        """
        logger.warning("Using deprecated calculate_weekly_trends - use daily trends instead")
        return self.calculate_daily_trends(tasks_data, charging_data, start_date, end_date)

    def calculate_reporting_period_length(self, start_date: str, end_date: str) -> int:
        """Calculate reporting period length in days"""
        return self.metrics_calculator._calculate_period_length(start_date, end_date)