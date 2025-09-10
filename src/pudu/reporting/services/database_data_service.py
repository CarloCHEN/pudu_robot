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
                               efficiency, battery_usage, consumption, water_consumption, progress, status,
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
        """Calculate metrics for individual robots with correct duration parsing"""
        logger.info("Calculating individual robot metrics")

        try:
            robot_metrics = []

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
                completed_tasks = len(robot_tasks[robot_tasks['status'].str.contains('end|complet', case=False, na=False)]) if not robot_tasks.empty and 'status' in robot_tasks.columns else 0

                # Calculate operational hours from task durations (seconds)
                operational_hours = 0
                if not robot_tasks.empty and 'duration' in robot_tasks.columns:
                    for duration in robot_tasks['duration']:
                        if pd.notna(duration):
                            try:
                                seconds = float(str(duration).strip())
                                hours = seconds / 3600
                                if hours > 0:
                                    operational_hours += hours
                            except:
                                continue

                # All robots are online, so status is operational
                status = "Operational"
                status_class = "status-excellent"

                # Get location info
                location_name = robot.get('building_name', robot.get('location_id', 'Unknown Location'))

                robot_metrics.append({
                    'robot_id': robot_sn,
                    'robot_name': robot.get('robot_name', f'Robot {robot_sn}'),
                    'location': location_name,
                    'tasks_completed': completed_tasks,
                    'total_tasks': total_tasks,
                    'running_hours': round(operational_hours, 1),
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
        """Calculate facility-specific performance metrics with correct units"""
        logger.info("Calculating facility-specific metrics")

        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            facility_metrics = {}

            for building_name in robot_locations['building_name'].dropna().unique():
                facility_robots = robot_locations[robot_locations['building_name'] == building_name]['robot_sn'].tolist()
                facility_tasks = tasks_data[tasks_data['robot_sn'].isin(facility_robots)]

                if facility_tasks.empty:
                    continue

                # Calculate metrics
                total_tasks = len(facility_tasks)
                completed_tasks = len(facility_tasks[facility_tasks['status'].str.contains('end|complet', case=False, na=False)]) if 'status' in facility_tasks.columns else 0

                # Area calculations - convert from square meters to square feet (1 m² = 10.764 sq ft)
                total_area_sqm = facility_tasks['actual_area'].fillna(0).sum() if 'actual_area' in facility_tasks.columns else 0
                planned_area_sqm = facility_tasks['plan_area'].fillna(0).sum() if 'plan_area' in facility_tasks.columns else 0

                total_area_sqft = total_area_sqm * 10.764  # Convert to sq ft
                planned_area_sqft = planned_area_sqm * 10.764  # Convert to sq ft

                # Coverage efficiency
                coverage_efficiency = (total_area_sqm / planned_area_sqm * 100) if planned_area_sqm > 0 else 0
                completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                # Operating hours from task durations (seconds)
                operating_hours = 0
                if 'duration' in facility_tasks.columns:
                    for duration in facility_tasks['duration']:
                        if pd.notna(duration):
                            try:
                                seconds = float(str(duration).strip())
                                hours = seconds / 3600
                                if hours > 0:
                                    operating_hours += hours
                            except:
                                continue

                # Energy consumption from 'consumption' column (kWh)
                total_energy = facility_tasks['consumption'].fillna(0).sum() if 'consumption' in facility_tasks.columns else 0

                # Power efficiency (square feet per kWh)
                power_efficiency = total_area_sqft / total_energy if total_energy > 0 else 0

                facility_metrics[building_name] = {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'completion_rate': round(completion_rate, 1),
                    'area_cleaned': round(total_area_sqft, 0),  # in square feet
                    'planned_area': round(planned_area_sqft, 0),  # in square feet
                    'coverage_efficiency': round(coverage_efficiency, 1),
                    'running_hours': round(operating_hours, 1),
                    'power_efficiency': round(power_efficiency, 0),  # sq ft per kWh
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
                    energy = week_tasks['consumption'].sum() if 'consumption' in week_tasks.columns else 0
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

            # Calculate event location mapping correctly
            if not events_data.empty and not robot_locations.empty:
                event_location_mapping = self.calculate_event_location_mapping(events_data, robot_locations)
                metrics['event_location_mapping'] = event_location_mapping

                # Calculate event type by location breakdown
                event_type_by_location = self.calculate_event_type_by_location(events_data, robot_locations)
                metrics['event_type_by_location'] = event_type_by_location
                logger.info(f"Added event_type_by_location with keys: {list(event_type_by_location.keys())}")
            else:
                metrics['event_location_mapping'] = {}
                metrics['event_type_by_location'] = {}
                logger.warning("No events or location data for event breakdown")

            # Enhanced facility performance metrics using location data
            if not robot_locations.empty:
                facility_metrics = self.calculate_facility_specific_metrics(tasks_data, robot_locations)
                metrics['facility_performance'] = {'facilities': facility_metrics}

                # FIX: Calculate facility efficiency metrics
                facility_efficiency = self.calculate_facility_efficiency_metrics(tasks_data, robot_locations)
                metrics['facility_efficiency_metrics'] = facility_efficiency
                logger.info(f"Added facility efficiency metrics: {list(facility_efficiency.keys())}")
            else:
                # Fallback to basic facility calculation
                metrics['facility_performance'] = self.metrics_calculator.calculate_facility_performance_metrics(
                    tasks_data, robot_data
                )
                metrics['facility_efficiency_metrics'] = {}

            # Individual robot metrics for detailed tables
            metrics['individual_robots'] = self.metrics_calculator.calculate_individual_robot_performance(
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

            logger.info("Comprehensive metrics calculation completed with facility efficiency")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating comprehensive metrics: {e}")
            return {}

    def calculate_daily_trends(self, tasks_data: pd.DataFrame, charging_data: pd.DataFrame,
                              start_date: str, end_date: str) -> Dict[str, List]:
        """Calculate daily trend data from actual database records"""
        try:
            if tasks_data.empty and charging_data.empty:
                return {}

            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Generate date range
            date_range = []
            current_date = start_dt
            while current_date <= end_dt and len(date_range) < 30:  # Limit to 30 days for chart readability
                date_range.append(current_date)
                current_date += timedelta(days=1)

            # Initialize daily data
            daily_data = {date.strftime('%m/%d'): {
                'charging_sessions': 0,
                'charging_duration_total': 0,
                'charging_count': 0,
                'energy_consumption': 0,
                'water_usage': 0
            } for date in date_range}

            # Process tasks data
            if not tasks_data.empty and 'start_time' in tasks_data.columns:
                for _, task in tasks_data.iterrows():
                    try:
                        task_date = pd.to_datetime(task['start_time']).date()
                        date_str = task_date.strftime('%m/%d')

                        if date_str in daily_data:
                            energy = float(task.get('consumption', 0) or 0)
                            water = float(task.get('water_consumption', 0) or 0)
                            daily_data[date_str]['energy_consumption'] += energy
                            daily_data[date_str]['water_usage'] += water
                    except:
                        continue

            # Process charging data
            if not charging_data.empty and 'start_time' in charging_data.columns:
                for _, charge in charging_data.iterrows():
                    try:
                        charge_date = pd.to_datetime(charge['start_time']).date()
                        date_str = charge_date.strftime('%m/%d')

                        if date_str in daily_data:
                            daily_data[date_str]['charging_sessions'] += 1

                            # Parse duration
                            duration_str = str(charge.get('duration', ''))
                            duration_minutes = self._parse_duration_to_minutes(duration_str)
                            if duration_minutes > 0:
                                daily_data[date_str]['charging_duration_total'] += duration_minutes
                                daily_data[date_str]['charging_count'] += 1
                    except:
                        continue

            # Convert to chart format
            dates = list(daily_data.keys())
            charging_sessions = [daily_data[date]['charging_sessions'] for date in dates]

            charging_durations = []
            for date in dates:
                total_duration = daily_data[date]['charging_duration_total']
                count = daily_data[date]['charging_count']
                avg_duration = total_duration / count if count > 0 else 0
                charging_durations.append(round(avg_duration, 1))

            energy_consumption = [round(daily_data[date]['energy_consumption'], 1) for date in dates]
            water_usage = [round(daily_data[date]['water_usage'], 0) for date in dates]

            return {
                'dates': dates,
                'charging_sessions_trend': charging_sessions,
                'charging_duration_trend': charging_durations,
                'energy_consumption_trend': energy_consumption,
                'water_usage_trend': water_usage
            }

        except Exception as e:
            logger.error(f"Error calculating daily trends: {e}")
            return {}

    def _parse_duration_to_minutes(self, duration_str) -> float:
        """Parse duration string to minutes"""
        try:
            if pd.isna(duration_str) or not str(duration_str).strip():
                return 0.0

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
                # Try to parse as pure seconds and convert to minutes
                seconds = float(duration_str)
                minutes = seconds / 60

            return hours * 60 + minutes
        except:
            return 0.0

    def calculate_facility_efficiency_metrics(self, tasks_data: pd.DataFrame,
                                            robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Calculate water efficiency and time efficiency for facilities"""
        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            facility_metrics = {}

            for building_name in robot_locations['building_name'].dropna().unique():
                facility_robots = robot_locations[robot_locations['building_name'] == building_name]['robot_sn'].tolist()
                facility_tasks = tasks_data[tasks_data['robot_sn'].isin(facility_robots)]

                if facility_tasks.empty:
                    continue

                # Area calculations - convert from square meters to square feet
                total_area_sqm = facility_tasks['actual_area'].fillna(0).sum() if 'actual_area' in facility_tasks.columns else 0
                total_area_sqft = total_area_sqm * 10.764

                # Water efficiency (area per unit water)
                water_consumption = facility_tasks['water_consumption'].fillna(0).sum() if 'water_consumption' in facility_tasks.columns else 0
                water_efficiency = total_area_sqft / water_consumption if water_consumption > 0 else 0

                # Time efficiency (area per unit hour) - use duration directly in seconds
                total_time_hours = 0
                if 'duration' in facility_tasks.columns:
                    for duration in facility_tasks['duration']:
                        if pd.notna(duration):
                            try:
                                seconds = float(str(duration).strip())
                                hours = seconds / 3600
                                if hours > 0:
                                    total_time_hours += hours
                            except:
                                continue

                time_efficiency = total_area_sqft / total_time_hours if total_time_hours > 0 else 0

                facility_metrics[building_name] = {
                    'water_efficiency': round(water_efficiency, 1),  # sq ft per fl oz
                    'time_efficiency': round(time_efficiency, 1),   # sq ft per hour
                    'total_area_cleaned': round(total_area_sqft, 0),
                    'total_time_hours': round(total_time_hours, 1)
                }

            return facility_metrics

        except Exception as e:
            logger.error(f"Error calculating facility efficiency metrics: {e}")
            return {}

    def calculate_event_type_by_location(self, events_data: pd.DataFrame,
                                       robot_locations: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Calculate event types breakdown by actual building locations
        """
        try:
            logger.info(f"Calculating event type by location - events: {len(events_data)}, locations: {len(robot_locations)}")

            if events_data.empty:
                logger.warning("Events data is empty")
                return {}

            if robot_locations.empty:
                logger.warning("Robot locations data is empty")
                return {}

            # Create robot to building mapping
            robot_building_map = {}
            for _, row in robot_locations.iterrows():
                robot_sn = row.get('robot_sn')
                building_name = row.get('building_name')
                if robot_sn and building_name:
                    robot_building_map[robot_sn] = building_name

            logger.info(f"Robot building mapping created: {robot_building_map}")

            # Count events by type and location
            event_type_location_breakdown = {}
            processed_events = 0

            for _, event in events_data.iterrows():
                robot_sn = event.get('robot_sn')
                event_type = event.get('event_type')

                if not event_type or pd.isna(event_type):
                    continue

                building_name = robot_building_map.get(robot_sn, 'Unknown Building')

                # Initialize if needed
                if event_type not in event_type_location_breakdown:
                    event_type_location_breakdown[event_type] = {}

                if building_name not in event_type_location_breakdown[event_type]:
                    event_type_location_breakdown[event_type][building_name] = 0

                event_type_location_breakdown[event_type][building_name] += 1
                processed_events += 1

            logger.info(f"Processed {processed_events} events")
            logger.info(f"Event type location breakdown: {event_type_location_breakdown}")
            return event_type_location_breakdown

        except Exception as e:
            logger.error(f"Error calculating event type by location: {e}")
            return {}

    def calculate_enhanced_period_comparisons(self, current_metrics: Dict[str, Any],
                                            previous_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate enhanced period comparisons including facility efficiency metrics
        """
        try:
            logger.info("Calculating enhanced period comparisons with facility efficiency")

            # Use the existing metrics_calculator for basic comparisons
            basic_comparisons = self.metrics_calculator.calculate_period_comparison_metrics(
                current_metrics, previous_metrics
            )

            # Helper function to calculate change
            def calculate_change(current, previous, format_type="number", suffix=""):
                if current == 'N/A' or previous == 'N/A' or previous == 0:
                    return "N/A"

                try:
                    current_val = float(current)
                    previous_val = float(previous)

                    if previous_val == 0:
                        return "N/A"

                    if format_type == "percent":
                        change = current_val - previous_val
                        return f"{'+' if change >= 0 else ''}{change:.1f}%"
                    else:
                        change = current_val - previous_val
                        return f"{'+' if change >= 0 else ''}{change:.1f}{suffix}"
                except (ValueError, TypeError):
                    return "N/A"

            # FIX: Add facility efficiency comparisons
            current_facility_eff = current_metrics.get('facility_efficiency_metrics', {})
            previous_facility_eff = previous_metrics.get('facility_efficiency_metrics', {})

            logger.info(f"Current facility efficiency: {current_facility_eff}")
            logger.info(f"Previous facility efficiency: {previous_facility_eff}")

            facility_efficiency_comparisons = {}
            for facility_name in current_facility_eff.keys():
                if facility_name in previous_facility_eff:
                    current_eff = current_facility_eff[facility_name]
                    previous_eff = previous_facility_eff[facility_name]

                    facility_efficiency_comparisons[facility_name] = {
                        'water_efficiency': calculate_change(
                            current_eff.get('water_efficiency', 0),
                            previous_eff.get('water_efficiency', 0),
                            "number", ""
                        ),
                        'time_efficiency': calculate_change(
                            current_eff.get('time_efficiency', 0),
                            previous_eff.get('time_efficiency', 0),
                            "number", ""
                        )
                    }

                    logger.info(f"Efficiency comparison for {facility_name}: {facility_efficiency_comparisons[facility_name]}")
                else:
                    facility_efficiency_comparisons[facility_name] = {
                        'water_efficiency': 'N/A',
                        'time_efficiency': 'N/A'
                    }
                    logger.info(f"No previous data for {facility_name} efficiency")

            # Add efficiency comparisons to basic comparisons
            enhanced_comparisons = basic_comparisons.copy()
            enhanced_comparisons['facility_efficiency_comparisons'] = facility_efficiency_comparisons

            logger.info(f"Enhanced comparisons keys: {list(enhanced_comparisons.keys())}")
            logger.info(f"Facility efficiency comparisons: {facility_efficiency_comparisons}")

            return enhanced_comparisons

        except Exception as e:
            logger.error(f"Error calculating enhanced period comparisons: {e}")
            # Return basic comparisons without efficiency if there's an error
            return self.metrics_calculator.calculate_period_comparison_metrics(current_metrics, previous_metrics)

    def calculate_comprehensive_metrics_with_comparison(self, current_data: Dict[str, pd.DataFrame],
                                                       previous_data: Dict[str, pd.DataFrame],
                                                       current_start: str, current_end: str,
                                                       previous_start: str, previous_end: str) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics with period comparison INCLUDING facility efficiency comparisons
        """
        logger.info("Calculating comprehensive metrics with period comparison")

        try:
            # Calculate current period metrics
            current_metrics = self.calculate_comprehensive_metrics(current_data, current_start, current_end)

            # Calculate previous period metrics
            previous_metrics = self.calculate_comprehensive_metrics(previous_data, previous_start, previous_end)

            # Get data for additional calculations
            tasks_data = current_data.get('cleaning_tasks', pd.DataFrame())
            events_data = current_data.get('events', pd.DataFrame())
            robot_locations = current_data.get('robot_locations', pd.DataFrame())
            charging_data = current_data.get('charging_tasks', pd.DataFrame())

            # Add weekend schedule completion and average duration
            weekend_completion = self.metrics_calculator.calculate_weekend_schedule_completion(tasks_data)
            current_metrics['task_performance']['weekend_schedule_completion'] = weekend_completion

            avg_duration = self.metrics_calculator.calculate_average_task_duration(tasks_data)
            current_metrics['task_performance']['avg_task_duration_minutes'] = avg_duration

            # Calculate weekday completion rates
            weekday_completion = self.metrics_calculator.calculate_weekday_completion_rates(tasks_data)
            current_metrics['weekday_completion'] = weekday_completion

            # Calculate facility-specific detailed metrics
            if not robot_locations.empty:
                # Calculate facility-specific detailed metrics
                facility_task_metrics = self.calculate_facility_specific_task_metrics(tasks_data, robot_locations)
                current_metrics['facility_task_metrics'] = facility_task_metrics

                facility_charging_metrics = self.calculate_facility_specific_charging_metrics(charging_data, robot_locations)
                current_metrics['facility_charging_metrics'] = facility_charging_metrics

                facility_resource_metrics = self.calculate_facility_specific_resource_metrics(tasks_data, robot_locations)
                current_metrics['facility_resource_metrics'] = facility_resource_metrics

                # Calculate facility efficiency metrics
                facility_efficiency = self.calculate_facility_efficiency_metrics(tasks_data, robot_locations)
                current_metrics['facility_efficiency_metrics'] = facility_efficiency

                # Calculate map performance by building
                map_performance = self.metrics_calculator.calculate_map_performance_by_building(tasks_data, robot_locations)
                current_metrics['map_performance_by_building'] = map_performance

                # Add event type by location breakdown
                if not events_data.empty:
                    event_type_by_location = self.calculate_event_type_by_location(events_data, robot_locations)
                    current_metrics['event_type_by_location'] = event_type_by_location
                    logger.info(f"Added event_type_by_location with {len(event_type_by_location)} event types")
                else:
                    current_metrics['event_type_by_location'] = {}
                    logger.warning("No events data for event type breakdown")

            # Update trend data to use daily instead of weekly
            daily_trend_data = self.calculate_daily_trends(tasks_data, charging_data, current_start, current_end)
            if daily_trend_data and daily_trend_data.get('dates'):
                current_metrics['trend_data'] = daily_trend_data

            # FIX: Calculate period comparisons INCLUDING facility efficiency
            period_comparisons = self.calculate_enhanced_period_comparisons(current_metrics, previous_metrics)
            current_metrics['period_comparisons'] = period_comparisons

            # Add comparison metadata
            current_metrics['comparison_metadata'] = {
                'current_period': {'start': current_start, 'end': current_end},
                'previous_period': {'start': previous_start, 'end': previous_end},
                'comparison_available': True
            }
            # Calculate daily financial trends for chart
            daily_financial_trends = self.calculate_daily_financial_trends(tasks_data, current_start, current_end)
            if daily_financial_trends and daily_financial_trends.get('dates'):
                current_metrics['financial_trend_data'] = daily_financial_trends


            logger.info("Successfully calculated metrics with period comparison and facility efficiency comparisons")
            return current_metrics

        except Exception as e:
            logger.error(f"Error calculating metrics with comparison: {e}")
            # Fallback to current metrics only
            current_metrics = self.calculate_comprehensive_metrics(current_data, current_start, current_end)
            # Add required fields even without comparison
            tasks_data = current_data.get('cleaning_tasks', pd.DataFrame())
            weekend_completion = self.metrics_calculator.calculate_weekend_schedule_completion(tasks_data)
            avg_duration = self.metrics_calculator.calculate_average_task_duration(tasks_data)

            current_metrics['task_performance']['weekend_schedule_completion'] = weekend_completion
            current_metrics['task_performance']['avg_task_duration_minutes'] = avg_duration
            current_metrics['period_comparisons'] = {}
            current_metrics['comparison_metadata'] = {'comparison_available': False}
            current_metrics['facility_task_metrics'] = {}
            current_metrics['facility_charging_metrics'] = {}
            current_metrics['facility_resource_metrics'] = {}
            current_metrics['facility_efficiency_metrics'] = {}
            current_metrics['map_performance_by_building'] = {}
            current_metrics['weekday_completion'] = {}
            current_metrics['trend_data'] = {}
            current_metrics['event_type_by_location'] = {}
            current_metrics['financial_trend_data'] = {}
            return current_metrics

    def calculate_facility_specific_task_metrics(self, tasks_data: pd.DataFrame,
                                               robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Calculate detailed task metrics per facility

        Args:
            tasks_data: Task performance data
            robot_locations: Robot location mapping data

        Returns:
            Dict with facility-specific task metrics including average duration
        """
        logger.info("Calculating facility-specific task metrics")

        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            facility_metrics = {}

            # Group by building/facility
            for building_name in robot_locations['building_name'].dropna().unique():
                facility_robots = robot_locations[robot_locations['building_name'] == building_name]['robot_sn'].tolist()
                facility_tasks = tasks_data[tasks_data['robot_sn'].isin(facility_robots)]

                if facility_tasks.empty:
                    continue

                # Calculate facility-specific average duration
                durations_minutes = []
                if 'duration' in facility_tasks.columns:
                    for duration in facility_tasks['duration']:
                        duration_minutes = self.metrics_calculator._parse_duration_to_minutes(duration)
                        if duration_minutes > 0:
                            durations_minutes.append(duration_minutes)

                avg_duration = np.mean(durations_minutes) if durations_minutes else 0

                # Calculate other metrics
                total_tasks = len(facility_tasks)
                completed_tasks = len(facility_tasks[facility_tasks['status'].str.contains('end|complet', case=False, na=False)]) if 'status' in facility_tasks.columns else 0
                completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                # Determine primary mode for this facility
                primary_mode = "Mixed tasks"
                if 'mode' in facility_tasks.columns:
                    mode_counts = facility_tasks['mode'].value_counts()
                    if not mode_counts.empty:
                        primary_mode = f"{mode_counts.index[0]} ({mode_counts.iloc[0]} tasks)"

                facility_metrics[building_name] = {
                    'total_tasks': total_tasks,
                    'completed_tasks': completed_tasks,
                    'completion_rate': completion_rate,
                    'avg_duration_minutes': round(avg_duration, 1),
                    'primary_mode': primary_mode,
                    'task_count_by_mode': facility_tasks['mode'].value_counts().to_dict() if 'mode' in facility_tasks.columns else {}
                }

            logger.info(f"Calculated task metrics for {len(facility_metrics)} facilities")
            return facility_metrics

        except Exception as e:
            logger.error(f"Error calculating facility-specific task metrics: {e}")
            return {}

    def calculate_daily_financial_trends(self, tasks_data: pd.DataFrame, start_date: str, end_date: str) -> Dict[str, List]:
        """
        Calculate daily financial trend data for charts

        Args:
            tasks_data: Task performance data
            start_date: Start date for data range
            end_date: End date for data range

        Returns:
            Dict with daily financial trend arrays
        """
        try:
            logger.info("Calculating daily financial trends")

            # Constants
            HOURLY_WAGE = 25.0
            HUMAN_CLEANING_SPEED = 1000.0  # sq ft per hour
            COST_PER_FL_OZ_WATER = 0.0
            COST_PER_KWH = 0.0

            start_dt = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d')
            end_dt = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d')

            # Create daily buckets
            daily_data = {}
            current_date = start_dt

            while current_date <= end_dt:
                date_str = current_date.strftime('%m/%d')
                daily_data[date_str] = {
                    'area_cleaned': 0,
                    'energy_consumption': 0,
                    'water_consumption': 0
                }
                current_date += timedelta(days=1)

            # Process tasks data by date
            if not tasks_data.empty and 'start_time' in tasks_data.columns:
                for _, task in tasks_data.iterrows():
                    try:
                        task_date = pd.to_datetime(task['start_time']).date()
                        if start_dt.date() <= task_date <= end_dt.date():
                            date_str = task_date.strftime('%m/%d')
                            if date_str in daily_data:
                                # Area cleaned (convert to sq ft)
                                area_sqm = float(task.get('actual_area', 0) or 0)
                                area_sqft = area_sqm * 10.764
                                daily_data[date_str]['area_cleaned'] += area_sqft

                                # Energy and water
                                energy = float(task.get('consumption', 0) or 0)
                                water = float(task.get('water_consumption', 0) or 0)
                                daily_data[date_str]['energy_consumption'] += energy
                                daily_data[date_str]['water_consumption'] += water
                    except:
                        continue

            # Calculate daily hours_saved and savings
            dates = list(daily_data.keys())
            hours_saved_trend = []
            savings_trend = []

            for date in dates:
                area_cleaned = daily_data[date]['area_cleaned']
                energy = daily_data[date]['energy_consumption']
                water = daily_data[date]['water_consumption']

                # Calculate daily hours saved
                hours_saved = area_cleaned / HUMAN_CLEANING_SPEED if HUMAN_CLEANING_SPEED > 0 else 0

                # Calculate daily costs
                robot_cost = (water * COST_PER_FL_OZ_WATER) + (energy * COST_PER_KWH)
                human_cost = hours_saved * HOURLY_WAGE
                savings = human_cost - robot_cost

                hours_saved_trend.append(round(hours_saved, 1))
                savings_trend.append(round(savings, 2))

            logger.info(f"Calculated daily financial trends for {len(dates)} days")
            return {
                'dates': dates,
                'hours_saved_trend': hours_saved_trend,
                'savings_trend': savings_trend
            }

        except Exception as e:
            logger.error(f"Error calculating daily financial trends: {e}")
            return {
                'dates': [],
                'hours_saved_trend': [],
                'savings_trend': []
            }

    def calculate_event_location_mapping(self, events_data: pd.DataFrame,
                                       robot_locations: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """Map events to actual building locations using robot_sn - FIX the level mapping"""
        try:
            if events_data.empty or robot_locations.empty:
                return {}

            # Create robot to building mapping
            robot_building_map = {}
            for _, row in robot_locations.iterrows():
                robot_sn = row.get('robot_sn')
                building_name = row.get('building_name')
                if robot_sn and building_name:
                    robot_building_map[robot_sn] = building_name

            # Count events by actual building
            building_events = {}
            for _, event in events_data.iterrows():
                robot_sn = event.get('robot_sn')
                event_level = str(event.get('event_level', 'info')).lower()

                building_name = robot_building_map.get(robot_sn, 'Unknown Building')

                if building_name not in building_events:
                    building_events[building_name] = {
                        'total_events': 0,
                        'critical_events': 0,  # FIX: This should map to fatal
                        'error_events': 0,
                        'warning_events': 0,
                        'info_events': 0
                    }

                building_events[building_name]['total_events'] += 1

                # FIX: Correct the level mapping
                if 'fatal' in event_level or 'critical' in event_level:
                    building_events[building_name]['critical_events'] += 1  # Map fatal->critical
                elif 'error' in event_level:
                    building_events[building_name]['error_events'] += 1
                elif 'warning' in event_level or 'warn' in event_level:
                    building_events[building_name]['warning_events'] += 1
                else:
                    building_events[building_name]['info_events'] += 1

            return building_events

        except Exception as e:
            logger.error(f"Error mapping events to locations: {e}")
            return {}

    def calculate_facility_specific_charging_metrics(self, charging_data: pd.DataFrame,
                                                robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Calculate REAL charging metrics per facility with proper duration parsing"""
        logger.info("Calculating facility-specific charging metrics")

        try:
            if robot_locations.empty or charging_data.empty:
                return {}

            facility_metrics = {}

            for building_name in robot_locations['building_name'].dropna().unique():
                facility_robots = robot_locations[robot_locations['building_name'] == building_name]['robot_sn'].tolist()
                facility_charging = charging_data[charging_data['robot_sn'].isin(facility_robots)]

                if facility_charging.empty:
                    facility_metrics[building_name] = {
                        'total_sessions': 0,
                        'avg_duration_minutes': 0.0,
                        'median_duration_minutes': 0.0,
                        'avg_power_gain_percent': 0.0,
                        'median_power_gain_percent': 0.0
                    }
                    continue

                total_sessions = len(facility_charging)

                # REAL duration parsing - fix the 0 duration issue
                durations = []
                for _, row in facility_charging.iterrows():
                    duration_str = str(row.get('duration', ''))
                    if pd.notna(duration_str) and duration_str.strip():
                        try:
                            # Parse your format: "0h 04min", "1h 59min", etc.
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

                            duration_minutes = hours * 60 + minutes
                            if duration_minutes > 0:
                                durations.append(duration_minutes)
                        except Exception as e:
                            logger.warning(f"Could not parse duration '{duration_str}': {e}")
                            continue

                # REAL power gain parsing
                power_gains = []
                for _, row in facility_charging.iterrows():
                    power_gain_str = str(row.get('power_gain', ''))
                    if pd.notna(power_gain_str) and power_gain_str.strip():
                        try:
                            # Parse your format: "+1%", "+59%", "+0%"
                            gain_value = float(power_gain_str.replace('+', '').replace('%', '').strip())
                            power_gains.append(gain_value)
                        except Exception as e:
                            logger.warning(f"Could not parse power gain '{power_gain_str}': {e}")
                            continue

                # Calculate real statistics
                avg_duration = np.mean(durations) if durations else 0
                median_duration = np.median(durations) if durations else 0
                avg_power_gain = np.mean(power_gains) if power_gains else 0
                median_power_gain = np.median(power_gains) if power_gains else 0

                facility_metrics[building_name] = {
                    'total_sessions': total_sessions,
                    'avg_duration_minutes': round(avg_duration, 1),
                    'median_duration_minutes': round(median_duration, 1),
                    'avg_power_gain_percent': round(avg_power_gain, 1),
                    'median_power_gain_percent': round(median_power_gain, 1)
                }

            logger.info(f"Calculated real charging metrics for {len(facility_metrics)} facilities")
            return facility_metrics

        except Exception as e:
            logger.error(f"Error calculating facility-specific charging metrics: {e}")
            return {}

    def calculate_facility_specific_resource_metrics(self, tasks_data: pd.DataFrame,
                                                    robot_locations: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Calculate REAL resource usage metrics per facility"""
        logger.info("Calculating facility-specific resource metrics")

        try:
            if robot_locations.empty or tasks_data.empty:
                return {}

            facility_metrics = {}

            for building_name in robot_locations['building_name'].dropna().unique():
                facility_robots = robot_locations[robot_locations['building_name'] == building_name]['robot_sn'].tolist()
                facility_tasks = tasks_data[tasks_data['robot_sn'].isin(facility_robots)]

                if facility_tasks.empty:
                    facility_metrics[building_name] = {
                        'energy_consumption_kwh': 0.0,
                        'water_consumption_floz': 0.0
                    }
                    continue

                # Use 'consumption' column (kWh) instead of 'battery_usage' (%)
                energy_consumption = facility_tasks['consumption'].fillna(0).sum() if 'consumption' in facility_tasks.columns else 0
                water_consumption = facility_tasks['water_consumption'].fillna(0).sum() if 'water_consumption' in facility_tasks.columns else 0

                facility_metrics[building_name] = {
                    'energy_consumption_kwh': round(energy_consumption, 1),
                    'water_consumption_floz': round(water_consumption, 0)
                }

            logger.info(f"Calculated resource metrics for {len(facility_metrics)} facilities")
            return facility_metrics

        except Exception as e:
            logger.error(f"Error calculating facility-specific resource metrics: {e}")
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