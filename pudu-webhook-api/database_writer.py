import logging
import time
from typing import Any, Dict

from database_config import DatabaseConfig
from rds_utils import batch_insert, connect_rds_instance, use_database

logger = logging.getLogger(__name__)


class DatabaseWriter:
    """Handles writing callback data to RDS database"""

    def __init__(self, config_path: str = "database_config.yaml", credentials_path: str = "credentials.yaml"):
        self.config = DatabaseConfig(config_path)
        self.credentials_path = credentials_path
        self.connections = {}

    def _get_connection(self, database_name: str):
        """Get or create database connection"""
        if database_name not in self.connections:
            try:
                connection = connect_rds_instance(self.credentials_path)
                cursor = connection.cursor()
                use_database(cursor, database_name)
                self.connections[database_name] = {"connection": connection, "cursor": cursor}
                logger.info(f"Established connection to database: {database_name}")
            except Exception as e:
                logger.error(f"Failed to connect to database {database_name}: {e}")
                raise

        return self.connections[database_name]

    def write_robot_status(self, robot_sn: str, status_data: Dict[str, Any]):
        """Write robot status data to mnt_robots_management table"""
        table_configs = self.config.get_table_configs().get("robot_status", [])
        database_names = set()
        table_names = set()

        if not table_configs:
            logger.warning("No robot_status table configurations found")
            return

        # Prepare data for database insertion
        db_data = {"robot_sn": robot_sn, "status": status_data.get("status", "")}

        # Remove None values
        db_data = {k: v for k, v in db_data.items() if v is not None}

        for table_config in table_configs:
            try:
                db_conn = self._get_connection(table_config["database"])
                batch_insert(db_conn["cursor"], table_config["table_name"], [db_data], table_config["primary_keys"])
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"Updated robot status for {robot_sn} in {table_config['database']}.{table_config['table_name']}")
            except Exception as e:
                logger.error(f"Failed to write robot status to {table_config['database']}.{table_config['table_name']}: {e}")

        return list(database_names), list(table_names)

    def write_robot_pose(self, robot_sn: str, pose_data: Dict[str, Any]):
        """Write robot pose data to mnt_robots_management table"""
        table_configs = self.config.get_table_configs().get("robot_status", [])
        database_names = set()
        table_names = set()
        if not table_configs:
            logger.warning("No robot_status table configurations found")
            return

        # Prepare data for database insertion
        db_data = {"robot_sn": robot_sn, "x": pose_data.get("x"), "y": pose_data.get("y"), "z": pose_data.get("z")}

        # Remove None values
        db_data = {k: v for k, v in db_data.items() if v is not None}

        for table_config in table_configs:
            try:
                db_conn = self._get_connection(table_config["database"])
                batch_insert(db_conn["cursor"], table_config["table_name"], [db_data], table_config["primary_keys"])
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"Updated robot pose for {robot_sn} in {table_config['database']}.{table_config['table_name']}")
            except Exception as e:
                logger.error(f"Failed to write robot pose to {table_config['database']}.{table_config['table_name']}: {e}")

        return list(database_names), list(table_names)

    def write_robot_power(self, robot_sn: str, power_data: Dict[str, Any]):
        """Write robot power data to mnt_robots_management table"""
        table_configs = self.config.get_table_configs().get("robot_status", [])
        database_names = set()
        table_names = set()
        if not table_configs:
            logger.warning("No robot_status table configurations found")
            return

        # Prepare data for database insertion
        db_data = {"robot_sn": robot_sn, "battery_level": power_data.get("power")}

        # Remove None values
        db_data = {k: v for k, v in db_data.items() if v is not None}

        for table_config in table_configs:
            try:
                db_conn = self._get_connection(table_config["database"])
                batch_insert(db_conn["cursor"], table_config["table_name"], [db_data], table_config["primary_keys"])
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"Updated robot power for {robot_sn} in {table_config['database']}.{table_config['table_name']}")
            except Exception as e:
                logger.error(f"Failed to write robot power to {table_config['database']}.{table_config['table_name']}: {e}")

        return list(database_names), list(table_names)

    def write_robot_event(self, robot_sn: str, event_data: Dict[str, Any]):
        """Write robot event data to mnt_robot_events table"""
        table_configs = self.config.get_table_configs().get("robot_events", [])
        database_names = set()
        table_names = set()
        if not table_configs:
            logger.warning("No robot_events table configurations found")
            return

        # Prepare data for database insertion
        db_data = {
            "robot_sn": robot_sn,
            "event_id": event_data.get("error_id", ""),
            "error_id": event_data.get("error_id", ""),
            "event_level": event_data.get("error_level", "").lower(),
            "event_type": event_data.get("error_type", ""),
            "event_detail": event_data.get("error_detail", ""),
            "task_time": event_data.get("timestamp", int(time.time())),
            "upload_time": int(time.time()),
        }

        # Remove None values
        db_data = {k: v for k, v in db_data.items() if v is not None}

        for table_config in table_configs:
            try:
                db_conn = self._get_connection(table_config["database"])
                batch_insert(db_conn["cursor"], table_config["table_name"], [db_data], table_config["primary_keys"])
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"Inserted robot event for {robot_sn} in {table_config['database']}.{table_config['table_name']}")
            except Exception as e:
                logger.error(f"Failed to write robot event to {table_config['database']}.{table_config['table_name']}: {e}")

        return list(database_names), list(table_names)

    def close_all_connections(self):
        """Close all database connections"""
        for database_name, conn_info in self.connections.items():
            try:
                conn_info["cursor"].close()
                conn_info["connection"].close()
                logger.info(f"Closed connection to database: {database_name}")
            except Exception as e:
                logger.warning(f"Error closing connection to {database_name}: {e}")

        self.connections.clear()
