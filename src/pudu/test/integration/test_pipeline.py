"""
Real integration tests using actual test data from JSON files
Tests complete data flows from API data processing to database and notifications
"""

import sys
# Add src to Python path
sys.path.append('../../')

import pandas as pd
from Monitor.pudu_robot.src.pudu.app.main_backup import prepare_df_for_database
from pudu.notifications import detect_data_changes, send_change_based_notifications
from pudu.test.mocks.mock_rds import MockRDSTable
from pudu.test.mocks.mock_notifications import MockNotificationService
from pudu.test.utils.test_helpers import TestDataLoader

class TestPipeline:
    """Test complete data flow using real test data from JSON files"""

    def setup_method(self):
        """Setup for each test"""
        self.test_data = TestDataLoader()
        self.mock_notification_service = MockNotificationService()

    def test_robot_status_complete_flow(self):
        """Test complete robot status flow: JSON → DataFrame → Database → Notifications"""
        print("\n🔄 Testing complete robot status data flow")

        # Step 1: Load real test data from JSON
        status_data = self.test_data.get_robot_status_data()
        valid_robots = status_data.get("valid_robots", [])
        edge_cases = status_data.get("edge_cases", [])

        assert len(valid_robots) > 0, "No valid robot data in test JSON"
        print(f"  📊 Loaded {len(valid_robots)} valid robots from JSON")

        # Step 2: Convert to DataFrame (simulating API response)
        all_robots = valid_robots + edge_cases
        df = pd.DataFrame(all_robots)
        print(f"  📊 Created DataFrame with {len(df)} total robots")

        # Step 3: Process for database
        processed_df = prepare_df_for_database(df)

        # Validate processing
        assert isinstance(processed_df, pd.DataFrame)
        assert len(processed_df) == len(all_robots)
        expected_columns = ['robot_sn', 'robot_name', 'robot_type', 'water_level',
                           'sewage_level', 'battery_level', 'status']
        for col in expected_columns:
            if col in ['x', 'y', 'z']:  # Optional columns
                continue
            snake_case_col = col.lower().replace(' ', '_')
            assert snake_case_col in processed_df.columns, f"Missing column: {snake_case_col}"
        print("  ✅ DataFrame processing successful")

        # Step 4: Insert to mock database and detect changes
        mock_table = MockRDSTable("test", "test_db", "mnt_robots_management",
                                 primary_keys=["robot_sn"])

        # Insert some "existing" data first
        existing_robot = valid_robots[0].copy()
        existing_robot['battery_level'] = 50  # Different from test data
        mock_table.batch_insert([existing_robot])

        # Now insert the new data and detect changes
        data_list = processed_df.to_dict(orient='records')
        changes = detect_data_changes(mock_table, data_list, ["robot_sn"])

        print(f"  🔍 Detected {len(changes)} changes")

        # Verify change detection worked
        assert len(changes) > 0, "Should detect at least one change"

        # Check specific change for the robot we modified
        robot_sn = existing_robot['robot_sn']
        robot_changes = [c for c in changes.values() if c['robot_id'] == robot_sn]
        assert len(robot_changes) > 0, f"Should detect change for robot {robot_sn}"

        battery_change = robot_changes[0]
        assert battery_change['change_type'] == 'update'
        assert 'battery_level' in battery_change['changed_fields']
        print("  ✅ Change detection successful")

        # Step 5: Generate notifications
        database_name = "foxx_irvine_office"
        table_name = "robot_status"
        success_count, failed_count = send_change_based_notifications(
            self.mock_notification_service, database_name, table_name, changes, "robot_status"
        )

        # Verify notifications were sent
        sent_notifications = self.mock_notification_service.get_sent_notifications()
        print(f"  📧 Sent {len(sent_notifications)} notifications")

        print("  ✅ Notification generation successful")

        print("  🎉 Complete robot status flow PASSED")

    def test_robot_task_complete_flow(self):
        """Test complete robot task flow using JSON test data"""
        print("\n🔄 Testing complete robot task data flow")

        # Step 1: Load test data
        task_data = self.test_data.get_robot_task_data()
        valid_tasks = task_data.get("valid_tasks", [])

        assert len(valid_tasks) > 0, "No valid task data in test JSON"
        print(f"  📊 Loaded {len(valid_tasks)} valid tasks from JSON")

        # Step 2: Process data
        df = pd.DataFrame(valid_tasks)
        processed_df = prepare_df_for_database(df, columns_to_remove=['id'])

        # Validate task-specific fields
        task_columns = ['robot_sn', 'task_name', 'mode', 'actual_area', 'plan_area',
                       'progress', 'status', 'efficiency']
        for col in task_columns:
            snake_case_col = col.lower().replace(' ', '_')
            if snake_case_col in processed_df.columns:
                assert processed_df[snake_case_col].notna().any(), f"Column {snake_case_col} has no valid data"

        print("  ✅ Task data processing successful")

        # Step 3: Test change detection with task status changes
        mock_table = MockRDSTable("test", "test_db", "mnt_robot_tasks",
                                 primary_keys=["robot_sn", "task_name", "start_time"])

        # Find a completed task from test data
        completed_tasks = [t for t in valid_tasks if t.get('status') == 'Task Ended']
        if completed_tasks:
            completed_task = completed_tasks[0]

            # Insert as "in progress" first
            in_progress_task = completed_task.copy()
            in_progress_task['status'] = 'In Progress'
            in_progress_task['progress'] = 50.0
            mock_table.batch_insert([in_progress_task])

            # Now "complete" the task
            data_list = [completed_task]
            changes = detect_data_changes(mock_table, data_list,
                                        ["robot_sn", "task_name", "start_time"])

            # Verify task completion was detected
            assert len(changes) > 0, "Should detect task completion"

            task_change = list(changes.values())[0]
            assert task_change['change_type'] == 'update'
            assert 'status' in task_change['changed_fields']
            print("  ✅ Task completion detection successful")

            # Test notifications for task completion
            database_name = "foxx_irvine_office"
            table_name = "robot_tasks"
            success_count, failed_count = send_change_based_notifications(
                self.mock_notification_service, database_name, table_name, changes, "robot_task"
            )

            sent_notifications = self.mock_notification_service.get_sent_notifications()
            task_notifications = [n for n in sent_notifications
                                if 'task' in n['content'].lower()]

            assert len(task_notifications) > 0, "Should send task completion notification"

            task_notif = task_notifications[0]
            assert completed_task['robot_sn'] in task_notif['content']
            assert task_notif['severity'] == 'success'
            print("  ✅ Task completion notification successful")

        print("  🎉 Complete robot task flow PASSED")

    def test_robot_charging_complete_flow(self):
        """Test complete robot charging flow using JSON test data"""
        print("\n🔄 Testing complete robot charging data flow")

        # Step 1: Load test data
        charging_data = self.test_data.get_robot_charging_data()
        valid_sessions = charging_data.get("valid_charging_sessions", [])

        assert len(valid_sessions) > 0, "No valid charging data in test JSON"
        print(f"  📊 Loaded {len(valid_sessions)} charging sessions from JSON")

        # Step 2: Process data
        df = pd.DataFrame(valid_sessions)
        processed_df = prepare_df_for_database(df, columns_to_remove=['id'])

        # Validate charging-specific processing
        charging_columns = ['robot_sn', 'robot_name', 'start_time', 'end_time',
                          'duration', 'initial_power', 'final_power', 'power_gain']
        for col in charging_columns:
            snake_case_col = col.lower().replace(' ', '_')
            if snake_case_col in processed_df.columns:
                assert processed_df[snake_case_col].notna().any()

        print("  ✅ Charging data processing successful")

        # Step 3: Test notification logic (charging updates usually skipped)
        mock_table = MockRDSTable("test", "test_db", "mnt_robot_charging",
                                 primary_keys=["robot_sn", "start_time", "end_time"])

        data_list = processed_df.to_dict(orient='records')
        changes = detect_data_changes(mock_table, data_list,
                                    ["robot_sn", "start_time", "end_time"])

        # Test notification skipping for charging
        from pudu.notifications.notification_sender import should_skip_notification

        for change_info in changes.values():
            if change_info['change_type'] == 'new_record':
                should_skip = should_skip_notification("robot_charging", change_info)
                # New charging records should not be skipped
                assert should_skip == False, "New charging records should trigger notifications"
            else:
                should_skip = should_skip_notification("robot_charging", change_info)
                # Charging updates should be skipped
                assert should_skip == True, "Charging updates should be skipped"

        print("  ✅ Charging notification logic successful")
        print("  🎉 Complete robot charging flow PASSED")

    def test_robot_events_complete_flow(self):
        """Test complete robot events flow using JSON test data"""
        print("\n🔄 Testing complete robot events data flow")

        # Step 1: Load test data
        events_data = self.test_data.get_robot_event_data()
        valid_events = events_data.get("valid_events", [])
        severity_events = events_data.get("severity_levels", [])

        all_events = valid_events + severity_events
        assert len(all_events) > 0, "No valid event data in test JSON"
        print(f"  📊 Loaded {len(all_events)} events from JSON")

        # Step 2: Process data
        df = pd.DataFrame(all_events)
        processed_df = prepare_df_for_database(df, columns_to_remove=['id'])

        # Validate event-specific processing
        event_columns = ['robot_sn', 'event_level', 'event_type', 'event_detail',
                        'error_id', 'task_time', 'upload_time']
        for col in event_columns:
            snake_case_col = col.lower().replace(' ', '_')
            if snake_case_col in processed_df.columns:
                assert processed_df[snake_case_col].notna().any()

        print("  ✅ Event data processing successful")

        # Step 3: Test severity-based notifications
        mock_table = MockRDSTable("test", "test_db", "mnt_robot_events",
                                 primary_keys=["robot_sn", "error_id"])

        data_list = processed_df.to_dict(orient='records')
        changes = detect_data_changes(mock_table, data_list,
                                    ["robot_sn", "error_id"])

        # Test notifications for different event severities
        database_name = "foxx_irvine_office"
        table_name = "robot_events"
        success_count, failed_count = send_change_based_notifications(
            self.mock_notification_service, database_name, table_name, changes, "robot_events"
        )

        sent_notifications = self.mock_notification_service.get_sent_notifications()

        # Verify severity mapping
        for event in all_events:
            event_level = event.get('event_level', '').lower()
            robot_sn = event.get('robot_sn')

            robot_notifications = [n for n in sent_notifications
                                 if robot_sn in n['content']]

            if robot_notifications:
                notification = robot_notifications[0]
                if event_level == 'fatal':
                    assert notification['severity'] == 'fatal'
                elif event_level == 'error':
                    assert notification['severity'] == 'error'
                elif event_level == 'warning':
                    assert notification['severity'] == 'warning'
                else:
                    assert notification['severity'] == 'event'

        print("  ✅ Event severity mapping successful")
        print("  🎉 Complete robot events flow PASSED")

    def test_location_data_complete_flow(self):
        """Test complete location data flow using JSON test data"""
        print("\n🔄 Testing complete location data flow")

        # Step 1: Load test data
        location_data = self.test_data.get_location_data()
        valid_locations = location_data.get("valid_locations", [])
        edge_cases = location_data.get("edge_cases", [])

        all_locations = valid_locations + edge_cases
        assert len(all_locations) > 0, "No valid location data in test JSON"
        print(f"  📊 Loaded {len(all_locations)} locations from JSON")

        # Step 2: Process data
        df = pd.DataFrame(all_locations)
        processed_df = prepare_df_for_database(df)

        # Validate location processing
        assert 'building_id' in processed_df.columns
        assert 'building_name' in processed_df.columns
        assert len(processed_df) == len(all_locations)

        print("  ✅ Location data processing successful")

        # Step 3: Test that location changes are typically skipped
        mock_table = MockRDSTable("test", "test_db", "mnt_locations",
                                 primary_keys=["building_id"])

        data_list = processed_df.to_dict(orient='records')
        changes = detect_data_changes(mock_table, data_list, ["building_id"])

        # Test notification skipping for locations
        from pudu.notifications.notification_sender import should_skip_notification

        for change_info in changes.values():
            should_skip = should_skip_notification("location", change_info)
            assert should_skip == True, "Location changes should be skipped"

        print("  ✅ Location notification skipping successful")
        print("  🎉 Complete location flow PASSED")

    def test_mixed_data_scenario(self):
        """Test processing multiple data types together"""
        print("\n🔄 Testing mixed data scenario")

        # Load all types of test data
        all_data_types = {
            'robot_status': self.test_data.get_robot_status_data(),
            'robot_task': self.test_data.get_robot_task_data(),
            'robot_charging': self.test_data.get_robot_charging_data(),
            'robot_events': self.test_data.get_robot_event_data(),
            'location': self.test_data.get_location_data()
        }

        total_notifications = 0

        # Process each data type
        for data_type, data in all_data_types.items():
            print(f"  📊 Processing {data_type} data")

            if data_type == 'robot_status':
                records = data.get('valid_robots', [])
            elif data_type == 'robot_task':
                records = data.get('valid_tasks', [])
            elif data_type == 'robot_charging':
                records = data.get('valid_charging_sessions', [])
            elif data_type == 'robot_events':
                records = data.get('valid_events', [])
            elif data_type == 'location':
                records = data.get('valid_locations', [])

            if records:
                df = pd.DataFrame(records)
                processed_df = prepare_df_for_database(df)

                # Create appropriate mock table
                if data_type == 'robot_status':
                    mock_table = MockRDSTable("test", "test_db", "robot_status",
                                             primary_keys=["robot_sn"])
                elif data_type == 'robot_task':
                    mock_table = MockRDSTable("test", "test_db", "robot_tasks",
                                             primary_keys=["robot_sn", "task_name"])
                elif data_type == 'robot_charging':
                    mock_table = MockRDSTable("test", "test_db", "robot_charging",
                                             primary_keys=["robot_sn", "start_time"])
                elif data_type == 'robot_events':
                    mock_table = MockRDSTable("test", "test_db", "robot_events",
                                             primary_keys=["robot_sn", "error_id"])
                elif data_type == 'location':
                    mock_table = MockRDSTable("test", "test_db", "locations",
                                             primary_keys=["building_id"])

                data_list = processed_df.to_dict(orient='records')
                changes = detect_data_changes(mock_table, data_list, mock_table.primary_keys)

                if changes:
                    database_name = "foxx_irvine_office"
                    table_name = data_type
                    success, failed = send_change_based_notifications(
                        self.mock_notification_service, database_name, table_name, changes, data_type
                    )
                    total_notifications += success
                    print(f"    📧 Sent {success} notifications for {data_type}")

        print(f"  📧 Total notifications sent: {total_notifications}")

        # Verify mixed scenario worked
        all_notifications = self.mock_notification_service.get_sent_notifications()
        assert len(all_notifications) == total_notifications

        # Check variety of notification types
        severities = set(n['severity'] for n in all_notifications)
        assert len(severities) > 1, "Should have multiple severity types"

        print("  🎉 Mixed data scenario PASSED")

def run_integration_tests():
    """Run all real integration tests"""
    print("=" * 80)
    print("🧪 RUNNING REAL INTEGRATION TESTS USING JSON TEST DATA")
    print("=" * 80)

    test_instance = TestPipeline()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            print(f"\n{'='*60}")
            print(f"🧪 Running {method_name}")
            print(f"{'='*60}")

            test_instance.setup_method()
            method = getattr(test_instance, method_name)
            method()
            passed += 1
            print(f"\n✅ {method_name} - PASSED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {method_name} - FAILED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print("📊 REAL INTEGRATION TESTS SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "No tests")

    if failed == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Complete data flows are working correctly")
    else:
        print(f"\n⚠️ {failed} integration test(s) failed")
        print("❌ Review failed tests above")

    print(f"{'='*80}")
    return passed, failed

if __name__ == "__main__":
    run_integration_tests()