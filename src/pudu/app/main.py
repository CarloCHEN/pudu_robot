from pudu.apis import get_schedule_table, get_charging_table, get_task_overview_data, get_events_table, get_location_table, get_robot_status_table
from pudu.rds import RDSTable
from pudu.notifications import send_change_based_notifications, detect_data_changes, NotificationService
import yaml
import logging
from typing import Dict, List
from datetime import datetime
import sys

# Add src to Python path
sys.path.append('../')
# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuration manager for database and table specifications"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise ValueError(f"Error parsing YAML configuration: {e}")

    def get_table_configs(self) -> Dict[str, List[Dict]]:
        """Get all table configurations grouped by table type"""
        return self.config.get('tables', {})

    def get_databases(self) -> List[str]:
        """Get list of all databases"""
        return self.config.get('databases', [])

def initialize_tables_from_config(config: DatabaseConfig, table_type: str) -> List[RDSTable]:
    """Initialize RDS tables based on configuration for a specific table type"""
    tables = []
    table_configs = config.get_table_configs().get(table_type, [])

    logger.info(f"Initializing {len(table_configs)} {table_type} tables")

    for table_config in table_configs:
        try:
            table = RDSTable(
                connection_config="credentials.yaml",
                database_name=table_config['database'],
                table_name=table_config['table_name'],
                fields=table_config.get('fields'),
                primary_keys=table_config['primary_keys']
            )

            # Verify table exists
            if verify_table_exists(table, table_config):
                tables.append(table)
                logger.info(f"✅ Initialized {table_type} table: {table_config['database']}.{table_config['table_name']}")
            else:
                logger.warning(f"⚠️ Table not accessible: {table_config['database']}.{table_config['table_name']}")
                table.close()  # Close connection if table verification failed

        except Exception as e:
            logger.error(f"❌ Failed to initialize {table_type} table {table_config['database']}.{table_config['table_name']}: {e}")

    logger.info(f"Successfully initialized {len(tables)}/{len(table_configs)} {table_type} tables")
    return tables

def verify_table_exists(table: RDSTable, table_config: dict) -> bool:
    """Verify that a table exists and is accessible"""
    try:
        # Try to execute a simple query to check if table exists
        test_query = f"SELECT 1 FROM {table_config['table_name']} LIMIT 1"

        # If RDSTable has a method to execute queries, use it
        # Otherwise, we'll catch the error during actual insert
        data = table.query_data(test_query)
        if data:
            return True
        else:
            return False

    except Exception as e:
        logger.debug(f"Table verification failed for {table_config['database']}.{table_config['table_name']}: {e}")
        return False

def prepare_df_for_database(df, columns_to_remove=[]):
    """Prepare DataFrame for database insertion"""
    # Make a copy to avoid modifying the original
    processed_df = df.copy()
    processed_df.columns = [col.lower().replace(' ', '_') for col in processed_df.columns]

    # Remove columns that might conflict with database auto-generated fields
    for col in columns_to_remove:
        if col in processed_df.columns:
            processed_df.drop(columns=[col], inplace=True)

    logger.debug(f"Prepared DataFrame with {processed_df.shape[0]} rows and {processed_df.shape[1]} columns")
    return processed_df



