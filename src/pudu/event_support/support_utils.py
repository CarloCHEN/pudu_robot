# src/pudu/event_support/support_utils.py (ENHANCED VERSION)
import pandas as pd
from pudu.rds import RDSDatabase
import logging

logger = logging.getLogger(__name__)

def get_database_name_for_query(database_name: str) -> str:
    """
    Format database name for SQL queries, handling special characters like hyphens.

    Parameters:
        database_name (str): The database name

    Returns:
        str: Properly formatted database name for SQL queries
    """
    # If database name contains special characters, wrap in backticks
    if '-' in database_name or any(char in database_name for char in [' ', '.', '@', '#']):
        return f"`{database_name}`"
    else:
        return database_name

def get_support_tickets_table(database: RDSDatabase):
    """
    Get support tickets from the database, focusing on new 'reported' tickets.

    Parameters:
        database (RDSDatabase): RDS database object for support tickets

    Returns:
        pd.DataFrame: DataFrame with new support tickets that need attention
    """
    logger.info(f"Fetching support tickets from database: {database.database_name}")

    # Format database name for query
    db_name_in_query = get_database_name_for_query(database.database_name)

    try:
        # First, check if the required tables exist
        tables_check_query = f"""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{database.database_name}'
        AND TABLE_NAME IN ('mnt_robot_event_reports', 'mnt_robot_events')
        """

        existing_tables = database.query_data(tables_check_query)
        existing_table_names = [table[0] if isinstance(table, tuple) else table.get('TABLE_NAME', '') for table in existing_tables]

        required_tables = ['mnt_robot_event_reports', 'mnt_robot_events']
        missing_tables = [table for table in required_tables if table not in existing_table_names]

        if missing_tables:
            logger.warning(f"Missing required tables in {database.database_name}: {missing_tables}")
            return pd.DataFrame()

        # Build the query to get latest status for each report_id
        base_query = f"""
        SELECT
            r.id AS report_id,
            r.event_id,
            r.reference_id,
            r.contact_method,
            r.contact_value,
            r.response_deadline,
            r.current_status,
            r.reported_at,
            r.is_new,
            r.last_updated,
            r.resolved_at,
            r.reported_by_user_id,

            e.id AS event_table_id,
            e.robot_sn,
            e.error_id,
            e.event_level,
            e.event_type,
            e.event_detail,
            e.task_time,
            e.upload_time,
            e.created_at,
            e.product_code,
            e.mac_address,
            e.software_version,
            e.hardware_version,
            e.os_version,
            COALESCE(e.tenant_id, 'unknown') AS tenant_id

        FROM {db_name_in_query}.mnt_robot_event_reports r
        JOIN {db_name_in_query}.mnt_robot_events e
            ON r.event_id = e.id
        WHERE r.is_new = 1
        ORDER BY r.reported_at DESC
        """

        logger.info(f"Executing query for new support tickets in {database.database_name}...")
        logger.debug(f"Query: {base_query}")

        tickets_data = database.execute_query(base_query)

        if not tickets_data.empty:
            # Ensure reported_at timestamp is in proper format
            tickets_data['reported_at'] = pd.to_datetime(tickets_data['reported_at'])

            # Add source database for tracking
            tickets_data['source_database'] = database.database_name

        logger.info(f"Retrieved {len(tickets_data)} new support tickets requiring attention from {database.database_name}")
        return tickets_data

    except Exception as e:
        logger.error(f"Error fetching support tickets from {database.database_name}: {e}")
        # Return empty DataFrame on error
        return pd.DataFrame()

def reset_new_flags(database: RDSDatabase, notified_tickets_df: pd.DataFrame):
    """
    Set is_new = 0 for notified tickets using existing query methods.

    Parameters:
        database (RDSDatabase): The database connection object
        notified_tickets_df (pd.DataFrame): DataFrame of tickets that were notified
    """
    # Format database name for query
    db_name_in_query = get_database_name_for_query(database.database_name)

    try:
        if notified_tickets_df.empty:
            logger.info(f"No tickets to update in {database.database_name}")
            return

        # Get report IDs from notified tickets
        report_ids = notified_tickets_df['report_id'].dropna().astype(str).tolist()

        if not report_ids:
            logger.warning(f"No valid report IDs found in notified tickets for {database.database_name}")
            return

        # Safely format the list for SQL (e.g., '123', '456')
        formatted_ids = ', '.join([f"'{rid}'" for rid in report_ids])

        update_query = f"""
        UPDATE {db_name_in_query}.mnt_robot_event_reports
        SET is_new = 0, last_updated = NOW()
        WHERE id IN ({formatted_ids})
        """

        logger.info(f"Updating is_new flag for {len(report_ids)} notified tickets in {database.database_name}...")
        logger.debug(f"Update query: {update_query}")

        # Use the existing query_data method (which can execute UPDATE queries)
        database.query_data(update_query)

        logger.info(f"✅ Successfully set is_new = 0 for {len(report_ids)} support tickets in {database.database_name}")

    except Exception as e:
        logger.warning(f"❌ Failed to reset is_new flags in {database.database_name}: {e}")

def validate_support_ticket_schema(database: RDSDatabase) -> bool:
    """
    Validate that the database has the required support ticket schema.

    Parameters:
        database (RDSDatabase): The database to validate

    Returns:
        bool: True if schema is valid, False otherwise
    """
    try:
        # Check for required tables
        tables_query = f"""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{database.database_name}'
        AND TABLE_NAME IN ('mnt_robot_event_reports', 'mnt_robot_events')
        """

        result = database.query_data(tables_query)
        table_names = [table[0] if isinstance(table, tuple) else table.get('TABLE_NAME', '') for table in result]

        required_tables = ['mnt_robot_event_reports', 'mnt_robot_events']
        has_all_tables = all(table in table_names for table in required_tables)

        if not has_all_tables:
            missing = [table for table in required_tables if table not in table_names]
            logger.warning(f"Database {database.database_name} missing tables: {missing}")
            return False

        # Check for required columns in mnt_robot_event_reports
        reports_columns_query = f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{database.database_name}'
        AND TABLE_NAME = 'mnt_robot_event_reports'
        """

        result = database.query_data(reports_columns_query)
        column_names = [col[0] if isinstance(col, tuple) else col.get('COLUMN_NAME', '') for col in result]

        required_columns = ['id', 'event_id', 'is_new', 'current_status', 'reported_at']
        has_all_columns = all(col in column_names for col in required_columns)

        if not has_all_columns:
            missing = [col for col in required_columns if col not in column_names]
            logger.warning(f"Database {database.database_name} missing columns in mnt_robot_event_reports: {missing}")
            return False

        logger.info(f"✅ Database {database.database_name} has valid support ticket schema")
        return True

    except Exception as e:
        logger.error(f"Error validating schema for {database.database_name}: {e}")
        return False