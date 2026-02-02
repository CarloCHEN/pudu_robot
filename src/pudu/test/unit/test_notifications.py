"""
Unit tests for notification logic - tests real notification functions with JSON data
"""

import sys
sys.path.append('../../')

from pudu.notifications.notification_sender import (
    generate_individual_notification_content,
    get_severity_and_status_for_change,
    should_skip_notification,
    get_severity_and_status_for_robot_status,
    get_severity_and_status_for_task,
    get_severity_and_status_for_events,
    TASK_STATUS_MAPPING,
    SEVERITY_LEVELS,
    STATUS_TAGS
)
from pudu.test.utils.test_helpers import TestDataLoader, TestValidator

class TestNotifications:
    """Test actual notification business logic with JSON data"""

    def setup_method(self):
        """Setup test data loader"""
        self.test_data = TestDataLoader()
        self.validator = TestValidator()

    def test_robot_status_notifications_with_json_data(self):
        """Test robot status notifications using JSON robot data"""
        print("  🤖 Testing robot status notifications with JSON data")

        # Get different battery level robots from JSON
        low_battery_robots = self.test_data.get_robots_by_battery_level(max_level=20)
        normal_battery_robots = self.test_data.get_robots_by_battery_level(min_level=50)

        # Test low battery notification generation
        for robot in low_battery_robots:
            change_info = {
                "robot_sn": robot['robot_sn'],
                "change_type": "update",
                "changed_fields": ["battery_level"],
                "old_values": {"battery_level": 50},
                "new_values": robot,
                "primary_key_values": {"robot_sn": robot['robot_sn']}
            }

            # Test severity mapping
            severity, status = get_severity_and_status_for_change("robot_status", change_info)

            battery_level = robot['battery_level']
            if battery_level < 5:
                assert severity == "fatal", f"Battery {battery_level}% should be fatal"
            elif battery_level < 10:
                assert severity == "error", f"Battery {battery_level}% should be error"
            elif battery_level < 20:
                assert severity == "warning", f"Battery {battery_level}% should be warning"

            assert status == "warning", f"Low battery should have warning status"

            # Test notification content generation
            title, content = generate_individual_notification_content("robot_status", change_info)
            assert "battery" in title.lower() or "battery" in content.lower()
            assert robot['robot_sn'] in content or robot.get('robot_name', '') in content

        # Test normal battery (should be skipped)
        for robot in normal_battery_robots:
            change_info = {
                "change_type": "update",
                "changed_fields": ["battery_level"],
                "new_values": robot
            }

            should_skip = should_skip_notification("robot_status", change_info)
            assert should_skip == True, f"High battery ({robot['battery_level']}%) updates should be skipped"

    def test_robot_online_offline_notifications_with_json_data(self):
        """Test online/offline notifications using JSON robot status data"""
        print("  📶 Testing online/offline notifications with JSON data")

        online_robots = self.test_data.get_robots_by_status("Online")
        offline_robots = self.test_data.get_robots_by_status("Offline")

        # Test online notification
        for robot in online_robots[:2]:  # Test first 2 to avoid too much output
            change_info = {
                "robot_sn": robot['robot_sn'],
                "change_type": "update",
                "changed_fields": ["status"],
                "old_values": {"status": "Offline"},
                "new_values": robot,
                "primary_key_values": {"robot_sn": robot['robot_sn']}
            }

            severity, status = get_severity_and_status_for_change("robot_status", change_info)
            assert severity == "success", "Robot coming online should be success"
            assert status == "online", "Robot coming online should have online status"

            title, content = generate_individual_notification_content("robot_status", change_info)
            assert "online" in title.lower() or "online" in content.lower()

        # Test offline notification
        for robot in offline_robots[:1]:  # Test one offline robot
            change_info = {
                "robot_sn": robot['robot_sn'],
                "change_type": "update",
                "changed_fields": ["status"],
                "old_values": {"status": "Online"},
                "new_values": robot,
                "primary_key_values": {"robot_sn": robot['robot_sn']}
            }

            severity, status = get_severity_and_status_for_change("robot_status", change_info)
            assert severity == "error", "Robot going offline should be error"
            assert status == "offline", "Robot going offline should have offline status"

    def test_task_notifications_with_json_task_data(self):
        """Test task notifications using JSON task data"""
        print("  📋 Testing task notifications with JSON task data")

        all_tasks = self.test_data.get_all_tasks_from_task_data()

        for task in all_tasks:
            task_status = task.get('status', 'Unknown')

            change_info = {
                "robot_sn": task['robot_sn'],
                "change_type": "new_record" if task.get('name') == 'completed_task' else "update",
                "changed_fields": ["status"],
                "old_values": {"status": "In Progress"},
                "new_values": task,
                "primary_key_values": {
                    "robot_sn": task['robot_sn'],
                    "task_name": task['task_name']
                }
            }

            # Test severity mapping for different task statuses
            severity, status = get_severity_and_status_for_change("robot_task", change_info)

            if task_status == "Task Ended":
                assert severity == "success"
                assert status == "completed"
            elif task_status == "In Progress":
                assert severity == "event"
                assert status == "in_progress"

            # Test notification content
            title, content = generate_individual_notification_content("robot_task", change_info)
            assert task['task_name'] in content
            assert task['robot_sn'] in content or task.get('robot_name', '') in content

    def test_event_notifications_with_json_event_data(self):
        """Test event notifications using JSON event data"""
        print("  ⚠️ Testing event notifications with JSON event data")

        all_events = self.test_data.get_all_events()

        for event in all_events:
            change_info = {
                "robot_sn": event['robot_sn'],
                "change_type": "new_record",
                "changed_fields": ["event_type"],
                "old_values": {},
                "new_values": event,
                "primary_key_values": {
                    "robot_sn": event['robot_sn'],
                    "error_id": event.get('error_id', 'unknown')
                }
            }

            # Test severity mapping based on event level
            severity, status = get_severity_and_status_for_change("robot_events", change_info)

            event_level = event.get('event_level', 'info').lower()
            if event_level == 'error':
                assert severity == "error"
                assert status == "abnormal"
            elif event_level == 'warning':
                assert severity == "warning"
                assert status == "warning"
            elif event_level == 'fatal':
                assert severity == "fatal"
                assert status == "abnormal"
            else:
                assert severity == "event"
                assert status == "normal"

            # Test notification content
            title, content = generate_individual_notification_content("robot_events", change_info)
            assert event.get('event_type', '') in title or event.get('event_type', '') in content
            assert event['robot_sn'] in content

    def test_charging_notifications_with_json_charging_data(self):
        """Test charging notifications using JSON charging data"""
        print("  🔌 Testing charging notifications with JSON charging data")

        all_charging = self.test_data.get_all_charging_sessions()

        for session in all_charging:
            # Test new charging session
            change_info = {
                "robot_sn": session['robot_sn'],
                "change_type": "new_record",
                "changed_fields": ["robot_sn"],
                "old_values": {},
                "new_values": session,
                "primary_key_values": {
                    "robot_sn": session['robot_sn'],
                    "start_time": session.get('start_time', '2024-09-01 10:00:00')
                }
            }

            # Test that new charging sessions are not skipped
            should_skip = should_skip_notification("robot_charging", change_info)
            assert should_skip == False, "New charging sessions should not be skipped"

            # Test notification content
            title, content = generate_individual_notification_content("robot_charging", change_info)
            assert "charging" in title.lower() or "charging" in content.lower()
            assert session['robot_sn'] in content or session.get('robot_name', '') in content

            # Test charging update (should be skipped)
            update_change_info = change_info.copy()
            update_change_info["change_type"] = "update"
            update_change_info["changed_fields"] = ["final_power"]

            should_skip_update = should_skip_notification("robot_charging", update_change_info)
            assert should_skip_update == True, "Charging updates should be skipped"

    def test_notification_skipping_logic_with_comprehensive_scenarios(self):
        """Test notification skipping with comprehensive scenarios from JSON"""
        print("  🚫 Testing notification skipping with comprehensive scenarios")

        # Create realistic change scenarios based on JSON data
        all_robots = self.test_data.get_all_robots_from_status_data()

        if len(all_robots) >= 2:
            robot1 = all_robots[0]
            robot2 = all_robots[1]

            # Test scenarios that should be skipped
            skip_scenarios = [
                # High battery level updates (>= 20%)
                ("robot_status", {
                    "change_type": "update",
                    "changed_fields": ["battery_level"],
                    "new_values": {"battery_level": 80}
                }, True),

                # Charging updates
                ("robot_charging", {
                    "change_type": "update",
                    "changed_fields": ["final_power"]
                }, True),

                # Non-status robot updates
                ("robot_status", {
                    "change_type": "update",
                    "changed_fields": ["water_level"]
                }, True),

                # Non-status task updates
                ("robot_task", {
                    "change_type": "update",
                    "changed_fields": ["progress"]
                }, True),

                # Location changes
                ("location", {
                    "change_type": "update",
                    "changed_fields": ["building_name"]
                }, True)
            ]

            # Test scenarios that should NOT be skipped
            no_skip_scenarios = [
                # Low battery alerts
                ("robot_status", {
                    "change_type": "update",
                    "changed_fields": ["battery_level"],
                    "new_values": {"battery_level": 15}
                }, False),

                # Status changes
                ("robot_status", {
                    "change_type": "update",
                    "changed_fields": ["status"]
                }, True),

                # Task status changes
                ("robot_task", {
                    "change_type": "update",
                    "changed_fields": ["status"]
                }, False),

                # New records
                ("robot_charging", {
                    "change_type": "new_record",
                    "changed_fields": ["robot_sn"]
                }, False)
            ]

            # Test all skip scenarios
            for data_type, change_info, expected_skip in skip_scenarios:
                result = should_skip_notification(data_type, change_info)
                assert result == expected_skip, f"{data_type} should be skipped: {expected_skip}, got {result}"

            # Test all no-skip scenarios
            for data_type, change_info, expected_skip in no_skip_scenarios:
                result = should_skip_notification(data_type, change_info)
                assert result == expected_skip, f"{data_type} should not be skipped: {expected_skip}, got {result}"

    def test_task_status_mapping_with_json_task_data(self):
        """Test task status code mapping with actual JSON task data"""
        print("  📊 Testing task status mapping with JSON task data")

        all_tasks = self.test_data.get_all_tasks_from_task_data()

        # Test that our status mapping handles the statuses in JSON data
        for task in all_tasks:
            task_status = task.get('status')

            if task_status in TASK_STATUS_MAPPING.values():
                # This is a string status, find its code
                status_code = None
                for code, name in TASK_STATUS_MAPPING.items():
                    if name == task_status:
                        status_code = code
                        break

                if status_code is not None:
                    change_info = {
                        "robot_sn": task['robot_sn'],
                        "change_type": "update",
                        "changed_fields": ["status"],
                        "old_values": {"status": 1},  # In Progress
                        "new_values": {"status": status_code},
                        "primary_key_values": {"robot_sn": task['robot_sn']}
                    }

                    severity, status_tag = get_severity_and_status_for_change("robot_task", change_info)

                    # Verify severity mapping
                    if task_status == "Task Ended":
                        assert severity == "success"
                        assert status_tag == "completed"
                    elif task_status in ["Task Abnormal", "Task Interrupted"]:
                        assert severity == "error"
                        assert status_tag == "failed"
                    elif task_status == "In Progress":
                        assert severity == "event"
                        assert status_tag == "in_progress"

    def test_event_severity_mapping_with_json_event_data(self):
        """Test event severity mapping with JSON event data"""
        print("  ⚠️ Testing event severity mapping with JSON event data")

        all_events = self.test_data.get_all_events()

        for event in all_events:
            change_info = {
                "robot_sn": event['robot_sn'],
                "change_type": "new_record",
                "new_values": event
            }

            severity, status = get_severity_and_status_for_change("robot_events", change_info)

            event_level = event.get('event_level', 'info').lower()

            # Test severity mapping based on actual JSON event levels
            if event_level == 'error':
                assert severity == "error"
                assert status == "abnormal"
            elif event_level == 'warning':
                assert severity == "warning"
                assert status == "warning"
            elif event_level == 'fatal':
                assert severity == "fatal"
                assert status == "abnormal"
            else:
                assert severity == "event"
                assert status == "normal"

            # Test notification content includes event details
            title, content = generate_individual_notification_content("robot_events", change_info)
            assert event.get('event_type', '') in title or event.get('event_type', '') in content

    def test_notification_content_with_json_robot_names(self):
        """Test notification content includes actual robot names from JSON"""
        print("  🏷️ Testing notification content with JSON robot names")

        all_robots = self.test_data.get_all_robots_from_status_data()

        for robot in all_robots:
            if 'robot_name' in robot and robot['robot_name']:
                change_info = {
                    "robot_sn": robot['robot_sn'],
                    "change_type": "update",
                    "changed_fields": ["status"],
                    "old_values": {"status": "Offline"},
                    "new_values": robot,
                    "primary_key_values": {"robot_sn": robot['robot_sn']}
                }

                title, content = generate_individual_notification_content("robot_status", change_info)

                # Should include either robot name or robot SN
                assert (robot['robot_name'] in content or
                       robot['robot_sn'] in content), f"Content should include robot identifier: {content}"

    def test_charging_notification_skipping_with_json_data(self):
        """Test charging notification skipping logic with JSON charging data"""
        print("  🔌 Testing charging notification skipping with JSON data")

        all_charging = self.test_data.get_all_charging_sessions()

        for session in all_charging:
            # Test new charging session (should not be skipped)
            new_session_change = {
                "change_type": "new_record",
                "changed_fields": ["robot_sn"],
                "new_values": session
            }

            should_skip = should_skip_notification("robot_charging", new_session_change)
            assert should_skip == False, "New charging sessions should not be skipped"

            # Test charging update (should be skipped)
            update_change = {
                "change_type": "update",
                "changed_fields": ["final_power"],
                "new_values": session
            }

            should_skip_update = should_skip_notification("robot_charging", update_change)
            assert should_skip_update == True, "Charging power updates should be skipped"

    def test_comprehensive_notification_flow_with_json_data(self):
        """Test complete notification flow using comprehensive JSON data"""
        print("  🔄 Testing comprehensive notification flow with JSON data")

        # Get comprehensive test scenarios
        comprehensive_data = self.test_data.get_comprehensive_data()
        robot_combinations = comprehensive_data.get("robot_combinations", [])

        for combination in robot_combinations:
            robot_sn = combination['robot_sn']
            location_id = combination['location_id']

            # Test notification flow for this robot across different data types

            # 1. Robot status notification
            robot_data = self.test_data.get_test_robot_by_sn(robot_sn)
            if robot_data:
                status_change = {
                    "robot_sn": robot_sn,
                    "change_type": "new_record",
                    "new_values": robot_data
                }

                title, content = generate_individual_notification_content("robot_status", status_change)
                assert robot_sn in content or robot_data.get('robot_name', '') in content

            # 2. Task completion notification
            tasks_for_robot = [t for t in self.test_data.get_all_tasks_from_task_data()
                             if t.get('robot_sn') == robot_sn]

            for task in tasks_for_robot:
                task_change = {
                    "robot_sn": robot_sn,
                    "change_type": "update",
                    "changed_fields": ["status"],
                    "new_values": task
                }

                title, content = generate_individual_notification_content("robot_task", task_change)
                assert task.get('task_name', '') in content

    def test_severity_and_status_consistency(self):
        """Test that severity and status mappings are consistent across all functions"""
        print("  ⚖️ Testing severity and status mapping consistency")

        # Test that all functions use the same severity levels
        test_scenarios = [
            ("robot_status", {"battery_level": 4.99}, ["battery_level"], "fatal", "warning"),
            ("robot_task", {"status": 4}, ["status"], "success", "completed"),
            ("robot_events", {"event_level": "error"}, [], "error", "abnormal")
        ]

        for data_type, new_values, changed_fields, expected_severity, expected_status in test_scenarios:
            change_info = {
                "change_type": "update",
                "changed_fields": changed_fields,
                "old_values": {},
                "new_values": new_values
            }

            severity, status = get_severity_and_status_for_change(data_type, change_info)
            assert severity == expected_severity, f"{data_type}: expected severity {expected_severity}, got {severity}"
            assert status == expected_status, f"{data_type}: expected status {expected_status}, got {status}"

    def test_notification_content_validation_with_json(self):
        """Test that notification content is properly formatted using JSON data"""
        print("  ✅ Testing notification content validation with JSON data")

        # Test with different data types
        all_robots = self.test_data.get_all_robots_from_status_data()
        all_tasks = self.test_data.get_all_tasks_from_task_data()
        all_events = self.test_data.get_all_events()

        # Test robot status notifications
        for robot in all_robots[:2]:  # Test first 2
            change_info = {
                "robot_sn": robot['robot_sn'],
                "change_type": "new_record",
                "new_values": robot
            }

            title, content = generate_individual_notification_content("robot_status", change_info)

            # Validate content structure
            assert self.validator.validate_notification_content(
                title, content, [robot['robot_name']]
            ), f"Robot status notification validation failed for {robot['robot_sn']}"

        # Test task notifications
        for task in all_tasks:
            change_info = {
                "robot_sn": task['robot_sn'],
                "change_type": "new_record",
                "new_values": task
            }

            title, content = generate_individual_notification_content("robot_task", change_info)

            # Validate task content
            assert self.validator.validate_notification_content(
                title, content, [task['task_name'], task['robot_sn']]
            ), f"Task notification validation failed for {task['task_name']}"

def run_notification_tests():
    """Run all notification tests with JSON data"""
    print("=" * 70)
    print("🧪 TESTING NOTIFICATION LOGIC WITH JSON DATA")
    print("=" * 70)

    test_instance = TestNotifications()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            test_instance.setup_method()
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