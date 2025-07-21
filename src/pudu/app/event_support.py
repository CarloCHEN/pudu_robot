from datetime import datetime, timezone
from typing import List
import pandas as pd
from pudu.rds.rdsTable import RDSDatabase
from pudu.event_support.support_utils import get_support_tickets_table, reset_new_flags
from pudu.app.main import DatabaseConfig
import logging
import boto3
import os

logger = logging.getLogger(__name__)

def initialize_databases_from_config(config: DatabaseConfig) -> List[RDSDatabase]:
    """
    Initialize databases from configuration

    Parameters:
        config (DatabaseConfig): Configuration object

    Returns:
        List[RDSDatabase]: List of initialized databases
    """
    databases = []
    for database_name in config.get_databases():
        database = RDSDatabase(connection_config="credentials.yaml", database_name=database_name)
        databases.append(database)
    return databases

def monitor_support_tickets(databases: List[RDSDatabase], function_name):
    """
    Monitor support tickets for new 'reported' status entries.
    Send a single SNS notification for all new tickets.

    Returns:
        (bool, int): Success flag and number of new tickets found
    """
    try:
        logger.info("🎫 Checking for new support tickets...")
        ticket_count = 0

        for database in databases:
            logger.info(f"🔍 Checking for new support tickets in {database.database_name}")
            new_tickets = get_support_tickets_table(database)
            if new_tickets.empty:
                logger.info("✅ No new support tickets requiring attention")
            else:
                count = len(new_tickets)
                ticket_count += count
                logger.info(f"🚨 Found {count} new support ticket(s) requiring attention!")

            if ticket_count > 0:
                send_support_ticket_notification_batch(function_name, database.database_name, new_tickets)

                # Reset flags after successful notification
                reset_new_flags(database, new_tickets)

        return True, ticket_count

    except Exception as e:
        logger.error(f"❌ Error monitoring support tickets: {e}", exc_info=True)
        return False, 0

def send_support_ticket_notification_batch(function_name, database_name: str, tickets_df: pd.DataFrame):
    """
    Send a single SNS notification summarizing all new support tickets.

    Parameters:
        function_name (str): Name of the Lambda function
        tickets_df (pd.DataFrame): DataFrame of new support tickets
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
            "🚨 NEW CUSTOMER SUPPORT TICKETS ALERT\n",
            f"📅 Notification Sent: {now_str}",
            f"🔗 Function Triggered: {function_name}",
            f"📋 Total New Tickets: {len(tickets_df)}",
            f"📊 Database: {database_name}",
            "\n🧾 Ticket Summaries:"
        ]

        for _, ticket in tickets_df.iterrows():
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
                —————————————
                🆔 Report ID: {report_id}
                🔗 Event ID: {event_id}
                🤖 Robot SN: {robot_sn}
                📛 Event Type: {event_type} ({event_level})
                🗓️ Reported At: {reported_at}
                📬 Contact: {contact_method} - {contact_value}
                📄 Status: {status}
                📋 Detail: {detail.strip()[:300]}
                """.strip()
            )

        message_lines.append(
            "\n🔧 Required Actions:\n"
            "1. Contact the customer\n"
            "2. Investigate the reported issues\n"
            "3. Log responses in the support system\n"
            "4. Follow up as needed\n"
        )

        message_lines.append("\nThis is an automated notification from the Pudu Robot Support Monitoring System.")

        full_message = "\n".join(message_lines)

        sns.publish(
            TopicArn=sns_topic_arn,
            Message=full_message,
            Subject=f"🎫 {len(tickets_df)} New Support Tickets Needing Attention"
        )

        logger.info(f"✅ Batch support ticket notification sent for {len(tickets_df)} tickets")

    except Exception as e:
        logger.error(f"❌ Failed to send batch support ticket notification: {e}", exc_info=True)


class EventSupportApp:
    def __init__(self, config_path: str = "database_config.yaml"):
        """Initialize the event support app with database configuration"""
        logger.info(f"Initializing App with config: {config_path}")
        self.config = DatabaseConfig(config_path)

        # Initialize tables for each type
        self.databases = initialize_databases_from_config(self.config)

    def run(self, function_name):
        """Run the event support app"""
        logger.info("Running event support app")
        success, ticket_count = monitor_support_tickets(self.databases, function_name)
        return success, ticket_count