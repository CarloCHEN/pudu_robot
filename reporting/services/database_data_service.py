# src/pudu/reporting/services/database_data_service.py
import logging
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime

# Reuse existing RDS infrastructure
from pudu.rds.rdsTable import RDSTable
from pudu.configs.database_config_loader import DynamicDatabaseConfig

logger = logging.getLogger(__name__)

class DatabaseDataService:
    """Service for querying historical data from databases for report generation"""

    def __init__(self, config: DynamicDatabaseConfig):
        """Initialize with database configuration"""
        self.config = config
        self.connection_config = "credentials.yaml"

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

            logger.info(f"Data fetching completed. Categories: {list(report_data.keys())}")
            return report_data

        except Exception as e:
            logger.error(f"Error fetching all report data: {e}")
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