def insert_to_databases_with_change_detection(df, tables: List[RDSTable], table_type: str):
    """Insert data to multiple database tables with change detection"""
    if df.shape[0] == 0:
        logger.warning(f"No data to insert into {table_type} tables")
        return 0, 0, {}

    # Prepare the data for insertion
    data_list = df.to_dict(orient='records')
    successful_inserts = 0
    failed_inserts = 0
    all_changes = {}

    logger.info(f"Inserting {len(data_list)} records to {len(tables)} {table_type} tables")

    # Insert the data into all configured tables
    for table in tables:
        try:
            # Detect changes before insertion
            changes = detect_data_changes(table, data_list, table.primary_keys)

            # Only proceed if there are actual changes
            if changes:
                table.batch_insert(data_list)
                successful_inserts += 1
                logger.info(f"✅ Successfully inserted {len(data_list)} records into {table.database_name}.{table.table_name}")

                # Merge changes from this table (use first table's changes as reference)
                if not all_changes:
                    all_changes = changes
            else:
                logger.info(f"ℹ️ No changes detected for {table.database_name}.{table.table_name}, skipping insert")
                successful_inserts += 1  # Count as successful since no changes needed

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

    # Summary
    total_tables = len(tables)
    logger.info(f"📊 {table_type} insert summary: {successful_inserts}/{total_tables} successful, {failed_inserts}/{total_tables} failed")

    # Warning if all inserts failed
    if successful_inserts == 0 and total_tables > 0:
        logger.warning(f"⚠️ WARNING: No data was successfully inserted to any {table_type} tables!")

    return successful_inserts, failed_inserts, all_changes



def get_location_data():
    """Fetch location data from API"""
    logger.info("Fetching location data")
    data = get_location_table()
    result = prepare_df_for_database(data, columns_to_remove=[])
    logger.info(f"Retrieved {result.shape[0]} location records")
    return result

def get_robot_status_data():
    """Fetch robot status data from API"""
    logger.info("Fetching robot status data")
    data = get_robot_status_table()
    result = prepare_df_for_database(data, columns_to_remove=[])
    logger.info(f"Retrieved {result.shape[0]} robot status records")
    return result

def get_robot_task_data(start_time: str, end_time: str):
    """Fetch robot task data from API"""
    logger.info(f"Fetching robot task data from {start_time} to {end_time}")
    data = get_schedule_table(start_time, end_time, timezone_offset=0)
    result = prepare_df_for_database(data, columns_to_remove=['id', 'location_id'])
    logger.info(f"Retrieved {result.shape[0]} robot task records")
    return result

def get_robot_task_overview_data(start_time: str, end_time: str):
    """Fetch robot task overview data from API"""
    logger.info(f"Fetching robot task overview data from {start_time} to {end_time}")
    data = get_task_overview_data(start_time, end_time, timezone_offset=0)
    result = prepare_df_for_database(data, columns_to_remove=['id', 'location_id'])
    logger.info(f"Retrieved {result.shape[0]} task overview records")
    return result

def get_robot_charging_data(start_time: str, end_time: str):
    """Fetch robot charging data from API"""
    logger.info(f"Fetching robot charging data from {start_time} to {end_time}")
    data = get_charging_table(start_time, end_time, timezone_offset=0)
    result = prepare_df_for_database(data, columns_to_remove=['id', 'location_id'])
    logger.info(f"Retrieved {result.shape[0]} charging records")
    return result

def get_robot_event_data(start_time: str, end_time: str):
    """Fetch robot event data from API"""
    logger.info(f"Fetching robot event data from {start_time} to {end_time}")
    data = get_events_table(start_time, end_time)
    result = prepare_df_for_database(data, columns_to_remove=['id', 'location_id'])
    logger.info(f"Retrieved {result.shape[0]} event records")
    return result

