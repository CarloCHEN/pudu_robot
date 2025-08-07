"""
Unit tests for notification logic - tests real notification functions
"""

import sys
sys.path.append('../../')

from pudu.notifications.notification_sender import (
    generate_individual_notification_content,
    get_severity_and_status_for_change,
    should_skip_notification,
    get_severity_and_status_for_robot_status,
    get_severity_and_status_for_task,
    TASK_STATUS_MAPPING,
    SEVERITY_LEVELS,
    STATUS_TAGS
)

class TestNotifications:
    """Test actual notification business logic with real scenarios"""

    def test_robot_status_severity_mapping(self):
        """Test severity mapping for robot status changes"""
        # Test battery level severity mapping
        battery_scenarios = [
            # (battery_level, expected_severity, expected_status)
            (3, "fatal", "warning"),      # Critical - immediate attention
            (8, "error", "warning"),      # Low - serious problem
            (15, "warning", "warning"),   # Warning - moderate issue
            (25, "success", "normal"),    # Normal - positive outcome
            (95, "success", "normal"),    # High - positive outcome
        ]

        for battery_level, expected_severity, expected_status in battery_scenarios:
            old_values = {"battery_level": 50}
            new_values = {"battery_level": battery_level}
            changed_fields = ["battery_level"]

            severity, status = get_severity_and_status_for_robot_status(old_values, new_values, changed_fields)

            assert severity == expected_severity, f"Battery {battery_level}%: expected severity '{expected_severity}', got '{severity}'"
            assert status == expected_status, f"Battery {battery_level}%: expected status '{expected_status}', got '{status}'"

        # Test online/offline status changes
        status_scenarios = [
            ("Online", "success", "online"),
            ("Offline", "error", "offline"),
            ("Unknown", "event", "active")
        ]

        for robot_status, expected_severity, expected_status in status_scenarios:
            old_values = {"status": "Offline"}
            new_values = {"status": robot_status}
            changed_fields = ["status"]

            severity, status = get_severity_and_status_for_robot_status(old_values, new_values, changed_fields)

            assert severity == expected_severity, f"Status '{robot_status}': expected severity '{expected_severity}', got '{severity}'"
            assert status == expected_status, f"Status '{robot_status}': expected status '{expected_status}', got '{status}'"

    def test_task_status_severity_mapping(self):
        """Test severity mapping for task status changes using real status codes"""
        # Use actual task status codes from TASK_STATUS_MAPPING
        task_scenarios = [
            # (status_code, status_name, expected_severity, expected_status)
            (4, "Task Ended", "success", "completed"),
            (5, "Task Abnormal", "error", "failed"),
            (3, "Task Interrupted", "error", "failed"),
            (6, "Task Cancelled", "warning", "uncompleted"),
            (2, "Task Suspended", "warning", "warning"),
            (1, "In Progress", "event", "in_progress"),
            (0, "Not Started", "event", "scheduled"),
        ]

        for status_code, status_name, expected_severity, expected_status in task_scenarios:
            # Verify our mapping is correct
            assert TASK_STATUS_MAPPING[status_code] == status_name

            old_values = {"status": 1}  # In Progress
            new_values = {"status": status_code}
            changed_fields = ["status"]

            severity, status = get_severity_and_status_for_task("update", old_values, new_values, changed_fields)

            assert severity == expected_severity, f"Task status {status_code} ({status_name}): expected severity '{expected_severity}', got '{severity}'"
            assert status == expected_status, f"Task status {status_code} ({status_name}): expected status '{expected_status}', got '{status}'"

    def test_notification_skipping_logic_real_scenarios(self):
        """Test notification skipping with actual use cases from your system"""
        # Real scenarios from your main.py code
        skip_scenarios = [
            # Robot charging updates should be skipped
            ("robot_charging", {"change_type": "update", "changed_fields": ["final_power"]}, True),
            ("robot_charging", {"change_type": "update", "changed_fields": ["power_gain"]}, True),
            ("robot_charging", {"change_type": "new_record", "changed_fields": ["initial_power"]}, False),

            # Robot status - high battery should be skipped
            ("robot_status", {"change_type": "update", "changed_fields": ["battery_level"], "new_values": {"battery_level": 80}}, True),
            # Robot status - low battery should NOT be skipped
            ("robot_status", {"change_type": "update", "changed_fields": ["battery_level"], "new_values": {"battery_level": 15}}, False),
            # Robot status - status changes should NOT be skipped
            ("robot_status", {"change_type": "update", "changed_fields": ["status"]}, False),
            # Robot status - other updates should be skipped
            ("robot_status", {"change_type": "update", "changed_fields": ["water_level"]}, True),

            # Robot task - status changes should NOT be skipped
            ("robot_task", {"change_type": "update", "changed_fields": ["status"]}, False),
            # Robot task - non-status updates should be skipped
            ("robot_task", {"change_type": "update", "changed_fields": ["progress"]}, True),
            ("robot_task", {"change_type": "new_record", "changed_fields": ["task_name"]}, False),

            # Location changes should be skipped
            ("location", {"change_type": "update", "changed_fields": ["building_name"]}, True),
            ("location", {"change_type": "new_record", "changed_fields": ["building_id"]}, True),
        ]

        for data_type, change_info, expected_skip in skip_scenarios:
            result = should_skip_notification(data_type, change_info)
            assert result == expected_skip, f"{data_type} with changes {change_info.get('changed_fields', [])}: expected skip={expected_skip}, got {result}"

    def test_notification_content_generation_real_robot_data(self):
        """Test notification content generation with your actual robot data structure"""
        # Use actual robot data structure from your system
        real_robot_change = {
            "robot_id": "1230",
            "change_type": "update",
            "changed_fields": ["battery_level"],
            "old_values": {"battery_level": 50},
            "new_values": {
                "robot_sn": "1230",
                "robot_type": "CC1",
                "robot_name": "demo_UF_demo",
                "location_id": "523670000",
                "battery_level": 8,
                "status": "Online",
                "tenant_id": "000000"
            },
            "primary_key_values": {"robot_sn": "1230"}
        }

        title, content = generate_individual_notification_content("robot_status", real_robot_change)

        # Test actual content generation logic
        assert "battery" in title.lower() or "battery" in content.lower()
        assert "demo_UF_demo" in content or "1230" in content
        assert "8" in content  # Battery level should be mentioned

    def test_task_completion_notification_real_data(self):
        """Test task notification with real task completion scenario"""
        # Real task completion from your system
        task_completion = {
            "robot_id": "1230",
            "change_type": "update",
            "changed_fields": ["status"],
            "old_values": {"status": 1},  # In Progress
            "new_values": {
                "robot_sn": "1230",
                "robot_type": "CC1",
                "robot_name": "demo_UF_demo",
                "task_name": "Library Cleaning",
                "status": 4,  # Task Ended
                "progress": 100.0,
                "actual_area": 150.56,
                "plan_area": 200.0
            },
            "primary_key_values": {"robot_sn": "1230", "task_name": "Library Cleaning"}
        }

        title, content = generate_individual_notification_content("robot_task", task_completion)

        # Verify task completion content
        assert "task" in title.lower()
        assert "Library Cleaning" in content
        assert "demo_UF_demo" in content or "1230" in content

        # Test severity mapping
        severity, status = get_severity_and_status_for_change("robot_task", task_completion)
        assert severity == "success"
        assert status == "completed"

    def test_robot_event_severity_mapping_real_events(self):
        """Test event severity mapping with actual robot events"""
        # Real robot events from your system
        event_scenarios = [
            # (event_level, expected_severity, expected_status)
            ("error", "error", "abnormal"),
            ("warning", "warning", "warning"),
            ("fatal", "fatal", "abnormal"),
            ("info", "event", "normal"),
            ("", "event", "normal"),  # Default case
        ]

        for event_level, expected_severity, expected_status in event_scenarios:
            event_change = {
                "robot_id": "1230",
                "change_type": "new_record",
                "new_values": {
                    "robot_sn": "1230",
                    "event_level": event_level,
                    "event_type": "Lost Localization",
                    "event_detail": "Odom Slip",
                    "error_id": "vir_1726794796"
                }
            }

            severity, status = get_severity_and_status_for_change("robot_events", event_change)

            assert severity == expected_severity, f"Event level '{event_level}': expected severity '{expected_severity}', got '{severity}'"
            assert status == expected_status, f"Event level '{event_level}': expected status '{expected_status}', got '{status}'"

    def test_severity_levels_and_status_tags_completeness(self):
        """Test that all severity levels and status tags are properly defined"""
        # Verify all expected severity levels exist
        expected_severities = ['fatal', 'error', 'warning', 'event', 'success', 'neutral']
        for severity in expected_severities:
            assert severity in SEVERITY_LEVELS, f"Missing severity level: {severity}"
            assert SEVERITY_LEVELS[severity] == severity, f"Severity level mapping incorrect for: {severity}"

        # Verify all expected status tags exist
        expected_statuses = ['completed', 'failed', 'uncompleted', 'in_progress', 'scheduled',
                           'normal', 'abnormal', 'active', 'inactive', 'pending',
                           'warning', 'charging', 'offline', 'online']
        for status in expected_statuses:
            assert status in STATUS_TAGS, f"Missing status tag: {status}"
            assert STATUS_TAGS[status] == status, f"Status tag mapping incorrect for: {status}"

def run_notification_tests():
    """Run all notification tests"""
    print("=" * 60)
    print("🧪 TESTING NOTIFICATION LOGIC")
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

    print(f"\n📊 Notification Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_notification_tests()