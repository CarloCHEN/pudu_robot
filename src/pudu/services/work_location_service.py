import logging
import pandas as pd
from typing import List, Dict, Optional
from pudu.rds.rdsTable import RDSTable
from pudu.apis.foxx_api import get_robot_work_location_and_mapping_data

logger = logging.getLogger(__name__)

class WorkLocationService:
    """
    Service to handle robot work location and map floor mapping updates with dynamic database resolution.

    This service manages:
    1. Robot work location tracking (mnt_robots_work_location table)
    2. Map to floor mapping updates (mnt_robot_map_floor_mapping table)
    """

    def __init__(self, config_path: str = "database_config.yaml"):
        """
        Initialize with dynamic database configuration

        Args:
            config_path (str): Path to database configuration YAML file
        """
        from pudu.configs.database_config_loader import DynamicDatabaseConfig # avoid circular import
        self.config = DynamicDatabaseConfig(config_path)

    def update_robot_work_locations_and_mappings(self) -> bool:
        """
        Update both robot work location data and map floor mappings with dynamic database resolution

        Returns:
            bool: True if all updates successful, False otherwise

        Process:
            1. Gets robot work location and mapping data from API
            2. Updates mnt_robots_work_location tables in appropriate project databases
            3. Updates mnt_robot_map_floor_mapping tables with resolved floor_ids
        """
        try:
            logger.info("🗺️ Updating robot work locations and map floor mappings (dynamic)...")

            # Get both datasets in a single API call
            work_location_data, mapping_data = get_robot_work_location_and_mapping_data()

            success = True

            # Update work locations
            if not work_location_data.empty:
                success &= self._update_work_locations(work_location_data)
            else:
                logger.info("No work location data to update")

            # Update map floor mappings
            if not mapping_data.empty:
                success &= self._update_map_floor_mappings(mapping_data, work_location_data)
            else:
                logger.info("No map floor mapping data to update")

            return success

        except Exception as e:
            logger.error(f"Error updating robot work locations and mappings: {e}")
            return False

    def _update_work_locations(self, work_location_data: pd.DataFrame) -> bool:
        """
        Update work location data with dynamic database resolution

        Args:
            work_location_data (pd.DataFrame): DataFrame with columns:
                - robot_sn (str): Robot serial number
                - map_name (str): Name of the map robot is on (None if idle)
                - x (float): X coordinate (None if idle)
                - y (float): Y coordinate (None if idle)
                - z (float): Z coordinate (None if idle)
                - status (str): 'normal' if in task, 'idle' if not in task
                - update_time (str): Timestamp of update

        Returns:
            bool: True if all updates successful, False otherwise
        """
        try:
            # Get robots from the data
            robots_in_data = work_location_data['robot_sn'].unique().tolist()

            # Get table configurations for these specific robots
            table_configs = self.config.get_table_configs_for_robots('robot_work_location', robots_in_data)

            success_count = 0
            total_count = len(table_configs)

            for table_config in table_configs:
                try:
                    # Initialize table
                    table = RDSTable(
                        connection_config="credentials.yaml",
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    # Filter data for robots that belong to this database
                    target_robots = table_config.get('robot_sns', [])
                    if target_robots:
                        filtered_data = work_location_data[work_location_data['robot_sn'].isin(target_robots)]
                    else:
                        filtered_data = work_location_data

                    if not filtered_data.empty:
                        data_list = filtered_data.to_dict(orient='records')
                        table.batch_insert(data_list)  # Commented for testing
                        success_count += 1
                        logger.info(f"✅ Updated work locations in {table_config['database']}.{table_config['table_name']} for {len(filtered_data)} robots")
                    else:
                        success_count += 1  # No data needed for this database
                        logger.info(f"ℹ️ No work location data for {table_config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"❌ Failed to update work locations in {table_config['database']}.{table_config['table_name']}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Error in _update_work_locations: {e}")
            return False

    def _update_map_floor_mappings(self, mapping_data: pd.DataFrame, work_location_data: pd.DataFrame) -> bool:
        """
        Update map floor mappings with dynamic database resolution

        Args:
            mapping_data (pd.DataFrame): DataFrame with columns:
                - map_name (str): Name of the map
                - floor_number (int): Floor number from robot task info

            work_location_data (pd.DataFrame): DataFrame with robot work location data

        Returns:
            bool: True if all updates successful, False otherwise
        """
        try:
            # Get all robots that have mapping data (simplified - no separate function needed)
            robots_with_mappings = self._get_robots_using_maps(mapping_data, work_location_data)

            if not robots_with_mappings:
                logger.info("No robots found for map floor mappings")
                return True

            # Resolve floor_ids for each map based on work_location_data (no extra DB queries!)
            # result is: {map_name: floor_id}
            resolved_mappings = self._resolve_floor_ids_dynamic(mapping_data, work_location_data)

            if resolved_mappings.empty:
                logger.info("No resolved map floor mappings to update")
                return True

            # Get table configurations for robots that use these maps
            table_configs = self.config.get_table_configs_for_robots('map_floor_mapping', robots_with_mappings)

            success_count = 0
            for table_config in table_configs:
                try:
                    # Initialize table
                    table = RDSTable(
                        connection_config="credentials.yaml",
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    # Update mappings for this database
                    self._update_map_floor_mappings_for_table(table, resolved_mappings)
                    success_count += 1

                    table.close()

                except Exception as e:
                    logger.error(f"❌ Error updating map floor mappings in {table_config['database']}.{table_config['table_name']}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Error in _update_map_floor_mappings: {e}")
            return False

    def _get_robots_using_maps(self, mapping_data: pd.DataFrame, work_location_data: pd.DataFrame) -> List[str]:
        """
        Get list of robots that are using the maps in mapping_data

        Args:
            mapping_data (pd.DataFrame): DataFrame with 'map_name' column
            work_location_data (pd.DataFrame): DataFrame with 'map_name', 'robot_sn', 'status' columns

        Returns:
            List[str]: List of robot serial numbers that are actively using the maps
        """
        if mapping_data.empty or work_location_data.empty:
            return []

        maps_in_mappings = mapping_data['map_name'].unique().tolist()
        robots_using_maps = work_location_data[
            work_location_data['map_name'].isin(maps_in_mappings) &
            (work_location_data['status'] == 'normal')
        ]['robot_sn'].unique().tolist()

        return robots_using_maps

    def _resolve_floor_ids_dynamic(self, mapping_data: pd.DataFrame, work_location_data: pd.DataFrame) -> pd.DataFrame:
        """
        Resolve floor numbers to floor_ids using building context from work_location_data

        Args:
            mapping_data (pd.DataFrame): DataFrame with columns:
                - map_name (str): Name of the map
                - floor_number (int): Floor number from robot task info

            work_location_data (pd.DataFrame): DataFrame with robot work location data

        Returns:
            pd.DataFrame: DataFrame with columns:
                - map_name (str): Name of the map
                - floor_id (int): Resolved floor ID for database insertion
        """
        resolved_mappings = []

        # Get building context for robots directly from work_location_data. result is: {robot_sn: building_id}
        building_context = self._get_robot_building_context_from_work_data(work_location_data)


        for _, row in mapping_data.iterrows():
            map_name = row['map_name']
            floor_number = row['floor_number']

            # Find building_id for this map from work_location_data. result is: building_id
            building_id = self._find_building_for_map_from_work_data(map_name, work_location_data, building_context)
            if building_id:
                # Look up floor_id using building_id and floor_number
                robots_using_map = work_location_data[
                    (work_location_data['map_name'] == map_name) &
                    (work_location_data['status'] == 'normal')
                ]['robot_sn'].tolist()

                floor_id = self._get_floor_id_dynamic(building_id, floor_number, robots_using_map)
                if floor_id:
                    resolved_mappings.append({
                        'map_name': map_name,
                        'floor_id': floor_id
                    })

        return pd.DataFrame(resolved_mappings)

    def _get_robot_building_context_from_work_data(self, work_location_data: pd.DataFrame) -> Dict[str, str]:
        """
        Get mapping of robot_sn to building_id from robot management tables

        Args:
            work_location_data (pd.DataFrame): DataFrame with 'robot_sn' column

        Returns:
            Dict[str, str]: Mapping of robot_sn to building_id (location_id)
                Example: {'811064412050012': 'B001', '811064412050013': 'B002'}
        """
        building_context = {}

        # Get unique robots from work location data
        robots_in_data = work_location_data['robot_sn'].unique().tolist()

        if not robots_in_data:
            return building_context

        # Get table configurations for robot status tables (project databases)
        table_configs = self.config.get_table_configs_for_robots('robot_status', robots_in_data)

        for table_config in table_configs:
            try:
                table = RDSTable(
                    connection_config="credentials.yaml",
                    database_name=table_config['database'],
                    table_name=table_config['table_name'],
                    fields=table_config.get('fields'),
                    primary_keys=table_config['primary_keys']
                )

                # Query robot management table for location_id (building_id)
                # Note: This queries the project database's mnt_robots_management table
                target_robots = table_config.get('robot_sns', [])
                if target_robots:
                    robot_list = "', '".join(target_robots)
                    query = f"SELECT robot_sn, location_id FROM {table.table_name} WHERE robot_sn IN ('{robot_list}')"
                else:
                    query = f"SELECT robot_sn, location_id FROM {table.table_name}"

                result = table.query_data(query)

                for record in result:
                    if isinstance(record, tuple) and len(record) >= 2:
                        robot_sn, location_id = record[0], record[1]
                        if robot_sn and location_id:
                            building_context[robot_sn] = location_id
                    elif isinstance(record, dict):
                        robot_sn = record.get('robot_sn')
                        location_id = record.get('location_id')
                        if robot_sn and location_id:
                            building_context[robot_sn] = location_id

                table.close()

            except Exception as e:
                logger.warning(f"Error getting building context from {table_config['database']}.{table_config['table_name']}: {e}")

        return building_context

    def _find_building_for_map_from_work_data(self, map_name: str, work_location_data: pd.DataFrame, building_context: Dict[str, str]) -> Optional[str]:
        """
        Find building_id for a map using work_location_data directly (no database query needed!)

        Args:
            map_name (str): Name of the map to find building for
            work_location_data (pd.DataFrame): DataFrame with columns:
                - robot_sn (str): Robot serial number
                - map_name (str): Map name
                - status (str): Robot status ('normal' or 'idle')
            building_context (Dict[str, str]): Mapping of robot_sn to building_id
                Example: {'811064412050012': 'B001', '811064412050013': 'B002'}

        Returns:
            Optional[str]: building_id if found, None if no robot is using this map
                Example: 'B001'
        """
        # Get robots that are currently using this map
        robots_using_map = work_location_data[
            (work_location_data['map_name'] == map_name) &
            (work_location_data['status'] == 'normal')
        ]['robot_sn'].tolist()

        # Find building_id from any robot using this map
        for robot_sn in robots_using_map:
            if robot_sn in building_context:
                return building_context[robot_sn]

    def _get_floor_id_dynamic(self, building_id: str, floor_number: int, robots_using_map: List[str]) -> Optional[int]:
        """
        Get floor_id from building_id and floor_number using dynamic database lookup

        Args:
            building_id (str): Building identifier (e.g., 'B001')
            floor_number (int): Floor number from robot task info (e.g., 1, 2, 3)
            robots_using_map (List[str]): List of robot SNs using this map

        Returns:
            Optional[int]: floor_id if found, None if no matching floor found
                Example: 12345 (the database primary key for this floor)
        """
        # Get table configurations for floor info tables
        table_configs = self.config.get_table_configs_for_robots('floor_info', robots_using_map)

        for table_config in table_configs:
            try:
                table = RDSTable(
                    connection_config="credentials.yaml",
                    database_name=table_config['database'],
                    table_name=table_config['table_name'],
                    fields=table_config.get('fields'),
                    primary_keys=table_config['primary_keys']
                )

                query = f"SELECT floor_id FROM {table.table_name} WHERE building_id = '{building_id}' AND floor_number = {floor_number}"
                result = table.query_data(query)

                if result:
                    floor_id = result[0][0] if isinstance(result[0], tuple) else result[0].get('floor_id')
                    table.close()
                    return floor_id

                table.close()

            except Exception as e:
                logger.debug(f"Error getting floor_id for building {building_id}, floor {floor_number}: {e}")

    def _update_map_floor_mappings_for_table(self, table: RDSTable, resolved_mappings: pd.DataFrame):
        """
        Update map floor mappings for a specific table with change detection

        Args:
            table (RDSTable): Database table instance for mnt_robot_map_floor_mapping
            resolved_mappings (pd.DataFrame): DataFrame with columns:
                - map_name (str): Name of the map
                - floor_id (int): Resolved floor ID

        Process:
            1. For each mapping, check if it exists in the database
            2. Update if floor_id changed
            3. Insert if mapping doesn't exist
        """
        try:
            # Check existing mappings
            for _, row in resolved_mappings.iterrows():
                map_name = row['map_name']
                new_floor_id = row['floor_id']

                # Check if a same map already exists
                query = f"SELECT id, floor_id FROM {table.table_name} WHERE map_name = '{map_name}'"
                existing = table.query_data(query)

                if existing: # if the map already exists
                    # Update if floor_id changed
                    existing_record = existing[0]
                    existing_floor_id = existing_record[1] if isinstance(existing_record, tuple) else existing_record.get('floor_id')

                    if existing_floor_id != new_floor_id:
                        record_id = existing_record[0] if isinstance(existing_record, tuple) else existing_record.get('id')
                        table.update_field_by_filters('floor_id', str(new_floor_id), {'id': record_id})  # Commented for testing
                        logger.info(f"Updated mapping for {map_name} in {table.database_name}.{table.table_name}: floor_id {existing_floor_id} -> {new_floor_id}")
                else:# a new map
                    # Insert new mapping
                    data = {
                        'map_name': map_name,
                        'floor_id': new_floor_id
                    }
                    table.insert_data(data)  # Commented for testing
                    logger.info(f"Inserted new mapping for {map_name} in {table.database_name}.{table.table_name}: floor_id {new_floor_id}")

        except Exception as e:
            logger.error(f"Error updating map floor mappings in {table.database_name}.{table.table_name}: {e}")

    def run_work_location_updates(self) -> bool:
        """
        Run all work location related updates with dynamic database resolution

        Returns:
            bool: True if all updates completed successfully, False if any failures occurred

        Process:
            1. Calls get_robot_work_location_and_mapping_data() to get current robot states
            2. Updates mnt_robots_work_location tables across all relevant project databases
            3. Resolves and updates mnt_robot_map_floor_mapping tables
            4. Handles cleanup and error reporting
        """
        logger.info("🚀 Starting dynamic work location updates...")

        try:
            # Update both robot work locations and map floor mappings efficiently
            success = self.update_robot_work_locations_and_mappings()

            if success:
                logger.info("✅ Dynamic work location updates completed successfully")
            else:
                logger.warning("⚠️ Dynamic work location updates completed with some failures")

            return success

        except Exception as e:
            logger.error(f"💥 Critical error in dynamic work location updates: {e}")
            return False
        finally:
            self.config.close()
