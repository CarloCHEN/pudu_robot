from datetime import datetime, timezone
from typing import List
import pandas as pd
from pudu.rds.rdsTable import RDSDatabase
from pudu.event_support.support_utils import get_support_tickets_table, reset_new_flags
from pudu.configs import DynamicDatabaseConfig
import logging
import boto3
import os

logger = logging.getLogger(__name__)

def initialize_project_databases_from_dynamic_config(config: DynamicDatabaseConfig) -> List[RDSDatabase]:
    """
    Initialize all project databases from dynamic configuration

    Parameters:
        config (DynamicDatabaseConfig): Dynamic configuration object

    Returns:
        List[RDSDatabase]: List of initialized project databases
    """
    databases = []

    try:
        # Get all project database names (exclude main database)
        all_project_databases = config.resolver.get_all_project_databases()

        logger.info(f"Found {len(all_project_databases)} project databases to monitor: {all_project_databases}")

        for database_name in all_project_databases:
            try:
                database = RDSDatabase(connection_config="credentials.yaml", database_name=database_name)
                databases.append(database)
                logger.info(f"✅ Initialized database: {database_name}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize database {database_name}: {e}")

        logger.info(f"Successfully initialized {len(databases)}/{len(all_project_databases)} project databases")

    except Exception as e:
        logger.error(f"Error getting project databases: {e}")

    return databases

def monitor_support_tickets(databases: List[RDSDatabase], function_name):
    """
    Monitor support tickets for new 'reported' status entries across all databases.
    Send a single SNS notification for all new tickets.

    Returns:
        (bool, int): Success flag and number of new tickets found
    """
    try:
        logger.info("🎫 Checking for new support tickets across all project databases...")
        total_ticket_count = 0
        all_new_tickets = []
        database_ticket_counts = {}

        for database in databases:
            try:
                logger.info(f"🔍 Checking for new support tickets in {database.database_name}")
                new_tickets = get_support_tickets_table(database)

                if new_tickets.empty:
                    logger.info(f"✅ No new support tickets in {database.database_name}")
                    database_ticket_counts[database.database_name] = 0
                else:
                    count = len(new_tickets)
                    total_ticket_count += count
                    database_ticket_counts[database.database_name] = count
                    logger.info(f"🚨 Found {count} new support ticket(s) in {database.database_name}!")

                    # Add database name to each ticket for notification context
                    new_tickets['source_database'] = database.database_name
                    all_new_tickets.append(new_tickets)

            except Exception as e:
                logger.error(f"❌ Error checking tickets in {database.database_name}: {e}")
                database_ticket_counts[database.database_name] = 0
                continue

        # Send notification if we found any tickets
        if total_ticket_count > 0:
            # Combine all tickets from all databases
            combined_tickets = pd.concat(all_new_tickets, ignore_index=True) if all_new_tickets else pd.DataFrame()

            # Send batch notification
            send_support_ticket_notification_batch(function_name, database_ticket_counts, combined_tickets)

            # Reset flags for each database
            for database in databases:
                try:
                    # Get tickets for this specific database
                    db_tickets = combined_tickets[combined_tickets['source_database'] == database.database_name]
                    if not db_tickets.empty:
                        reset_new_flags(database, db_tickets)
                        logger.info(f"✅ Reset flags for {len(db_tickets)} tickets in {database.database_name}")
                except Exception as e:
                    logger.error(f"❌ Error resetting flags in {database.database_name}: {e}")

        else:
            logger.info("✅ No new support tickets found across all databases")

        return True, total_ticket_count

    except Exception as e:
        logger.error(f"❌ Error monitoring support tickets: {e}", exc_info=True)
        return False, 0

