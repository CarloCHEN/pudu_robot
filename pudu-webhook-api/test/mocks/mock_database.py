"""
Mock Database Service for Testing
Validates database operations without requiring actual database connection
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional
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
    Performs comprehensive validation of field mappings and constraints
    """

    def __init__(self, config_path: str = "database_config.yaml", credentials_path: str = "credentials.yaml"):
        self.config_path = config_path
        self.credentials_path = credentials_path
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
            "databases": ["foxx_irvine_office"],
            "tables": {
                "robot_status": [{"database": "foxx_irvine_office", "table_name": "mnt_robots_management", "primary_keys": ["robot_sn"]}],
                "robot_events": [
                    {"database": "foxx_irvine_office", "table_name": "mnt_robot_events", "primary_keys": ["robot_sn", "event_id"]}
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
                    "z",
                    "yaw",
                    "charge_state",
                    "last_updated",
                ],
                "primary_keys": ["robot_sn"],
                "field_types": {
                    "robot_sn": "VARCHAR(50)",
                    "status": "VARCHAR(50)",
                    "battery_level": "INT",
                    "x": "DECIMAL(10,6)",
                    "y": "DECIMAL(10,6)",
                    "yaw": "DECIMAL(10,6)",
                    "charge_state": "VARCHAR(50)",
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

    def _get_connection(self, database_name: str):
        """Get mock database connection"""
        if database_name not in self.connections:
            connection = MockDatabaseConnection()
            self.connections[database_name] = {"connection": connection, "cursor": connection.cursor()}
            logger.info(f"Mock connection established to database: {database_name}")

        return self.connections[database_name]

    def _validate_data_against_schema(self, table_name: str, data: Dict[str, Any]) -> bool:
        """Validate data against table schema"""
        if table_name not in self.table_schemas:
            logger.warning(f"No schema defined for table: {table_name}")
            return False

        schema = self.table_schemas[table_name]

        # Check if all provided fields exist in schema
        for field in data.keys():
            if field not in schema["fields"]:
                logger.error(f"Field '{field}' not found in {table_name} schema. Available fields: {schema['fields']}")
                return False

        # Validate primary keys are present for upsert operations
        for pk in schema["primary_keys"]:
            if pk not in data:
                logger.error(f"Primary key '{pk}' missing in data for table {table_name}")
                return False

        logger.info(f"✅ Data validation passed for table {table_name}")
        return True

    def _validate_config_consistency(self, table_type: str) -> bool:
        """Validate that configuration matches expected table schema"""
        table_configs = self.database_config.get("tables", {}).get(table_type, [])

        for config in table_configs:
            table_name = config["table_name"]
            config_primary_keys = config["primary_keys"]

            if table_name in self.table_schemas:
                schema_primary_keys = self.table_schemas[table_name]["primary_keys"]

                if set(config_primary_keys) != set(schema_primary_keys):
                    logger.error(f"❌ Primary key mismatch for {table_name}")
                    logger.error(f"   Config: {config_primary_keys}")
                    logger.error(f"   Schema: {schema_primary_keys}")
                    return False
                else:
                    logger.info(f"✅ Primary key validation passed for {table_name}")

        return True

    def write_robot_status(self, robot_sn: str, status_data: Dict[str, Any]):
        """Mock write robot status with validation"""
        logger.info(f"🔍 Testing robot status write for: {robot_sn}")

        # Validate configuration consistency
        if not self._validate_config_consistency("robot_status"):
            logger.error("❌ Configuration validation failed for robot_status")
            return

        table_configs = self.database_config.get("tables", {}).get("robot_status", [])
        database_names = set()
        table_names = set()
        for table_config in table_configs:
            db_data = {"robot_sn": robot_sn, "status": status_data.get("status", "")}

            # Remove None values
            db_data = {k: v for k, v in db_data.items() if v is not None}

            if self._validate_data_against_schema(table_config["table_name"], db_data):
                self.written_data[table_config["table_name"]].append(db_data)
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"✅ Mock write robot status: {robot_sn} -> {table_config['table_name']}")
                logger.info(f"   Data written: {db_data}")
            else:
                logger.error(f"❌ Schema validation failed for robot status write")

        return list(database_names), list(table_names)

    def write_robot_pose(self, robot_sn: str, pose_data: Dict[str, Any]):
        """Mock write robot pose with validation"""
        logger.info(f"🔍 Testing robot pose write for: {robot_sn}")

        table_configs = self.database_config.get("tables", {}).get("robot_status", [])
        database_names = set()
        table_names = set()
        for table_config in table_configs:
            db_data = {"robot_sn": robot_sn, "x": pose_data.get("x"), "y": pose_data.get("y"), "yaw": pose_data.get("yaw")}

            # Remove None values
            db_data = {k: v for k, v in db_data.items() if v is not None}

            if self._validate_data_against_schema(table_config["table_name"], db_data):
                self.written_data[table_config["table_name"]].append(db_data)
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"✅ Mock write robot pose: {robot_sn} -> {table_config['table_name']}")
                logger.info(f"   Data written: {db_data}")
            else:
                logger.error(f"❌ Schema validation failed for robot pose write")
        return list(database_names), list(table_names)

    def write_robot_power(self, robot_sn: str, power_data: Dict[str, Any]):
        """Mock write robot power with validation"""
        logger.info(f"🔍 Testing robot power write for: {robot_sn}")

        table_configs = self.database_config.get("tables", {}).get("robot_status", [])
        database_names = set()
        table_names = set()
        for table_config in table_configs:
            db_data = {
                "robot_sn": robot_sn,
                "battery_level": power_data.get("power"),
                "charge_state": power_data.get("charge_state"),
            }

            # Remove None values
            db_data = {k: v for k, v in db_data.items() if v is not None}

            if self._validate_data_against_schema(table_config["table_name"], db_data):
                self.written_data[table_config["table_name"]].append(db_data)
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"✅ Mock write robot power: {robot_sn} -> {table_config['table_name']}")
                logger.info(f"   Data written: {db_data}")
            else:
                logger.error(f"❌ Schema validation failed for robot power write")
        return list(database_names), list(table_names)

    def write_robot_event(self, robot_sn: str, event_data: Dict[str, Any]):
        """Mock write robot event with validation"""
        logger.info(f"🔍 Testing robot event write for: {robot_sn}")

        # Validate configuration consistency
        if not self._validate_config_consistency("robot_events"):
            logger.error("❌ Configuration validation failed for robot_events")
            return

        table_configs = self.database_config.get("tables", {}).get("robot_events", [])
        database_names = set()
        table_names = set()
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
                database_names.add(table_config["database"])
                table_names.add(table_config["table_name"])
                logger.info(f"✅ Mock write robot event: {robot_sn} -> {table_config['table_name']}")
                logger.info(f"   Data written: {db_data}")
            else:
                logger.error(f"❌ Schema validation failed for robot event write")
        return list(database_names), list(table_names)

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
