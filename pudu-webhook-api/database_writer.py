# pudu-webhook-api/database_writer.py
from datetime import datetime
import logging
import time
from typing import Any, Dict, List, Tuple

from configs.database_config import DatabaseConfig
from rds.rdsTable import RDSTable
from notifications.change_detector import detect_data_changes
from services.transform_service import TransformService

logger = logging.getLogger(__name__)

GS_robot_battery_capacity = {'S': 0.96, '40': 1.44}

class DatabaseWriter:
    """Enhanced database writer with change detection and coordinate transformation"""

    def __init__(self, config_path: str = "database_config.yaml"):
        self.config = DatabaseConfig(config_path)
        self.transform_service = TransformService(self.config)
        self.table_cache = {}  # Cache RDSTable instances

    def _get_table(self, database_name: str, table_name: str, fields: List[str], primary_keys: List[str]) -> RDSTable:
        """Get or create RDSTable instance"""
        table_key = f"{database_name}.{table_name}"

        if table_key not in self.table_cache:
            try:
                table = RDSTable(
                    connection_config="credentials.yaml",
                    database_name=database_name,
                    table_name=table_name,
                    fields=fields,
                    primary_keys=primary_keys
                )
                self.table_cache[table_key] = table
                logger.info(f"Created RDSTable instance for {database_name}.{table_name}")
            except Exception as e:
                logger.error(f"Failed to create table instance for {database_name}.{table_name}: {e}")
                raise

        return self.table_cache[table_key]

    def _get_robot_name(self, robot_sn: str) -> str:
        """Get robot name using table configs"""
        try:
            # Use the existing config system to get robot info table configs
            robot_info_configs = self.config.get_table_configs_for_robots('robot_info', [robot_sn])

            if not robot_info_configs:
                logger.warning(f"No robot_info table config found for {robot_sn}")
                return robot_sn

            # Use the first config (should be the main database)
            config = robot_info_configs[0]

            # Get table instance using existing method
            table = self._get_table(
                database_name=config['database'],
                table_name=config['table_name'],
                fields=config.get('fields', []),
                primary_keys=config['primary_keys']
            )

            query = f"SELECT robot_name FROM {config['table_name']} WHERE robot_sn = '{robot_sn}'"
            result = table.query_data(query)

            if result and len(result) > 0:
                first_row = result[0]

                # Handle different return types
                if isinstance(first_row, (tuple, list)):
                    robot_name = first_row[0] if len(first_row) > 0 else None
                elif isinstance(first_row, dict):
                    robot_name = first_row.get('robot_name')
                else:
                    robot_name = first_row

                # Return robot_name if it exists and is not empty, otherwise fallback to robot_sn
                if robot_name and str(robot_name).strip():
                    logger.info(f"Found robot_name for {robot_sn}: {robot_name}")
                    return str(robot_name).strip()

            logger.debug(f"No robot_name found for {robot_sn}, using robot_sn as fallback")

        except Exception as e:
            logger.warning(f"Could not retrieve robot_name for {robot_sn} using config: {e}")

        return robot_sn  # Fallback to robot_sn if name not found

    def _transform_robot_status_data(self, robot_sn: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform callback status data to database format"""
        db_data = {
            "robot_sn": robot_sn,
            "status": status_data.get("status", "").capitalize(),
            "timestamp_utc": datetime.fromtimestamp(status_data.get("timestamp", int(time.time()))).strftime('%Y-%m-%d %H:%M:%S')
        }
        # Remove None values
        return {k: v for k, v in db_data.items() if v is not None}

    def _transform_robot_pose_data(self, robot_sn: str, pose_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform callback pose data to database format with coordinate transformation"""
        # Basic database data structure
        db_data = {
            "robot_sn": robot_sn,
            "x": pose_data.get("x"),
            "y": pose_data.get("y"),
            "z": pose_data.get("z"),  # Note: callback uses 'yaw' but db expects 'z'
            "update_time": datetime.fromtimestamp(pose_data.get("timestamp", int(time.time()))).strftime('%Y-%m-%d %H:%M:%S')
        }

        # Handle the yaw -> z mapping if needed
        if "yaw" in pose_data and db_data["z"] is None:
            db_data["z"] = pose_data["yaw"]

        # Apply coordinate transformation
        try:
            transformed_data = self.transform_service.transform_robot_coordinates_single(db_data)

            # Add transformed coordinates to database data
            db_data["new_x"] = transformed_data.get("new_x")
            db_data["new_y"] = transformed_data.get("new_y")
            db_data["new_z"] = db_data["z"] if db_data["new_x"] is not None and db_data["new_y"] is not None else None  # No z transformation, keep original

            # NEW: Add original coordinates (preserve API values)
            db_data["original_x"] = transformed_data.get("original_x")
            db_data["original_y"] = transformed_data.get("original_y")
            db_data["original_z"] = db_data["z"] if db_data["new_x"] is not None and db_data["new_y"] is not None else None

            db_data["x"] = db_data["new_x"]
            db_data["y"] = db_data["new_y"]

            if db_data["new_x"] is not None and db_data["new_y"] is not None:
                logger.debug(f"Applied coordinate transformation for robot {robot_sn}: ({db_data['x']}, {db_data['y']}) → ({db_data['new_x']}, {db_data['new_y']})")
            else:
                logger.debug(f"No coordinate transformation applied for robot {robot_sn}")

        except Exception as e:
            logger.warning(f"Error applying coordinate transformation for robot {robot_sn}: {e}")
            # Set to None if transformation fails
            db_data["new_x"] = None
            db_data["new_y"] = None
            db_data["new_z"] = None
            db_data["original_x"] = None
            db_data["original_y"] = None
            db_data["original_z"] = None
            db_data["x"] = None
            db_data["y"] = None
            db_data["z"] = None

        # Remove None values
        return {k: v for k, v in db_data.items() if v is not None}

    def _transform_robot_power_data(self, robot_sn: str, power_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform callback power data to database format"""
        db_data = {
            "robot_sn": robot_sn,
            "battery_level": power_data.get("battery_level")  # API uses 'power', DB uses 'battery_level'
        }

        # Remove None values
        return {k: v for k, v in db_data.items() if v is not None}

    def _transform_robot_event_data(self, robot_sn: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform callback event data to database format"""
        db_data = {
            "robot_sn": robot_sn,
            "event_id": event_data.get("error_id", ""),
            "error_id": event_data.get("error_id", ""),  # Keep both for compatibility
            "event_level": event_data.get("event_level", "").lower(),
            "event_type": event_data.get("event_type", ""),
            "event_detail": event_data.get("event_detail", ""),
            "task_time": datetime.fromtimestamp(event_data.get("task_time", int(time.time()))).strftime('%Y-%m-%d %H:%M:%S'),
            "upload_time": datetime.fromtimestamp(event_data.get("upload_time", int(time.time()))).strftime('%Y-%m-%d %H:%M:%S'),
            "extra_fields": event_data.get("extra_fields"),  # JSON string
        }

        # Remove None values
        return {k: v for k, v in db_data.items() if v is not None}

    def _transform_robot_task_data(self, robot_sn: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform callback task data to database format"""
        import time
        from datetime import datetime

        def estimate_remaining_time(progress, duration_elapsed):
            """
            Estimate remaining time using elapsed duration and progress

            Args:
                progress (float): Progress as decimal (0.0 to 1.0)
                duration_elapsed (float): Time already spent in minutes

            Returns:
                float: Estimated remaining time in minutes
            """
            if progress is None or duration_elapsed is None:
                return None

            if progress <= 0:
                return None  # Can't estimate if no progress
            elif progress >= 1:
                return 0  # Task completed

            # Calculate: time_remaining = (time_elapsed / progress) * (1 - progress)
            total_estimated_time = duration_elapsed / progress
            remaining_time = total_estimated_time * (1 - progress)

            return round(remaining_time, 2)

        remaining_time = estimate_remaining_time(task_data.get("progress"), task_data.get("duration"))
        robot_type = str(task_data.get("robot_type", "")).upper()
        # check if robot_type contains 'S' or '40'
        if 'S' in robot_type and '40' not in robot_type:
            robot_battery_capacity = GS_robot_battery_capacity['S']
        elif '40' in robot_type:
            robot_battery_capacity = GS_robot_battery_capacity['40']
        else:
            robot_battery_capacity = 0

        consumption = round((task_data.get("battery_usage") / 100) * robot_battery_capacity, 5)

        db_data = {
            "robot_sn": robot_sn,
            "task_id": task_data.get("task_id", ""),
            "task_name": task_data.get("task_name", ""),
            "map_name": task_data.get("map_name", ""),
            "start_time": datetime.fromtimestamp(task_data.get("start_time", int(time.time()))).strftime('%Y-%m-%d %H:%M:%S') if task_data.get("start_time") else None,
            "end_time": datetime.fromtimestamp(task_data.get("end_time", int(time.time()))).strftime('%Y-%m-%d %H:%M:%S') if task_data.get("end_time") else None,
            "progress": task_data.get("progress") * 100,
            "duration": task_data.get("duration"),
            "actual_area": task_data.get("actual_area"),
            "plan_area": task_data.get("plan_area"),
            "efficiency": task_data.get("efficiency"),
            "water_consumption": task_data.get("water_consumption"),
            "mode": task_data.get("mode", ""),
            "status": task_data.get("status"),
            "map_url": task_data.get("map_url", ""),
            "remaining_time": remaining_time,
            "battery_usage": task_data.get("battery_usage"),
            "consumption": consumption,
            "extra_fields": task_data.get("extra_fields"),  # JSON string
        }


        # Remove None values
        return {k: v for k, v in db_data.items() if v is not None}

    def write_robot_status(self, robot_sn: str, status_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Write robot status data with change detection  and get database IDs"""
        return self._write_with_change_detection(
            'robot_status',
            robot_sn,
            status_data,
            self._transform_robot_status_data
        )

    def write_robot_pose(self, robot_sn: str, pose_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Write robot pose data with change detection and coordinate transformation"""
        # Write to robot_status table first (for status updates)
        status_db_names, status_table_names, status_changes = self._write_with_change_detection(
            'robot_status',
            robot_sn,
            pose_data,
            self._transform_robot_pose_data
        )

        # Write to robot_work_location table (for location tracking with coordinates)
        if robot_sn in self.config.filter_robots_for_transform_support([robot_sn])[0]:
            logger.info(f"🔍 Robot {robot_sn} is in a transform-supported database, writing to robot_work_location table")
            location_db_names, location_table_names, location_changes = self._write_with_change_detection(
                'robot_work_location',
                robot_sn,
                pose_data,
                self._transform_robot_pose_data
            )
        else:
            logger.info(f"🔍 Robot {robot_sn} is not in a transform-supported database, skipping robot_work_location table")
            location_db_names = []
            location_table_names = []
            location_changes = {}

        return location_db_names, location_table_names, location_changes

    def write_robot_power(self, robot_sn: str, power_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Write robot power data with change detection"""
        return self._write_with_change_detection(
            'robot_status',
            robot_sn,
            power_data,
            self._transform_robot_power_data
        )

    def write_robot_event(self, robot_sn: str, event_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Write robot event data with change detection"""
        return self._write_with_change_detection(
            'robot_events',
            robot_sn,
            event_data,
            self._transform_robot_event_data
        )

    def write_robot_task(self, robot_sn: str, task_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Write robot task report data with change detection"""
        return self._write_with_change_detection(
            'robot_task',
            robot_sn,
            task_data,
            self._transform_robot_task_data
        )

    def _get_table_columns(self, table: RDSTable) -> List[str]:
        """Get actual column names from database table"""
        try:
            # Query table structure to get actual columns
            columns_query = f"DESCRIBE {table.table_name}"
            columns_result = table.query_data(columns_query)
            if columns_result:
                return [col[0] for col in columns_result]
        except Exception as e:
            logger.warning(f"Could not get columns for {table.table_name}: {e}")

        # Fallback: return empty list
        return []

    def _filter_data_for_table(self, data: Dict[str, Any], table: RDSTable) -> Dict[str, Any]:
        """Filter data to only include columns that exist in the database table"""
        table_columns = self._get_table_columns(table)

        if not table_columns:
            # If we can't get table columns, return data as-is and let DB handle it
            logger.warning(f"No table columns found for {table.table_name}, proceeding with all data")
            return data

        # Filter data to only include existing columns
        filtered_data = {}
        for key, value in data.items():
            if key in table_columns:
                filtered_data[key] = value
            else:
                logger.debug(f"Skipping column '{key}' - not found in table {table.table_name}")

        logger.debug(f"Filtered data from {len(data)} to {len(filtered_data)} columns for {table.table_name}")
        return filtered_data

    def _write_with_change_detection(
        self,
        table_type: str,
        robot_sn: str,
        raw_data: Dict[str, Any],
        transform_func
    ) -> Tuple[List[str], List[str], Dict]:
        """Write data with change detection and return database information"""
        robot_name = self._get_robot_name(robot_sn)

        # Transform the raw callback data to database format
        transformed_data = transform_func(robot_sn, raw_data)

        if not transformed_data:
            logger.warning(f"No data to write after transformation for {robot_sn}")
            return [], [], {}

        logger.info(f"Transformed data: {transformed_data}")

        # Get table configurations for this robot
        table_configs = self.config.get_table_configs_for_robots(table_type, [robot_sn])

        database_names = []
        table_names = []
        all_changes = {}

        for table_config in table_configs:
            try:
                # Get actual RDSTable instance
                table = self._get_table(
                    database_name=table_config['database'],
                    table_name=table_config['table_name'],
                    fields=table_config.get('fields', []),
                    primary_keys=table_config['primary_keys']
                )

                # Filter data for robots that belong to this database
                target_robots = table_config.get('robot_sns', [])
                if target_robots and robot_sn not in target_robots:
                    continue

                # Filter transformed data to only include columns that exist in the table
                filtered_data = self._filter_data_for_table(transformed_data, table)

                if not filtered_data:
                    logger.warning(f"No valid columns found for {table.table_name} after filtering")
                    continue

                # Detect changes using the filtered data
                changes = detect_data_changes(
                    table, [filtered_data], table_config['primary_keys']
                )

                if changes:
                    # Extract changed records for database insertion
                    changed_records = []
                    for change_info in changes.values():
                        changed_records.append(change_info['new_values'])

                    # Use batch_insert_with_ids to get database keys
                    ids = table.batch_insert_with_ids(changed_records)

                    # Map database keys back to changes
                    pk_to_db_id = {}
                    for original_data, db_id in ids:
                        pk_values = tuple(str(original_data.get(pk, '')) for pk in table.primary_keys)
                        pk_to_db_id[pk_values] = db_id

                    # Add database_key to changes dictionary
                    for unique_id, change_info in changes.items():
                        pk_values = tuple(str(change_info['primary_key_values'].get(pk, '')) for pk in table.primary_keys)
                        db_id = pk_to_db_id.get(pk_values)
                        changes[unique_id]['database_key'] = db_id
                        changes[unique_id]['robot_name'] = robot_name

                    database_names.append(table_config['database'])
                    table_names.append(table_config['table_name'])

                    # Store changes with table identifier
                    table_key = (table.database_name, table.table_name)
                    all_changes[table_key] = changes

                    logger.info(f"Updated {len(changed_records)} records in {table_config['database']}.{table_config['table_name']}")
                else:
                    logger.debug(f"No changes detected for {table_config['database']}.{table_config['table_name']}")

            except Exception as e:
                logger.error(f"Failed to write to {table_config['database']}.{table_config['table_name']}: {e}")

        return database_names, table_names, all_changes

    def close_all_connections(self):
        """Close all table connections"""
        for table_key, table in self.table_cache.items():
            try:
                table.close()
                logger.info(f"Closed connection for table: {table_key}")
            except Exception as e:
                logger.warning(f"Error closing table {table_key}: {e}")

        self.table_cache.clear()
        self.config.close()

        # Close transform service
        try:
            self.transform_service.close()
        except Exception as e:
            logger.warning(f"Error closing transform service: {e}")