class App:
    def __init__(self, config_path: str = "database_config.yaml"):
        """Initialize the application with database configuration and notification service"""
        logger.info(f"Initializing App with config: {config_path}")
        self.config = DatabaseConfig(config_path)
        self.notification_service = NotificationService()

        # Initialize tables for each type
        self.location_tables = initialize_tables_from_config(self.config, 'location')
        self.robot_status_tables = initialize_tables_from_config(self.config, 'robot_status')
        self.task_tables = initialize_tables_from_config(self.config, 'robot_task')
        # IMPORTANT: Task overview data is not used for now
        # self.task_overview_tables = initialize_tables_from_config(self.config, 'robot_task_overview')
        self.charging_tables = initialize_tables_from_config(self.config, 'robot_charging')
        self.event_tables = initialize_tables_from_config(self.config, 'robot_events')

        # Log initialization summary
        config_summary = self.get_config_summary()
        logger.info(f"📊 Initialization complete: {config_summary['total_tables']} total tables across {len(config_summary['databases'])} databases")

    def run(self, start_time: str, end_time: str):
        """Run the data pipeline for the specified time range"""
        pipeline_start = datetime.now()
        logger.info(f"🚀 Starting data pipeline for period: {start_time} to {end_time}")

        # Track overall pipeline statistics
        pipeline_stats = {
            'total_successful_inserts': 0,
            'total_failed_inserts': 0,
            'total_successful_notifications': 0,
            'total_failed_notifications': 0,
        }

        try:
            # Fetch and insert location data
            logger.info("=" * 50)
            logger.info("📋 Processing location data...")
            location_data = get_location_data()
            successful, failed, changes = insert_to_databases_with_change_detection(location_data, self.location_tables, 'location')
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed

            # Send notifications only for actual changes
            if successful > 0 and changes:
                notif_success, notif_failed = send_change_based_notifications(
                    self.notification_service, changes, 'location'
                )
                pipeline_stats['total_successful_notifications'] += notif_success
                pipeline_stats['total_failed_notifications'] += notif_failed

            # Fetch and insert robot status data
            logger.info("=" * 50)
            logger.info("📋 Processing robot status data...")
            robot_status_data = get_robot_status_data()
            successful, failed, changes = insert_to_databases_with_change_detection(robot_status_data, self.robot_status_tables, 'robot_status')
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed

            # Send notifications only for actual changes
            if successful > 0 and changes:
                notif_success, notif_failed = send_change_based_notifications(
                    self.notification_service, changes, 'robot_status'
                )
                pipeline_stats['total_successful_notifications'] += notif_success
                pipeline_stats['total_failed_notifications'] += notif_failed

            # Fetch and insert task data
            logger.info("=" * 50)
            logger.info("📋 Processing robot task data...")
            task_data = get_robot_task_data(start_time, end_time)
            successful, failed, changes = insert_to_databases_with_change_detection(task_data, self.task_tables, 'robot_task')
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed

            # Send notifications only for actual changes
            if successful > 0 and changes:
                notif_success, notif_failed = send_change_based_notifications(
                    self.notification_service, changes, 'robot_task',
                    time_range=f"{start_time} to {end_time}"
                )
                pipeline_stats['total_successful_notifications'] += notif_success
                pipeline_stats['total_failed_notifications'] += notif_failed

            # IMPORTANT: Task overview data is not used for now
            # Fetch and insert task overview data
            # logger.info("=" * 50)
            # logger.info("📊 Processing robot task overview data...")
            # task_overview_data = get_robot_task_overview_data(start_time, end_time)
            # successful, failed, changes = insert_to_databases_with_change_detection(task_overview_data, self.task_overview_tables, 'robot_task_overview')
            # pipeline_stats['total_successful_inserts'] += successful
            # pipeline_stats['total_failed_inserts'] += failed

            # Fetch and insert charging data
            logger.info("=" * 50)
            logger.info("🔋 Processing robot charging data...")
            charging_data = get_robot_charging_data(start_time, end_time)
            successful, failed, changes = insert_to_databases_with_change_detection(charging_data, self.charging_tables, 'robot_charging')
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed

            # Send notifications only for actual changes
            if successful > 0 and changes:
                notif_success, notif_failed = send_change_based_notifications(
                    self.notification_service, changes, 'robot_charging',
                    time_range=f"{start_time} to {end_time}"
                )
                pipeline_stats['total_successful_notifications'] += notif_success
                pipeline_stats['total_failed_notifications'] += notif_failed

            # Fetch and insert event data
            logger.info("=" * 50)
            logger.info("🚨 Processing robot event data...")
            event_data = get_robot_event_data(start_time, end_time)
            successful, failed, changes = insert_to_databases_with_change_detection(event_data, self.event_tables, 'robot_events')
            pipeline_stats['total_successful_inserts'] += successful
            pipeline_stats['total_failed_inserts'] += failed

            # Send notifications only for actual changes
            if successful > 0 and changes:
                notif_success, notif_failed = send_change_based_notifications(
                    self.notification_service, changes, 'robot_events',
                    time_range=f"{start_time} to {end_time}"
                )
                pipeline_stats['total_successful_notifications'] += notif_success
                pipeline_stats['total_failed_notifications'] += notif_failed

            # Calculate execution time
            pipeline_end = datetime.now()
            execution_time = (pipeline_end - pipeline_start).total_seconds()

            # Print final summary
            logger.info("=" * 60)
            logger.info("📊 PIPELINE EXECUTION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"⏱️  Execution time: {execution_time:.2f} seconds")
            logger.info(f"✅ Total successful inserts: {pipeline_stats['total_successful_inserts']}")
            logger.info(f"❌ Total failed inserts: {pipeline_stats['total_failed_inserts']}")
            logger.info(f"📧 Total successful notifications: {pipeline_stats['total_successful_notifications']}")
            logger.info(f"📧 Total failed notifications: {pipeline_stats['total_failed_notifications']}")

            if pipeline_stats['total_successful_inserts'] > 0 and pipeline_stats['total_failed_inserts'] == 0:
                logger.info("✅ Data pipeline completed successfully with all successful inserts")
                return True  # Success indicator for Airflow
            elif pipeline_stats['total_successful_inserts'] > 0 and pipeline_stats['total_failed_inserts'] > 0:
                logger.info("❌ Data pipeline completed with some successful inserts but some failed inserts")
                return False  # Partial success indicator for Airflow
            elif pipeline_stats['total_successful_inserts'] == 0 and pipeline_stats['total_failed_inserts'] == 0:
                logger.info("✅ Data pipeline completed but NO new data were fetched!")
                return True  #  Success indicator for Airflow
            elif pipeline_stats['total_successful_inserts'] == 0 and pipeline_stats['total_failed_inserts'] > 0:
                logger.error("❌ Data pipeline completed but NO data was successfully inserted anywhere!")
                return False  # Failure indicator for Airflow

        except Exception as e:
            logger.error(f"💥 Critical error in data pipeline: {e}", exc_info=True)
            logger.error("Pipeline execution stopped")
            raise  # Re-raise for Airflow to catch

        finally:
            # Close all database connections
            self._close_all_connections()

    def _close_all_connections(self):
        """Close all database connections"""
        all_tables = (
            self.location_tables +
            self.robot_status_tables +
            self.task_tables +
            # self.task_overview_tables + # IMPORTANT: Task overview data is not used for now
            self.charging_tables +
            self.event_tables
        )

        closed_count = 0
        for table in all_tables:
            try:
                table.close()
                closed_count += 1
            except Exception as e:
                logger.warning(f"Error closing connection for {table.database_name}.{table.table_name}: {e}")

        logger.info(f"🔌 Closed {closed_count}/{len(all_tables)} database connections")

    def get_config_summary(self) -> dict:
        """Get a summary of the current configuration"""
        summary = {
            'databases': self.config.get_databases(),
            'table_counts': {
                'robot_status': len(self.robot_status_tables),
                'robot_task': len(self.task_tables),
                'location': len(self.location_tables),
                # 'robot_task_overview': len(self.task_overview_tables), # IMPORTANT: Task overview data is not used for now
                'robot_charging': len(self.charging_tables),
                'robot_events': len(self.event_tables)
            },
            'total_tables': (
                len(self.location_tables) +
                len(self.robot_status_tables) +
                len(self.task_tables) +
                # len(self.task_overview_tables) + # IMPORTANT: Task overview data is not used for now
                len(self.charging_tables) +
                len(self.event_tables)
            )
        }
        return summary

# Example usage:
if __name__ == "__main__":
    # Initialize app with your API host
    app = App(config_path="database_config.yaml", api_host="your-api-host.com")

    # Run pipeline with time range
    app.run(start_time="2025-01-01 00:00:00", end_time="2025-01-02 00:00:00")