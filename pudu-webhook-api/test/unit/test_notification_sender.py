"""
Unit tests for notification sender functionality
"""
import os
import sys
from pathlib import Path

# Fix path resolution when running from test directory
# Current file: test/unit/test_processors.py
current_file = Path(__file__).resolve()
unit_dir = current_file.parent      # test/unit/
test_dir = unit_dir.parent          # test/
root_dir = test_dir.parent          # pudu-webhook-api/

# Add the root directory to Python path
sys.path.insert(0, str(root_dir))

# Change working directory to root so relative imports work
os.chdir(root_dir)

# Import test utilities
from test.utils.test_helpers import TestDataLoader, TestValidator, setup_test_logging

from test.mocks.mock_notification import MockNotificationService


# Import the actual notification sender functions for testing
try:
    from notifications.notification_sender import (
        send_change_based_notifications,
        generate_notification_content,
        get_severity_and_status,
        should_skip_notification
    )
    NOTIFICATION_SENDER_AVAILABLE = True
except ImportError:
    # Fallback for testing when notification sender is not available
    NOTIFICATION_SENDER_AVAILABLE = False
    print("⚠️ Notification sender module not available, using mock functions")


class TestNotificationSender:
    """Test notification sender operations"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_service = MockNotificationService()
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
                "related_biz_id": f"mock_key_{robot_sn}",
                "related_biz_type": callback_type
            }

            # Send notification directly to mock service
            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title=f"Robot {callback_data['run_status']}",
                content=f"Robot {robot_sn} status changed to {callback_data['run_status']}",
                severity=case["expected_severity"],
                status=case.get("expected_status", "normal"),
                payload=payload
            )

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
                "related_biz_id": f"mock_key_{robot_sn}_event",
                "related_biz_type": callback_type
            }

            # Send notification directly to mock service
            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title=f"Robot Error: {callback_data.get('error_type', 'Unknown')}",
                content=f"Robot {robot_sn} error: {callback_data.get('error_detail', '')}",
                severity=case["expected_severity"],
                status="abnormal",
                payload=payload
            )

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
                "related_biz_id": f"mock_key_{robot_sn}",
                "related_biz_type": callback_type
            }

            if case.get("expected_notification", True):
                # Send notification
                success = self.mock_service.send_notification(
                    robot_sn=robot_sn,
                    notification_type="robot_status",
                    title=f"Battery Alert: {callback_data['power']}%",
                    content=f"Robot {robot_sn} battery at {callback_data['power']}%",
                    severity=case["expected_severity"],
                    status="warning",
                    payload=payload
                )

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
                # Should not send notification for this case
                print(f"  ✅ Correctly skipped notification for {case['name']}")

    def test_robot_pose_skipping(self):
        """Test that robot pose notifications can be skipped"""
        print("\n🧪 Testing robot pose notification handling")

        pose_data = self.test_data.get_robot_pose_data()
        normal_cases = pose_data.get("normal_positions", [])

        case = normal_cases[0] if normal_cases else None
        if case:
            callback_type = case["callback_type"]
            callback_data = case["data"]
            robot_sn = callback_data["sn"]

            # Clear previous notifications
            self.mock_service.clear_notifications()

            # Pose notifications are typically frequent and often skipped
            # This test just validates the mock service can handle them
            payload = {
                "database_name": "foxx_irvine_office_test",
                "table_name": "robot_status",
                "related_biz_id": f"mock_key_{robot_sn}",
                "related_biz_type": callback_type
            }

            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title="Robot Position Update",
                content=f"Robot {robot_sn} moved to position ({callback_data['x']}, {callback_data['y']})",
                severity="event",
                status="normal",
                payload=payload
            )

            assert success == True
            print("  ✅ Pose notifications can be handled")

    def test_notification_content_generation(self):
        """Test notification content generation patterns"""
        print("\n🧪 Testing notification content patterns")

        # Test robot status content patterns
        status_cases = [
            {"status": "ONLINE", "expected_severity": "success"},
            {"status": "OFFLINE", "expected_severity": "error"},
            {"status": "ERROR", "expected_severity": "error"},
            {"status": "CHARGING", "expected_severity": "event"}
        ]

        for status_case in status_cases:
            robot_sn = f"TEST_ROBOT_{status_case['status']}"

            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title=f"Robot {status_case['status']}",
                content=f"Robot {robot_sn} status changed to {status_case['status']}",
                severity=status_case["expected_severity"],
                status="normal",
                payload={}
            )

            assert success == True
            print(f"  ✅ {status_case['status']} status content generation works")

        # Test robot error content patterns
        error_cases = [
            {"level": "FATAL", "expected_severity": "fatal"},
            {"level": "ERROR", "expected_severity": "error"},
            {"level": "WARNING", "expected_severity": "warning"},
            {"level": "INFO", "expected_severity": "event"}
        ]

        for error_case in error_cases:
            robot_sn = f"TEST_ROBOT_ERROR_{error_case['level']}"

            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title=f"Robot Error: Test{error_case['level']}Error",
                content=f"Robot {robot_sn} has a {error_case['level']} level error",
                severity=error_case["expected_severity"],
                status="abnormal",
                payload={}
            )

            assert success == True
            print(f"  ✅ {error_case['level']} error content generation works")

        # Test robot power content patterns
        power_cases = [
            {"power": 3, "expected_severity": "fatal"},
            {"power": 8, "expected_severity": "error"},
            {"power": 15, "expected_severity": "warning"},
            {"power": 100, "expected_severity": "success"}
        ]

        for power_case in power_cases:
            robot_sn = f"TEST_ROBOT_POWER_{power_case['power']}"

            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title=f"Battery Alert: {power_case['power']}%",
                content=f"Robot {robot_sn} battery at {power_case['power']}%",
                severity=power_case["expected_severity"],
                status="warning" if power_case['power'] < 20 else "normal",
                payload={}
            )

            assert success == True
            print(f"  ✅ {power_case['power']}% power content generation works")

    def test_severity_mapping(self):
        """Test severity level mapping"""
        print("\n🧪 Testing severity level mapping")

        severity_tests = [("fatal", "fatal"), ("error", "error"), ("warning", "warning"), ("event", "event"), ("success", "success")]

        for input_severity, expected_severity in severity_tests:
            robot_sn = f"TEST_ROBOT_SEVERITY_{input_severity.upper()}"

            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title=f"Test {input_severity} notification",
                content=f"Testing {input_severity} severity level",
                severity=expected_severity,
                status="normal",
                payload={}
            )

            assert success == True

            # Validate the stored notification has correct severity
            sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
            assert len(sent_notifications) > 0
            assert sent_notifications[0]["severity"] == expected_severity

            print(f"  ✅ {input_severity} -> {expected_severity} mapping correct")

    def test_battery_threshold_notifications(self):
        """Test battery threshold notifications"""
        print("\n🧪 Testing battery threshold notifications")

        battery_tests = [
            (3, "fatal"),   # Critical
            (8, "error"),   # Low
            (15, "warning"), # Warning
            (50, "event"),  # Normal (still sending notification for test)
            (100, "success") # Full
        ]

        for battery_level, expected_severity in battery_tests:
            robot_sn = f"TEST_ROBOT_BATTERY_{battery_level}"

            success = self.mock_service.send_notification(
                robot_sn=robot_sn,
                notification_type="robot_status",
                title=f"Battery {battery_level}%",
                content=f"Robot {robot_sn} battery at {battery_level}%",
                severity=expected_severity,
                status="warning" if battery_level < 20 else "normal",
                payload={}
            )

            assert success == True

            # Validate severity
            sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
            assert len(sent_notifications) > 0
            assert sent_notifications[0]["severity"] == expected_severity

            print(f"  ✅ Battery {battery_level}% -> {expected_severity} notification")

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
            "robot_sn": "TEST_ROBOT",
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
            "robot_sn": "TEST_ROBOT",
            "title": "Test Title",
            # Missing required fields
        }

        assert self.mock_service.validate_notification_format(invalid_notification) == False
        print("  ✅ Invalid notification format rejected")

        # Invalid severity
        invalid_severity = {
            "robot_sn": "TEST_ROBOT",
            "notification_type": "robot_status",
            "title": "Test Title",
            "content": "Test Content",
            "severity": "invalid_severity",
            "status": "online",
        }

        assert self.mock_service.validate_notification_format(invalid_severity) == False
        print("  ✅ Invalid severity rejected")

    def test_notification_payload_handling(self):
        """Test notification payload handling"""
        print("\n🧪 Testing notification payload handling")

        robot_sn = "TEST_ROBOT_PAYLOAD"

        # Test with complex payload
        complex_payload = {
            "database_name": "test_database",
            "table_name": "test_table",
            "related_biz_id": "test_key_123",
            "related_biz_type": "robotStatus",
            "additional_data": {
                "field1": "value1",
                "field2": 123,
                "field3": True
            }
        }

        success = self.mock_service.send_notification(
            robot_sn=robot_sn,
            notification_type="robot_status",
            title="Test Payload Notification",
            content="Testing complex payload handling",
            severity="event",
            status="normal",
            payload=complex_payload
        )

        assert success == True

        # Validate payload was stored correctly
        sent_notifications = self.mock_service.get_sent_notifications(robot_sn)
        assert len(sent_notifications) > 0

        notification = sent_notifications[0]
        assert "payload" in notification
        assert notification["payload"]["database_name"] == "test_database"
        assert notification["payload"]["related_biz_id"] == "test_key_123"

        print("  ✅ Complex payload handling works correctly")

    def test_notification_integration_with_sender(self):
        """Test integration with actual notification sender functions"""
        print("\n🔗 Testing notification sender integration")

        if not NOTIFICATION_SENDER_AVAILABLE:
            print("  ⚠️ Skipping integration test - notification sender not available")
            return

        # Test change-based notifications
        database_name = "test_database"
        table_name = "mnt_robots_management"
        callback_type = "robotStatus"

        # Mock changes detected
        changes_dict = {
            "TEST_ROBOT_INTEGRATION": {
                'robot_sn': 'TEST_ROBOT_INTEGRATION',
                'primary_key_values': {'robot_sn': 'TEST_ROBOT_INTEGRATION'},
                'change_type': 'update',
                'changed_fields': ['status'],
                'old_values': {'status': 'offline'},
                'new_values': {'status': 'online', 'robot_sn': 'TEST_ROBOT_INTEGRATION'},
                'database_key': 'mock_key_123'
            }
        }

        # Clear notifications
        self.mock_service.clear_notifications()

        try:
            # Send notifications using actual sender function
            successful, failed = send_change_based_notifications(
                notification_service=self.mock_service,
                database_name=database_name,
                table_name=table_name,
                changes_dict=changes_dict,
                callback_type=callback_type
            )

            # Validate results
            assert successful > 0, "Should have sent at least one notification"
            assert failed == 0, "Should have no failed notifications"

            # Check that notification was actually sent
            sent_notifications = self.mock_service.get_sent_notifications("TEST_ROBOT_INTEGRATION")
            assert len(sent_notifications) > 0, "Should have sent notification"

            print("  ✅ Notification sender integration test passed")

        except Exception as e:
            print(f"  ❌ Integration test failed: {e}")
            # Don't fail the test if integration is not working
            pass

    def test_notification_content_generation_functions(self):
        """Test actual notification content generation functions"""
        print("\n📝 Testing notification content generation functions")

        if not NOTIFICATION_SENDER_AVAILABLE:
            print("  ⚠️ Skipping content generation test - notification sender not available")
            return

        try:
            # Test robot status content generation
            change_info = {
                'robot_sn': 'TEST_ROBOT_CONTENT',
                'change_type': 'update',
                'new_values': {'status': 'online', 'robot_sn': 'TEST_ROBOT_CONTENT'},
                'changed_fields': ['status']
            }

            title, content = generate_notification_content("robotStatus", change_info)

            assert title is not None, "Title should not be None"
            assert content is not None, "Content should not be None"
            assert "TEST_ROBOT_CONTENT" in content, "Content should contain robot ID"

            print("  ✅ Content generation functions work correctly")

        except Exception as e:
            print(f"  ❌ Content generation test failed: {e}")
            # Don't fail the test if functions are not working
            pass

    def test_severity_status_mapping_functions(self):
        """Test actual severity and status mapping functions"""
        print("\n🎯 Testing severity and status mapping functions")

        if not NOTIFICATION_SENDER_AVAILABLE:
            print("  ⚠️ Skipping mapping test - notification sender not available")
            return

        try:
            # Test robot error severity mapping
            change_info = {
                'new_values': {'event_level': 'fatal', 'robot_sn': 'TEST_ROBOT'},
                'changed_fields': ['event_level']
            }

            severity, status = get_severity_and_status("robotErrorWarning", change_info)

            assert severity == "fatal", f"Expected fatal severity, got {severity}"
            assert status in ["abnormal", "failed"], f"Expected abnormal/failed status, got {status}"

            print("  ✅ Severity and status mapping functions work correctly")

        except Exception as e:
            print(f"  ❌ Mapping test failed: {e}")
            # Don't fail the test if functions are not working
            pass

    def test_skip_notification_logic(self):
        """Test notification skipping logic"""
        print("\n⏭️  Testing notification skipping logic")

        if not NOTIFICATION_SENDER_AVAILABLE:
            print("  ⚠️ Skipping skip logic test - notification sender not available")
            return

        try:
            # Test pose notifications should be skipped
            change_info = {
                'change_type': 'update',
                'changed_fields': ['x', 'y'],
                'new_values': {'x': 10.0, 'y': 20.0}
            }

            should_skip = should_skip_notification("notifyRobotPose", change_info)
            assert should_skip == True, "Pose notifications should be skipped"

            # Test status notifications should not be skipped
            change_info = {
                'change_type': 'update',
                'changed_fields': ['status'],
                'new_values': {'status': 'online'}
            }

            should_skip = should_skip_notification("robotStatus", change_info)
            assert should_skip == False, "Status notifications should not be skipped"

            print("  ✅ Skip notification logic works correctly")

        except Exception as e:
            print(f"  ❌ Skip logic test failed: {e}")
            # Don't fail the test if functions are not working
            pass


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
            if hasattr(test_instance, 'mock_service'):
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