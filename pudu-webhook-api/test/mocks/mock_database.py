"""
Mock Database Service for Testing
Validates database operations without requiring actual database connection
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import yaml

logger = logging.getLogger(__name__)


class MockDatabaseConnection:
    """Mock database connection that simulates real database behavior"""

    def __init__(self):
        self.cursor_mock = MockCursor()
        self.is_connected = True

    def cursor(self):
        return self.cursor_mock

    def close(self):
        self.is_connected = False
        logger.info("Mock database connection closed")


class MockCursor:
    """Mock database cursor that validates SQL operations"""

    def __init__(self):
        self.connection = MagicMock()
        self.executed_queries = []
        self.current_database = None

    def execute(self, query: str):
        """Execute and validate SQL query"""
        self.executed_queries.append(query)
        logger.info(f"Mock SQL executed: {query[:100]}{'...' if len(query) > 100 else ''}")

        # Parse USE database commands
        if query.upper().startswith("USE"):
            if "`" in query:
                self.current_database = query.split("`")[1]
            else:
                self.current_database = query.split()[-1].rstrip(";")
            logger.info(f"Mock database switched to: {self.current_database}")

    def close(self):
        logger.info("Mock cursor closed")


class MockDatabaseWriter:
    """
    Mock Database Writer that validates operations without actual database writes
    Updated to match EnhancedDatabaseWriter interface
    """

    def __init__(self, config_path: str = "configs/database_config.yaml"):
        self.config_path = config_path
        self.connections = {}
        self.written_data = defaultdict(list)  # Store all written data for validation

        # Load configuration for validation
        self.database_config = self._load_database_config()
        self.table_schemas = self._define_table_schemas()

        logger.info("MockDatabaseWriter initialized with schema validation")

    def _load_database_config(self) -> Dict:
        """Load database configuration"""
        try:
            with open(self.config_path, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Default configuration matching the real system"""
        return {
            "main_database": "ry-vue",
            "tables": {
                "robot_status": [{"database": "project", "table_name": "mnt_robots_management", "primary_keys": ["robot_sn"]}],
                "robot_events": [
                    {"database": "project", "table_name": "mnt_robot_events", "primary_keys": ["robot_sn", "event_id"]}
                ],
            },
        }

    def _define_table_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Define expected table schemas for validation"""
        return {
            "mnt_robots_management": {
                "fields": [
                    "robot_sn",
                    "status",
                    "battery_level",
                    "water_level",
                    "sewage_level",
                    "x",
                    "y",
                    "z"
                ],
                "primary_keys": ["robot_sn"],
                "field_types": {
                    "robot_sn": "VARCHAR(50)",
                    "status": "VARCHAR(50)",
                    "battery_level": "INT",
                    "x": "DECIMAL(10,6)",
                    "y": "DECIMAL(10,6)"
                },
            },
            "mnt_robot_events": {
                "fields": ["robot_sn", "event_id", "error_id", "event_level", "event_type", "event_detail", "task_time", "upload_time"],
                "primary_keys": ["robot_sn", "event_id"],
                "field_types": {
                    "robot_sn": "VARCHAR(50)",
                    "event_id": "VARCHAR(100)",
                    "event_level": "VARCHAR(20)",
                    "event_type": "VARCHAR(100)",
                    "event_detail": "TEXT",
                    "task_time": "INT",
                    "upload_time": "INT",
                },
            },
        }

    def _validate_data_against_schema(self, table_name: str, data: Dict[str, Any]) -> bool:
        """Validate data against table schema"""
        if table_name not in self.table_schemas:
            logger.warning(f"No schema defined for table: {table_name}")
            return False

        schema = self.table_schemas[table_name]

        # Validate primary keys are present for upsert operations
        for pk in schema["primary_keys"]:
            print(pk, data)
            if pk not in data:
                logger.error(f"Primary key '{pk}' missing in data for table {table_name}")
                return False

        logger.info(f"✅ Data validation passed for table {table_name}")
        return True

    def write_robot_status(self, robot_sn: str, status_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Mock write robot status with validation - updated to match new interface"""
        logger.info(f"🔍 Testing robot status write for: {robot_sn}")

        # Build table configs similar to real implementation
        table_configs = self.database_config.get("tables", {}).get("robot_status", [])
        database_names = []
        table_names = []
        changes_detected = {}

        for table_config in table_configs:
            db_data = {"robot_sn": robot_sn}
            db_data.update({k: v for k, v in status_data.items() if v is not None})

            if self._validate_data_against_schema(table_config["table_name"], db_data):
                self.written_data[table_config["table_name"]].append(db_data)
                database_names.append(table_config.get("database", "mock_db"))
                table_names.append(table_config["table_name"])

                # Mock changes detection
                changes_detected[f"{robot_sn}_status"] = {
                    'robot_id': robot_sn,
                    'primary_key_values': {'robot_sn': robot_sn},
                    'change_type': 'update',
                    'changed_fields': list(db_data.keys()),
                    'old_values': {},
                    'new_values': db_data,
                    'database_key': f'mock_db_key_{robot_sn}'
                }

                logger.info(f"✅ Mock write robot status: {robot_sn} -> {table_config['table_name']}")

        return database_names, table_names, changes_detected

    def write_robot_pose(self, robot_sn: str, pose_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Mock write robot pose with validation"""
        logger.info(f"🔍 Testing robot pose write for: {robot_sn}")

        table_configs = self.database_config.get("tables", {}).get("robot_status", [])
        database_names = []
        table_names = []
        changes_detected = {}

        for table_config in table_configs:
            db_data = {"robot_sn": robot_sn}
            db_data.update({k: v for k, v in pose_data.items() if v is not None})

            if self._validate_data_against_schema(table_config["table_name"], db_data):
                self.written_data[table_config["table_name"]].append(db_data)
                database_names.append(table_config.get("database", "mock_db"))
                table_names.append(table_config["table_name"])

                changes_detected[f"{robot_sn}_pose"] = {
                    'robot_id': robot_sn,
                    'primary_key_values': {'robot_sn': robot_sn},
                    'change_type': 'update',
                    'changed_fields': list(db_data.keys()),
                    'old_values': {},
                    'new_values': db_data,
                    'database_key': f'mock_db_key_{robot_sn}'
                }

                logger.info(f"✅ Mock write robot pose: {robot_sn} -> {table_config['table_name']}")

        return database_names, table_names, changes_detected

    def write_robot_power(self, robot_sn: str, power_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Mock write robot power with validation"""
        logger.info(f"🔍 Testing robot power write for: {robot_sn}")

        table_configs = self.database_config.get("tables", {}).get("robot_status", [])
        database_names = []
        table_names = []
        changes_detected = {}

        for table_config in table_configs:
            db_data = {"robot_sn": robot_sn}
            # Map power to battery_level
            if 'power' in power_data:
                db_data['battery_level'] = power_data['power']
            db_data.update({k: v for k, v in power_data.items() if v is not None and k != 'power'})

            if self._validate_data_against_schema(table_config["table_name"], db_data):
                self.written_data[table_config["table_name"]].append(db_data)
                database_names.append(table_config.get("database", "mock_db"))
                table_names.append(table_config["table_name"])

                changes_detected[f"{robot_sn}_power"] = {
                    'robot_id': robot_sn,
                    'primary_key_values': {'robot_sn': robot_sn},
                    'change_type': 'update',
                    'changed_fields': list(db_data.keys()),
                    'old_values': {},
                    'new_values': db_data,
                    'database_key': f'mock_db_key_{robot_sn}'
                }

                logger.info(f"✅ Mock write robot power: {robot_sn} -> {table_config['table_name']}")

        return database_names, table_names, changes_detected

    def write_robot_event(self, robot_sn: str, event_data: Dict[str, Any]) -> Tuple[List[str], List[str], Dict]:
        """Mock write robot event with validation"""
        logger.info(f"🔍 Testing robot event write for: {robot_sn}")

        table_configs = self.database_config.get("tables", {}).get("robot_events", [])
        database_names = []
        table_names = []
        changes_detected = {}

        for table_config in table_configs:
            db_data = {
                "robot_sn": robot_sn,
                "event_id": event_data.get("error_id", ""),
                "error_id": event_data.get("error_id", ""),
                "event_level": event_data.get("error_level", "").lower(),
                "event_type": event_data.get("error_type", ""),
                "event_detail": event_data.get("error_detail", ""),
                "task_time": event_data.get("timestamp", 0),
                "upload_time": 1640997000,  # Mock current time
            }

            # Remove None values
            db_data = {k: v for k, v in db_data.items() if v is not None}

            if self._validate_data_against_schema(table_config["table_name"], db_data):
                self.written_data[table_config["table_name"]].append(db_data)
                database_names.append(table_config.get("database", "mock_db"))
                table_names.append(table_config["table_name"])

                changes_detected[f"{robot_sn}_event"] = {
                    'robot_id': robot_sn,
                    'primary_key_values': {'robot_sn': robot_sn, 'event_id': event_data.get("error_id", "")},
                    'change_type': 'new_record',
                    'changed_fields': list(db_data.keys()),
                    'old_values': {},
                    'new_values': db_data,
                    'database_key': f'mock_db_key_{robot_sn}_event'
                }

                logger.info(f"✅ Mock write robot event: {robot_sn} -> {table_config['table_name']}")

        return database_names, table_names, changes_detected

    def get_written_data(self, table_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get all written data for testing verification"""
        if table_name:
            return {table_name: self.written_data.get(table_name, [])}
        return dict(self.written_data)

    def clear_written_data(self):
        """Clear all written data for fresh test"""
        self.written_data.clear()
        logger.info("Cleared all mock written data")

    def close_all_connections(self):
        """Close all mock connections"""
        for database_name, conn_info in self.connections.items():
            if isinstance(conn_info, dict) and 'cursor' in conn_info:
                conn_info["cursor"].close()
                conn_info["connection"].close()
            logger.info(f"Closed mock connection to database: {database_name}")

        self.connections.clear()

    def print_summary(self):
        """Print summary of all database operations"""
        logger.info("\n" + "=" * 60)
        logger.info("DATABASE OPERATION SUMMARY")
        logger.info("=" * 60)

        if not self.written_data:
            logger.info("No database operations performed")
            return

        for table_name, records in self.written_data.items():
            logger.info(f"\nTable: {table_name}")
            logger.info(f"Records written: {len(records)}")

            for i, record in enumerate(records, 1):
                logger.info(f"  Record {i}: {record}")

        logger.info("=" * 60)
