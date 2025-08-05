"""
Unit tests for notification sender functionality
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test.mocks.mock_notification import MockNotificationService
from test.utils.test_helpers import TestDataLoader, setup_test_logging


# Mock the notification sender imports
class MockNotificationSender:
    """Mock notification sender for testing"""

    def __init__(self, mock_service):
        self.mock_service = mock_service

    def send_webhook_notification(self, callback_type: str, callback_data: dict, payload: dict, notification_service) -> bool:
        """Send notification using mock service"""
        from notifications.notification_sender import send_webhook_notification

        return send_webhook_notification(callback_type, callback_data, payload, notification_service)

    def generate_webhook_notification_content(self, callback_type: str, callback_data: dict):
        """Generate notification content"""
        from notifications.notification_sender import generate_webhook_notification_content

        return generate_webhook_notification_content(callback_type, callback_data)


class TestNotificationSender:
    """Test notification sender operations"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_service = MockNotificationService()
        self.sender = MockNotificationSender(self.mock_service)
        self.test_data = TestDataLoader()

    def test_robot_status_notifications(self):
        """Test robot status notifications"""
        print("\n🧪 Testing robot status notifications")

        status_data = self.test_data.get_robot_status_data()
        valid_cases = status_data.get("valid_status_changes", [])

        for case in valid_cases[:4]:  # Test first 4 cases
            callback_type = case["callback_type"]
            callback_data = case["data"]
            robot_sn = callback_data["sn"]

            print(f"  Testing notification for: {case['name']}")

            # Clear previous notifications
            self.mock_service.clear_notifications()

            payload = {
                "database_name": "foxx_irvine_office_test",
                "table_name": "robot_status",
                "primary_key_values": {"robot_sn": robot_sn}
            }

            # Send notification
            success = self.sender.send_webhook_notification(callback_type, callback_data, payload, self.mock_service)

            # Validate notification was sent
            assert success == True

            sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
            assert len(sent_notifications) > 0

            # Validate notification content
            notification = sent_notifications[0]
            assert self.mock_service.validate_notification_format(notification)
            assert notification["severity"] == case["expected_severity"]

            print(f"  ✅ Notification validated for {case['name']}")

    def test_robot_error_notifications(self):
        """Test robot error notifications"""
        print("\n🧪 Testing robot error notifications")

        error_data = self.test_data.get_robot_error_data()

        # Test different error types
        for category_name, cases in error_data.items():
            if category_name == "edge_cases":
                continue

            case = cases[0] if cases else None  # Test first case from each category
            if not case:
                continue

            callback_type = case["callback_type"]
            callback_data = case["data"]
            robot_sn = callback_data["sn"]

            print(f"  Testing error notification: {category_name}")

            # Clear previous notifications
            self.mock_service.clear_notifications()

            payload = {
                "database_name": "foxx_irvine_office_test",
                "table_name": "robot_events",
                "primary_key_values": {"robot_sn": robot_sn, "event_id": callback_data["error_id"]}
            }

            # Send notification
            success = self.sender.send_webhook_notification(callback_type, callback_data, payload, self.mock_service)

            # Validate notification was sent
            assert success == True

            sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
            assert len(sent_notifications) > 0

            # Validate notification content
            notification = sent_notifications[0]
            assert self.mock_service.validate_notification_format(notification)
            assert notification["severity"] == case["expected_severity"]

            print(f"  ✅ Error notification validated for {category_name}")

    def test_robot_power_notifications(self):
        """Test robot power notifications"""
        print("\n🧪 Testing robot power notifications")

        power_data = self.test_data.get_robot_power_data()

        # Test low battery alerts
        low_battery_cases = power_data.get("low_battery_alerts", [])
        for case in low_battery_cases:
            callback_type = case["callback_type"]
            callback_data = case["data"]
            robot_sn = callback_data["sn"]

            print(f"  Testing power notification: {case['name']}")

            # Clear previous notifications
            self.mock_service.clear_notifications()

            payload = {
                "database_name": "foxx_irvine_office_test",
                "table_name": "robot_status",
                "primary_key_values": {"robot_sn": robot_sn}
            }

            # Send notification
            success = self.sender.send_webhook_notification(callback_type, callback_data, payload, self.mock_service)

            if case.get("expected_notification", True):
                # Should send notification
                assert success == True

                sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
                assert len(sent_notifications) > 0

                # Validate notification content
                notification = sent_notifications[0]
                assert self.mock_service.validate_notification_format(notification)
                assert notification["severity"] == case["expected_severity"]

                print(f"  ✅ Power notification validated for {case['name']}")
            else:
                # Should not send notification or success is still True but no notifications
                sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
                if len(sent_notifications) == 0:
                    print(f"  ✅ Correctly skipped notification for {case['name']}")
                else:
                    print(f"  ⚠️ Unexpected notification sent for {case['name']}")

    def test_robot_pose_skipping(self):
        """Test that robot pose notifications are skipped"""
        print("\n🧪 Testing robot pose notification skipping")

        pose_data = self.test_data.get_robot_pose_data()
        normal_cases = pose_data.get("normal_positions", [])

        case = normal_cases[0] if normal_cases else None
        if case:
            callback_type = case["callback_type"]
            callback_data = case["data"]
            robot_sn = callback_data["sn"]

            # Clear previous notifications
            self.mock_service.clear_notifications()

            # Send notification (should be skipped)
            payload = {
                "database_name": "foxx_irvine_office_test",
                "table_name": "robot_status",
                "primary_key_values": {"robot_sn": robot_sn}
            }
            success = self.sender.send_webhook_notification(callback_type, callback_data, payload, self.mock_service)

            # Should succeed but not send notification
            assert success == True

            sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
            assert len(sent_notifications) == 0

            print("  ✅ Pose notifications correctly skipped")

    def test_notification_content_generation(self):
        """Test notification content generation"""
        print("\n🧪 Testing notification content generation")

        # Test robot status content
        status_data = {"sn": "TEST_ROBOT_CONTENT", "run_status": "ONLINE"}
        title, content, severity, status = self.sender.generate_webhook_notification_content("robotStatus", status_data)

        assert title is not None
        assert content is not None
        assert severity is not None
        assert status is not None
        assert "TEST_ROBOT_CONTENT" in content
        print("  ✅ Robot status content generation works")

        # Test robot error content
        error_data = {
            "sn": "TEST_ROBOT_ERROR",
            "error_level": "ERROR",
            "error_type": "TestError",
            "error_detail": "Test error detail",
            "error_id": "test_001",
        }
        title, content, severity, status = self.sender.generate_webhook_notification_content("robotErrorWarning", error_data)

        assert title is not None
        assert content is not None
        assert severity == "error"
        assert "TEST_ROBOT_ERROR" in content
        print("  ✅ Robot error content generation works")

        # Test robot power content
        power_data = {"sn": "TEST_ROBOT_POWER", "power": 4, "charge_state": "discharging"}
        title, content, severity, status = self.sender.generate_webhook_notification_content("notifyRobotPower", power_data)

        assert title is not None
        assert content is not None
        assert severity == "fatal"  # Critical battery
        assert "TEST_ROBOT_POWER" in content
        print("  ✅ Robot power content generation works")

    def test_severity_mapping(self):
        """Test severity level mapping"""
        print("\n🧪 Testing severity level mapping")

        severity_tests = [("FATAL", "fatal"), ("ERROR", "error"), ("WARNING", "warning"), ("INFO", "event")]

        for input_level, expected_severity in severity_tests:
            error_data = {
                "sn": "TEST_ROBOT_SEVERITY",
                "error_level": input_level,
                "error_type": "TestError",
                "error_detail": f"Testing {input_level}",
                "error_id": f"test_{input_level.lower()}",
            }

            title, content, severity, status = self.sender.generate_webhook_notification_content(
                "robotErrorWarning", error_data
            )

            assert severity == expected_severity
            print(f"  ✅ {input_level} -> {expected_severity} mapping correct")

    def test_battery_threshold_notifications(self):
        """Test battery threshold notifications"""
        print("\n🧪 Testing battery threshold notifications")

        battery_tests = [
            (3, "fatal"),  # Critical
            (8, "error"),  # Low
            (15, "warning"),  # Warning
            (50, None),  # Normal (no notification)
        ]

        for battery_level, expected_severity in battery_tests:
            power_data = {"sn": f"TEST_ROBOT_BATTERY_{battery_level}", "power": battery_level, "charge_state": "discharging"}

            title, content, severity, status = self.sender.generate_webhook_notification_content(
                "notifyRobotPower", power_data
            )

            if expected_severity:
                assert severity == expected_severity
                print(f"  ✅ Battery {battery_level}% -> {expected_severity} notification")
            else:
                assert title is None  # No notification for normal levels
                print(f"  ✅ Battery {battery_level}% correctly skipped")

    def test_notification_service_connectivity(self):
        """Test notification service connectivity"""
        print("\n🧪 Testing notification service connectivity")

        # Test connection
        connection_success = self.mock_service.test_connection()
        assert connection_success == True
        print("  ✅ Mock notification service connection test passed")

        # Verify connection attempts were logged
        attempts = self.mock_service.connection_attempts
        assert len(attempts) > 0
        assert attempts[-1]["success"] == True
        print("  ✅ Connection attempts properly logged")

    def test_notification_format_validation(self):
        """Test notification format validation"""
        print("\n🧪 Testing notification format validation")

        # Valid notification
        valid_notification = {
            "robot_id": "TEST_ROBOT",
            "notification_type": "robot_status",
            "title": "Test Title",
            "content": "Test Content",
            "severity": "success",
            "status": "online",
        }

        assert self.mock_service.validate_notification_format(valid_notification) == True
        print("  ✅ Valid notification format accepted")

        # Invalid notification (missing field)
        invalid_notification = {
            "robot_id": "TEST_ROBOT",
            "title": "Test Title",
            # Missing required fields
        }

        assert self.mock_service.validate_notification_format(invalid_notification) == False
        print("  ✅ Invalid notification format rejected")

        # Invalid severity
        invalid_severity = {
            "robot_id": "TEST_ROBOT",
            "notification_type": "robot_status",
            "title": "Test Title",
            "content": "Test Content",
            "severity": "invalid_severity",
            "status": "online",
        }

        assert self.mock_service.validate_notification_format(invalid_severity) == False
        print("  ✅ Invalid severity rejected")


# Test runner function
def run_notification_tests():
    """Run all notification sender tests"""
    setup_test_logging("INFO")

    print("=" * 60)
    print("RUNNING NOTIFICATION SENDER TESTS")
    print("=" * 60)

    test_instance = TestNotificationSender()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    total_tests = 0
    passed_tests = 0

    for method_name in test_methods:
        total_tests += 1
        try:
            test_instance.setup_method()
            method = getattr(test_instance, method_name)
            method()
            passed_tests += 1
            print(f"✅ {method_name} - PASSED")
        except Exception as e:
            print(f"❌ {method_name} - FAILED: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # Print notification summary after each test
            test_instance.mock_service.print_summary()

    print(f"\n{'='*60}")
    print("NOTIFICATION TESTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_notification_tests()
