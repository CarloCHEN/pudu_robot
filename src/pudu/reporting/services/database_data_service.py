# src/pudu/reporting/services/database_data_service.py
import logging
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime

# Reuse existing RDS infrastructure
from pudu.rds.rdsTable import RDSTable
from pudu.configs.database_config_loader import DynamicDatabaseConfig

# Import new calculators
from ..calculators.metrics_calculator import PerformanceMetricsCalculator

logger = logging.getLogger(__name__)

class DatabaseDataService:
    """Enhanced service for querying and processing historical data from databases for report generation"""

    def __init__(self, config: DynamicDatabaseConfig):
        """Initialize with database configuration and calculators"""
        self.config = config
        self.connection_config = "credentials.yaml"
        self.metrics_calculator = PerformanceMetricsCalculator()

    def fetch_robot_status_data(self, target_robots: List[str]) -> pd.DataFrame:
        """
        Fetch current robot status data from databases

        Args:
            target_robots: List of robot serial numbers

        Returns:
            DataFrame with robot status data
        """
        logger.info(f"Fetching robot status data for {len(target_robots)} robots")

        try:
            # Get table configurations for robot status
            table_configs = self.config.get_table_configs_for_robots('robot_status', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=True
                    )

                    # Get target robots for this database
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    # Query robot status data
                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, robot_type, robot_name, location_id, water_level, sewage_level, battery_level, status
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} robot status records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching robot status from {table_config['database']}: {e}")
                    continue

            # Combine all data
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total robot status records: {len(combined_df)}")
                return combined_df
            else:
                logger.warning("No robot status data found")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_robot_status_data: {e}")
            return pd.DataFrame()

    def fetch_cleaning_tasks_data(self, target_robots: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical cleaning tasks data from databases

        Args:
            target_robots: List of robot serial numbers
            start_date: Start date for data range (YYYY-MM-DD HH:MM:SS)
            end_date: End date for data range (YYYY-MM-DD HH:MM:SS)

        Returns:
            DataFrame with cleaning tasks data
        """
        logger.info(f"Fetching cleaning tasks data for {len(target_robots)} robots from {start_date} to {end_date}")

        try:
            # Get table configurations for robot tasks
            table_configs = self.config.get_table_configs_for_robots('robot_task', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=True
                    )

                    # Get target robots for this database
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    # Query tasks data with date range
                    robot_list = "', '".join(db_robots)
                    query = f"""
                        SELECT robot_sn, task_name, mode, sub_mode, type,
                               actual_area, plan_area, start_time, end_time, duration,
                               efficiency, battery_usage, water_consumption, progress, status,
                               map_name, map_url, new_map_url
                        FROM {table.table_name}
                        WHERE robot_sn IN ('{robot_list}')
                        AND start_time >= '{start_date}'
                        AND start_time <= '{end_date}'
                        ORDER BY start_time DESC
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        all_data.append(result_df)
                        logger.info(f"Retrieved {len(result_df)} task records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching tasks from {table_config['database']}: {e}")
                    continue

            # Combine all data
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total cleaning task records: {len(combined_df)}")
                return combined_df
            else:
                logger.warning("No cleaning tasks data found")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_cleaning_tasks_data: {e}")
            return pd.DataFrame()

    def fetch_charging_data(self, target_robots: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical charging sessions data from databases

        Args:
            target_robots: List of robot serial numbers
            start_date: Start date for data range (YYYY-MM-DD HH:MM:SS)
            end_date: End date for data range (YYYY-MM-DD HH:MM:SS)

        Returns:
            DataFrame with charging sessions data
        """
        logger.info(f"Fetching charging data for {len(target_robots)} robots from {start_date} to {end_date}")

        try:
            # Get table configurations for robot charging
            table_configs = self.config.get_table_configs_for_robots('robot_charging', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=True
                    )

                    # Get target robots for this database
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    # Query charging data with date range
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
                        logger.info(f"Retrieved {len(result_df)} charging records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching charging data from {table_config['database']}: {e}")
                    continue

            # Combine all data
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total charging session records: {len(combined_df)}")
                return combined_df
            else:
                logger.warning("No charging data found")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_charging_data: {e}")
            return pd.DataFrame()

    def fetch_events_data(self, target_robots: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical robot events data from databases

        Args:
            target_robots: List of robot serial numbers
            start_date: Start date for data range (YYYY-MM-DD HH:MM:SS)
            end_date: End date for data range (YYYY-MM-DD HH:MM:SS)

        Returns:
            DataFrame with robot events data
        """
        logger.info(f"Fetching events data for {len(target_robots)} robots from {start_date} to {end_date}")

        try:
            # Get table configurations for robot events
            table_configs = self.config.get_table_configs_for_robots('robot_events', target_robots)

            all_data = []
            for table_config in table_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=True
                    )

                    # Get target robots for this database
                    db_robots = table_config.get('robot_sns', [])
                    if not db_robots:
                        continue

                    # Query events data with date range
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
                        logger.info(f"Retrieved {len(result_df)} event records from {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching events from {table_config['database']}: {e}")
                    continue

            # Combine all data
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"Total event records: {len(combined_df)}")
                return combined_df
            else:
                logger.warning("No events data found")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error in fetch_events_data: {e}")
            return pd.DataFrame()

    def fetch_map_coverage_data(self, target_robots: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch map coverage data for efficiency calculations

        Args:
            target_robots: List of robot serial numbers
            start_date: Start date for data range
            end_date: End date for data range

        Returns:
            DataFrame with map coverage information
        """
        logger.info(f"Fetching map coverage data for {len(target_robots)} robots")

        try:
            # This would query map-specific coverage data if available
            # For now, we'll extract from tasks data
            tasks_data = self.fetch_cleaning_tasks_data(target_robots, start_date, end_date)

            if not tasks_data.empty and 'map_name' in tasks_data.columns:
                # Calculate coverage by map
                map_coverage = tasks_data.groupby('map_name').agg({
                    'actual_area': 'sum',
                    'plan_area': 'sum',
                    'efficiency': 'mean'
                }).reset_index()

                # Calculate coverage percentage
                map_coverage['coverage_percentage'] = (
                    map_coverage['actual_area'] / map_coverage['plan_area'] * 100
                ).round(1)

                return map_coverage
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching map coverage data: {e}")
            return pd.DataFrame()

    def fetch_operational_hours_data(self, target_robots: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch robot operational hours for availability calculations

        Args:
            target_robots: List of robot serial numbers
            start_date: Start date for data range
            end_date: End date for data range

        Returns:
            DataFrame with operational hours by robot
        """
        logger.info(f"Fetching operational hours for {len(target_robots)} robots")

        try:
            # Calculate from tasks data
            tasks_data = self.fetch_cleaning_tasks_data(target_robots, start_date, end_date)

            if not tasks_data.empty:
                # Group by robot and sum operational hours
                # Note: task table only has robot_sn, not robot_name
                robot_hours = tasks_data.groupby('robot_sn').agg({
                    'duration': lambda x: self._sum_durations(x)
                }).reset_index()

                robot_hours.columns = ['robot_sn', 'operational_hours']

                # Optionally get robot names from robot status table if needed
                try:
                    robot_status_data = self.fetch_robot_status_data(target_robots)
                    if not robot_status_data.empty and 'robot_name' in robot_status_data.columns:
                        # Merge to get robot names
                        robot_hours = robot_hours.merge(
                            robot_status_data[['robot_sn', 'robot_name']].drop_duplicates(),
                            on='robot_sn',
                            how='left'
                        )
                        # Fill missing robot names with robot_sn
                        robot_hours['robot_name'] = robot_hours['robot_name'].fillna(robot_hours['robot_sn'])
                    else:
                        # If no robot names available, use robot_sn as name
                        robot_hours['robot_name'] = robot_hours['robot_sn']
                except Exception as e:
                    logger.warning(f"Could not fetch robot names: {e}")
                    robot_hours['robot_name'] = robot_hours['robot_sn']

                return robot_hours
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching operational hours: {e}")
            return pd.DataFrame()

    def fetch_all_report_data(self, target_robots: List[str], start_date: str, end_date: str,
                             content_categories: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Fetch all required data for report generation based on content categories

        Args:
            target_robots: List of robot serial numbers
            start_date: Start date for data range
            end_date: End date for data range
            content_categories: List of content categories to fetch

        Returns:
            Dict mapping category names to DataFrames
        """
        logger.info(f"Fetching all report data for categories: {content_categories}")

        report_data = {}

        try:
            if 'robot-status' in content_categories:
                logger.info("Fetching robot status data...")
                report_data['robot_status'] = self.fetch_robot_status_data(target_robots)

            if 'cleaning-tasks' in content_categories:
                logger.info("Fetching cleaning tasks data...")
                report_data['cleaning_tasks'] = self.fetch_cleaning_tasks_data(target_robots, start_date, end_date)

            if 'charging-tasks' in content_categories:
                logger.info("Fetching charging data...")
                report_data['charging_tasks'] = self.fetch_charging_data(target_robots, start_date, end_date)

            if any(cat in content_categories for cat in ['robot-status', 'performance']):
                logger.info("Fetching events data...")
                report_data['events'] = self.fetch_events_data(target_robots, start_date, end_date)

            # Always fetch map coverage and operational hours for comprehensive metrics
            logger.info("Fetching map coverage data...")
            report_data['map_coverage'] = self.fetch_map_coverage_data(target_robots, start_date, end_date)

            logger.info("Fetching operational hours data...")
            report_data['operational_hours'] = self.fetch_operational_hours_data(target_robots, start_date, end_date)

            logger.info(f"Data fetching completed. Categories: {list(report_data.keys())}")
            return report_data

        except Exception as e:
            logger.error(f"Error fetching all report data: {e}")
            return {}

    def calculate_comprehensive_metrics(self, report_data: Dict[str, pd.DataFrame],
                                      start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics using the calculator

        Args:
            report_data: Raw data from database queries
            start_date: Start date for calculations
            end_date: End date for calculations

        Returns:
            Dict with all calculated metrics for the template
        """
        logger.info("Calculating comprehensive metrics for report template")

        try:
            # Extract DataFrames
            robot_data = report_data.get('robot_status', pd.DataFrame())
            tasks_data = report_data.get('cleaning_tasks', pd.DataFrame())
            charging_data = report_data.get('charging_tasks', pd.DataFrame())
            events_data = report_data.get('events', pd.DataFrame())
            map_coverage_data = report_data.get('map_coverage', pd.DataFrame())

            # Calculate all metrics using the calculator
            metrics = {}

            # Fleet performance metrics
            metrics['fleet_performance'] = self.metrics_calculator.calculate_fleet_availability(
                robot_data, tasks_data, charging_data, start_date, end_date
            )

            # Task performance metrics
            metrics['task_performance'] = self.metrics_calculator.calculate_task_performance_metrics(tasks_data)

            # Charging performance metrics
            metrics['charging_performance'] = self.metrics_calculator.calculate_charging_performance_metrics(charging_data)

            # Resource utilization metrics
            metrics['resource_utilization'] = self.metrics_calculator.calculate_resource_utilization_metrics(
                tasks_data, charging_data
            )

            # Event analysis metrics
            metrics['event_analysis'] = self.metrics_calculator.calculate_event_analysis_metrics(events_data)

            # Facility performance metrics
            metrics['facility_performance'] = self.metrics_calculator.calculate_facility_performance_metrics(
                tasks_data, robot_data
            )

            # Trend data for charts
            metrics['trend_data'] = self.metrics_calculator.calculate_trend_data(
                tasks_data, charging_data, start_date, end_date
            )

            # Cost analysis metrics (with placeholders)
            metrics['cost_analysis'] = self.metrics_calculator.calculate_cost_analysis_metrics(
                tasks_data, metrics['resource_utilization']
            )

            # Add map coverage if available
            if not map_coverage_data.empty:
                metrics['map_coverage'] = map_coverage_data.to_dict('records')
            else:
                metrics['map_coverage'] = []

            logger.info("Comprehensive metrics calculation completed")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating comprehensive metrics: {e}")
            return {}

    def get_robot_count_summary(self, target_robots: List[str]) -> Dict[str, Any]:
        """
        Get summary of robot counts by database

        Args:
            target_robots: List of robot serial numbers

        Returns:
            Dict with robot count summary
        """
        try:
            # Use resolver to group robots by database
            db_to_robots = self.config.resolver.group_robots_by_database(target_robots)

            summary = {
                'total_robots': len(target_robots),
                'databases_involved': len(db_to_robots),
                'robots_by_database': {}
            }

            for database, robots in db_to_robots.items():
                summary['robots_by_database'][database] = {
                    'robot_count': len(robots),
                    'robot_sns': robots
                }

            return summary

        except Exception as e:
            logger.error(f"Error getting robot count summary: {e}")
            return {'total_robots': len(target_robots), 'databases_involved': 0}

    def _sum_durations(self, duration_series) -> float:
        """
        Helper method to sum duration values that may be in various formats

        Args:
            duration_series: Pandas series with duration values

        Returns:
            Total duration in hours
        """
        total_hours = 0

        for duration in duration_series:
            if pd.notna(duration):
                try:
                    if isinstance(duration, str):
                        # Parse duration like "120min" or "2h 30min"
                        hours = 0
                        minutes = 0
                        if 'h' in duration:
                            hours = int(duration.split('h')[0])
                        if 'min' in duration:
                            min_part = duration.split('min')[0]
                            if 'h' in min_part:
                                minutes = int(min_part.split('h')[1].strip())
                            else:
                                minutes = int(min_part)
                        total_hours += hours + minutes/60
                    else:
                        total_hours += float(duration)
                except:
                    continue

        return total_hours