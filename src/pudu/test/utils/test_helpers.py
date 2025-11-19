"""
Test utility functions and helpers for loading JSON test data
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class TestDataLoader:
    """Load comprehensive test data from JSON files"""

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

    def get_comprehensive_data(self) -> Dict:
        """Get comprehensive test scenarios"""
        return self.load_test_data("comprehensive_test_data.json")

    def get_all_robots_from_status_data(self) -> List[Dict]:
        """Get all robot records from status data (valid + edge cases)"""
        status_data = self.get_robot_status_data()
        all_robots = []
        all_robots.extend(status_data.get("valid_robots", []))
        all_robots.extend(status_data.get("edge_cases", []))
        return all_robots

    def get_all_tasks_from_task_data(self) -> List[Dict]:
        """Get all task records from task data"""
        task_data = self.get_robot_task_data()
        return task_data.get("valid_tasks", [])

    def get_all_charging_sessions(self) -> List[Dict]:
        """Get all charging session records"""
        charging_data = self.get_robot_charging_data()
        all_sessions = []
        all_sessions.extend(charging_data.get("valid_charging_sessions", []))
        all_sessions.extend(charging_data.get("edge_cases", []))
        return all_sessions

    def get_all_events(self) -> List[Dict]:
        """Get all event records (valid + severity levels)"""
        event_data = self.get_robot_event_data()
        all_events = []
        all_events.extend(event_data.get("valid_events", []))
        all_events.extend(event_data.get("severity_levels", []))
        return all_events

    def get_all_locations(self) -> List[Dict]:
        """Get all location records (valid + edge cases)"""
        location_data = self.get_location_data()
        all_locations = []
        all_locations.extend(location_data.get("valid_locations", []))
        all_locations.extend(location_data.get("edge_cases", []))
        return all_locations

    def get_robots_by_battery_level(self, min_level: int = None, max_level: int = None) -> List[Dict]:
        """Get robots filtered by battery level range"""
        all_robots = self.get_all_robots_from_status_data()
        filtered = []

        for robot in all_robots:
            battery = robot.get('battery_level')
            if battery is not None:
                if min_level is not None and battery < min_level:
                    continue
                if max_level is not None and battery > max_level:
                    continue
                filtered.append(robot)

        return filtered

    def get_robots_by_status(self, status: str) -> List[Dict]:
        """Get robots filtered by status"""
        all_robots = self.get_all_robots_from_status_data()
        return [robot for robot in all_robots if robot.get('status', '').lower() == status.lower()]

    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """Get tasks filtered by status"""
        all_tasks = self.get_all_tasks_from_task_data()
        return [task for task in all_tasks if task.get('status', '').lower() == status.lower()]

    def get_events_by_level(self, level: str) -> List[Dict]:
        """Get events filtered by event level"""
        all_events = self.get_all_events()
        return [event for event in all_events if event.get('event_level', '').lower() == level.lower()]

    def get_test_robot_by_sn(self, robot_sn: str) -> Dict:
        """Get specific robot data by serial number"""
        all_robots = self.get_all_robots_from_status_data()
        for robot in all_robots:
            if robot.get("robot_sn") == robot_sn:
                return robot
        return {}

    def get_decimal_precision_test_cases(self) -> List[Dict]:
        """Extract decimal precision test cases from all JSON data"""
        test_cases = []

        # From robot status data
        for robot in self.get_all_robots_from_status_data():
            for field in ['battery_level', 'water_level', 'sewage_level', 'x', 'y', 'z']:
                if field in robot and robot[field] is not None:
                    test_cases.append({
                        'value': robot[field],
                        'field': field,
                        'source': 'robot_status',
                        'robot_sn': robot.get('robot_sn', 'unknown')
                    })

        # From task data
        for task in self.get_all_tasks_from_task_data():
            for field in ['actual_area', 'plan_area', 'progress', 'efficiency']:
                if field in task and task[field] is not None:
                    test_cases.append({
                        'value': task[field],
                        'field': field,
                        'source': 'robot_task',
                        'robot_sn': task.get('robot_sn', 'unknown')
                    })

        return test_cases

class TestValidator:
    """Validate test results and expectations"""

    @staticmethod
    def validate_robot_data(robot_data: Dict, required_fields: List[str]) -> bool:
        """Validate robot data has expected fields"""
        for field in required_fields:
            if field not in robot_data:
                logger.error(f"Missing required field: {field} in robot data")
                return False
        return True

    @staticmethod
    def validate_change_detection_result(changes: Dict, expected_count: int = None,
                                       expected_change_types: List[str] = None) -> bool:
        """Validate change detection results"""
        if expected_count is not None and len(changes) != expected_count:
            logger.error(f"Expected {expected_count} changes, got {len(changes)}")
            return False

        if expected_change_types:
            actual_types = [change['change_type'] for change in changes.values()]
            for expected_type in expected_change_types:
                if expected_type not in actual_types:
                    logger.error(f"Expected change type '{expected_type}' not found")
                    return False

        return True

    @staticmethod
    def validate_notification_content(title: str, content: str, expected_keywords: List[str]) -> bool:
        """Validate notification content contains expected keywords"""
        full_text = f"{title} {content}".lower()
        for keyword in expected_keywords:
            if keyword.lower() not in full_text:
                logger.error(f"Expected keyword '{keyword}' not found in notification")
                return False
        return True

def setup_test_logging(level: str = "INFO"):
    """Setup logging for tests"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )