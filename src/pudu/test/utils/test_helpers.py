"""
Test utility functions and helpers
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

class TestDataLoader:
    """Load test data from JSON files"""

    def __init__(self, test_data_dir: str = "test_data"):
        self.test_data_dir = Path(__file__).parent.parent / test_data_dir
        self.loaded_data = {}

    def load_test_data(self, filename: str) -> Dict[str, Any]:
        """Load test data from JSON file"""
        if filename in self.loaded_data:
            return self.loaded_data[filename]

        file_path = self.test_data_dir / filename
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.loaded_data[filename] = data
                logger.info(f"Loaded test data from {filename}")
                return data
        except FileNotFoundError:
            logger.error(f"Test data file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in test data file {filename}: {e}")
            return {}

    def get_robot_status_data(self) -> Dict:
        """Get robot status test data"""
        return self.load_test_data("robot_status_data.json")

    def get_robot_task_data(self) -> Dict:
        """Get robot task test data"""
        return self.load_test_data("robot_task_data.json")

    def get_robot_charging_data(self) -> Dict:
        """Get robot charging test data"""
        return self.load_test_data("robot_charging_data.json")

    def get_robot_event_data(self) -> Dict:
        """Get robot event test data"""
        return self.load_test_data("robot_event_data.json")

    def get_location_data(self) -> Dict:
        """Get location test data"""
        return self.load_test_data("location_data.json")

    def get_all_test_robots(self) -> list:
        """Get all robot serial numbers from test data"""
        robots = []

        # From status data
        status_data = self.get_robot_status_data()
        robots.extend([r.get("robot_sn") for r in status_data.get("valid_robots", []) if r.get("robot_sn")])

        # From task data
        task_data = self.get_robot_task_data()
        robots.extend([t.get("robot_sn") for t in task_data.get("valid_tasks", []) if t.get("robot_sn")])

        return list(set(robots))  # Remove duplicates

    def get_test_robot_by_sn(self, robot_sn: str) -> Dict:
        """Get specific robot data by serial number"""
        status_data = self.get_robot_status_data()

        # Check valid robots
        for robot in status_data.get("valid_robots", []):
            if robot.get("robot_sn") == robot_sn:
                return robot

        # Check edge cases
        for robot in status_data.get("edge_cases", []):
            if robot.get("robot_sn") == robot_sn:
                return robot

        return {}

def setup_test_logging(level: str = "INFO"):
    """Setup logging for tests"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )

class TestValidator:
    """Validate test results and expectations"""

    @staticmethod
    def validate_robot_data(robot_data: Dict, expected_fields: list) -> bool:
        """Validate robot data has expected fields"""
        for field in expected_fields:
            if field not in robot_data:
                logger.error(f"Missing field: {field}")
                return False
        return True

    @staticmethod
    def validate_database_insert(stored_data: list, original_data: list, primary_keys: list) -> bool:
        """Validate that data was stored correctly"""
        if len(stored_data) != len(original_data):
            logger.error(f"Data count mismatch: {len(stored_data)} vs {len(original_data)}")
            return False

        for original in original_data:
            # Find matching record in stored data
            match = None
            for stored in stored_data:
                if all(stored.get(pk) == original.get(pk) for pk in primary_keys):
                    match = stored
                    break

            if not match:
                logger.error(f"No matching stored record for: {original}")
                return False

        return True