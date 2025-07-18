import pandas as pd
from pudu.rds import RDSDatabase
import logging

logger = logging.getLogger(__name__)

def get_support_tickets_table(database: RDSDatabase):
    """
    Get support tickets from the database, focusing on new 'reported' tickets.

    Parameters:
        ticket_table (RDSTable): RDS table object for support tickets

    Returns:
        pd.DataFrame: DataFrame with new support tickets that need attention
    """
    logger.info("Fetching support tickets from database")

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

            e.id AS event_id,
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

        FROM {database.database_name}.mnt_robot_event_reports r
        JOIN {database.database_name}.mnt_robot_events e
            ON r.event_id = e.event_id
        WHERE r.is_new = 1
        ORDER BY r.reported_at DESC;
        """

        logger.info(f"Executing query: {base_query}")
        # Execute the query
        tickets_data = database.query_data_as_df(base_query)

        if not tickets_data.empty:
            # Ensure reported_at timestamp is in proper format
            tickets_data['reported_at'] = pd.to_datetime(tickets_data['reported_at'])

        # Close the connection
        database.close()

        logger.info(f"Retrieved {len(tickets_data)} new support tickets requiring attention")
        return tickets_data

    except Exception as e:
        logger.error(f"Error fetching support tickets: {e}")
        # Return empty DataFrame on error
        return pd.DataFrame()

def reset_new_flags(database: RDSDatabase, notified_tickets_df: pd.DataFrame):
    """
    Update the last Lambda execution timestamp and set is_new = 0 for notified tickets.

    Parameters:
        database (RDSDatabase): The database connection object
        timestamp (str): Current timestamp in 'YYYY-MM-DD HH:MM:SS' format
        notified_tickets_df (pd.DataFrame): DataFrame of tickets that were notified
    """
    try:
        # Mark notified support tickets as not new ===
        if not notified_tickets_df.empty:
            report_ids = notified_tickets_df['report_id'].dropna().astype(str).tolist()

            # Safely format the list for SQL (e.g., '123', '456')
            formatted_ids = ', '.join([f"'{rid}'" for rid in report_ids])

            update_query = f"""
            UPDATE {database.database_name}.mnt_robot_event_reports
            SET is_new = 0
            WHERE report_id IN ({formatted_ids});
            """

            logger.info(f"Executing update for {len(report_ids)} notified tickets...")
            database.execute_query(update_query)
            logger.info(f"✅ is_new set to 0 for {len(report_ids)} support tickets")

    except Exception as e:
        logger.warning(f"❌ Failed to update last run time or reset is_new flags: {e}")