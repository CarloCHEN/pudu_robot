# src/pudu/event_support/support_utils.py (CORRECTED VERSION)
import pandas as pd
from pudu.rds import RDSDatabase
import logging

logger = logging.getLogger(__name__)

def get_support_tickets_table(database: RDSDatabase):
    """
    Get support tickets from the database, focusing on new 'reported' tickets.

    Parameters:
        database (RDSDatabase): RDS database object for support tickets

    Returns:
        pd.DataFrame: DataFrame with new support tickets that need attention
    """
    logger.info("Fetching support tickets from database")
    if '-' in database.database_name:
        # Database name has hyphen, needs backticks in SQL
        db_name_in_query = f"`{database.database_name}`"
    else:
        # Normal database name, no backticks needed
        db_name_in_query = database.database_name
    try:
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
            e.tenant_id

        FROM {db_name_in_query}.mnt_robot_event_reports r
        JOIN {db_name_in_query}.mnt_robot_events e
            ON r.event_id = e.id
        WHERE r.is_new = 1
        ORDER BY r.reported_at DESC
        """

        logger.info(f"Executing query for new support tickets...")
        tickets_data = database.execute_query(base_query)

        if not tickets_data.empty:
            # Ensure reported_at timestamp is in proper format
            tickets_data['reported_at'] = pd.to_datetime(tickets_data['reported_at'])

        logger.info(f"Retrieved {len(tickets_data)} new support tickets requiring attention")
        return tickets_data

    except Exception as e:
        logger.error(f"Error fetching support tickets: {e}")
        # Return empty DataFrame on error
        return pd.DataFrame()

def reset_new_flags(database: RDSDatabase, notified_tickets_df: pd.DataFrame):
    """
    Set is_new = 0 for notified tickets using existing query methods.

    Parameters:
        database (RDSDatabase): The database connection object
        notified_tickets_df (pd.DataFrame): DataFrame of tickets that were notified
    """
    if '-' in database.database_name:
        # Database name has hyphen, needs backticks in SQL
        db_name_in_query = f"`{database.database_name}`"
    else:
        # Normal database name, no backticks needed
        db_name_in_query = database.database_name
    try:
        if notified_tickets_df.empty:
            logger.info("No tickets to update")
            return

        # Get report IDs from notified tickets
        report_ids = notified_tickets_df['report_id'].dropna().astype(str).tolist()

        if not report_ids:
            logger.warning("No valid report IDs found in notified tickets")
            return

        # Safely format the list for SQL (e.g., '123', '456')
        formatted_ids = ', '.join([f"'{rid}'" for rid in report_ids])

        update_query = f"""
        UPDATE {db_name_in_query}.mnt_robot_event_reports
        SET is_new = 0, last_updated = NOW()
        WHERE id IN ({formatted_ids})
        """

        logger.info(f"Updating is_new flag for {len(report_ids)} notified tickets...")

        # Use the existing query_data method (which can execute UPDATE queries)
        database.query_data(update_query)

        logger.info(f"✅ Successfully set is_new = 0 for {len(report_ids)} support tickets")

    except Exception as e:
        logger.warning(f"❌ Failed to reset is_new flags: {e}")