def send_support_ticket_notification_batch(function_name, database_ticket_counts: dict, tickets_df: pd.DataFrame):
    """
    Send a single SNS notification summarizing all new support tickets across all databases.

    Parameters:
        function_name (str): Name of the Lambda function
        database_ticket_counts (dict): Dictionary mapping database names to ticket counts
        tickets_df (pd.DataFrame): DataFrame of new support tickets from all databases
    """
    try:
        sns_topic_arn = os.getenv('SUPPORT_TICKET_SNS_TOPIC_ARN')
        if not sns_topic_arn:
            logger.warning("No SNS topic configured for support ticket notifications")
            return

        sns = boto3.client('sns')
        now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Compose summary
        message_lines = [
            "🚨 NEW CUSTOMER SUPPORT TICKETS ALERT (Multi-Database)\n",
            f"📅 Notification Sent: {now_str}",
            f"🔗 Function Triggered: {function_name}",
            f"📋 Total New Tickets: {len(tickets_df)}",
            f"📊 Databases Monitored: {len(database_ticket_counts)}",
            ""
        ]

        # Add database breakdown
        message_lines.append("📊 Tickets by Database:")
        for db_name, count in database_ticket_counts.items():
            if count > 0:
                message_lines.append(f"   🔸 {db_name}: {count} tickets")
            else:
                message_lines.append(f"   🔹 {db_name}: No new tickets")

        message_lines.append("\n🧾 Ticket Details:")

        # Group tickets by database for better organization
        for db_name in database_ticket_counts.keys():
            if database_ticket_counts[db_name] > 0:
                db_tickets = tickets_df[tickets_df['source_database'] == db_name]

                message_lines.append(f"\n📂 Database: {db_name} ({len(db_tickets)} tickets)")
                message_lines.append("─" * 50)

                for _, ticket in db_tickets.iterrows():
                    report_id = ticket.get('report_id', 'Unknown')
                    event_id = ticket.get('event_id', 'Unknown')
                    status = ticket.get('current_status', 'Unknown')
                    reported_at = ticket.get('reported_at', 'Unknown')
                    contact_method = ticket.get('contact_method', 'Unknown')
                    contact_value = ticket.get('contact_value', 'Unknown')
                    robot_sn = ticket.get('robot_sn', 'Unknown')
                    event_type = ticket.get('event_type', 'Unknown')
                    event_level = ticket.get('event_level', 'Unknown')
                    detail = ticket.get('event_detail', 'No detail')

                    message_lines.append(
                        f"""
                        🆔 Report ID: {report_id}
                        🔗 Event ID: {event_id}
                        🤖 Robot SN: {robot_sn}
                        📛 Event Type: {event_type} ({event_level})
                        🗓️ Reported At: {reported_at}
                        📬 Contact: {contact_method} - {contact_value}
                        📄 Status: {status}
                        📋 Detail: {detail.strip()[:200]}...
                        """.strip()
                    )

        message_lines.append(
            f"\n🔧 Required Actions:\n"
            f"1. Contact the customers for each ticket\n"
            f"2. Investigate the reported issues\n"
            f"3. Log responses in the appropriate database systems\n"
            f"4. Follow up as needed\n"
            f"5. Check all {len(database_ticket_counts)} project databases for updates\n"
        )

        message_lines.append("\nThis is an automated notification from the Pudu Robot Support Monitoring System.")
        message_lines.append(f"Monitoring {len(database_ticket_counts)} project databases for support tickets.")

        full_message = "\n".join(message_lines)

        sns.publish(
            TopicArn=sns_topic_arn,
            Message=full_message,
            Subject=f"🎫 {len(tickets_df)} New Support Tickets from {len([db for db, count in database_ticket_counts.items() if count > 0])} Databases"
        )

        logger.info(f"✅ Batch support ticket notification sent for {len(tickets_df)} tickets across {len(database_ticket_counts)} databases")

    except Exception as e:
        logger.error(f"❌ Failed to send batch support ticket notification: {e}", exc_info=True)


class EventSupportApp:
    """Enhanced event support app with dynamic database resolution"""

    def __init__(self, config_path: str = "database_config.yaml"):
        """Initialize the dynamic event support app with database configuration"""
        logger.info(f"Initializing Dynamic Event Support App with config: {config_path}")
        self.config = DynamicDatabaseConfig(config_path)

        # Initialize all project databases dynamically
        self.databases = initialize_project_databases_from_dynamic_config(self.config)

    def run(self, function_name):
        """Run the dynamic event support app"""
        logger.info("Running dynamic event support app")

        try:
            if not self.databases:
                logger.warning("No project databases found to monitor")
                return True, 0

            success, ticket_count = monitor_support_tickets(self.databases, function_name)

            return success, ticket_count

        except Exception as e:
            logger.error(f"Error in dynamic event support app: {e}")
            return False, 0
        finally:
            # Close database connections
            for db in self.databases:
                try:
                    db.close()
                except:
                    pass
            self.config.close()
