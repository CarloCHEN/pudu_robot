#!/usr/bin/env python3
"""
Support Ticket Timeline API

A simple API to update support ticket timeline status.
Can be called from terminal or imported as a module.

Usage:
    python support_timeline_api.py --report-id 12345 --status "Email sent to customer"
    python support_timeline_api.py --report-id 12345 --status "Issue resolved" --user-id admin_001
    python support_timeline_api.py --report-id 12345 --database "foxx_irvine_office" --status "Customer contacted"
    python support_timeline_api.py --report-id 12345 --history
"""

import argparse
import sys
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

sys.path.insert(0, '../src')

# Add current directory to Python path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from pudu.rds.rdsTable import RDSDatabase
from pudu.app.main import DatabaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SupportTicketTimelineAPI:
    """API for updating support ticket timeline entries"""

    def __init__(self, config_path: str = "database_config.yaml"):
        """
        Initialize the API with database configuration

        Parameters:
            config_path (str): Path to database configuration file
        """
        logger.info(f"Initializing Support Ticket Timeline API with config: {config_path}")

        # Load configuration
        self.config = DatabaseConfig(config_path)

        # Initialize databases from configuration
        self.databases = self._initialize_databases()
        self.database_map = {db.database_name: db for db in self.databases}

        logger.info(f"✅ API initialized with {len(self.databases)} databases")

    def _initialize_databases(self) -> List[RDSDatabase]:
        """Initialize databases from configuration"""
        databases = []

        # Get support ticket timeline table configurations
        timeline_configs = self.config.get_table_configs().get('support_tickets_timeline', [])

        for config in timeline_configs:
            try:
                database = RDSDatabase(
                    connection_config="credentials.yaml",
                    database_name=config['database']
                )
                databases.append(database)
                logger.info(f"✅ Connected to database: {config['database']}")
            except Exception as e:
                logger.error(f"❌ Failed to connect to database {config['database']}: {e}")

        return databases

    def find_databases_with_report_id(self, report_id: str) -> List[RDSDatabase]:
        """
        Find databases that contain the specified report_id

        Parameters:
            report_id (str): The report ID to search for

        Returns:
            List[RDSDatabase]: Databases that contain the report_id
        """
        databases_with_report = []

        logger.info(f"🔍 Searching for report_id {report_id} across {len(self.databases)} databases...")

        for database in self.databases:
            try:
                # Handle database names with hyphens
                if '-' in database.database_name:
                    db_name_in_query = f"`{database.database_name}`"
                else:
                    db_name_in_query = database.database_name

                # Check if report_id exists in mnt_robot_event_reports table
                search_query = f"""
                SELECT COUNT(*) as count
                FROM {db_name_in_query}.mnt_robot_event_reports
                WHERE id = '{report_id}'
                """

                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
                    result_df = database.query_data_as_df(search_query)

                if not result_df.empty and result_df.iloc[0]['count'] > 0:
                    databases_with_report.append(database)
                    logger.info(f"✅ Found report_id {report_id} in database: {database.database_name}")
                else:
                    logger.debug(f"   Report_id {report_id} not found in database: {database.database_name}")

            except Exception as e:
                logger.warning(f"⚠️ Error searching database {database.database_name}: {e}")

        if databases_with_report:
            logger.info(f"📋 Report_id {report_id} found in {len(databases_with_report)} database(s)")
        else:
            logger.warning(f"⚠️ Report_id {report_id} not found in any database")

        return databases_with_report

    def add_timeline_entry(
        self,
        report_id: str,
        status_text: str,
        created_by_user_id: Optional[str] = None,
        created_by_type: str = "admin",
        metadata: Optional[Dict[str, Any]] = None,
        target_database: Optional[str] = None
    ) -> bool:
        """
        Add a new timeline entry for a support ticket

        Parameters:
            report_id (str): The report ID to update
            status_text (str): The status message to add
            created_by_user_id (str, optional): User ID who created this entry
            created_by_type (str): Type of creator (default: "admin")
            metadata (dict, optional): Additional metadata as JSON
            target_database (str, optional): Specific database to target. If None, searches all databases.

        Returns:
            bool: True if successful, False otherwise
        """
        if not report_id or not status_text:
            logger.error("❌ report_id and status_text are required")
            return False

        # Determine target databases
        if target_database:
            # Use specific database if provided
            if target_database in self.database_map:
                target_databases = [self.database_map[target_database]]
                logger.info(f"🎯 Targeting specific database: {target_database}")
            else:
                logger.error(f"❌ Database '{target_database}' not found in configuration")
                return False
        else:
            # Search for databases containing the report_id
            target_databases = self.find_databases_with_report_id(report_id)
            if not target_databases:
                logger.error(f"❌ Report_id {report_id} not found in any database. Cannot add timeline entry.")
                return False

        # Prepare the data for insertion
        timeline_data = {
            'report_id': report_id,
            'status_text': status_text.strip(),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'created_by_type': created_by_type,
            'created_by_user_id': created_by_user_id or 'system',
            'metadata': str(metadata) if metadata else None
        }

        success_count = 0
        total_databases = len(target_databases)

        logger.info(f"📝 Adding timeline entry for report_id: {report_id}")
        logger.info(f"   Status: {status_text}")
        logger.info(f"   Created by: {timeline_data['created_by_user_id']} ({created_by_type})")
        logger.info(f"   Target databases: {[db.database_name for db in target_databases]}")

        # Insert into target databases
        for database in target_databases:
            try:
                # Handle database names with hyphens
                if '-' in database.database_name:
                    db_name_in_query = f"`{database.database_name}`"
                else:
                    db_name_in_query = database.database_name

                # Escape single quotes in the status text
                escaped_status = timeline_data['status_text'].replace("'", "''")

                # Prepare insert query
                insert_query = f"""
                INSERT INTO {db_name_in_query}.mnt_robot_report_timeline
                (report_id, status_text, timestamp, created_by_type, created_by_user_id, metadata)
                VALUES (
                    '{timeline_data['report_id']}',
                    '{escaped_status}',
                    '{timeline_data['timestamp']}',
                    '{timeline_data['created_by_type']}',
                    '{timeline_data['created_by_user_id']}',
                    {f"'{timeline_data['metadata']}'" if timeline_data['metadata'] else 'NULL'}
                )
                """

                # Execute the insert
                database.query_data(insert_query)
                success_count += 1

                logger.info(f"✅ Successfully added timeline entry to {database.database_name}")

            except Exception as e:
                logger.error(f"❌ Failed to add timeline entry to {database.database_name}: {e}")

        # Summary
        if success_count == total_databases:
            logger.info(f"✅ Timeline entry added successfully to all {total_databases} databases")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️ Timeline entry added to {success_count}/{total_databases} databases")
            return True
        else:
            logger.error(f"❌ Failed to add timeline entry to any database")
            return False

    def get_timeline_history(self, report_id: str, target_database: Optional[str] = None) -> List[Dict]:
        """
        Get timeline history for a specific report ID

        Parameters:
            report_id (str): The report ID to query
            target_database (str, optional): Specific database to query. If None, uses first available database.

        Returns:
            List[Dict]: Timeline entries
        """
        if not self.databases:
            logger.error("❌ No databases available")
            return []

        try:
            # Determine which database to query
            if target_database and target_database in self.database_map:
                database = self.database_map[target_database]
                logger.info(f"🎯 Querying specific database: {target_database}")
            else:
                # Find databases with the report_id
                databases_with_report = self.find_databases_with_report_id(report_id)
                if databases_with_report:
                    database = databases_with_report[0]  # Use the first one found
                    logger.info(f"📋 Using database {database.database_name} for timeline query")
                else:
                    logger.warning(f"⚠️ Report_id {report_id} not found in any database")
                    return []

            # Handle database names with hyphens
            if '-' in database.database_name:
                db_name_in_query = f"`{database.database_name}`"
            else:
                db_name_in_query = database.database_name

            query = f"""
            SELECT id, report_id, status_text, timestamp,
                   created_by_type, created_by_user_id, metadata
            FROM {db_name_in_query}.mnt_robot_report_timeline
            WHERE report_id = '{report_id}'
            ORDER BY timestamp DESC
            """

            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")
                timeline_df = database.query_data_as_df(query)

            if timeline_df.empty:
                logger.info(f"📭 No timeline entries found for report_id: {report_id}")
                return []

            logger.info(f"📋 Found {len(timeline_df)} timeline entries for report_id: {report_id}")
            return timeline_df.to_dict('records')

        except Exception as e:
            logger.error(f"❌ Error querying timeline history: {e}")
            return []

    def close(self):
        """Close all database connections"""
        closed_count = 0
        for database in self.databases:
            try:
                database.close()
                closed_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Error closing database connection: {e}")

        logger.info(f"🔌 Closed {closed_count}/{len(self.databases)} database connections")


