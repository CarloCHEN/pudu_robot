from datetime import datetime
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
    Monitor support tickets for new 'reported' status entries
    Send SNS notifications for new tickets requiring attention

    Returns:
        int: Number of new tickets found
    """
    try:
        logger.info("🎫 Checking for new support tickets...")
        # Get new support tickets
        ticket_count = 0
        for database in databases:
            logger.info(f"🔍 Checking for new support tickets in {database.database_name}")
            new_tickets = get_support_tickets_table(database)
            if new_tickets.empty:
                logger.info("✅ No new support tickets requiring attention")
                ticket_count += 0
            else:
                ticket_count += len(new_tickets)
                logger.info(f"🚨 Found {ticket_count} new support ticket(s) requiring attention!")

                # Send notification for each new ticket
                for _, ticket in new_tickets.iterrows():
                    send_support_ticket_notification(function_name, ticket)

            # Reset new flags for notified tickets
            reset_new_flags(database, new_tickets)

        return True, ticket_count

    except Exception as e:
        logger.error(f"❌ Error monitoring support tickets: {e}", exc_info=True)
        return False, 0

def send_support_ticket_notification(function_name, ticket):
    """
    Send SNS notification for a new support ticket

    Parameters:
        function_name (str): Lambda function name
        ticket (pd.Series): Ticket data from DataFrame row
    """
    try:
        sns_topic_arn = os.getenv('SUPPORT_TICKET_SNS_TOPIC_ARN')

        if not sns_topic_arn:
            logger.warning("No SNS topic configured for support ticket notifications")
            return

        sns = boto3.client('sns')

        # Extract relevant fields from the joined ticket record
        report_id = ticket.get('report_id', 'Unknown')
        event_id = ticket.get('event_id', 'Unknown')
        status = ticket.get('current_status', 'Unknown')
        reported_at = ticket.get('reported_at', 'Unknown')
        contact_method = ticket.get('contact_method', 'Unknown')
        contact_value = ticket.get('contact_value', 'Unknown')
        resolved_at = ticket.get('resolved_at', 'N/A')
        reported_by_user_id = ticket.get('reported_by_user_id', 'Unknown')

        # Event-related fields
        robot_sn = ticket.get('robot_sn', 'Unknown')
        event_level = ticket.get('event_level', 'Unknown')
        event_type = ticket.get('event_type', 'Unknown')
        event_detail = ticket.get('event_detail', 'No detail')

        subject = f"🎫 NEW Support Ticket - Report #{report_id}"

        message = f"""
        🚨 NEW CUSTOMER SUPPORT TICKET ALERT

        🧾 Report Info:
        • Report ID: {report_id}
        • Event ID: {event_id}
        • Status: {status}
        • Reported At: {reported_at}
        • Resolved At: {resolved_at if pd.notnull(resolved_at) else 'Unresolved'}
        • Reported By User ID: {reported_by_user_id}
        • Contact via {contact_method}: {contact_value}

        🤖 Robot Event Info:
        • Robot SN: {robot_sn}
        • Event Level: {event_level}
        • Event Type: {event_type}
        • Event Detail: {event_detail}

        🔧 Required Actions:
        1. Contact the customer
        2. Investigate the reported issue
        3. Log your response using the support system
        4. Follow up as needed

        📅 Notification Sent: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        🔗 Function Triggered: {function_name}

        This is an automated notification from the Pudu Robot Support Monitoring System.
        Please respond promptly to maintain customer satisfaction.
        """.strip()

        sns.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            Subject=subject
        )

        logger.info(f"✅ Support ticket notification sent for Report ID: {report_id}")

    except Exception as e:
        logger.error(f"❌ Failed to send support ticket notification: {e}")


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