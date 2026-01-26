import logging
import traceback
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import concurrent.futures
from pudu.rds.rdsTable import RDSTable
from pudu.apis.foxx_api import get_robot_work_location_and_mapping_data
from pudu.apis.core.config_manager import config_manager


logger = logging.getLogger(__name__)

class WorkLocationService:
    """
    Service to handle robot work location and map floor mapping updates with dynamic database resolution.

    This service manages:
    1. Robot work location tracking (mnt_robots_work_location table) with historical data
    2. Map to floor mapping updates (mnt_robot_map_floor_mapping table)
    3. Coordinate transformation for supported databases
    4. Data archival to S3 to maintain performance
    """

    def __init__(self, config, s3_config: Dict, run_backfill: bool = True):
        """
        Initialize with dynamic database configuration

        Args:
            config: DynamicDatabaseConfig object
            s3_config: S3 configuration dictionary
        """
        from pudu.services.transform_service import TransformService

        self.config = config
        self.s3_config = s3_config
        self.transform_service = TransformService(self.config, self.s3_config)

        # NEW: Archival configuration for historical data management
        self.MAX_RETENTION_HOURS = 24 * 31     # 31 days max
        # self.MAX_RETENTION_COUNT = 1000    # 1000 records max
        self.ARCHIVE_BATCH_SIZE = 500      # Archive 500 records at a time
        self.MIN_ARCHIVE_THRESHOLD = 100    # Only archive if we have at least 100 excess records

        self.run_backfill = run_backfill

    def _get_customers_and_robot_types(self) -> Dict[str, List[str]]:
        """
        Determine which customers and robot types are enabled via environment/config.

        Mirrors the main app pipeline logic so the work location flow calls the
        right APIs per customer instead of relying on database-derived robot types.
        """
        customers = config_manager.get_customers_from_env(env_variable_name='ROBOT_LOCATION_CUSTOMERS')

        if not customers:
            logger.warning("No customers configured - using default customer with pudu+gas")
            return {'default': ['pudu', 'gas']}

        customer_robot_types: Dict[str, List[str]] = {}

        for customer in customers:
            try:
                enabled_apis = config_manager.get_customer_enabled_apis(customer)

                if enabled_apis:
                    customer_robot_types[customer] = enabled_apis
                    logger.info(f"Customer '{customer}' has robot types: {enabled_apis}")
                else:
                    logger.warning(f"Customer '{customer}' has no enabled robot types")

            except Exception as e:
                logger.error(f"Error getting robot types for customer '{customer}': {e}")
                continue

        if not customer_robot_types:
            logger.warning("No valid customer configurations found - using default customer with pudu+gas")
            return {'default': ['pudu', 'gas']}

        return customer_robot_types

    def update_robot_work_locations_and_mappings(self) -> bool:
        """
        Update both robot work location data and map floor mappings with dynamic database resolution
        Supports multiple robot types and combines results from all types

        Returns:
            bool: True if all updates successful, False otherwise

        Process:
            1. Detect active robot types in current region
            2. Get robot work location and mapping data from all active robot type APIs
            3. Combine results from all robot types
            4. Transforms coordinates for robots in supported databases
            5. Updates mnt_robots_work_location tables in appropriate project databases (APPEND mode)
            6. Runs archival process to maintain performance
            7. Updates mnt_robot_map_floor_mapping tables with resolved floor_ids
        """
        try:
            logger.info("🗺️ Updating robot work locations and map floor mappings (dynamic multi-type)...")

            # Determine customers and robot types from config/env (align with main pipeline)
            customer_robot_types = self._get_customers_and_robot_types()
            api_calls = [
                (customer_name, robot_type)
                for customer_name, robot_types in customer_robot_types.items()
                for robot_type in robot_types
            ]

            if not api_calls:
                logger.warning("No customer robot types resolved - defaulting to pudu+gas for default customer")
                api_calls = [('default', 'pudu'), ('default', 'gas')]

            logger.info(f"🔄 Fetching work location data for customers/types: {customer_robot_types}")

            # Fetch data from all customer/robot_type combinations in parallel
            all_work_location_data = []
            all_mapping_data = []

            # Use ThreadPoolExecutor to get data from all customer/robot-type pairs simultaneously
            max_workers = max(len(api_calls), 1)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="work_location_worker") as executor:
                # Submit API calls for all robot types scoped to each customer
                future_to_context = {}
                for customer_name, robot_type in api_calls:
                    future = executor.submit(
                        get_robot_work_location_and_mapping_data,
                        robot_type=robot_type,
                        customer_name=customer_name
                    )
                    future_to_context[future] = (customer_name, robot_type)
                    logger.debug(f"📡 Submitted work location API call for {customer_name}.{robot_type}")

                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_context, timeout=60):
                    customer_name, robot_type = future_to_context[future]
                    try:
                        work_location_data, mapping_data = future.result()
                        all_work_location_data.append(work_location_data)
                        all_mapping_data.append(mapping_data)
                        logger.info(
                            f"✅ Completed work location API call for {customer_name} ({robot_type}): "
                            f"{len(work_location_data)} work locations, {len(mapping_data)} mappings"
                        )
                    except Exception as e:
                        logger.error(f"❌ Work location API call failed for {customer_name} ({robot_type}): {e}")
                        # Add empty DataFrames as fallback
                        all_work_location_data.append(pd.DataFrame())
                        all_mapping_data.append(pd.DataFrame())

            # Combine results from all robot types
            combined_work_location_data = pd.concat(all_work_location_data, ignore_index=True) if all_work_location_data else pd.DataFrame()
            combined_mapping_data = pd.concat(all_mapping_data, ignore_index=True) if all_mapping_data else pd.DataFrame()

            logger.info(f"📊 Combined results: {len(combined_work_location_data)} total work locations, {len(combined_mapping_data)} total mappings")

            success = True

            # Update work locations (with coordinate transformation and archival)
            if not combined_work_location_data.empty:
                success &= self._update_work_locations_with_archival(combined_work_location_data)
            else:
                logger.info("No work location data to update")

            # Update map floor mappings
            if not combined_mapping_data.empty:
                success &= self._update_map_floor_mappings(combined_mapping_data, combined_work_location_data)
            else:
                logger.info("No map floor mapping data to update")

            # Also backfill floor info table
            if self.run_backfill:
                backfill_success = self._backfill_floor_info_from_tasks()
                success &= backfill_success
            else:
                logger.info("Floor info backfill is disabled, skipping...")
            return success

        except Exception as e:
            logger.error(f"Error updating robot work locations and mappings: {e}")
            return False

    def _prepare_df_for_database(self, df, columns_to_remove=[]):
        """Prepare DataFrame for database insertion"""
        if df.empty:
            return df

        # Make a copy to avoid modifying the original
        processed_df = df.copy()
        processed_df.columns = [col.lower().replace(' ', '_') for col in processed_df.columns]

        # Remove columns that might conflict with database auto-generated fields
        for col in columns_to_remove:
            if col in processed_df.columns:
                processed_df.drop(columns=[col], inplace=True)

        logger.debug(f"Prepared DataFrame with {processed_df.shape[0]} rows and {processed_df.shape[1]} columns")
        return processed_df

    def _update_work_locations_with_archival(self, work_location_data: pd.DataFrame) -> bool:
        """
        NEW METHOD: Update work location data with coordinate transformation and archival management
        OPTIMIZED: For idle robots (x, y, z all None), only update the most recent record's update_time

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
            # Transform coordinates and prepare enhanced data
            enhanced_data = self._prepare_enhanced_work_location_data(work_location_data)

            # OPTIMIZATION: Separate active and idle robots
            active_robots_data = enhanced_data[enhanced_data['status'] != 'idle'].copy()
            idle_robots_data = enhanced_data[enhanced_data['status'] == 'idle'].copy()

            # Get robots from the data
            all_robots = enhanced_data['robot_sn'].unique().tolist()

            # Get table configurations for these specific robots
            table_configs = self.config.get_table_configs_for_robots('robot_work_location', all_robots)

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
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=True
                    )

                    # Get robots that belong to this database
                    target_robots = table_config.get('robot_sns', [])

                    # Process active robots (normal batch insert)
                    if not active_robots_data.empty:
                        if target_robots:
                            filtered_active_data = active_robots_data[active_robots_data['robot_sn'].isin(target_robots)]
                        else:
                            filtered_active_data = active_robots_data

                        if not filtered_active_data.empty:
                            # Use INSERT ON DUPLICATE KEY UPDATE for active robots (new records)
                            active_data_list = filtered_active_data.to_dict(orient='records')
                            table.batch_insert(active_data_list)
                            logger.debug(f"Inserted {len(filtered_active_data)} active robot records")

                    # Process idle robots (update most recent record's update_time only)
                    if not idle_robots_data.empty:
                        if target_robots:
                            filtered_idle_data = idle_robots_data[idle_robots_data['robot_sn'].isin(target_robots)]
                        else:
                            filtered_idle_data = idle_robots_data

                        if not filtered_idle_data.empty:
                            self._update_idle_robots_efficiently(table, filtered_idle_data)

                    # Run archival after processing new data
                    self._run_archival_for_table(table)

                    # Log stats for this database
                    db_active = len(active_robots_data[active_robots_data['robot_sn'].isin(target_robots)]) if target_robots else len(active_robots_data)
                    db_idle = len(idle_robots_data[idle_robots_data['robot_sn'].isin(target_robots)]) if target_robots else len(idle_robots_data)
                    db_transformed = len(enhanced_data[(enhanced_data['robot_sn'].isin(target_robots) if target_robots else slice(None)) & enhanced_data['new_x'].notna()])

                    logger.info(f"✅ Updated work locations in {table_config['database']}.{table_config['table_name']}: "
                               f"{db_active} active robots (inserted), {db_idle} idle robots (time updated), "
                               f"{db_transformed} with coordinates transformed")
                    success_count += 1

                    table.close()

                except Exception as e:
                    tb = traceback.extract_tb(e.__traceback__)
                    last_frame = tb[-1]
                    logger.error(f"❌ Failed to update work locations in {table_config['database']}.{table_config['table_name']}")
                    logger.error(f"   Error: {type(e).__name__}: {e}")
                    logger.error(f"   Line {last_frame.lineno}: {last_frame.line}")

            return success_count > 0

        except Exception as e:
            logger.error(f"Error in _update_work_locations_with_archival: {e}")
            return False

    def _update_idle_robots_efficiently(self, table: RDSTable, idle_robots_data: pd.DataFrame):
        """
        OPTIMIZATION: For idle robots, only update the most recent record's update_time
        instead of inserting new records.

        Note: Table uses (robot_sn, update_time) as composite primary key, no id column.

        Args:
            table: Database table instance
            idle_robots_data: DataFrame containing only idle robots data
        """
        try:
            for _, robot_row in idle_robots_data.iterrows():
                robot_sn = robot_row['robot_sn']
                new_update_time = robot_row['update_time']

                try:
                    # Find the most recent idle record for this robot
                    query = f"""
                        SELECT update_time FROM {table.table_name}
                        WHERE robot_sn = '{robot_sn}' AND status = 'idle'
                        ORDER BY update_time DESC
                        LIMIT 1
                    """

                    result = table.query_data(query)

                    if result:
                        # Get the most recent update_time
                        most_recent_time = result[0][0] if isinstance(result[0], tuple) else result[0].get('update_time')

                        # Update the most recent record by using the composite key
                        table.update_field_by_filters(
                            'update_time',
                            str(new_update_time),
                            {
                                'robot_sn': robot_sn,
                                'update_time': most_recent_time
                            }
                        )
                        logger.debug(f"Updated idle robot {robot_sn} most recent record time from {most_recent_time} to {new_update_time}")
                    else:
                        # No existing record - insert as usual (first time seeing this robot)
                        robot_data = robot_row.to_dict()
                        table.insert_data(robot_data)
                        logger.info(f"Inserted first record for idle robot {robot_sn}")

                except Exception as e:
                    logger.warning(f"Error updating idle robot {robot_sn}: {e}")

        except Exception as e:
            logger.error(f"Error in _update_idle_robots_efficiently: {e}")

    def _prepare_enhanced_work_location_data(self, work_location_data: pd.DataFrame) -> pd.DataFrame:
        """
        NEW METHOD: Prepare enhanced work location data with coordinate transformation and proper column mapping

        Returns DataFrame with columns:
        - robot_sn, map_name, status, update_time
        - x, y, z (current/converted coordinates)
        - new_x, new_y, new_z (floor plan coordinates)
        - original_x, original_y, original_z (robot map coordinates)
        """
        try:
            # Transform coordinates before saving to database
            logger.info("🔧 Applying coordinate transformations...")
            transformed_data = self.transform_service.transform_robot_coordinates_batch(work_location_data)

            # Create enhanced data with proper column mapping
            enhanced_data = transformed_data.copy()

            # Map original coordinates to original_* columns
            enhanced_data['original_z'] = enhanced_data['z'] if enhanced_data['new_x'] is not None and enhanced_data['new_y'] is not None else None

            # For new_z, keep original z value (no z transformation implemented)
            enhanced_data['new_z'] = enhanced_data['z'] if enhanced_data['new_x'] is not None and enhanced_data['new_y'] is not None else None

            # x, y could be original or converted
            enhanced_data['x'] = enhanced_data['new_x']
            enhanced_data['y'] = enhanced_data['new_y']

            # Ensure None values stay as None (not converted to 0) for idle robots
            idle_mask = enhanced_data['status'] == 'idle'
            coordinate_cols = ['x', 'y', 'z', 'original_x', 'original_y', 'original_z']

            for col in coordinate_cols:
                if col in enhanced_data.columns:
                    # Convert nan values to None for idle robots (pandas converts None to nan)
                    enhanced_data.loc[idle_mask & (enhanced_data[col].isna()), col] = None

            # Handle new_x, new_y - set to null when no transformation available
            if 'new_x' in enhanced_data.columns:
                enhanced_data.loc[enhanced_data['new_x'].isna(), 'new_x'] = None
            if 'new_y' in enhanced_data.columns:
                enhanced_data.loc[enhanced_data['new_y'].isna(), 'new_y'] = None

            # Handle map_name - set to null when robot is idle
            enhanced_data.loc[enhanced_data['status'] == 'idle', 'map_name'] = None

            # Log transformation results
            transformed_count = len(enhanced_data[enhanced_data['new_x'].notna()])
            total_count = len(enhanced_data)
            logger.info(f"Enhanced work location data: {transformed_count}/{total_count} robots with coordinate transformation")

            return enhanced_data

        except Exception as e:
            logger.error(f"Error preparing enhanced work location data: {e}")
            return work_location_data.copy()


    def _run_archival_for_table(self, table: RDSTable):
        """
        Run archival process for a specific table to maintain performance
        """
        try:
            # Check which robots need archival
            robots_needing_archive = self._check_robots_needing_archive(table)

            if not robots_needing_archive:
                logger.debug(f"No archival needed for {table.database_name}.{table.table_name}")
                return

            logger.info(f"📦 {len(robots_needing_archive)} robots need archival in {table.database_name}")

            for robot_sn, archive_info in robots_needing_archive.items():
                try:
                    # Get data to archive
                    archive_data = self._get_archive_data_for_robot(table, robot_sn, archive_info)

                    if not archive_data.empty:
                        # Archive to S3
                        s3_success = self._upload_robot_data_to_s3(archive_data, robot_sn, table.database_name)

                        if s3_success:
                            # Delete from database
                            self._delete_archived_data(table, robot_sn, archive_data)
                            logger.info(f"✅ Archived {len(archive_data)} records for robot {robot_sn}")
                        else:
                            logger.warning(f"⚠️ Failed to upload to S3 for robot {robot_sn}, keeping data in DB")

                except Exception as e:
                    logger.error(f"❌ Error archiving robot {robot_sn}: {e}")

        except Exception as e:
            logger.error(f"Error running archival for {table.database_name}.{table.table_name}: {e}")

    def _check_robots_needing_archive(self, table: RDSTable) -> Dict[str, Dict]:
        """
        Check which robots need archival based on dual conditions:
        - Keep max 24 hours OR 1000 records (whichever is LESS)
        """
        robots_needing_archive = {}

        try:
            # Get all robots that have data in this table
            robots_query = f"SELECT DISTINCT robot_sn FROM {table.table_name}"
            robot_results = table.query_data(robots_query)

            for robot_record in robot_results:
                robot_sn = robot_record[0] if isinstance(robot_record, tuple) else robot_record.get('robot_sn')
                if not robot_sn:
                    continue

                archive_info = self._check_robot_archive_needs(table, robot_sn)
                if archive_info:
                    robots_needing_archive[robot_sn] = archive_info

        except Exception as e:
            logger.error(f"Error checking archive needs: {e}")

        return robots_needing_archive

    def _check_robot_archive_needs(self, table: RDSTable, robot_sn: str) -> Optional[Dict]:
        """
        NEW METHOD: Check if specific robot needs archival based on time AND count limits
        """
        try:
            # Get robot's data statistics
            stats_query = f"""
                SELECT
                    COUNT(*) as total_count,
                    MIN(update_time) as oldest_time,
                    MAX(update_time) as newest_time
                FROM {table.table_name}
                WHERE robot_sn = '{robot_sn}'
            """

            result = table.query_data(stats_query)
            if not result:
                return None

            stats = result[0]
            total_count = stats[0] if isinstance(stats, tuple) else stats.get('total_count')
            oldest_time = stats[1] if isinstance(stats, tuple) else stats.get('oldest_time')

            if total_count < self.MIN_ARCHIVE_THRESHOLD:
                return None  # Not enough data to bother archiving

            # Convert string timestamps to datetime if needed
            if isinstance(oldest_time, str):
                oldest_time = pd.to_datetime(oldest_time)

            current_time = datetime.now()
            time_cutoff = current_time - timedelta(hours=self.MAX_RETENTION_HOURS)

            # Check both conditions: time-based and count-based
            archive_info = None

            # Condition 1: Count limit exceeded
            # if total_count > self.MAX_RETENTION_COUNT:
            #     excess_count = total_count - self.MAX_RETENTION_COUNT
            #     archive_info = {
            #         'excess_count': excess_count,
            #         'cutoff_method': 'count',
            #         'reason': f'Count limit exceeded: {total_count} > {self.MAX_RETENTION_COUNT}',
            #         'archive_count': min(excess_count, self.ARCHIVE_BATCH_SIZE) # archive at most ARCHIVE_BATCH_SIZE records
            #     }

            # Condition 2: Time limit exceeded
            if oldest_time < time_cutoff:
                # Count how many records are older than 24 hours
                old_count_query = f"""
                    SELECT COUNT(*)
                    FROM {table.table_name}
                    WHERE robot_sn = '{robot_sn}'
                    AND update_time < '{time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}'
                """

                old_count_result = table.query_data(old_count_query)
                old_count = old_count_result[0][0] if old_count_result else 0

                if old_count > 0:
                    archive_info = {
                        'excess_count': old_count,
                        'cutoff_method': 'time',
                        'cutoff_time': time_cutoff,
                        'reason': f'Time limit exceeded: oldest record from {oldest_time} < {time_cutoff}',
                        'archive_count': min(old_count, self.ARCHIVE_BATCH_SIZE) # archive at most ARCHIVE_BATCH_SIZE records
                    }

            if archive_info:
                logger.debug(f"🗂️ Robot {robot_sn} needs archive: {archive_info['reason']}")

            return archive_info

        except Exception as e:
            logger.error(f"Error checking archive needs for robot {robot_sn}: {e}")
            return None

    def _get_archive_data_for_robot(self, table: RDSTable, robot_sn: str, archive_info: Dict) -> pd.DataFrame:
        """
        NEW METHOD: Get the specific data that should be archived for a robot
        """
        try:
            if archive_info['cutoff_method'] == 'count':
                # Archive oldest records when count limit exceeded
                query = f"""
                    SELECT * FROM {table.table_name}
                    WHERE robot_sn = '{robot_sn}'
                    ORDER BY update_time ASC
                    LIMIT {archive_info['archive_count']}
                """
            else:  # time-based
                # Archive records older than cutoff time
                cutoff_time = archive_info['cutoff_time']
                query = f"""
                    SELECT * FROM {table.table_name}
                    WHERE robot_sn = '{robot_sn}'
                    AND update_time < '{cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}'
                    ORDER BY update_time ASC
                    LIMIT {archive_info['archive_count']}
                """

            # Use execute_query to get DataFrame
            archive_data = table.execute_query(query)

            logger.debug(f"📦 Retrieved {len(archive_data)} records for archival: robot {robot_sn}")
            return archive_data

        except Exception as e:
            logger.error(f"Error getting archive data for robot {robot_sn}: {e}")
            return pd.DataFrame()

    def _upload_robot_data_to_s3(self, archive_data: pd.DataFrame, robot_sn: str, database_name: str) -> bool:
        """
        NEW METHOD: Upload robot work location data to S3 for archival

        Uses the existing S3 service if available, or creates a simple S3 uploader
        """
        try:
            # Use transform service's S3 service if available
            if hasattr(self.transform_service, 's3_service') and self.transform_service.s3_service:
                return self.transform_service.s3_service.upload_work_location_data(
                    archive_data, robot_sn, database_name
                )
            else:
                logger.warning(f"S3 service not available, cannot archive data for robot {robot_sn}")
                return False

        except Exception as e:
            logger.error(f"Error uploading robot data to S3 for {robot_sn}: {e}")
            return False

    def _delete_archived_data(self, table: RDSTable, robot_sn: str, archived_data: pd.DataFrame):
        """
        Delete the data that was successfully archived
        """
        try:
            if archived_data.empty:
                return

            # Use 'id' column for precise deletion if available
            if 'id' in archived_data.columns:
                ids = archived_data['id'].tolist()
                ids_str = ','.join(map(str, ids))
                delete_query = f"DELETE FROM {table.table_name} WHERE id IN ({ids_str})"
            else:
                # Fallback: delete by robot_sn and time range
                min_time = archived_data['update_time'].min()
                max_time = archived_data['update_time'].max()
                delete_query = f"""
                    DELETE FROM {table.table_name}
                    WHERE robot_sn = '{robot_sn}'
                    AND update_time BETWEEN '{min_time}' AND '{max_time}'
                    LIMIT {len(archived_data)}
                """

            table.cursor.execute(delete_query)
            table.cursor.connection.commit()

            logger.debug(f"🗑️ Deleted {len(archived_data)} archived records for robot {robot_sn}")

        except Exception as e:
            logger.error(f"Error deleting archived data for robot {robot_sn}: {e}")

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
            # Get all robots that have mapping data
            robots_with_mappings = self._get_robots_using_maps(mapping_data, work_location_data)

            if not robots_with_mappings:
                logger.info("No robots found for map floor mappings")
                return True

            # Resolve floor_ids for each map based on work_location_data
            resolved_mappings = self._resolve_floor_ids_dynamic(mapping_data, work_location_data)

            if resolved_mappings.empty:
                logger.info("No resolved map floor mappings to update")
                return True
            logger.info(f"Resolved mappings: {resolved_mappings}")

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
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=True
                    )

                    # FIXED: Filter mappings for this specific database
                    target_robots = table_config.get('robot_sns', [])
                    database_mappings = self._filter_mappings_for_database(
                        resolved_mappings, work_location_data, target_robots
                    )

                    if not database_mappings.empty:
                        # Update mappings for this database
                        self._update_map_floor_mappings_for_table(table, database_mappings)
                        logger.info(f"✅ Updated {len(database_mappings)} mappings in {table_config['database']}.{table_config['table_name']}")
                    else:
                        logger.info(f"ℹ️ No relevant mappings for {table_config['database']}")

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
        logger.info(f"Building context: {building_context}")

        for _, row in mapping_data.iterrows():
            map_name = row['map_name']
            floor_number = row['floor_number']

            # Find building_id for this map from work_location_data. result is: building_id
            building_id = self._find_building_for_map_from_work_data(map_name, work_location_data, building_context)
            logger.info(f"Building id for {map_name}: {building_id}")

            if building_id:
                # Look up floor_id using building_id and floor_number
                robots_using_map = work_location_data[
                    (work_location_data['map_name'] == map_name) &
                    (work_location_data['status'] == 'normal')
                ]['robot_sn'].tolist()

                floor_id = self._get_floor_id_dynamic(building_id, floor_number, robots_using_map, map_name)
                logger.info(f"Floor id for {map_name} is: {floor_id}")
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

        # Get table configurations for robot management tables (project databases)
        table_configs = self.config.get_table_configs_for_robots('robot_management', robots_in_data)

        for table_config in table_configs:
            try:
                table = RDSTable(
                    connection_config="credentials.yaml",
                    database_name=table_config['database'],
                    table_name=table_config['table_name'],
                    fields=table_config.get('fields'),
                    primary_keys=table_config['primary_keys'],
                    reuse_connection=True
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
        # So we need to make sure map name is unique for a building (different buildings cannot have the same map name)
        for robot_sn in robots_using_map:
            if robot_sn in building_context:
                return building_context[robot_sn]

    def _get_floor_id_dynamic(self, building_id: str, floor_number: int, robots_using_map: List[str], map_name: str) -> Optional[int]:
        """
        Get floor_id from building_id and floor_number using dynamic database lookup

        Args:
            building_id (str): Building identifier (e.g., 'B001')
            floor_number (int): Floor number from robot task info (e.g., 1, 2, 3)
            robots_using_map (List[str]): List of robot SNs using this map
            map_name (str): Name of the map

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
                    primary_keys=table_config['primary_keys'],
                    reuse_connection=True
                )

                query = f"SELECT floor_id FROM {table.table_name} WHERE building_id = '{building_id}' AND floor_number = {floor_number} AND robot_map_name = '{map_name}'"
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
                        table.update_field_by_filters('floor_id', str(new_floor_id), {'id': record_id})
                        logger.info(f"Updated mapping for {map_name} in {table.database_name}.{table.table_name}: floor_id {existing_floor_id} -> {new_floor_id}")
                else:# a new map
                    # Insert new mapping
                    data = {
                        'map_name': map_name,
                        'floor_id': new_floor_id
                    }
                    table.insert_data(data)
                    logger.info(f"Inserted new mapping for {map_name} in {table.database_name}.{table.table_name}: floor_id {new_floor_id}")

        except Exception as e:
            logger.error(f"Error updating map floor mappings in {table.database_name}.{table.table_name}: {e}")

    def _backfill_floor_info_from_tasks(self) -> bool:
        """
        Insert missing floor info rows based on map_name/building_id in robot task tables.

        Mirrors provided SQL and runs per database where both robot_task and floor_info
        tables are configured for the relevant robots.
        """
        try:
            # Use ALL configured table mappings (not only robots_with_mappings) to ensure every DB is covered
            floor_configs = self.config.get_all_table_configs('floor_info')
            task_configs = self.config.get_all_table_configs('robot_task')
            management_configs = self.config.get_all_table_configs('robot_management')

            if not floor_configs or not task_configs or not management_configs:
                logger.info("No floor/task/management table configs available for backfill")
                return True

            task_by_db = {cfg['database']: cfg for cfg in task_configs}
            management_by_db = {cfg['database']: cfg for cfg in management_configs}

            success_ops = 0
            for floor_cfg in floor_configs:
                db_name = floor_cfg['database']
                task_cfg = task_by_db.get(db_name)
                management_cfg = management_by_db.get(db_name)
                if not task_cfg or not management_cfg:
                    logger.debug(f"Skipping floor backfill for {db_name}: no robot_task config")
                    continue

                try:
                    floor_table = RDSTable(
                        connection_config="credentials.yaml",
                        database_name=db_name,
                        table_name=floor_cfg['table_name'],
                        fields=floor_cfg.get('fields'),
                        primary_keys=floor_cfg['primary_keys'],
                        reuse_connection=True
                    )

                    # Build SQL using the configured table names within the same database
                    sql = f"""
                        INSERT INTO {floor_cfg['table_name']}
                          (robot_map_name, floor_number, floor_name, building_id)
                        SELECT DISTINCT
                          t.map_name AS robot_map_name,
                          CASE
                            WHEN t.map_name REGEXP '^-?[0-9]+#'
                              THEN CAST(SUBSTRING_INDEX(t.map_name, '#', 1) AS SIGNED)
                            ELSE 1
                          END AS floor_number,
                          CASE
                            WHEN t.map_name REGEXP '^-?[0-9]+#'
                              THEN CONCAT('f_', CAST(SUBSTRING_INDEX(t.map_name, '#', 1) AS SIGNED))
                            ELSE 'floor_unknown'
                          END AS floor_name,
                          m.location_id AS building_id
                        FROM {task_cfg['table_name']} t
                        JOIN {management_cfg['table_name']} m
                          ON m.robot_sn = t.robot_sn
                        WHERE t.map_name IS NOT NULL
                          AND TRIM(t.map_name) <> ''
                          AND m.location_id IS NOT NULL
                          AND NOT EXISTS (
                            SELECT 1
                            FROM {floor_cfg['table_name']} f
                            WHERE LOWER(TRIM(f.robot_map_name)) = LOWER(TRIM(t.map_name))
                              AND f.building_id = m.location_id
                          );
                    """

                    floor_table.cursor.execute(sql)
                    floor_table.cursor.connection.commit()
                    success_ops += 1
                    logger.info(f"✅ Backfilled floor info in {db_name}.{floor_cfg['table_name']} from {task_cfg['table_name']}")

                    floor_table.close()
                except Exception as e:
                    logger.error(f"❌ Failed floor info backfill for {db_name}: {e}")
                    continue

            if success_ops == 0:
                logger.info("Floor info backfill: no applicable databases found")
            return True

        except Exception as e:
            logger.error(f"Error during floor info backfill: {e}")
            return False

    def _filter_mappings_for_database(self, resolved_mappings: pd.DataFrame, work_location_data: pd.DataFrame, target_robots: List[str]) -> pd.DataFrame:
        """
        Filter resolved mappings to only include maps used by robots in the target database

        Args:
            resolved_mappings (pd.DataFrame): All resolved mappings
            work_location_data (pd.DataFrame): Robot work location data
            target_robots (List[str]): Robot SNs that belong to this database

        Returns:
            pd.DataFrame: Filtered mappings relevant to this database
        """
        if resolved_mappings.empty or not target_robots:
            return pd.DataFrame()

        # Get maps used by robots in this database
        maps_used_by_target_robots = work_location_data[
            (work_location_data['robot_sn'].isin(target_robots)) &
            (work_location_data['status'] == 'normal') &
            (work_location_data['map_name'].notna())
        ]['map_name'].unique().tolist()

        # Filter resolved mappings to only include maps used by target robots
        filtered_mappings = resolved_mappings[
            resolved_mappings['map_name'].isin(maps_used_by_target_robots)
        ].copy()

        logger.debug(f"Filtered {len(filtered_mappings)} mappings for {len(target_robots)} robots using maps: {maps_used_by_target_robots}")
        return filtered_mappings

    def run_work_location_updates(self) -> bool:
        """
        Run all work location related updates with dynamic database resolution

        Returns:
            bool: True if all updates completed successfully, False if any failures occurred

        Process:
            1. Calls get_robot_work_location_and_mapping_data() to get current robot states
            2. Applies coordinate transformations for supported databases
            3. Updates mnt_robots_work_location tables across all relevant project databases (APPEND mode)
            4. Runs archival process to maintain 24h/1000 record limits per robot
            5. Resolves and updates mnt_robot_map_floor_mapping tables
            6. Handles cleanup and error reporting
        """
        logger.info("🚀 Starting dynamic work location updates with archival...")

        try:
            # Update both robot work locations and map floor mappings efficiently
            success = self.update_robot_work_locations_and_mappings()

            if success:
                logger.info("✅ Dynamic work location updates with archival completed successfully")
            else:
                logger.warning("⚠️ Dynamic work location updates completed with some failures")

            return success

        except Exception as e:
            logger.error(f"💥 Critical error in dynamic work location updates: {e}")
            return False
        finally:
            self.config.close()