def main():
    """Command line interface for the Support Ticket Timeline API"""
    parser = argparse.ArgumentParser(
        description="Support Ticket Timeline API - Update support ticket status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
          python support_timeline_api.py --report-id 12345 --status "Email sent to customer"
          python support_timeline_api.py --report-id 12345 --status "Issue resolved" --user-id admin_001
          python support_timeline_api.py --report-id 12345 --database "foxx_irvine_office" --status "Customer contacted"
          python support_timeline_api.py --report-id 12345 --history
          python support_timeline_api.py --report-id 12345 --history --database "foxx_irvine_office_test"
        """
    )

    parser.add_argument(
        '--report-id',
        required=True,
        help='Report ID to update'
    )

    parser.add_argument(
        '--status',
        help='Status message to add to timeline'
    )

    parser.add_argument(
        '--database',
        help='Specific database to target (if not provided, searches all databases for the report_id)'
    )

    parser.add_argument(
        '--user-id',
        help='User ID who is creating this entry (default: system)'
    )

    parser.add_argument(
        '--user-type',
        default='admin',
        choices=['admin', 'system', 'customer_service', 'technician'],
        help='Type of user creating this entry (default: admin)'
    )

    parser.add_argument(
        '--history',
        action='store_true',
        help='Show timeline history for the report ID'
    )

    parser.add_argument(
        '--config',
        default='../src/pudu/configs/database_config.yaml',
        help='Path to database configuration file'
    )
    args = parser.parse_args()

    try:
        # Initialize the API
        api = SupportTicketTimelineAPI(config_path=args.config)

        if args.history:
            # Show timeline history
            logger.info(f"📋 Retrieving timeline history for report_id: {args.report_id}")
            history = api.get_timeline_history(args.report_id, target_database=args.database)

            if history:
                print(f"\n📋 Timeline History for Report ID: {args.report_id}")
                print("=" * 60)
                for i, entry in enumerate(history, 1):
                    print(f"{i}. [{entry['timestamp']}] by {entry['created_by_user_id']} ({entry['created_by_type']})")
                    print(f"   Status: {entry['status_text']}")
                    if entry['metadata']:
                        print(f"   Metadata: {entry['metadata']}")
                    print()
            else:
                print(f"📭 No timeline entries found for report_id: {args.report_id}")

        elif args.status:
            # Add new timeline entry
            success = api.add_timeline_entry(
                report_id=args.report_id,
                status_text=args.status,
                created_by_user_id=args.user_id,
                created_by_type=args.user_type,
                target_database=args.database
            )

            if success:
                print(f"✅ Successfully added timeline entry for report_id: {args.report_id}")
                print(f"   Status: {args.status}")
                if args.database:
                    print(f"   Database: {args.database}")
                sys.exit(0)
            else:
                print(f"❌ Failed to add timeline entry for report_id: {args.report_id}")
                sys.exit(1)

        else:
            parser.error("Either --status or --history must be specified")

    except KeyboardInterrupt:
        logger.info("⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Critical error: {e}")
        sys.exit(1)
    finally:
        if 'api' in locals():
            api.close()


if __name__ == "__main__":
    main()