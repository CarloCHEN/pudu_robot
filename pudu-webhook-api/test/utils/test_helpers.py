"""
Test utility functions and helpers
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestDataLoader:
    """Load and manage test data from JSON files"""

    def __init__(self, test_data_dir: str = "test_data"):
        self.test_data_dir = Path(__file__).parent.parent / test_data_dir
        self.loaded_data = {}

    def load_test_data(self, filename: str) -> Dict[str, Any]:
        """Load test data from JSON file"""
        if filename in self.loaded_data:
            return self.loaded_data[filename]

        file_path = self.test_data_dir / filename
        try:
            with open(file_path, "r") as f:
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

    def get_robot_status_data(self) -> Dict[str, List[Dict]]:
        """Get robot status test cases"""
        return self.load_test_data("robot_status_data.json")

    def get_robot_error_data(self) -> Dict[str, List[Dict]]:
        """Get robot error test cases"""
        return self.load_test_data("robot_error_data.json")

    def get_robot_pose_data(self) -> Dict[str, List[Dict]]:
        """Get robot pose test cases"""
        return self.load_test_data("robot_pose_data.json")

    def get_robot_power_data(self) -> Dict[str, List[Dict]]:
        """Get robot power test cases"""
        return self.load_test_data("robot_power_data.json")

    def get_all_test_cases(self) -> List[Dict[str, Any]]:
        """Get all test cases from all data files"""
        all_cases = []

        # Load all data types
        status_data = self.get_robot_status_data()
        error_data = self.get_robot_error_data()
        pose_data = self.get_robot_pose_data()
        power_data = self.get_robot_power_data()

        # Combine all test cases
        for category_name, cases in status_data.items():
            for case in cases:
                case["category"] = f"status_{category_name}"
                all_cases.append(case)

        for category_name, cases in error_data.items():
            for case in cases:
                case["category"] = f"error_{category_name}"
                all_cases.append(case)

        for category_name, cases in pose_data.items():
            for case in cases:
                case["category"] = f"pose_{category_name}"
                all_cases.append(case)

        for category_name, cases in power_data.items():
            for case in cases:
                case["category"] = f"power_{category_name}"
                all_cases.append(case)

        logger.info(f"Loaded {len(all_cases)} total test cases")
        return all_cases


class TestValidator:
    """Validate test results and expectations"""

    @staticmethod
    def validate_callback_response(response: Dict[str, Any], expected_status: str = "success") -> bool:
        """Validate callback response structure and status"""
        required_fields = ["status", "message", "timestamp"]

        for field in required_fields:
            if field not in response:
                logger.error(f"❌ Missing required field in response: {field}")
                return False

        if response["status"] != expected_status:
            logger.error(f"❌ Expected status '{expected_status}', got '{response['status']}'")
            return False

        logger.info(f"✅ Callback response validation passed")
        return True

    @staticmethod
    def validate_database_write(written_data: Dict[str, List[Dict]], expected_table: str, expected_robot_sn: str) -> bool:
        """Validate that data was written to expected database table"""
        if expected_table not in written_data:
            logger.error(f"❌ No data written to expected table: {expected_table}")
            return False

        table_data = written_data[expected_table]
        if not table_data:
            logger.error(f"❌ No records found in table: {expected_table}")
            return False

        # Find record for specific robot
        robot_records = [r for r in table_data if r.get("robot_sn") == expected_robot_sn]
        if not robot_records:
            logger.error(f"❌ No records found for robot: {expected_robot_sn}")
            return False

        logger.info(f"✅ Database write validation passed for {expected_robot_sn} in {expected_table}")
        return True

    @staticmethod
    def validate_notification_sent(
        sent_notifications: List[Dict], expected_robot_id: str, expected_severity: Optional[str] = None
    ) -> bool:
        """Validate that notification was sent for robot"""
        robot_notifications = [n for n in sent_notifications if n["robot_id"] == expected_robot_id]

        if not robot_notifications:
            logger.error(f"❌ No notifications sent for robot: {expected_robot_id}")
            return False

        if expected_severity:
            severity_matches = [n for n in robot_notifications if n["severity"] == expected_severity]
            if not severity_matches:
                logger.error(f"❌ No notifications with severity '{expected_severity}' for robot: {expected_robot_id}")
                logger.error(f"   Found severities: {[n['severity'] for n in robot_notifications]}")
                return False

        logger.info(f"✅ Notification validation passed for {expected_robot_id}")
        return True


class TestReporter:
    """Generate test reports and summaries"""

    def __init__(self):
        self.test_results = []
        self.start_time = time.time()

    def add_test_result(self, test_name: str, success: bool, details: Optional[Dict] = None):
        """Add test result"""
        result = {"test_name": test_name, "success": success, "timestamp": time.time(), "details": details or {}}
        self.test_results.append(result)

    def print_summary(self):
        """Print comprehensive test summary"""
        end_time = time.time()
        duration = end_time - self.start_time

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests

        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests")
        logger.info(f"Duration: {duration:.2f} seconds")

        if failed_tests > 0:
            logger.info(f"\nFAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    logger.error(f"❌ {result['test_name']}")
                    if result["details"]:
                        for key, value in result["details"].items():
                            logger.error(f"   {key}: {value}")

        logger.info("\nTEST DETAILS:")
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            logger.info(f"{status} {result['test_name']}")

        logger.info("=" * 80)

    def get_failed_tests(self) -> List[Dict]:
        """Get list of failed tests"""
        return [r for r in self.test_results if not r["success"]]

    def get_success_rate(self) -> float:
        """Get test success rate"""
        if not self.test_results:
            return 0.0
        return sum(1 for r in self.test_results if r["success"]) / len(self.test_results)


class CallbackBuilder:
    """Build callback payloads for testing"""

    @staticmethod
    def build_robot_status(robot_sn: str, status: str, timestamp: Optional[int] = None) -> Dict[str, Any]:
        """Build robot status callback"""
        return {
            "callback_type": "robotStatus",
            "data": {"sn": robot_sn, "run_status": status, "timestamp": timestamp or int(time.time())},
        }

    @staticmethod
    def build_robot_error(
        robot_sn: str, error_level: str, error_type: str, error_detail: str, error_id: str, timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build robot error callback"""
        return {
            "callback_type": "robotErrorWarning",
            "data": {
                "sn": robot_sn,
                "error_level": error_level,
                "error_type": error_type,
                "error_detail": error_detail,
                "error_id": error_id,
                "timestamp": timestamp or int(time.time()),
            },
        }

    @staticmethod
    def build_robot_pose(
        robot_sn: str, x: float, y: float, yaw: float, mac: Optional[str] = None, timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build robot pose callback"""
        return {
            "callback_type": "notifyRobotPose",
            "data": {
                "sn": robot_sn,
                "mac": mac or "B0:0C:9D:59:16:E0",
                "x": x,
                "y": y,
                "yaw": yaw,
                "timestamp": timestamp or int(time.time()),
            },
        }

    @staticmethod
    def build_robot_power(
        robot_sn: str, power: int, charge_state: str, mac: Optional[str] = None, timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build robot power callback"""
        return {
            "callback_type": "notifyRobotPower",
            "data": {
                "sn": robot_sn,
                "mac": mac or "B0:0C:9D:59:16:E0",
                "power": power,
                "charge_state": charge_state,
                "timestamp": timestamp or int(time.time()),
            },
        }


def setup_test_logging(level: str = "DEBUG"):
    """Setup logging for tests"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Reduce noise from some modules
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
