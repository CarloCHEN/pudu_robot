import logging
from typing import Any, Dict, List

from configs.database_config import DatabaseConfig
from rds.rdsTable import RDSTable
from notifications.change_detector import detect_data_changes

logger = logging.getLogger(__name__)


class DatabaseWriter:
    """Enhanced database writer with dynamic routing and change detection"""

    def __init__(self, config_path: str = "database_config.yaml"):
        self.config = DatabaseConfig(config_path)
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

    def write_robot_status(self, robot_sn: str, status_data: Dict[str, Any]):
        """Write robot status data with dynamic routing and change detection"""
        return self._write_with_dynamic_routing(
            'robot_status', [robot_sn], [status_data]
        )

    def write_robot_pose(self, robot_sn: str, pose_data: Dict[str, Any]):
        """Write robot pose data with dynamic routing and change detection"""
        return self._write_with_dynamic_routing(
            'robot_status', [robot_sn], [pose_data]
        )

    def write_robot_power(self, robot_sn: str, power_data: Dict[str, Any]):
        """Write robot power data with dynamic routing and change detection"""
        return self._write_with_dynamic_routing(
            'robot_status', [robot_sn], [power_data]
        )

    def write_robot_event(self, robot_sn: str, event_data: Dict[str, Any]):
        """Write robot event data with dynamic routing and change detection"""
        return self._write_with_dynamic_routing(
            'robot_events', [robot_sn], [event_data]
        )

    def _write_with_dynamic_routing(self, table_type: str, robot_sns: List[str], data_list: List[Dict]):
        """
        Write data with dynamic database routing and change detection

        Returns:
            tuple: (database_names, table_names, primary_key_values, changes_detected)
        """
        if not robot_sns or not data_list:
            return [], [], {}, {}

        # Get table configurations for these robots
        table_configs = self.config.get_table_configs_for_robots(table_type, robot_sns)

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
                if target_robots:
                    filtered_data = [data for data in data_list
                                   if data.get('robot_sn') in target_robots]
                else:
                    filtered_data = data_list

                if not filtered_data:
                    continue

                # Detect changes using the actual table object
                changes = detect_data_changes(
                    table, filtered_data, table_config['primary_keys']
                )

                if changes:
                    # Insert changed records and get database keys
                    changed_records = []
                    for change_info in changes.values():
                        changed_records.append(change_info['new_values'])

                    # Use the table's batch_insert_with_ids method
                    ids = table.batch_insert_with_ids(changed_records)

                    # ids is a list of tuples, each tuple contains (original_data_dict, unique_key_in_db)
                    # now we need to add the database_key to each change record
                    # step 1: add database_key to primary_key_values dict
                    pk_to_db_id = {}
                    for original_data, db_id in ids:
                        # Create primary key tuple for matching
                        pk_values = tuple(str(original_data.get(pk, '')) for pk in table.primary_keys)
                        pk_to_db_id[pk_values] = db_id

                    # step 2: add database_key to changes dictionary
                    for unique_id, change_info in changes.items():
                        # Create primary key tuple from change info
                        pk_values = tuple(str(change_info['primary_key_values'].get(pk, '')) for pk in table.primary_keys)
                        # Add database_key to the change info
                        db_id = pk_to_db_id.get(pk_values)
                        changes[unique_id]['database_key'] = db_id

                    database_names.append(table_config['database'])
                    table_names.append(table_config['table_name'])

                    # Store changes with table identifier
                    table_key = tuple([table.database_name, table.table_name])
                    all_changes[table_key] = changes

                    logger.info(f"Updated {len(filtered_data)} records in {table_config['database']}.{table_config['table_name']}")
                else:
                    logger.info(f"No changes detected for {table_config['database']}.{table_config['table_name']}")

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