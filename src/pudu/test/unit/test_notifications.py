"""
Test real notification content generation and logic
"""

import sys
# Add src to Python path
sys.path.append('../../')

from pudu.notifications.notification_sender import (
    generate_individual_notification_content,
    get_severity_and_status_for_change,
    should_skip_notification
)

class TestNotifications:
    """Test actual notification business logic"""

    def test_battery_severity_logic(self):
        """Test battery level severity determination logic"""
        test_scenarios = [
            # (battery_level, expected_severity, expected_status)
            (3, "fatal", "warning"),      # Critical
            (8, "error", "warning"),      # Low
            (15, "warning", "warning"),   # Warning
            (25, "success", "normal"),    # Normal
            (95, "success", "normal"),    # High
        ]

        for battery_level, expected_severity, expected_status in test_scenarios:
            change_info = {
                "change_type": "update",
                "changed_fields": ["battery_level"],
                "old_values": {"battery_level": 50},
                "new_values": {"battery_level": battery_level}
            }

            severity, status = get_severity_and_status_for_change("robot_status", change_info)

            assert severity == expected_severity, f"Battery {battery_level}%: expected severity {expected_severity}, got {severity}"
            assert status == expected_status, f"Battery {battery_level}%: expected status {expected_status}, got {status}"

    def test_task_status_severity_logic(self):
        """Test task status severity mapping"""
        task_status_tests = [
            # (status_code, expected_severity, expected_status)
            (4, "success", "completed"),   # Task Ended
            (5, "error", "failed"),        # Task Abnormal
            (3, "error", "failed"),        # Task Interrupted
            (6, "warning", "uncompleted"), # Task Cancelled
            (2, "warning", "warning"),     # Task Suspended
            (1, "event", "in_progress"),   # In Progress
            (0, "event", "scheduled"),     # Not Started
        ]

        for status_code, expected_severity, expected_status in task_status_tests:
            change_info = {
                "change_type": "update",
                "changed_fields": ["status"],
                "old_values": {"status": 1},
                "new_values": {"status": status_code}
            }

            severity, status = get_severity_and_status_for_change("robot_task", change_info)

            assert severity == expected_severity, f"Task status {status_code}: expected severity {expected_severity}, got {severity}"
            assert status == expected_status, f"Task status {status_code}: expected status {expected_status}, got {status}"

    def test_notification_skipping_logic(self):
        """Test which notifications should be skipped"""
        skip_scenarios = [
            # (data_type, change_info, should_skip)
            ("robot_charging", {"change_type": "update", "changed_fields": ["final_power"]}, True),
            ("robot_status", {"change_type": "update", "changed_fields": ["battery_level"], "new_values": {"battery_level": 80}}, True),
            ("robot_status", {"change_type": "update", "changed_fields": ["battery_level"], "new_values": {"battery_level": 15}}, False),
            ("robot_task", {"change_type": "update", "changed_fields": ["status"]}, False),
            ("robot_task", {"change_type": "update", "changed_fields": ["progress"]}, True),
            ("location", {"change_type": "update", "changed_fields": ["building_name"]}, True),
        ]

        for data_type, change_info, expected_skip in skip_scenarios:
            result = should_skip_notification(data_type, change_info)
            assert result == expected_skip, f"{data_type} with {change_info['changed_fields']}: expected skip={expected_skip}, got {result}"

    def test_notification_content_generation_battery(self):
        """Test notification content for battery scenarios"""
        low_battery_change = {
            "robot_id": "ROBOT_001",
            "change_type": "update",
            "changed_fields": ["battery_level"],
            "old_values": {"battery_level": 50},
            "new_values": {
                "robot_sn": "ROBOT_001",
                "robot_name": "Lobby Cleaner",
                "battery_level": 8
            }
        }

        title, content = generate_individual_notification_content("robot_status", low_battery_change)

        # Test actual content logic
        assert "battery" in title.lower() or "battery" in content.lower()
        assert "ROBOT_001" in content or "Lobby Cleaner" in content
        assert "8" in content  # Battery level should be mentioned

    def test_notification_content_generation_task_completion(self):
        """Test notification content for task completion"""
        task_completion_change = {
            "robot_id": "ROBOT_002",
            "change_type": "update",
            "changed_fields": ["status"],
            "old_values": {"status": 1},  # In Progress
            "new_values": {
                "robot_sn": "ROBOT_002",
                "robot_name": "Hall Cleaner",
                "task_name": "Evening Cleaning",
                "status": 4  # Task Ended
            }
        }

        title, content = generate_individual_notification_content("robot_task", task_completion_change)

        # Test actual content logic
        assert "task" in title.lower() or "task" in content.lower()
        assert "Evening Cleaning" in content
        assert "ROBOT_002" in content or "Hall Cleaner" in content

def run_notification_tests():
    """Run real notification logic tests"""
    print("=" * 60)
    print("🧪 TESTING REAL NOTIFICATION LOGIC")
    print("=" * 60)

    test_instance = TestNotifications()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            passed += 1
            print(f"✅ {method_name} - PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {method_name} - FAILED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n📊 Real Notification Logic Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_notification_tests()