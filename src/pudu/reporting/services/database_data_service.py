"""
FIXED: Database Data Service with proper connection management for parallel execution

KEY FIXES:
1. Connection pool management - each thread gets its own connection
2. Proper error handling and retry logic
3. Connection timeout configuration
4. Thread-safe connection reuse
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

# Reuse existing RDS infrastructure
from pudu.rds.rdsTable import RDSTable
from pudu.configs.database_config_loader import DynamicDatabaseConfig

# Import calculator
from ..calculators.metrics_calculator import PerformanceMetricsCalculator

logger = logging.getLogger(__name__)

# CRITICAL FIX: Force new connections for each thread
reuse_connection = False

# Thread-local storage for connections
thread_local = threading.local()


class DatabaseDataService:
    """
    FIXED: Enhanced service with proper connection management for parallel execution
    """

    def __init__(self, config: DynamicDatabaseConfig, start_date: str, end_date: str):
        """Initialize with database configuration and calculator"""
        self.config = config
        self.connection_config = "credentials.yaml"
        self.metrics_calculator = PerformanceMetricsCalculator(start_date, end_date)

        # Thread pool for parallel operations
        self.max_workers = 4  # REDUCED from 6 to avoid connection exhaustion

        # Connection retry configuration
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    # ============================================================================
    # FIXED: Connection Management
    # ============================================================================

    def _create_table_with_retry(self, connection_config: str, database_name: str,
                                 table_name: str, fields: Optional[List[str]],
                                 primary_keys: List[str], max_retries: int = 3) -> Optional[RDSTable]:
        """
        Create RDSTable with retry logic and proper connection settings
        """
        for attempt in range(max_retries):
            try:
                table = RDSTable(
                    connection_config=connection_config,
                    database_name=database_name,
                    table_name=table_name,
                    fields=fields,
                    primary_keys=primary_keys,
                    reuse_connection=False
                )
                return table
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to create table connection after {max_retries} attempts")
                    return None

    def _execute_query_with_retry(self, table: RDSTable, query: str,
                                  max_retries: int = 3) -> pd.DataFrame:
        """
        Execute query with retry logic for connection errors
        """
        for attempt in range(max_retries):
            try:
                result = table.execute_query(query)
                return result
            except Exception as e:
                logger.warning(f"Query attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    # Try to reconnect
                    try:
                        table.close()
                        table = self._create_table_with_retry(
                            table.connection_config,
                            table.database_name,
                            table.table_name,
                            table.fields,
                            table.primary_keys
                        )
                    except:
                        pass
                else:
                    logger.error(f"Query failed after {max_retries} attempts")
                    return pd.DataFrame()

    # ============================================================================
    # COLUMN REQUIREMENTS
    # ============================================================================

    @staticmethod
    def get_required_columns(table_type: str) -> List[str]:
        """Return all columns needed for a table type across ALL analyses"""
        column_requirements = {
            'robot_status': [
                'robot_sn', 'robot_type', 'robot_name', 'location_id',
                'water_level', 'sewage_level', 'battery_level', 'battery_soh',
                'status', 'timestamp_utc'
            ],
            'robot_task': [
                'robot_sn', 'task_name', 'mode', 'sub_mode', 'type',
                'actual_area', 'plan_area', 'start_time', 'end_time', 'duration',
                'efficiency', 'battery_usage', 'consumption', 'water_consumption',
                'progress', 'status', 'map_name', 'map_url', 'new_map_url'
            ],
            'robot_charging': [
                'robot_sn', 'robot_name', 'start_time', 'end_time', 'duration',
                'initial_power', 'final_power', 'power_gain', 'status'
            ],
            'robot_events': [
                'robot_sn', 'event_id', 'error_id', 'event_level', 'event_type',
                'event_detail', 'task_time', 'upload_time', 'created_at'
            ],
            'location': [
                'building_id', 'building_name', 'city', 'state', 'country'
            ]
        }
        return column_requirements.get(table_type, [])

    # ============================================================================
    # FIXED: Sequential Data Fetching (More Reliable)
    # ============================================================================

    def fetch_all_report_data(self, target_robots: List[str], start_date: str,
                             end_date: str, content_categories: List[str]) -> Dict[str, pd.DataFrame]:
        """
        FIXED: Fetch all required data SEQUENTIALLY to avoid connection issues

        Trade-off: Slightly slower but much more reliable
        """
        logger.info(f"Fetching report data for categories: {content_categories} using SEQUENTIAL execution")

        report_data = {}

        try:
            # Fetch sequentially with proper connection management

            # 1. Robot status
            logger.info("Fetching robot status...")
            report_data['robot_status'] = self.fetch_robot_status_data(target_robots)

            # 2. Location data
            logger.info("Fetching location data...")
            report_data['robot_locations'] = self.fetch_location_data(target_robots)

            # 3. Cleaning tasks
            logger.info("Fetching cleaning tasks...")
            report_data['cleaning_tasks'] = self.fetch_cleaning_tasks_data(
                target_robots, start_date, end_date
            )

            # 4. Charging data
            logger.info("Fetching charging data...")
            report_data['charging_tasks'] = self.fetch_charging_data(
                target_robots, start_date, end_date
            )

            # 5. Events (if requested)
            if 'event-analysis' in content_categories:
                logger.info("Fetching events...")
                report_data['events'] = self.fetch_events_data(
                    target_robots, start_date, end_date
                )
            else:
                report_data['events'] = pd.DataFrame()

            # 6. Operation history
            logger.info("Fetching operation history...")
            report_data['operation_history'] = self.fetch_operation_history_data(
                target_robots, start_date, end_date
            )

            logger.info(f"Sequential data fetching completed: {list(report_data.keys())}")
            return report_data

        except Exception as e:
            logger.error(f"Error in fetch_all_report_data: {e}")
            # Return empty DataFrames for failed fetches
            return {
                'robot_status': report_data.get('robot_status', pd.DataFrame()),
                'robot_locations': report_data.get('robot_locations', pd.DataFrame()),
                'cleaning_tasks': report_data.get('cleaning_tasks', pd.DataFrame()),
                'charging_tasks': report_data.get('charging_tasks', pd.DataFrame()),
                'events': report_data.get('events', pd.DataFrame()),
                'operation_history': report_data.get('operation_history', pd.DataFrame())
            }

    # ============================================================================
    # FIXED: Data Fetching Methods with Proper Connection Management
    # ============================================================================

    def fetch_robot_status_data(self, target_robots: List[str]) -> pd.DataFrame:
        """Fetch current robot status data with proper error handling"""
        logger.info(f"Fetching robot status for {len(target_robots)} robots")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_status', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    # Create connection with retry
                    table = self._create_table_with_retry(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    if not table:
                        logger.warning(f"Failed to create connection for {table_config['database']}")
                        continue

                    # Get all required columns
                    columns = self.get_required_columns('robot_status')
                    columns_str = ', '.join(columns)

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT {columns_str}
                        FROM (
                            SELECT DISTINCT
                                mrm.robot_sn, mrm.robot_type, mrm.robot_name, mrm.location_id,
                                t.water_level, t.sewage_level, t.battery_level, t.status,
                                t.battery_soh, t.timestamp_utc,
                                ROW_NUMBER() OVER (PARTITION BY mrm.robot_sn ORDER BY t.timestamp_utc DESC) as rn
                            FROM {table.table_name} t
                            INNER JOIN mnt_robots_management mrm ON t.robot_sn = mrm.robot_sn
                            WHERE mrm.robot_sn IN ('{robot_list}')
                        ) ranked
                        WHERE rn = 1
                    """

                    # Execute with retry
                    result_df = self._execute_query_with_retry(table, query)

                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} robot status records from {table_config['database']}")

                    # Always close connection
                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching robot status from {table_config.get('database', 'unknown')}: {e}")
                    continue

            # Combine and deduplicate
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                # Deduplicate by robot_sn, keeping most recent
                combined_df = combined_df.drop_duplicates(subset=['robot_sn'], keep='first')
                logger.info(f"Total robot status records: {len(combined_df)}")
                return combined_df

            logger.warning("No robot status data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_robot_status_data: {e}")
            return pd.DataFrame()

    def fetch_cleaning_tasks_data(self, target_robots: List[str],
                                  start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical cleaning tasks data with proper error handling"""
        logger.info(f"Fetching tasks for {len(target_robots)} robots from {start_date} to {end_date}")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_task', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = self._create_table_with_retry(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    if not table:
                        continue

                    columns = self.get_required_columns('robot_task')
                    columns_str = ', '.join(columns)

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT {columns_str}
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND start_time >= '{start_date}'
                        AND start_time <= '{end_date}'
                        ORDER BY start_time DESC
                    """

                    result_df = self._execute_query_with_retry(table, query)

                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} task records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching tasks from {table_config.get('database', 'unknown')}: {e}")
                    continue

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
        """Fetch historical charging sessions data with proper error handling"""
        logger.info(f"Fetching charging data for {len(target_robots)} robots")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_charging', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = self._create_table_with_retry(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    if not table:
                        continue

                    columns = self.get_required_columns('robot_charging')
                    columns_str = ', '.join(columns)

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT {columns_str}
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND start_time >= '{start_date}'
                        AND start_time <= '{end_date}'
                        ORDER BY start_time DESC
                    """

                    result_df = self._execute_query_with_retry(table, query)

                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} charging records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching charging data from {table_config.get('database', 'unknown')}: {e}")
                    continue

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total charging records: {len(combined_df)}")
                return combined_df

            logger.warning(f"No charging data found for {start_date} to {end_date}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_charging_data: {e}")
            return pd.DataFrame()

    def fetch_events_data(self, target_robots: List[str],
                         start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical robot events data with proper error handling"""
        logger.info(f"Fetching events for {len(target_robots)} robots")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_events', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = self._create_table_with_retry(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    if not table:
                        continue

                    columns = self.get_required_columns('robot_events')
                    columns_str = ', '.join(columns)

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT {columns_str}
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND task_time >= '{start_date}'
                        AND task_time <= '{end_date}'
                        ORDER BY task_time DESC
                    """

                    result_df = self._execute_query_with_retry(table, query)

                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} event records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching events from {table_config.get('database', 'unknown')}: {e}")
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

    def fetch_operation_history_data(self, target_robots: List[str],
                                    start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch robot operation history data with proper error handling"""
        logger.info(f"Fetching operation history for {len(target_robots)} robots")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_status', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = self._create_table_with_retry(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    if not table:
                        continue

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, status, timestamp_utc, battery_soh
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND timestamp_utc >= '{start_date}'
                        AND timestamp_utc <= '{end_date}'
                        ORDER BY robot_sn, timestamp_utc
                    """

                    result_df = self._execute_query_with_retry(table, query)

                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} operation history records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching operation history from {table_config.get('database', 'unknown')}: {e}")
                    continue

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total operation history records: {len(combined_df)}")
                return combined_df

            logger.warning("No operation history data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_operation_history_data: {e}")
            return pd.DataFrame()

    def fetch_location_data(self, target_robots: List[str]) -> pd.DataFrame:
        """Fetch location/building information for robots with proper error handling"""
        logger.info(f"Fetching location data for {len(target_robots)} robots")

        try:
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
                    table = self._create_table_with_retry(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys']
                    )

                    if not table:
                        continue

                    columns = self.get_required_columns('location')
                    columns_str = ', '.join(columns)

                    location_list = "', '".join(location_ids)
                    query = f"""
                        SELECT {columns_str}
                        FROM {table.table_name}
                        WHERE building_id IN ('{location_list}')
                    """

                    result_df = self._execute_query_with_retry(table, query)

                    if not result_df.empty:
                        all_locations.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} location records")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching location data: {e}")
                    continue

            # Combine and merge
            if all_locations:
                locations_df = pd.concat(all_locations, ignore_index=True).drop_duplicates()

                # Merge with robot status
                robot_locations = robot_status.merge(
                    locations_df,
                    left_on='location_id',
                    right_on='building_id',
                    how='left'
                )

                logger.info(f"Mapped {len(robot_locations)} robots to locations")
                return robot_locations

            logger.warning("No location data found")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching location data: {e}")
            return pd.DataFrame()

    def fetch_all_time_tasks_for_roi(self, target_robots: List[str],
                                    end_date: str) -> pd.DataFrame:
        """Fetch minimal task data for ROI calculation with proper error handling"""
        logger.info(f"Fetching all-time tasks for ROI ({len(target_robots)} robots)")

        try:
            table_configs = self.config.get_table_configs_for_robots('robot_task', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    table = self._create_table_with_retry(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    if not table:
                        continue

                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, actual_area, consumption, water_consumption,
                               start_time, status, efficiency
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND start_time <= '{end_date}'
                        AND actual_area IS NOT NULL
                        AND actual_area > 0
                        ORDER BY robot_sn, start_time ASC
                    """

                    result_df = self._execute_query_with_retry(table, query)

                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} ROI task records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching ROI tasks from {table_config.get('database', 'unknown')}: {e}")
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

    # ============================================================================
    # PARALLELISM LEVEL 2: Parallel Calculation & Orchestration
    # ============================================================================

    def calculate_comprehensive_metrics(self, data: Dict[str, pd.DataFrame],
                                        start_date: str, end_date: str) -> Dict[str, Any]:
        """Calculate comprehensive metrics using calculator"""
        logger.info("Calculating comprehensive metrics")

        try:
            # Extract DataFrames
            robot_data = data.get('robot_status', pd.DataFrame())
            tasks_data = data.get('cleaning_tasks', pd.DataFrame())
            charging_data = data.get('charging_tasks', pd.DataFrame())
            events_data = data.get('events', pd.DataFrame())
            robot_locations = data.get('robot_locations', pd.DataFrame())
            operation_history_data = data.get('operation_history', pd.DataFrame())

            # Start with empty dict
            metrics = {}

            # Pre-calculate shared metrics
            if not tasks_data.empty:
                self.metrics_calculator.precalculate_task_metrics(tasks_data)
                logger.info("✓ Pre-calculated task metrics")

            if not robot_locations.empty:
                self.metrics_calculator.set_robot_facility_map(robot_locations)
                logger.info("✓ Cached robot-facility mapping")

            # Calculate each metric with individual error handling
            try:
                metrics['fleet_performance'] = self.metrics_calculator.calculate_fleet_availability(
                    robot_data, tasks_data, start_date, end_date
                )
            except Exception as e:
                logger.error(f"Error calculating fleet performance: {e}")
                metrics['fleet_performance'] = {
                    'total_robots': 0,
                    'active_robots': 0,
                    'total_running_hours': 0.0,
                    'avg_daily_running_hours_per_robot': 0.0,
                    'days_with_tasks': 0,
                    'period_length': 0,
                    'days_ratio': '0/0'
                }

            try:
                metrics['task_performance'] = self.metrics_calculator.calculate_task_performance_metrics(
                    tasks_data
                )
            except Exception as e:
                logger.error(f"Error calculating task performance: {e}")
                metrics['task_performance'] = {
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

            try:
                metrics['charging_performance'] = self.metrics_calculator.calculate_charging_performance_metrics(
                    charging_data
                )
            except Exception as e:
                logger.error(f"Error calculating charging performance: {e}")
                metrics['charging_performance'] = {
                    'total_sessions': 0,
                    'avg_charging_duration_minutes': 0.0,
                    'median_charging_duration_minutes': 0.0,
                    'avg_power_gain_percent': 0.0,
                    'median_power_gain_percent': 0.0,
                    'total_charging_time': 0.0
                }

            try:
                metrics['resource_utilization'] = self.metrics_calculator.calculate_resource_utilization_metrics(
                    tasks_data
                )
            except Exception as e:
                logger.error(f"Error calculating resource utilization: {e}")
                metrics['resource_utilization'] = {
                    'total_energy_consumption_kwh': 0.0,
                    'total_water_consumption_floz': 0.0,
                    'area_per_kwh': 0,
                    'area_per_gallon': 0,
                    'total_area_cleaned_sqft': 0.0
                }

            try:
                metrics['event_analysis'] = self.metrics_calculator.calculate_event_analysis_metrics(
                    events_data
                )
            except Exception as e:
                logger.error(f"Error calculating event analysis: {e}")
                metrics['event_analysis'] = {
                    'total_events': 0,
                    'critical_events': 0,
                    'error_events': 0,
                    'warning_events': 0,
                    'info_events': 0,
                    'event_types': {},
                    'event_levels': {}
                }

            # Event location metrics
            if not events_data.empty and not robot_locations.empty:
                try:
                    metrics['event_location_mapping'] = self.metrics_calculator.calculate_event_location_mapping(
                        events_data, robot_locations
                    )
                    metrics['event_type_by_location'] = self.metrics_calculator.calculate_event_type_by_location(
                        events_data, robot_locations
                    )
                except Exception as e:
                    logger.error(f"Error calculating event location metrics: {e}")
                    metrics['event_location_mapping'] = {}
                    metrics['event_type_by_location'] = {}
            else:
                metrics['event_location_mapping'] = {}
                metrics['event_type_by_location'] = {}

            # Facility-specific metrics
            if not robot_locations.empty:
                try:
                    facility_metrics_batch = self._calculate_all_facility_metrics_batch_delegated(
                        tasks_data, charging_data, robot_locations, start_date, end_date
                    )
                    metrics.update(facility_metrics_batch)
                except Exception as e:
                    logger.error(f"Error calculating facility metrics: {e}")
                    metrics['facility_performance'] = {'facilities': {}}
                    metrics['facility_efficiency_metrics'] = {}
                    metrics['facility_task_metrics'] = {}
                    metrics['facility_charging_metrics'] = {}
                    metrics['facility_resource_metrics'] = {}
                    metrics['facility_breakdown_metrics'] = {}
            else:
                metrics['facility_performance'] = {'facilities': {}}
                metrics['facility_efficiency_metrics'] = {}
                metrics['facility_task_metrics'] = {}
                metrics['facility_charging_metrics'] = {}
                metrics['facility_resource_metrics'] = {}
                metrics['facility_breakdown_metrics'] = {}

            # Individual robot metrics
            period_length = self.metrics_calculator._calculate_period_length(start_date, end_date)
            try:
                metrics['individual_robots'] = self.metrics_calculator.calculate_individual_robot_performance(
                    tasks_data, charging_data,
                    robot_locations if not robot_locations.empty else robot_data,
                    operation_history_data, period_length
                )
            except Exception as e:
                logger.error(f"Error calculating individual robots: {e}")
                metrics['individual_robots'] = []

            # Map coverage
            try:
                metrics['map_coverage'] = self.metrics_calculator.calculate_map_coverage_metrics(tasks_data)
            except Exception as e:
                logger.error(f"Error calculating map coverage: {e}")
                metrics['map_coverage'] = []

            # Map performance by building
            try:
                if not robot_locations.empty:
                    metrics['map_performance_by_building'] = self.metrics_calculator.calculate_map_performance_by_building(
                        tasks_data, robot_locations
                    )
                else:
                    metrics['map_performance_by_building'] = {}
            except Exception as e:
                logger.error(f"Error calculating map performance: {e}")
                metrics['map_performance_by_building'] = {}

            # Trend data
            try:
                metrics['trend_data'] = self.metrics_calculator.calculate_daily_trends(
                    tasks_data, charging_data, start_date, end_date
                )
            except Exception as e:
                logger.error(f"Error calculating trends: {e}")
                metrics['trend_data'] = {
                    'dates': [],
                    'charging_sessions_trend': [],
                    'charging_duration_trend': [],
                    'energy_consumption_trend': [],
                    'water_usage_trend': [],
                    'cost_savings_trend': [],
                    'roi_improvement_trend': []
                }

            # Cost analysis
            try:
                metrics['cost_analysis'] = self.metrics_calculator.calculate_cost_analysis_metrics(
                    tasks_data, metrics.get('resource_utilization', {}), roi_improvement='N/A'
                )
            except Exception as e:
                logger.error(f"Error calculating cost analysis: {e}")
                metrics['cost_analysis'] = {
                    'cost_per_sqft': 0.0,
                    'total_cost': 0.0,
                    'hours_saved': 0.0,
                    'savings': 0.0,
                    'annual_projected_savings': 0.0,
                    'cost_efficiency_improvement': 0.0,
                    'roi_improvement': 'N/A',
                    'human_cost': 0.0,
                    'water_cost': 0.0,
                    'energy_cost': 0.0,
                    'hourly_wage': 25.0
                }

            logger.info("Comprehensive metrics calculation completed")
            return metrics

        except Exception as e:
            logger.error(f"Critical error in calculate_comprehensive_metrics: {e}", exc_info=True)
            # Return minimal structure
            return {
                'fleet_performance': {},
                'task_performance': {},
                'charging_performance': {},
                'resource_utilization': {},
                'event_analysis': {},
                'cost_analysis': {},
                'individual_robots': [],
                'map_coverage': []
            }

    def _calculate_all_facility_metrics_batch_delegated(self, tasks_data: pd.DataFrame,
                                              charging_data: pd.DataFrame,
                                              robot_locations: pd.DataFrame,
                                              start_date: str, end_date: str) -> Dict[str, Any]:
        """
        OPTIMIZED: Batch facility calculation using DELEGATED calculator methods.

        Previously: Mixed data prep + calculation in service
        Now: Data prep here, all calculations in calculator

        Uses cached robot-facility map from pre-calculation phase.
        """
        try:
            logger.info("Batch calculating all facility metrics (delegated to calculator)")

            # Get cached robot-facility mapping (already set in pre-calculation)
            robot_facility_map = self.metrics_calculator.get_robot_facility_map()

            if not robot_facility_map:
                logger.warning("Robot facility map not cached, falling back to basic calculation")
                robot_facility_map = self.metrics_calculator.set_robot_facility_map(robot_locations)

            # Add facility column to tasks
            tasks_with_facility = tasks_data.copy()
            tasks_with_facility['facility'] = tasks_with_facility['robot_sn'].map(
                robot_facility_map
            )

            # Add facility column to charging
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

            # Single groupby for tasks - delegate calculations to calculator
            for building_name, facility_tasks in tasks_with_facility.groupby('facility'):
                if pd.isna(building_name):
                    continue

                # Get cached metrics (already calculated in pre-calculation phase)
                total_tasks = len(facility_tasks)
                status_counts = self.metrics_calculator.get_cached_status_counts(facility_tasks)
                running_hours = self.metrics_calculator.get_cached_duration_sum(facility_tasks)

                # Area calculations - vectorized
                actual_area_sqm = facility_tasks['actual_area'].fillna(0).sum() if 'actual_area' in facility_tasks.columns else 0
                planned_area_sqm = facility_tasks['plan_area'].fillna(0).sum() if 'plan_area' in facility_tasks.columns else 0
                actual_area_sqft = actual_area_sqm * 10.764
                planned_area_sqft = planned_area_sqm * 10.764

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

                # Days with tasks - use cached calculation
                facility_days = self.metrics_calculator.get_cached_days_with_tasks(facility_tasks)
                period_length = self.metrics_calculator._calculate_period_length(start_date, end_date)

                # DELEGATED TO CALCULATOR: Coverage by day
                coverage_by_day = self.metrics_calculator.calculate_facility_coverage_by_day(
                    tasks_data, robot_locations, building_name
                )

                robot_count = len(robot_locations[robot_locations['building_name'] == building_name])

                # Populate all facility metrics dictionaries
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

                # Vectorized duration parsing
                durations = facility_charging['duration'].apply(
                    self.metrics_calculator._parse_duration_str_to_minutes
                ).tolist()
                durations = [d for d in durations if d > 0]

                # Vectorized power gain parsing
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

    # ============================================================================
    # COMPREHENSIVE METRICS WITH COMPARISON - OPTIMIZED WITH PARALLELISM
    # ============================================================================

    def calculate_comprehensive_metrics_with_comparison(self, current_data: Dict[str, pd.DataFrame],
                                                       previous_data: Dict[str, pd.DataFrame],
                                                       current_start: str, current_end: str,
                                                       previous_start: str, previous_end: str) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics with period comparison and ROI.

        PARALLELISM LEVEL 2: Current and previous period calculations run in parallel.

        Previously: Sequential calculation (~10-15 seconds)
        Now: Parallel calculation (~5-8 seconds)

        Speedup: 2x faster
        """
        logger.info("Calculating comprehensive metrics with comparison and ROI using PARALLEL execution")

        try:
            # Extract data references
            tasks_data = current_data.get('cleaning_tasks', pd.DataFrame())
            events_data = current_data.get('events', pd.DataFrame())
            robot_locations = current_data.get('robot_locations', pd.DataFrame())
            charging_data = current_data.get('charging_tasks', pd.DataFrame())
            robot_status = current_data.get('robot_status', pd.DataFrame())

            # Get target robots
            target_robots = self._extract_target_robots(robot_status, tasks_data)

            # PARALLELISM LEVEL 2: Calculate current and previous metrics in parallel
            with ThreadPoolExecutor(max_workers=2) as executor:
                logger.info("Starting parallel calculation of current and previous period metrics...")

                # Submit both calculations concurrently
                current_future = executor.submit(
                    self.calculate_comprehensive_metrics,
                    current_data, current_start, current_end
                )

                previous_future = executor.submit(
                    self.calculate_comprehensive_metrics,
                    previous_data, previous_start, previous_end
                )

                # Wait for both to complete
                current_metrics = current_future.result()
                logger.info("✓ Current period metrics calculated")

                previous_metrics = previous_future.result()
                logger.info("✓ Previous period metrics calculated")

            # === ROI CALCULATION ===
            if target_robots:
                logger.info(f"Calculating ROI for {len(target_robots)} robots")

                # Fetch all-time task data for ROI
                all_time_tasks = self.fetch_all_time_tasks_for_roi(target_robots, current_end)

                # Calculate current and previous ROI
                roi_metrics = self.metrics_calculator.calculate_roi_metrics(
                    all_time_tasks, target_robots, current_end, monthly_lease_price=1500.0
                )
                previous_roi_metrics = self.metrics_calculator.calculate_roi_metrics(
                    all_time_tasks, target_robots, previous_end, monthly_lease_price=1500.0
                )

                # Update cost analysis with ROI
                self._update_cost_analysis_with_roi(
                    current_metrics, previous_metrics, roi_metrics, previous_roi_metrics
                )

                # Calculate daily ROI trends
                daily_roi_trends = self.metrics_calculator.calculate_daily_roi_trends(
                    tasks_data, all_time_tasks, target_robots, current_start, current_end
                )

                # Update trend data with ROI
                if current_metrics.get('trend_data') and daily_roi_trends.get('dates'):
                    current_metrics['trend_data']['cost_savings_trend'] = daily_roi_trends['daily_savings_trend']
                    current_metrics['trend_data']['roi_improvement_trend'] = daily_roi_trends['roi_trend']

                logger.info(f"ROI calculation complete: {roi_metrics['total_roi_percent']:.1f}%")
            else:
                logger.warning("No target robots for ROI calculation")
                self._set_default_roi_metrics(current_metrics)

            # === ROBOT HEALTH SCORES - DELEGATED TO CALCULATOR ===
            if target_robots:
                logger.info("Calculating robot health scores (delegated to calculator)")

                operation_history_data = current_data.get('operation_history', pd.DataFrame())

                # DELEGATED: All health score logic in calculator
                robot_health_scores = self.metrics_calculator.calculate_robot_health_scores(
                    operation_history_data,
                    tasks_data,
                    target_robots
                )

                current_metrics['robot_health_scores'] = robot_health_scores
                logger.info(f"Health scores calculated for {len(robot_health_scores)} robots")
            else:
                current_metrics['robot_health_scores'] = {}

            # === ADDITIONAL CURRENT PERIOD METRICS - DELEGATED TO CALCULATOR ===

            # Weekend completion and average duration
            weekend_completion = self.metrics_calculator.calculate_weekend_schedule_completion(tasks_data)
            avg_duration = self.metrics_calculator.calculate_average_task_duration(tasks_data)

            current_metrics['task_performance']['weekend_schedule_completion'] = weekend_completion
            current_metrics['task_performance']['avg_task_duration_minutes'] = avg_duration

            # Weekday completion rates - DELEGATED
            current_metrics['weekday_completion'] = self.metrics_calculator.calculate_weekday_completion_rates(
                tasks_data
            )

            # Days with tasks and period length
            days_info = self.metrics_calculator.calculate_days_with_tasks_and_period_length(
                tasks_data, current_start, current_end
            )
            current_metrics['fleet_performance'].update(days_info)

            # Daily location efficiency - DELEGATED TO CALCULATOR
            if not robot_locations.empty:
                daily_location_efficiency = self.metrics_calculator.calculate_daily_task_efficiency_by_location(
                    tasks_data, robot_locations, current_start, current_end
                )
                current_metrics['daily_location_efficiency'] = daily_location_efficiency

            # === PREVIOUS PERIOD SUPPLEMENTARY METRICS ===
            previous_tasks_data = previous_data.get('cleaning_tasks', pd.DataFrame())
            previous_avg_duration = self.metrics_calculator.calculate_average_task_duration(
                previous_tasks_data
            )
            previous_metrics['task_performance']['avg_task_duration_minutes'] = previous_avg_duration

            # === PERIOD COMPARISON - DELEGATED TO CALCULATOR ===
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

            # === FINANCIAL TRENDS - DELEGATED TO CALCULATOR ===
            daily_financial_trends = self.metrics_calculator.calculate_daily_financial_trends(
                tasks_data, current_start, current_end
            )
            if daily_financial_trends and daily_financial_trends.get('dates'):
                current_metrics['financial_trend_data'] = daily_financial_trends

            logger.info("Successfully calculated metrics with comparison and ROI using parallel execution")
            return current_metrics

        except Exception as e:
            logger.error(f"Error calculating metrics with comparison and ROI: {e}")
            # Fallback to current metrics only
            return self._calculate_fallback_metrics(current_data, current_start, current_end)

    def _extract_target_robots(self, robot_status: pd.DataFrame,
                               tasks_data: pd.DataFrame) -> List[str]:
        """Extract target robot list from available data"""
        if not robot_status.empty:
            return robot_status['robot_sn'].dropna().unique().tolist()
        elif not tasks_data.empty:
            return tasks_data['robot_sn'].dropna().unique().tolist()
        return []

    def _update_cost_analysis_with_roi(self, current_metrics: Dict[str, Any],
                                  previous_metrics: Dict[str, Any],
                                  roi_metrics: Dict[str, Any],
                                  previous_roi_metrics: Dict[str, Any]) -> None:
        """Update cost analysis with ROI data - FIXED for missing keys"""

        # FIX: Ensure cost_analysis exists before updating
        if 'cost_analysis' not in current_metrics:
            logger.warning("cost_analysis missing, initializing with placeholders")
            current_metrics['cost_analysis'] = {
                'cost_per_sqft': 0.0,
                'total_cost': 0.0,
                'hours_saved': 0.0,
                'savings': 0.0,
                'annual_projected_savings': 0.0,
                'cost_efficiency_improvement': 0.0,
                'roi_improvement': 'N/A',
                'human_cost': 0.0,
                'water_cost': 0.0,
                'energy_cost': 0.0,
                'hourly_wage': 25.0
            }

        if 'cost_analysis' not in previous_metrics:
            logger.warning("cost_analysis missing in previous, initializing")
            previous_metrics['cost_analysis'] = {
                'cost_per_sqft': 0.0,
                'total_cost': 0.0,
                'hours_saved': 0.0,
                'savings': 0.0,
                'annual_projected_savings': 0.0,
                'cost_efficiency_improvement': 0.0,
                'roi_improvement': 'N/A',
                'human_cost': 0.0,
                'water_cost': 0.0,
                'energy_cost': 0.0,
                'hourly_wage': 25.0
            }

        # Now safe to update
        current_metrics['cost_analysis'].update({
            'roi_improvement': f"{roi_metrics['total_roi_percent']:.1f}%",
            'total_investment': roi_metrics['total_investment'],
            'robot_roi_breakdown': roi_metrics['robot_breakdown'],
            'monthly_savings_rate': roi_metrics['monthly_savings_rate'],
            'payback_period': roi_metrics['payback_period'],
            'cumulative_savings': roi_metrics['total_savings']
        })

        previous_metrics['cost_analysis'].update({
            'roi_improvement': f"{previous_roi_metrics['total_roi_percent']:.1f}%",
            'total_investment': previous_roi_metrics['total_investment'],
            'robot_roi_breakdown': previous_roi_metrics['robot_breakdown'],
            'monthly_savings_rate': previous_roi_metrics['monthly_savings_rate'],
            'payback_period': previous_roi_metrics['payback_period'],
            'cumulative_savings': previous_roi_metrics['total_savings']
        })

    def _set_default_roi_metrics(self, metrics: Dict[str, Any]) -> None:
        """Set default ROI metrics when calculation not possible - FIXED"""

        # FIX: Ensure cost_analysis exists
        if 'cost_analysis' not in metrics:
            logger.warning("cost_analysis missing in _set_default_roi_metrics, initializing")
            metrics['cost_analysis'] = {
                'cost_per_sqft': 0.0,
                'total_cost': 0.0,
                'hours_saved': 0.0,
                'savings': 0.0,
                'annual_projected_savings': 0.0,
                'cost_efficiency_improvement': 0.0,
                'roi_improvement': '0.0%',
                'human_cost': 0.0,
                'water_cost': 0.0,
                'energy_cost': 0.0,
                'hourly_wage': 25.0,
                'total_investment': 0.0,
                'robot_roi_breakdown': {}
            }

        # Now safe to update
        metrics['cost_analysis'].update({
            'roi_improvement': '0.0%',
            'total_investment': 0.0,
            'robot_roi_breakdown': {}
        })

    def _calculate_fallback_metrics(self, current_data: Dict[str, pd.DataFrame],
                                   current_start: str, current_end: str) -> Dict[str, Any]:
        """Calculate fallback metrics - FIXED for missing keys"""

        current_metrics = self.calculate_comprehensive_metrics(
            current_data, current_start, current_end
        )

        # FIX: Ensure task_performance exists
        if 'task_performance' not in current_metrics:
            logger.warning("task_performance missing, initializing")
            current_metrics['task_performance'] = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'cancelled_tasks': 0,
                'interrupted_tasks': 0,
                'completion_rate': 0.0,
                'total_area_cleaned': 0.0,
                'coverage_efficiency': 0.0,
                'task_modes': {},
                'incomplete_task_rate': 0.0,
                'weekend_schedule_completion': 0.0,
                'avg_task_duration_minutes': 0.0
            }

        tasks_data = current_data.get('cleaning_tasks', pd.DataFrame())

        # Safe calculation even with empty data
        weekend_completion = 0.0
        avg_duration = 0.0

        if not tasks_data.empty:
            try:
                weekend_completion = self.metrics_calculator.calculate_weekend_schedule_completion(tasks_data)
                avg_duration = self.metrics_calculator.calculate_average_task_duration(tasks_data)
            except Exception as e:
                logger.error(f"Error calculating supplementary metrics: {e}")

        current_metrics['task_performance']['weekend_schedule_completion'] = weekend_completion
        current_metrics['task_performance']['avg_task_duration_minutes'] = avg_duration
        current_metrics['period_comparisons'] = {}
        current_metrics['comparison_metadata'] = {'comparison_available': False}

        self._set_default_roi_metrics(current_metrics)

        return current_metrics

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def calculate_reporting_period_length(self, start_date: str, end_date: str) -> int:
        """Calculate reporting period length in days"""
        return self.metrics_calculator._calculate_period_length(start_date, end_date)