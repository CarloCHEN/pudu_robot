import logging
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

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

    def fetch_location_data(self, target_robots: List[str]) -> pd.DataFrame:
        """
        Fetch location/building information for robots to enable facility-specific analysis

        Args:
            target_robots: List of robot serial numbers

        Returns:
            DataFrame with robot location mappings
        """
        logger.info(f"Fetching location data for {len(target_robots)} robots")

        try:
            # Get robot status data which contains location_id
            robot_status = self.fetch_robot_status_data(target_robots)

            if robot_status.empty or 'location_id' not in robot_status.columns:
                logger.warning("No location data available in robot status")
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
                        reuse_connection=True
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
                        logger.info(f"Retrieved {len(result_df)} location records from {config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error fetching location data from {config['database']}: {e}")
                    continue

            # Combine location data
            if all_locations:
                locations_df = pd.concat(all_locations, ignore_index=True).drop_duplicates()

                # Merge with robot status to get robot-location mapping
                robot_locations = robot_status.merge(
                    locations_df,
                    left_on='location_id',
                    right_on='building_id',
                    how='left'
                )

                logger.info(f"Successfully mapped {len(robot_locations)} robots to locations")
                return robot_locations
            else:
                logger.warning("No location data found")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching location data: {e}")
            return pd.DataFrame()

    def calculate_individual_robot_metrics(self, tasks_data: pd.DataFrame,
                                         charging_data: pd.DataFrame,
                                         robot_status: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Calculate metrics for individual robots

        Args:
            tasks_data: Task performance data
            charging_data: Charging session data
            robot_status: Robot status data

        Returns:
            List of robot performance dictionaries
        """
        logger.info("Calculating individual robot metrics")

        try:
            robot_metrics = []

            # Get unique robots from status data
            if robot_status.empty:
                logger.warning("No robot status data available")
                return []

            for _, robot in robot_status.iterrows():
                robot_sn = robot.get('robot_sn')
                if not robot_sn:
                    continue

                # Filter data for this robot
                robot_tasks = tasks_data[tasks_data['robot_sn'] == robot_sn] if not tasks_data.empty else pd.DataFrame()
                robot_charging = charging_data[charging_data['robot_sn'] == robot_sn] if not charging_data.empty else pd.DataFrame()

                # Calculate metrics
                total_tasks = len(robot_tasks)
                completed_tasks = len(robot_tasks[robot_tasks['status'] == 'Task Ended']) if not robot_tasks.empty and 'status' in robot_tasks.columns else 0

                # Calculate operational hours
                operational_hours = 0
                if not robot_tasks.empty and 'duration' in robot_tasks.columns:
                    operational_hours = self._sum_durations(robot_tasks['duration'])

                # Determine status
                status = robot.get('status', 'Unknown')
                status_class = self._get_status_class(status, completed_tasks, total_tasks)

                # Get location info
                location_name = robot.get('building_name', robot.get('location_id', 'Unknown Location'))

                robot_metrics.append({
                    'robot_id': robot_sn,
                    'robot_name': robot.get('robot_name', f'Robot {robot_sn}'),
                    'location': location_name,
                    'tasks_completed': completed_tasks,
                    'total_tasks': total_tasks,
                    'operational_hours': round(operational_hours, 1),
                    'status': status,
                    'status_class': status_class,
                    'charging_sessions': len(robot_charging)
                })

            logger.info(f"Calculated metrics for {len(robot_metrics)} robots")
            return robot_metrics

        except Exception as e:
            logger.error(f"Error calculating individual robot metrics: {e}")
            return []

    def calculate_facility_specific_metrics(self, tasks_data: pd.DataFrame,
                                          robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Calculate facility-specific performance metrics

        Args:
            tasks_data: Task performance data
            robot_locations: Robot location mapping data

        Returns:
            Dict with facility metrics
        """
        logger.info("Calculating facility-specific metrics")

        try:
            if robot_locations.empty or tasks_data.empty:
                logger.warning("No data available for facility metrics")
                return {}

            # Group robots by facility
            facility_metrics = {}

            for building_name in robot_locations['building_name'].dropna().unique():
                facility_robots = robot_locations[robot_locations['building_name'] == building_name]['robot_sn'].tolist()
                facility_tasks = tasks_data[tasks_data['robot_sn'].isin(facility_robots)]

                if facility_tasks.empty:
                    continue

                # Calculate metrics
                total_tasks = len(facility_tasks)
                completed_tasks = len(facility_tasks[facility_tasks['status'] == 'Task Ended']) if 'status' in facility_tasks.columns else 0

                # Area calculations
                total_area = facility_tasks['actual_area'].sum() if 'actual_area' in facility_tasks.columns else 0
                planned_area = facility_tasks['plan_area'].sum() if 'plan_area' in facility_tasks.columns else 0

                # Coverage efficiency
                coverage_efficiency = (total_area / planned_area * 100) if planned_area > 0 else 0

                # Task completion rate
                completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                # Operating hours
                operating_hours = 0
                if 'duration' in facility_tasks.columns:
                    operating_hours = self._sum_durations(facility_tasks['duration'])

                # Power efficiency
                total_energy = facility_tasks['battery_usage'].sum() if 'battery_usage' in facility_tasks.columns else 1
                power_efficiency = total_area / total_energy if total_energy > 0 else 0

                facility_metrics[building_name] = {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'completion_rate': round(completion_rate, 1),
                    'area_cleaned': round(total_area, 0),
                    'planned_area': round(planned_area, 0),
                    'coverage_efficiency': round(coverage_efficiency, 1),
                    'operating_hours': round(operating_hours, 1),
                    'power_efficiency': round(power_efficiency, 0),
                    'robot_count': len(facility_robots)
                }

            logger.info(f"Calculated metrics for {len(facility_metrics)} facilities")
            return facility_metrics

        except Exception as e:
            logger.error(f"Error calculating facility metrics: {e}")
            return {}

    def calculate_map_coverage_metrics(self, tasks_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Calculate detailed map coverage metrics

        Args:
            tasks_data: Task performance data with map information

        Returns:
            List of map coverage dictionaries
        """
        logger.info("Calculating map coverage metrics")

        try:
            if tasks_data.empty or 'map_name' not in tasks_data.columns:
                logger.warning("No map data available")
                return []

            map_metrics = []

            for map_name in tasks_data['map_name'].dropna().unique():
                map_tasks = tasks_data[tasks_data['map_name'] == map_name]

                # Calculate coverage metrics
                total_actual_area = map_tasks['actual_area'].sum() if 'actual_area' in map_tasks.columns else 0
                total_planned_area = map_tasks['plan_area'].sum() if 'plan_area' in map_tasks.columns else 0

                coverage_percentage = (total_actual_area / total_planned_area * 100) if total_planned_area > 0 else 0

                # Task completion for this map
                completed_tasks = len(map_tasks[map_tasks['status'] == 'Task Ended']) if 'status' in map_tasks.columns else 0
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

            # Sort by coverage percentage descending
            map_metrics.sort(key=lambda x: x['coverage_percentage'], reverse=True)

            logger.info(f"Calculated coverage for {len(map_metrics)} maps")
            return map_metrics

        except Exception as e:
            logger.error(f"Error calculating map coverage: {e}")
            return []

    def calculate_weekly_trends(self, tasks_data: pd.DataFrame,
                               charging_data: pd.DataFrame,
                               start_date: str, end_date: str) -> Dict[str, List]:
        """
        Calculate weekly trend data from actual database records

        Args:
            tasks_data: Task performance data
            charging_data: Charging session data
            start_date: Report start date
            end_date: Report end date

        Returns:
            Dict with weekly trend arrays
        """
        logger.info("Calculating weekly trends from actual data")

        try:
            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create 4 week periods
            total_days = (end_dt - start_dt).days
            days_per_week = max(1, total_days // 4)

            weeks = []
            task_completion_trend = []
            charging_sessions_trend = []
            charging_duration_trend = []
            energy_consumption_trend = []
            water_usage_trend = []

            for week in range(4):
                week_start = start_dt + timedelta(days=week * days_per_week)
                week_end = start_dt + timedelta(days=(week + 1) * days_per_week)

                weeks.append(f"Week {week + 1}")

                # Filter data for this week
                if not tasks_data.empty and 'start_time' in tasks_data.columns:
                    week_tasks = tasks_data[
                        (pd.to_datetime(tasks_data['start_time']) >= week_start) &
                        (pd.to_datetime(tasks_data['start_time']) < week_end)
                    ]

                    # Task completion rate
                    completed = len(week_tasks[week_tasks['status'] == 'Task Ended']) if 'status' in week_tasks.columns else 0
                    total = len(week_tasks)
                    completion_rate = (completed / total * 100) if total > 0 else 0
                    task_completion_trend.append(round(completion_rate, 1))

                    # Energy consumption
                    energy = week_tasks['battery_usage'].sum() if 'battery_usage' in week_tasks.columns else 0
                    energy_consumption_trend.append(round(energy, 1))

                    # Water usage
                    water = week_tasks['water_consumption'].sum() if 'water_consumption' in week_tasks.columns else 0
                    water_usage_trend.append(round(water, 0))

                else:
                    task_completion_trend.append(0)
                    energy_consumption_trend.append(0)
                    water_usage_trend.append(0)

                # Charging data for this week
                if not charging_data.empty and 'start_time' in charging_data.columns:
                    week_charging = charging_data[
                        (pd.to_datetime(charging_data['start_time']) >= week_start) &
                        (pd.to_datetime(charging_data['start_time']) < week_end)
                    ]

                    charging_sessions_trend.append(len(week_charging))

                    # Average duration
                    if not week_charging.empty and 'duration' in week_charging.columns:
                        durations = self._parse_duration_series(week_charging['duration'])
                        avg_duration = np.mean(durations) if durations else 0
                        charging_duration_trend.append(round(avg_duration, 1))
                    else:
                        charging_duration_trend.append(0)
                else:
                    charging_sessions_trend.append(0)
                    charging_duration_trend.append(0)

            return {
                'weeks': weeks,
                'task_completion_trend': task_completion_trend,
                'charging_sessions_trend': charging_sessions_trend,
                'charging_duration_trend': charging_duration_trend,
                'energy_consumption_trend': energy_consumption_trend,
                'water_usage_trend': water_usage_trend,
                'cost_savings_trend': [0, 0, 0, 0],  # Placeholder - will calculate later
                'roi_improvement_trend': [0, 0, 0, 0]  # Placeholder - will calculate later
            }

        except Exception as e:
            logger.error(f"Error calculating weekly trends: {e}")
            # Return default structure
            return {
                'weeks': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                'task_completion_trend': [0, 0, 0, 0],
                'charging_sessions_trend': [0, 0, 0, 0],
                'charging_duration_trend': [0, 0, 0, 0],
                'energy_consumption_trend': [0, 0, 0, 0],
                'water_usage_trend': [0, 0, 0, 0],
                'cost_savings_trend': [0, 0, 0, 0],
                'roi_improvement_trend': [0, 0, 0, 0]
            }

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
            # Always fetch robot status for basic info
            logger.info("Fetching robot status data...")
            report_data['robot_status'] = self.fetch_robot_status_data(target_robots)

            # Always fetch location data for facility analysis
            logger.info("Fetching location data...")
            report_data['robot_locations'] = self.fetch_location_data(target_robots)

            if 'cleaning-tasks' in content_categories or 'performance' in content_categories:
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

    def calculate_comprehensive_metrics(self, report_data: Dict[str, pd.DataFrame],
                                       start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics using the calculator and enhanced data

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
            robot_locations = report_data.get('robot_locations', pd.DataFrame())

            # Calculate all metrics using the calculator
            metrics = {}

            # Fleet performance metrics
            metrics['fleet_performance'] = self.metrics_calculator.calculate_fleet_availability(
                robot_data, tasks_data, start_date, end_date
            )

            # Task performance metrics
            metrics['task_performance'] = self.metrics_calculator.calculate_task_performance_metrics(tasks_data)

            # Charging performance metrics
            metrics['charging_performance'] = self.metrics_calculator.calculate_charging_performance_metrics(charging_data)

            # Resource utilization metrics
            metrics['resource_utilization'] = self.metrics_calculator.calculate_resource_utilization_metrics(tasks_data)

            # Event analysis metrics
            metrics['event_analysis'] = self.metrics_calculator.calculate_event_analysis_metrics(events_data)

            # Enhanced facility performance metrics using location data
            if not robot_locations.empty:
                facility_metrics = self.calculate_facility_specific_metrics(tasks_data, robot_locations)
                metrics['facility_performance'] = {'facilities': facility_metrics}
            else:
                # Fallback to basic facility calculation
                metrics['facility_performance'] = self.metrics_calculator.calculate_facility_performance_metrics(
                    tasks_data, robot_data
                )

            # Individual robot metrics for detailed tables
            metrics['individual_robots'] = self.calculate_individual_robot_metrics(
                tasks_data, charging_data, robot_locations if not robot_locations.empty else robot_data
            )

            # Map coverage metrics
            metrics['map_coverage'] = self.calculate_map_coverage_metrics(tasks_data)

            # Enhanced trend data from actual records
            metrics['trend_data'] = self.calculate_weekly_trends(
                tasks_data, charging_data, start_date, end_date
            )

            # Cost analysis metrics (with placeholders)
            metrics['cost_analysis'] = self.metrics_calculator.calculate_cost_analysis_metrics(
                tasks_data, metrics['resource_utilization']
            )
            # Override with N/A placeholders for cost data
            metrics['cost_analysis'].update({
                'monthly_operational_cost': 'N/A',
                'traditional_cleaning_cost': 'N/A',
                'monthly_cost_savings': 'N/A',
                'annual_projected_savings': 'N/A',
                'cost_efficiency_improvement': 'N/A',
                'cost_per_sqft': 'N/A',
                'roi_improvement': 'N/A',
                'note': 'Cost metrics require configuration - data not available'
            })

            logger.info("Comprehensive metrics calculation completed")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating comprehensive metrics: {e}")
            return {}

    def _get_status_class(self, status: str, completed_tasks: int, total_tasks: int) -> str:
        """Determine CSS status class based on robot status and performance"""
        if not status or status.lower() in ['unknown', 'offline']:
            return 'status-error'
        elif status.lower() in ['operational', 'online', 'active']:
            if total_tasks > 0 and completed_tasks / total_tasks >= 0.9:
                return 'status-excellent'
            else:
                return 'status-good'
        elif status.lower() in ['warning', 'maintenance']:
            return 'status-warning'
        else:
            return 'status-error'

    def _parse_duration_series(self, duration_series) -> List[float]:
        """Parse a series of duration values into minutes"""
        durations = []
        for duration in duration_series:
            if pd.notna(duration):
                try:
                    if isinstance(duration, str):
                        # Parse duration like "120min" or "2h 30min"
                        hours = 0
                        minutes = 0
                        if 'h' in duration:
                            parts = duration.split('h')
                            hours = int(parts[0])
                            if len(parts) > 1 and 'min' in parts[1]:
                                minutes = int(parts[1].replace('min', '').strip())
                        elif 'min' in duration:
                            minutes = int(duration.replace('min', '').strip())
                        durations.append(hours * 60 + minutes)
                    else:
                        durations.append(float(duration))
                except:
                    continue
        return durations

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