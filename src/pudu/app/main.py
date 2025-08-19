from pudu.apis import get_schedule_table, get_charging_table, get_events_table, get_location_table, get_robot_status_table, get_ongoing_tasks_table
from pudu.rds import RDSTable
from pudu.notifications import send_change_based_notifications, detect_data_changes, NotificationService
from pudu.configs import DynamicDatabaseConfig
from pudu.services.task_management_service import TaskManagementService
import logging
from typing import Dict, List
from datetime import datetime
import sys
import pandas as pd

# Add src to Python path
sys.path.append('../')
# Configure logging
logger = logging.getLogger(__name__)


class App:
    """Main application with dynamic database resolution and work location functionality"""
    def __init__(self, config_path: str = "database_config.yaml"):
        """Initialize the application with dynamic database configuration"""
        logger.info(f"Initializing App with config: {config_path}")
        self.config = DynamicDatabaseConfig(config_path)
        self.notification_service = NotificationService()

        # Get all robots and their database mappings
        self.robot_db_mapping = self.config.resolver.get_robot_database_mapping()
        logger.info(f"Resolved {len(self.robot_db_mapping)} robot database mappings")

        # Group robots by database for efficient processing
        self.all_robots = list(self.robot_db_mapping.keys())
        self.db_to_robots = self.config.resolver.group_robots_by_database(self.all_robots)
        logger.info(f"Found robots in {len(self.db_to_robots)} databases: {list(self.db_to_robots.keys())}")

    def _get_robots_for_data(self, data_df, robot_sn_column='robot_sn'):
        """Extract robot SNs from data DataFrame"""
        if robot_sn_column in data_df.columns:
            return data_df[robot_sn_column].unique().tolist()
        return []

    def _initialize_tables_for_data(self, table_type: str, data_df, robot_sn_column='robot_sn') -> List[RDSTable]:
        """Initialize tables for specific data, only for databases that have relevant robots"""
        if data_df.empty:
            return True, []

        robots_in_data = self._get_robots_for_data(data_df, robot_sn_column)
        # only get table configs for robots that exist in the data
        # since we call apis for all robots, we need to filter out the robots that do not exist in the database
        robots_in_data = [robot for robot in robots_in_data if robot in self.all_robots]
        if len(robots_in_data) == 0:
            return True, []
        table_configs = self.config.get_table_configs_for_robots(table_type, robots_in_data)

        tables = []
        for table_config in table_configs:
            try:
                table = RDSTable(
                    connection_config="credentials.yaml",
                    database_name=table_config['database'],
                    table_name=table_config['table_name'],
                    fields=table_config.get('fields'),
                    primary_keys=table_config['primary_keys']
                )
                table.target_robots = table_config.get('robot_sns', [])  # Store which robots this table serves
                tables.append(table)
                logger.info(f"✅ Initialized {table_type} table: {table_config['database']}.{table_config['table_name']} for {len(table.target_robots)} robots")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {table_type} table {table_config['database']}.{table_config['table_name']}: {e}")

        if len(tables) > 0:
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
                    # extract the 'new_values' from changes_detected which contains the original records
                    # do not use data_list, because it can contain some original records
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
        """Process location data with proper project_id-based routing

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
                primary_keys=main_config['primary_keys']
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
            main_table.close()

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
                primary_keys=main_config['primary_keys']
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

            main_table.close()

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
                        primary_keys=project_config['primary_keys']
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

    def _process_ongoing_robot_tasks(self, table_type: str):
        """Process ongoing robot tasks with simple upsert logic and change tracking"""
        logger.info("📋 Processing ongoing robot tasks (simple upsert with change tracking)...")

        try:
            # Get ongoing tasks data
            raw_data = get_ongoing_tasks_table()
            processed_data = self._prepare_df_for_database(raw_data, columns_to_remove=['id', 'location_id'])

            if processed_data.empty:
                logger.info("No ongoing tasks from API - will clean up existing ongoing tasks")
                return 0, 0, {}

            # Initialize tables for robots in this data
            success, tables = self._initialize_tables_for_data(table_type, processed_data, robot_sn_column='robot_sn')
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
                    # Filter data to only include robots in target_robots
                    if target_robots:
                        table_data = processed_data[processed_data['robot_sn'].isin(target_robots)].copy()
                    else:
                        table_data = processed_data.copy()

                    if table_data.empty:
                        logger.info(f"ℹ️ No relevant data for {table.database_name}.{table.table_name}")
                        successful_operations += 1  # Count as successful since no data needed
                        continue

                    # Convert to list of dicts
                    data_list = table_data.to_dict(orient='records')

                    # Use TaskManagementService to handle simple upsert logic with change tracking
                    changes = TaskManagementService.upsert_ongoing_tasks(table, data_list)

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

    def _process_robot_data(self, table_type: str, data_func, robot_column: str, start_time: str = None, end_time: str = None, columns_to_remove: list = []):
        """Process robot-specific data with dynamic database routing"""
        logger.info(f"📋 Processing {table_type} data...")

        try:
            # Get data
            if start_time and end_time:
                raw_data = data_func(start_time, end_time, timezone_offset=0)
            else:
                raw_data = data_func()

            processed_data = self._prepare_df_for_database(raw_data, columns_to_remove=columns_to_remove)

            if processed_data.empty:
                logger.info(f"No {table_type} data to process")
                return 0, 0, {}

            # Initialize tables for robots in this data
            success, tables = self._initialize_tables_for_data(table_type, processed_data, robot_column)

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

    def run(self, start_time: str, end_time: str):
        """Run the dynamic data pipeline"""
        pipeline_start = datetime.now()
        logger.info(f"🚀 Starting dynamic data pipeline for period: {start_time} to {end_time}")

        pipeline_stats = {
            'total_successful_inserts': 0,
            'total_failed_inserts': 0,
            'total_successful_notifications': 0,
            'total_failed_notifications': 0,
        }

        try:
            # Process each data type
            logger.info("=" * 50)

            # 1. Location data (special case)
            # successful, failed, changes = self._process_location_data()
            # pipeline_stats['total_successful_inserts'] += successful
            # pipeline_stats['total_failed_inserts'] += failed
            # self._handle_notifications(changes, 'location', pipeline_stats)

            # logger.info("=" * 50)

            # 2. Robot status data
            successful, failed, changes = self._process_robot_data(
                'robot_status', get_robot_status_table, 'robot_sn', columns_to_remove=['id', 'location_id']
            )
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed
            self._handle_notifications(changes, 'robot_status', pipeline_stats)

            logger.info("=" * 50)

            # 3. Robot task data
            # 3.1 Ongoing task data from get_ongoing_tasks_table
            successful, failed, changes = self._process_ongoing_robot_tasks('robot_task')
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed
            self._handle_notifications(changes, 'robot_task', pipeline_stats)

            logger.info("=" * 50)

            # 3.2 Report task data from get_schedule_table
            successful, failed, changes = self._process_robot_data(
                'robot_task', get_schedule_table, 'robot_sn', start_time, end_time, columns_to_remove=['id', 'location_id']
            )
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed
            self._handle_notifications(changes, 'robot_task', pipeline_stats, start_time, end_time)

            logger.info("=" * 50)

            # 4. Robot charging data
            successful, failed, changes = self._process_robot_data(
                'robot_charging', get_charging_table, 'robot_sn', start_time, end_time, columns_to_remove=['id', 'location_id']
            )
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed
            self._handle_notifications(changes, 'robot_charging', pipeline_stats, start_time, end_time)

            logger.info("=" * 50)

            # 5. Robot events data
            successful, failed, changes = self._process_robot_data(
                'robot_events', get_events_table, 'robot_sn', start_time, end_time, columns_to_remove=['id', 'location_id']
            )
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed
            self._handle_notifications(changes, 'robot_events', pipeline_stats, start_time, end_time)

            logger.info("=" * 50)

            # 6. Robot work location data
            from pudu.services.work_location_service import WorkLocationService
            work_location_service = WorkLocationService()
            work_location_success = work_location_service.run_work_location_updates()

            # Calculate execution time and print summary
            pipeline_end = datetime.now()
            execution_time = (pipeline_end - pipeline_start).total_seconds()

            logger.info("=" * 60)
            logger.info("📊 DYNAMIC PIPELINE EXECUTION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Execution time: {execution_time:.2f} seconds")
            logger.info(f"✅ Total successful inserts: {pipeline_stats['total_successful_inserts']}")
            logger.info(f"❌ Total failed inserts: {pipeline_stats['total_failed_inserts']}")
            logger.info(f"📧 Total successful notifications: {pipeline_stats['total_successful_notifications']}")
            logger.info(f"📧 Total failed notifications: {pipeline_stats['total_failed_notifications']}")
            logger.info(f"🗺️ Work location updates success: {work_location_success}")

            success = pipeline_stats['total_failed_inserts'] == 0 and work_location_success == True
            if success:
                logger.info("✅ Lambda service completed successfully")
            else:
                logger.warning("⚠️ Lambda service completed with some failures")

            return success

        except Exception as e:
            logger.error(f"💥 Critical error in dynamic data pipeline: {e}", exc_info=True)
            raise
        finally:
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

    # Run standard pipeline
    app.run(start_time="2025-06-01 00:00:00", end_time="2025-12-01 00:00:00")
