# src/pudu/app/main.py
from pudu.apis import get_schedule_table, get_charging_table, get_events_table, get_location_table, get_robot_status_table, get_ongoing_tasks_table
from pudu.rds import RDSTable
from pudu.notifications import send_change_based_notifications, detect_data_changes, NotificationService
from pudu.configs import DynamicDatabaseConfig
from pudu.services.task_management_service import TaskManagementService
from pudu.services.transform_service import TransformService
from pudu.rds.rdsTable import ConnectionManager
import logging
from typing import Dict, List
from datetime import datetime
import sys
import pandas as pd
import concurrent.futures
import threading

# Add src to Python path
sys.path.append('../')
# Configure logging
logger = logging.getLogger(__name__)


class App:
    """Main application with parallel API processing and dynamic database resolution"""
    def __init__(self, config_path: str = "database_config.yaml"):
        """Initialize the application with dynamic database configuration"""
        logger.info(f"Initializing App with config: {config_path}")
        self.config = DynamicDatabaseConfig(config_path)
        s3_config = self._load_s3_config(config_path)
        self.notification_service = NotificationService()
        self.transform_service = TransformService(self.config, s3_config)

        # Get all robots and their database mappings
        self.robot_db_mapping = self.config.resolver.get_robot_database_mapping()
        logger.info(f"Resolved {len(self.robot_db_mapping)} robot database mappings")

        # Group robots by database for efficient processing
        self.all_robots = list(self.robot_db_mapping.keys())
        self.db_to_robots = self.config.resolver.group_robots_by_database(self.all_robots)
        logger.info(f"Found robots in {len(self.db_to_robots)} databases: {list(self.db_to_robots.keys())}")

        # Test S3 connectivity for transform-supported databases
        self._test_s3_connectivity()

    def _load_s3_config(self, config_path: str) -> Dict:
        """Load S3 configuration from the database config file"""
        try:
            import yaml
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                s3_config = config.get('s3_config', {})

                if s3_config:
                    logger.info(f"Loaded S3 config: region={s3_config.get('region', 'us-east-2')}, "
                              f"buckets={len(s3_config.get('buckets', {}))}")
                else:
                    logger.warning("No S3 configuration found - transformed maps will not be uploaded")

                return s3_config

        except Exception as e:
            logger.error(f"Error loading S3 config: {e}")
            return {}

    def _test_s3_connectivity(self):
        """Test S3 connectivity for all configured databases"""
        if hasattr(self.transform_service, 's3_service') and self.transform_service.s3_service:
            logger.info("🔗 Testing S3 connectivity...")
            connectivity_results = self.transform_service.test_s3_connectivity()

            if connectivity_results:
                successful = sum(1 for status in connectivity_results.values() if status)
                total = len(connectivity_results)
                logger.info(f"S3 connectivity test: {successful}/{total} databases accessible")

                if successful < total:
                    failed_dbs = [db for db, status in connectivity_results.items() if not status]
                    logger.warning(f"S3 access issues for databases: {failed_dbs}")
            else:
                logger.warning("No S3 connectivity tests performed")
        else:
            logger.info("S3 service not configured - skipping connectivity test")

    def _fetch_all_api_data_parallel(self, start_time: str, end_time: str) -> Dict[str, any]:
        """
        Fetch all API data in parallel to reduce total API call time.
        This is the main optimization - instead of calling APIs sequentially,
        we call them all at once using ThreadPoolExecutor.
        """
        logger.info("🔄 Fetching all API data in parallel...")
        api_start_time = datetime.now()

        # Define all API calls with their parameters
        api_calls = {
            'robot_status': (get_robot_status_table, ()),
            'ongoing_tasks': (get_ongoing_tasks_table, ()),
            'schedule': (get_schedule_table, (start_time, end_time, None, None, 0)),
            'charging': (get_charging_table, (start_time, end_time, None, None, 0)),
            'events': (get_events_table, (start_time, end_time, None, None, None, None, 0))
        }

        api_data = {}

        # Use ThreadPoolExecutor to make all API calls simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="api_worker") as executor:
            # Submit all API calls
            future_to_name = {}
            for api_name, (api_func, args) in api_calls.items():
                future = executor.submit(api_func, *args)
                future_to_name[future] = api_name
                logger.debug(f"📡 Submitted API call for {api_name}")

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_name, timeout=60):
                api_name = future_to_name[future]
                try:
                    result = future.result()
                    api_data[api_name] = result
                    logger.info(f"✅ Completed API call for {api_name}: {len(result) if hasattr(result, '__len__') else 'N/A'} records")
                except Exception as e:
                    logger.error(f"❌ API call failed for {api_name}: {e}")
                    api_data[api_name] = pd.DataFrame()  # Empty DataFrame as fallback

        api_total_time = (datetime.now() - api_start_time).total_seconds()
        logger.info(f"🚀 All API calls completed in {api_total_time:.2f} seconds")

        return api_data

    def _get_robots_for_data(self, data_df, robot_sn_column='robot_sn'):
        """Extract robot SNs from data DataFrame"""
        if robot_sn_column in data_df.columns:
            return data_df[robot_sn_column].unique().tolist()
        return []

    def _initialize_tables_for_robots(self, table_type: str, robots: List[str]) -> tuple:
        """
        Initialize tables for specified robots.

        Args:
            table_type (str): Type of table to initialize (e.g., 'robot_status', 'robot_task', etc.)
            robots (List[str]): List of robot SNs to initialize tables for

        Returns:
            tuple: (success: bool, tables: List[RDSTable])
        """
        if not robots:
            logger.info(f"No robots provided for {table_type}")
            return True, []

        # Filter to only robots that exist in our mapping
        robots_in_mapping = [robot for robot in robots if robot in self.all_robots]

        if not robots_in_mapping:
            logger.info(f"No robots found in database mapping for {table_type}")
            return True, []

        # Get table configurations for these robots
        table_configs = self.config.get_table_configs_for_robots(table_type, robots_in_mapping)

        if not table_configs:
            logger.warning(f"No table configurations found for {table_type}")
            return False, []

        # Initialize tables
        tables = []
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
                table.target_robots = table_config.get('robot_sns', [])
                tables.append(table)
                logger.info(f"✅ Initialized {table_type} table: {table_config['database']}.{table_config['table_name']} for {len(table.target_robots)} robots")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {table_type} table {table_config['database']}.{table_config['table_name']}: {e}")

        if tables:
            return True, tables
        else:
            return False, []

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

    def _insert_to_database_with_filtering(self, data_df, tables: List[RDSTable], table_type: str, robot_sn_column='robot_sn'):
        """Insert data to databases with robot filtering and change detection"""
        if data_df.empty:
            logger.warning(f"No data to insert into {table_type} tables")
            return 0, 0, {}

        successful_inserts = 0
        failed_inserts = 0
        all_changes = {}

        for table in tables:
            try:
                # Filter data for robots that belong to this database
                target_robots = getattr(table, 'target_robots', [])
                if target_robots:
                    table_data = data_df[data_df[robot_sn_column].isin(target_robots)].copy()
                else:
                    table_data = data_df.copy()

                if table_data.empty:
                    logger.info(f"ℹ️ No relevant data for {table.database_name}.{table.table_name}")
                    successful_inserts += 1  # Count as successful since no data needed
                    continue

                # Prepare data for insertion
                data_list = table_data.to_dict(orient='records')

                # Detect changes before insertion
                changes = detect_data_changes(table, data_list, table.primary_keys)

                if changes:
                    # extract the 'new_values' from changes_detected which only contains the fields that are in the table
                    # do not use data_list, because it can contain new fields that are not in the table
                    changed_records = []
                    for change_info in changes.values():
                        changed_records.append(change_info['new_values'])
                    # insert the changed records and get the ids (formatted as (original_data_dict, unique_key_in_db))
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

                    successful_inserts += 1
                    logger.info(f"✅ Successfully inserted {len(data_list)} records into {table.database_name}.{table.table_name}")
                    all_changes[tuple([table.database_name, table.table_name])] = changes
                else:
                    logger.info(f"ℹ️ No changes detected for {table.database_name}.{table.table_name}, skipping insert")
                    successful_inserts += 1

            except Exception as e:
                failed_inserts += 1
                error_message = str(e).lower()

                # Categorize different types of errors
                if any(keyword in error_message for keyword in ['table', 'not exist', 'doesn\'t exist']):
                    logger.error(f"❌ Table missing: {table.database_name}.{table.table_name} - {e}")
                elif any(keyword in error_message for keyword in ['column', 'field']):
                    logger.error(f"❌ Schema mismatch: {table.database_name}.{table.table_name} - {e}")
                elif any(keyword in error_message for keyword in ['connection', 'timeout', 'network']):
                    logger.error(f"❌ Connection error: {table.database_name}.{table.table_name} - {e}")
                elif any(keyword in error_message for keyword in ['permission', 'access', 'denied']):
                    logger.error(f"❌ Permission error: {table.database_name}.{table.table_name} - {e}")
                else:
                    logger.error(f"❌ Unknown error inserting into {table.database_name}.{table.table_name}: {e}")

        return successful_inserts, failed_inserts, all_changes

    def _process_location_data(self):
        """
        Process location data with proper project_id-based routing

        New Logic Flow:

        Step 1: Process Main Database (ry-vue)

        Update: If building_id exists but building_name changed → update building_name
        Insert: If building_id doesn't exist → insert with project_id = NULL (unassigned)
        Uses change detection to track what actually changed


        Step 2: Get Enriched Data

        Query main database to get all buildings WITH project assignments
        Join with pro_project_info to get project_name (database name)
        Only includes buildings that have been assigned to projects AND those queried from get_location_table()
        Later when buildings are assigned projects in the main database, they will be distributed to project databases automatically


        Step 3: Process Project Databases

        Group buildings by project_name (target database)
        For each project database, only process buildings that belong to that project
        Only update existing records - no new inserts since new buildings start unassigned
        Use change detection to avoid unnecessary updates
        """
        logger.info("📋 Processing location data...")
        try:
            # Get location data from API (building_id, building_name)
            raw_data = get_location_table()
            processed_data = self._prepare_df_for_database(raw_data)
            building_ids = processed_data['building_id'].unique().tolist()

            if processed_data.empty:
                logger.info("No location data to process")
                return 0, 0, {}

            total_successful = 0
            total_failed = 0
            all_changes = {}

            # Step 1: Update/insert to main database (ry-vue) first
            main_successful, main_failed, main_changes = self._process_main_database_locations(processed_data)
            total_successful += main_successful
            total_failed += main_failed
            all_changes.update(main_changes)

            # Step 2: Get enriched location data with project_id from main database
            enriched_location_data = self._get_enriched_location_data(building_ids=building_ids)

            # Step 3: Route to appropriate project databases based on project_id
            if not enriched_location_data.empty:
                project_successful, project_failed, project_changes = self._process_project_database_locations(enriched_location_data)
                total_successful += project_successful
                total_failed += project_failed
                all_changes.update(project_changes)
            return total_successful, total_failed, all_changes

        except Exception as e:
            logger.error(f"Error processing location data: {e}")
            return 0, 1, {}

    def _process_main_database_locations(self, processed_data):
        """Update/insert location data in main database (ry-vue)"""
        try:
            # Get main database table configuration
            main_configs = [config for config in self.config.get_all_table_configs('main_building_info')
                           if config['database'] == self.config.main_database_name]

            if not main_configs:
                logger.warning("No main database building info table configuration found")
                return 0, 1, {}

            main_config = main_configs[0]

            # Initialize main database table
            main_table = RDSTable(
                connection_config="credentials.yaml",
                database_name=main_config['database'],
                table_name=main_config['table_name'],
                fields=main_config.get('fields'),
                primary_keys=main_config['primary_keys'],
                reuse_connection=True
            )

            # Use change detection for main database updates
            data_list = processed_data.to_dict(orient='records')

            # Use existing change detection logic
            changes = detect_data_changes(main_table, data_list, main_config['primary_keys'])

            successful_inserts = 0
            failed_inserts = 0
            all_changes = {}

            if changes:
                main_table.batch_insert(data_list)
                successful_inserts += 1
                logger.info(f"✅ Successfully processed location data in main database")
                # Format changes for notification system
                table_key = tuple([main_config['database'], main_config['table_name']])
                all_changes[table_key] = changes
            else:
                logger.info(f"ℹ️ No changes detected for main database location data")

            # Close main database connection
            main_table.close() # This will NOT actually close the pooled connection

            return successful_inserts, failed_inserts, all_changes

        except Exception as e:
            logger.error(f"Error processing main database locations: {e}")
            return 0, 1, {}

    def _get_enriched_location_data(self, building_ids):
        """Get location data enriched with project_id and project_name from main database ONLY for those from get_location_table()"""
        try:
            # Get main database configuration
            main_configs = [config for config in self.config.get_all_table_configs('main_building_info')
                           if config['database'] == self.config.main_database_name]

            if not main_configs:
                logger.warning("No main database configuration found for enriched location data")
                return pd.DataFrame()

            main_config = main_configs[0]

            # Initialize main database table
            main_table = RDSTable(
                connection_config="credentials.yaml",
                database_name=main_config['database'],
                table_name=main_config['table_name'],
                fields=main_config.get('fields'),
                primary_keys=main_config['primary_keys'],
                reuse_connection=True
            )

            # Query all buildings with project assignments
            query = f"""
            SELECT b.building_id, b.building_name, b.project_id, p.project_name
            FROM {main_table.table_name} b
            JOIN pro_project_info p ON b.project_id = p.project_id
            WHERE b.project_id IS NOT NULL AND b.building_id IN ({','.join(building_ids)})
            """

            results = main_table.query_data(query)

            enriched_data = []
            for result in results:
                if isinstance(result, tuple) and len(result) >= 4:
                    building_id, building_name, project_id, project_name = result[0], result[1], result[2], result[3]
                elif isinstance(result, dict):
                    building_id = result.get('building_id')
                    building_name = result.get('building_name')
                    project_id = result.get('project_id')
                    project_name = result.get('project_name')
                else:
                    continue

                if building_id and building_name and project_id and project_name:
                    enriched_data.append({
                        'building_id': building_id,
                        'building_name': building_name,
                        'project_id': project_id,
                        'project_name': project_name
                    })

            main_table.close() # This will NOT actually close the pooled connection

            enriched_df = pd.DataFrame(enriched_data)
            logger.info(f"Retrieved {len(enriched_df)} buildings with project assignments for distribution to project databases")
            return enriched_df

        except Exception as e:
            logger.error(f"Error getting enriched location data: {e}")
            return pd.DataFrame()

    def _process_project_database_locations(self, enriched_location_data):
        """Process location data in project databases - only update existing records based on project_id match"""
        try:
            successful_inserts = 0
            failed_inserts = 0
            all_changes = {}

            # Group enriched data by project_name (database)
            grouped_by_project = enriched_location_data.groupby('project_name')

            for project_name, project_buildings in grouped_by_project:
                try:
                    logger.info(f"Processing {len(project_buildings)} buildings for project database: {project_name}")

                    # Get table configuration for this project database
                    project_configs = [config for config in self.config.get_all_table_configs('location')
                                     if config['database'] == project_name]

                    if not project_configs:
                        logger.warning(f"No location table configuration found for project database: {project_name}")
                        # failed_inserts += 1
                        continue

                    project_config = project_configs[0]

                    # Initialize project database table
                    project_table = RDSTable(
                        connection_config="credentials.yaml",
                        database_name=project_config['database'],
                        table_name=project_config['table_name'],
                        fields=project_config.get('fields'),
                        primary_keys=project_config['primary_keys'],
                        reuse_connection=True
                    )

                    # Prepare data for batch processing
                    project_data_list = []
                    for _, building_row in project_buildings.iterrows():
                        project_data_list.append({
                            'building_id': building_row['building_id'],
                            'building_name': building_row['building_name'],
                            'project_id': building_row['project_id']
                        })

                    # Use change detection for this project database
                    if project_data_list:
                        changes = detect_data_changes(project_table, project_data_list, project_config['primary_keys'])

                        if changes:
                            project_table.batch_insert(project_data_list)
                            successful_inserts += 1
                            logger.info(f"✅ Successfully processed {len(project_data_list)} buildings in project database {project_name}")

                            # Track changes for notifications
                            table_key = tuple([project_config['database'], project_config['table_name']])
                            all_changes[table_key] = changes
                        else:
                            logger.info(f"ℹ️ No changes detected for project database {project_name}")

                    # Close project database connection
                    project_table.close()

                except Exception as e:
                    logger.error(f"Error processing project database {project_name}: {e}")
                    failed_inserts += 1

            logger.info(f"Project database location processing: {successful_inserts} successful, {failed_inserts} failed")
            return successful_inserts, failed_inserts, all_changes

        except Exception as e:
            logger.error(f"Error processing project database locations: {e}")
            return 0, 1, {}

    def _process_ongoing_robot_tasks(self, table_type: str, ongoing_tasks_data):
        """
        Process ongoing robot tasks with complete upsert and cleanup logic.

        Logic:
        1. For robots with ongoing tasks from API: upsert (update existing or insert new)
        2. For robots without ongoing tasks from API: cleanup existing ongoing tasks in database
        3. Track all changes for notifications
        """
        logger.info("📋 Processing ongoing robot tasks (complete upsert with cleanup)...")

        try:
            processed_data = self._prepare_df_for_database(ongoing_tasks_data, columns_to_remove=['id', 'location_id'])

            # Get all robots that have data OR need cleanup
            robots_with_tasks = set()
            if not processed_data.empty:
                robots_with_tasks = self._get_robots_for_data(processed_data, 'robot_sn')

            logger.info(f"Robots with ongoing tasks from API: {len(robots_with_tasks)}")
            logger.info(f"Total monitored robots: {len(self.all_robots)}")

            # Initialize tables for all monitored robots (not just those with current tasks)
            success, tables = self._initialize_tables_for_robots(table_type, self.all_robots)
            if not success:
                logger.warning(f"No tables initialized for {table_type}")
                return 0, 1, {}
            elif len(tables) == 0:
                logger.warning(f"No need to initialize tables for {table_type}")
                return 0, 0, {}

            successful_operations = 0
            failed_operations = 0
            all_changes = {}

            for table in tables:
                try:
                    target_robots = getattr(table, 'target_robots', [])
                    if not target_robots:
                        logger.info(f"ℹ️ No target robots for {table.database_name}.{table.table_name}")
                        successful_operations += 1
                        continue

                    # Separate robots with tasks vs robots needing cleanup
                    table_robots_with_tasks = [robot for robot in target_robots if robot in robots_with_tasks]
                    table_robots_needing_cleanup = [robot for robot in target_robots if robot not in robots_with_tasks]

                    # Process robots with ongoing tasks
                    table_data = None
                    if table_robots_with_tasks and not processed_data.empty:
                        table_data = processed_data[processed_data['robot_sn'].isin(table_robots_with_tasks)].copy()

                    # Use TaskManagementService to handle complete ongoing task management
                    changes = TaskManagementService.manage_ongoing_tasks_complete(
                        table,
                        table_data.to_dict(orient='records') if table_data is not None and not table_data.empty else [],
                        table_robots_needing_cleanup
                    )

                    successful_operations += 1
                    logger.info(f"✅ Processed ongoing tasks for {table.database_name}.{table.table_name}")

                    # Track changes for notifications if any changes detected
                    if changes:
                        table_key = tuple([table.database_name, table.table_name])
                        all_changes[table_key] = changes

                    table.close()

                except Exception as e:
                    failed_operations += 1
                    logger.error(f"❌ Failed to process ongoing tasks for {table.database_name}.{table.table_name}: {e}")

            return successful_operations, failed_operations, all_changes

        except Exception as e:
            logger.error(f"Error processing ongoing robot tasks: {e}")
            return 0, 1, {}

    def _process_robot_data_with_prefetched(self, table_type: str, raw_data, robot_column: str, columns_to_remove: list = []):
        """Process robot-specific data with dynamic database routing - using pre-fetched data"""
        logger.info(f"📋 Processing {table_type} data...")

        try:
            processed_data = self._prepare_df_for_database(raw_data, columns_to_remove=columns_to_remove)

            if processed_data.empty:
                logger.info(f"No {table_type} data to process")
                return 0, 0, {}

            # Extract robots from the data
            robots_in_data = self._get_robots_for_data(processed_data, robot_column)

            # Initialize tables for robots in this data
            success, tables = self._initialize_tables_for_robots(table_type, robots_in_data)

            if not success:
                logger.warning(f"No tables initialized for {table_type}")
                return 0, 1, {}
            elif len(tables) == 0:
                logger.warning(f"No need to initialize tables for {table_type}")
                return 0, 0, {}

            # Insert data with robot filtering
            successful_inserts, failed_inserts, all_changes = self._insert_to_database_with_filtering(
                processed_data, tables, table_type, robot_column
            )

            # Close table connections
            for table in tables:
                try:
                    table.close()
                except:
                    pass

            return successful_inserts, failed_inserts, all_changes

        except Exception as e:
            logger.error(f"Error processing {table_type} data: {e}")
            return 0, 1, {}

    def _process_schedule_data_with_transforms(self, table_type: str, raw_data, robot_column: str, columns_to_remove: list = []):
        """Process schedule data with map transformations applied - with efficiency check"""
        logger.info(f"📋 Processing {table_type} data with map transformations...")

        try:
            processed_data = self._prepare_df_for_database(raw_data, columns_to_remove=columns_to_remove)

            if processed_data.empty:
                logger.info(f"No {table_type} data to process")
                return 0, 0, {}

            # NEW: Check existing new_map_url values to avoid redundant transformations
            filtered_data = self._filter_tasks_needing_transformation(processed_data)

            if filtered_data.empty:
                logger.info("All tasks already have transformed maps, skipping transformation")
                # Process data without transformation - don't add new_map_url column
                robots_in_data = self._get_robots_for_data(processed_data, robot_column)
                success, tables = self._initialize_tables_for_robots(table_type, robots_in_data)

                if not success or len(tables) == 0:
                    return 0, 0, {}

                successful_inserts, failed_inserts, all_changes = self._insert_to_database_with_filtering(
                    processed_data, tables, table_type, robot_column
                )

                for table in tables:
                    try:
                        table.close()
                    except:
                        pass

                return successful_inserts, failed_inserts, all_changes

            # Apply map transformations only to tasks that need them
            logger.info(f"🔧 Applying map transformations to {len(filtered_data)} tasks (out of {len(processed_data)} total)...")
            transformed_subset = self.transform_service.transform_task_maps_batch(filtered_data)

            # Use original processed_data and only update new_map_url for transformed tasks
            tasks_with_urls, tasks_without_urls = self._update_with_transformed_urls(processed_data, transformed_subset)

            # Process both groups separately to avoid NULL inserts
            all_changes = {}
            successful_inserts = 0
            failed_inserts = 0

            # Extract robots from all data
            all_robots = self._get_robots_for_data(processed_data, robot_column)
            success, tables = self._initialize_tables_for_robots(table_type, all_robots)

            if not success or len(tables) == 0:
                logger.warning(f"No tables initialized for {table_type}")
                return 0, 1, {}

            # Process tasks with transformed URLs (includes new_map_url column)
            if not tasks_with_urls.empty:
                logger.info(f"Processing {len(tasks_with_urls)} tasks with transformed URLs")
                s1, f1, c1 = self._insert_to_database_with_filtering(
                    tasks_with_urls, tables, table_type, robot_column
                )
                successful_inserts += s1
                failed_inserts += f1
                all_changes.update(c1)

            # Process tasks without URLs (no new_map_url column - preserves existing DB values)
            if not tasks_without_urls.empty:
                logger.info(f"Processing {len(tasks_without_urls)} tasks without transformed URLs")
                s2, f2, c2 = self._insert_to_database_with_filtering(
                    tasks_without_urls, tables, table_type, robot_column
                )
                successful_inserts += s2
                failed_inserts += f2
                all_changes.update(c2)

            # Log transformation results
            total_count = len(processed_data)
            transformed_count = len(filtered_data)
            logger.info(f"Map transformation: {transformed_count}/{total_count} tasks processed")

            # Close table connections
            for table in tables:
                try:
                    table.close()
                except:
                    pass

            return successful_inserts, failed_inserts, all_changes

        except Exception as e:
            logger.error(f"Error processing {table_type} data with transforms: {e}")
            return 0, 1, {}

    def _filter_tasks_needing_transformation(self, processed_data):
        """
        Filter tasks that need map transformation by checking existing new_map_url values in database

        Returns:
            pd.DataFrame: Tasks that need transformation (no existing valid new_map_url)
        """
        tasks_needing_transform = []

        # Get robots from the data to determine which tables to check
        robots_in_data = self._get_robots_for_data(processed_data, 'robot_sn')

        # Get table configurations for these robots
        table_configs = self.config.get_table_configs_for_robots('robot_task', robots_in_data)

        # Check each task against database
        for _, task_row in processed_data.iterrows():
            robot_sn = task_row['robot_sn']
            task_name = task_row['task_name']
            start_time = task_row['start_time']
            map_url = task_row.get('map_url', '')

            # Skip if no map_url (basic filtering)
            if not map_url or not map_url.startswith('https://'):
                continue

            needs_transform = True

            # Check if this task already has a valid new_map_url in any relevant database
            for table_config in table_configs:
                target_robots = table_config.get('robot_sns', [])
                if robot_sn not in target_robots:
                    continue

                try:
                    table = RDSTable(
                        connection_config="credentials.yaml",
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys'],
                        reuse_connection=True
                    )

                    # Query for existing new_map_url
                    query = f"""
                        SELECT new_map_url FROM {table.table_name}
                        WHERE robot_sn = '{robot_sn}'
                        AND task_name = '{task_name}'
                        AND start_time = '{start_time}'
                        AND new_map_url IS NOT NULL
                        AND new_map_url != ''
                        AND new_map_url LIKE 'https://%'
                        LIMIT 1
                    """

                    result = table.query_data(query)
                    table.close()

                    if result:
                        # Task already has transformed map URL
                        needs_transform = False
                        logger.debug(f"Task {task_name} for robot {robot_sn} already has transformed map")
                        break

                except Exception as e:
                    logger.debug(f"Error checking existing new_map_url for {robot_sn}: {e}")
                    continue

            if needs_transform:
                tasks_needing_transform.append(task_row)

        return pd.DataFrame(tasks_needing_transform) if tasks_needing_transform else pd.DataFrame()

    def _update_with_transformed_urls(self, original_data, transformed_subset):
        """
        Safely update original data with new_map_url only for transformed tasks

        Args:
            original_data: Full dataset (NO new_map_url column)
            transformed_subset: Subset that was transformed (HAS new_map_url column)

        Returns:
            pd.DataFrame: Original data with new_map_url column added ONLY for rows that actually have URLs
        """
        # Create a copy of original data
        result_data = original_data.copy()

        # Only process if we have transformed data with URLs
        if not transformed_subset.empty and 'new_map_url' in transformed_subset.columns:
            # Create a mapping of transformed URLs
            transformed_urls = {}

            for _, transformed_row in transformed_subset.iterrows():
                robot_sn = transformed_row['robot_sn']
                task_name = transformed_row['task_name']
                start_time = transformed_row['start_time']
                new_map_url = transformed_row.get('new_map_url', '')

                # Only store valid transformed URLs
                if new_map_url and new_map_url.startswith('https://'):
                    key = (robot_sn, task_name, start_time)
                    transformed_urls[key] = new_map_url

            # Only add new_map_url column if we have valid URLs to add
            if transformed_urls:
                # Add new_map_url column and populate only for transformed tasks
                result_data['new_map_url'] = result_data.apply(
                    lambda row: transformed_urls.get(
                        (row['robot_sn'], row['task_name'], row['start_time']),
                        None
                    ),
                    axis=1
                )

                # Remove rows where new_map_url is None to avoid NULL inserts
                # Split into two groups: with URLs and without URLs
                tasks_with_urls = result_data[result_data['new_map_url'].notna()].copy()
                tasks_without_urls = result_data[result_data['new_map_url'].isna()].copy()

                # Remove new_map_url column from tasks without URLs
                if not tasks_without_urls.empty:
                    tasks_without_urls = tasks_without_urls.drop(columns=['new_map_url'])

                # Combine back - this ensures new_map_url column only exists where there are actual URLs
                if not tasks_with_urls.empty and not tasks_without_urls.empty:
                    # Need to handle different column sets
                    return tasks_with_urls, tasks_without_urls
                elif not tasks_with_urls.empty:
                    return tasks_with_urls, pd.DataFrame()
                else:
                    return pd.DataFrame(), tasks_without_urls

        # No transformation needed, return original data as-is
        return result_data, pd.DataFrame()

    def run(self, start_time: str, end_time: str):
        """Run the dynamic data pipeline with parallel API processing"""
        pipeline_start = datetime.now()
        logger.info(f"🚀 Starting PARALLEL API data pipeline for period: {start_time} to {end_time}")

        # Log connection pool status at start
        pool_status = ConnectionManager.get_pool_status()
        logger.info(f"🔗 Connection pool status at start: {pool_status}")

        pipeline_stats = {
            'total_successful_inserts': 0,
            'total_failed_inserts': 0,
            'total_successful_notifications': 0,
            'total_failed_notifications': 0,
        }

        try:
            # STEP 1: Fetch all API data in parallel (NEW OPTIMIZATION)
            logger.info("=" * 50)
            logger.info("🔄 PARALLEL API FETCH PHASE")
            logger.info("=" * 50)

            api_data = self._fetch_all_api_data_parallel(start_time, end_time)

            # STEP 2: Process each data type using pre-fetched data
            logger.info("=" * 50)
            logger.info("🔄 DATA PROCESSING PHASE")
            logger.info("=" * 50)

            # 1.1. Location data (special case)
            # successful, failed, changes = self._process_location_data()
            # pipeline_stats['total_successful_inserts'] += successful
            # pipeline_stats['total_failed_inserts'] += failed
            # self._handle_notifications(changes, 'location', pipeline_stats)

            # 1. Robot status data
            if api_data.get('robot_status') is not None and not api_data['robot_status'].empty:
                successful, failed, changes = self._process_robot_data_with_prefetched(
                    'robot_status', api_data['robot_status'], 'robot_sn', columns_to_remove=['id', 'location_id']
                )
                pipeline_stats['total_successful_inserts'] += successful
                pipeline_stats['total_failed_inserts'] += failed
                self._handle_notifications(changes, 'robot_status', pipeline_stats)
            else:
                logger.info("ℹ️ No robot status data to process")

            logger.info("=" * 50)

            # 2. Ongoing task data
            if api_data.get('ongoing_tasks') is not None and not api_data['ongoing_tasks'].empty:
                successful, failed, changes = self._process_ongoing_robot_tasks('robot_task', api_data['ongoing_tasks'])
                pipeline_stats['total_successful_inserts'] += successful
                pipeline_stats['total_failed_inserts'] += failed
                self._handle_notifications(changes, 'robot_task', pipeline_stats)
            else:
                logger.info("ℹ️ No ongoing tasks data to process")

            logger.info("=" * 50)

            # 3. Report task data WITH MAP TRANSFORMATIONS
            if api_data.get('schedule') is not None and not api_data['schedule'].empty:
                successful, failed, changes = self._process_schedule_data_with_transforms(
                    'robot_task', api_data['schedule'], 'robot_sn', columns_to_remove=['id', 'location_id']
                )
                pipeline_stats['total_successful_inserts'] += successful
                pipeline_stats['total_failed_inserts'] += failed
                self._handle_notifications(changes, 'robot_task', pipeline_stats, start_time, end_time)
            else:
                logger.info("ℹ️ No schedule data to process")

            logger.info("=" * 50)

            # 4. Robot charging data
            if api_data.get('charging') is not None and not api_data['charging'].empty:
                successful, failed, changes = self._process_robot_data_with_prefetched(
                    'robot_charging', api_data['charging'], 'robot_sn', columns_to_remove=['id', 'location_id']
                )
                pipeline_stats['total_successful_inserts'] += successful
                pipeline_stats['total_failed_inserts'] += failed
                self._handle_notifications(changes, 'robot_charging', pipeline_stats, start_time, end_time)
            else:
                logger.info("ℹ️ No charging data to process")

            logger.info("=" * 50)

            # 5. Robot events data
            if api_data.get('events') is not None and not api_data['events'].empty:
                successful, failed, changes = self._process_robot_data_with_prefetched(
                    'robot_events', api_data['events'], 'robot_sn', columns_to_remove=['id', 'location_id']
                )
                pipeline_stats['total_successful_inserts'] += successful
                pipeline_stats['total_failed_inserts'] += failed
                self._handle_notifications(changes, 'robot_events', pipeline_stats, start_time, end_time)
            else:
                logger.info("ℹ️ No events data to process")

            logger.info("=" * 50)

            # 6. Robot work location data WITH COORDINATE TRANSFORMATIONS
            from pudu.services.work_location_service import WorkLocationService
            work_location_service = WorkLocationService()
            work_location_success = work_location_service.run_work_location_updates()

            # Calculate execution time and print summary
            pipeline_end = datetime.now()
            execution_time = (pipeline_end - pipeline_start).total_seconds()

            # Log final connection pool status
            final_pool_status = ConnectionManager.get_pool_status()
            logger.info(f"🔗 Connection pool status at end: {final_pool_status}")

            logger.info("=" * 60)
            logger.info("📊 PARALLEL API PIPELINE EXECUTION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Execution time: {execution_time:.2f} seconds")
            logger.info(f"✅ Total successful inserts: {pipeline_stats['total_successful_inserts']}")
            logger.info(f"❌ Total failed inserts: {pipeline_stats['total_failed_inserts']}")
            logger.info(f"📧 Total successful notifications: {pipeline_stats['total_successful_notifications']}")
            logger.info(f"📧 Total failed notifications: {pipeline_stats['total_failed_notifications']}")
            logger.info(f"🗺️ Work location updates success: {work_location_success}")
            logger.info(f"🔗 Active database connections: {pool_status['active_connections']}")

            success = pipeline_stats['total_failed_inserts'] == 0 and work_location_success == True
            if success:
                logger.info("✅ Parallel API Lambda service completed successfully")
            else:
                logger.warning("⚠️ Parallel API Lambda service completed with some failures")

            return success

        except Exception as e:
            logger.error(f"💥 Critical error in parallel API data pipeline: {e}", exc_info=True)
            raise
        finally:
            # IMPORTANT: Close all connections at the end of Lambda execution
            # This ensures clean state for next invocation while allowing reuse during execution
            logger.info("🔒 Closing all pooled connections...")
            ConnectionManager.close_all_connections()

            # Close resolver connection
            self.config.close()

    def _handle_notifications(self, changes: Dict, table_type: str, pipeline_stats: Dict, start_time: str = None, end_time: str = None):
        """Handle notifications for changes"""
        logger.info(f"📧 Handling notifications for {table_type} changes...")
        if not changes:
            logger.info(f"No changes detected for {table_type}, skipping notifications")
            return
        notification_databases = self.config.get_notification_databases()
        for (database_name, table_name), change_data in changes.items():
            if database_name in notification_databases:
                try:
                    time_range = f"{start_time} to {end_time}" if start_time and end_time else None
                    notif_success, notif_failed = send_change_based_notifications(
                        self.notification_service, database_name, table_name, change_data, table_type,
                        time_range=time_range
                    )
                    pipeline_stats['total_successful_notifications'] += notif_success
                    pipeline_stats['total_failed_notifications'] += notif_failed
                except Exception as e:
                    logger.error(f"Error sending notifications for {database_name}.{table_name}: {e}")
                    pipeline_stats['total_failed_notifications'] += 1

# Example usage:
if __name__ == "__main__":
    import os
    # Get configuration file path - try multiple locations
    config_paths = [
        'database_config.yaml',
        '../src/pudu/configs/database_config.yaml',
        'src/pudu/configs/database_config.yaml',
        'pudu/configs/database_config.yaml',
        '/opt/database_config.yaml'
    ]

    config_path = None
    for path in config_paths:
        if os.path.exists(path):
            config_path = path
            break
    if not config_path:
        raise FileNotFoundError("Configuration file not found")

    # Initialize app
    app = App(config_path=config_path)

    # Run parallel API pipeline
    app.run(start_time="2025-06-01 00:00:00", end_time="2025-12-01 00:00:00")