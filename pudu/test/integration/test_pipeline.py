"""
Integration tests for complete pipeline flows - tests real functions together with JSON data
"""

import sys
sys.path.append('../../')

import pandas as pd
from unittest.mock import MagicMock
from pudu.notifications.change_detector import detect_data_changes, normalize_record_for_comparison
from pudu.notifications.notification_sender import (
    generate_individual_notification_content,
    get_severity_and_status_for_change,
    should_skip_notification
)
from pudu.app.main import App
from pudu.test.utils.test_helpers import TestDataLoader, TestValidator

class TestPipelineIntegration:
    """Test complete pipeline flows with real functions and JSON data"""

    def setup_method(self):
        """Setup for integration tests"""
        self.test_data = TestDataLoader()
        self.validator = TestValidator()

        # Create app instance for testing
        self.app = App.__new__(App)

        # Setup realistic mock responses
        self.setup_realistic_mocks()

    def setup_realistic_mocks(self):
        """Setup realistic mock responses based on JSON test data"""
        # Get test data for mocking
        all_robots = self.test_data.get_all_robots_from_status_data()
        all_tasks = self.test_data.get_all_tasks_from_task_data()
        all_events = self.test_data.get_all_events()
        all_charging = self.test_data.get_all_charging_sessions()
        all_locations = self.test_data.get_all_locations()

        # Store for use in tests
        self.mock_data = {
            'robots': all_robots,
            'tasks': all_tasks,
            'events': all_events,
            'charging': all_charging,
            'locations': all_locations
        }

    def test_complete_robot_status_pipeline_with_json(self):
        """Test complete robot status pipeline using JSON data"""
        print("\n🔄 Testing complete robot status pipeline with JSON data")

        # Get robots with different battery levels for realistic testing
        low_battery_robots = self.test_data.get_robots_by_battery_level(max_level=20)
        normal_battery_robots = self.test_data.get_robots_by_battery_level(min_level=50)

        if len(low_battery_robots) > 0 and len(normal_battery_robots) > 0:
            # Scenario: Robot with normal battery changes to low battery
            existing_robot = normal_battery_robots[0].copy()
            updated_robot = low_battery_robots[0].copy()
            updated_robot['robot_sn'] = existing_robot['robot_sn']  # Same robot, different battery

            # Step 1: Test data processing
            robot_df = pd.DataFrame([updated_robot])
            processed_df = self.app._prepare_df_for_database(robot_df)

            assert 'robot_sn' in processed_df.columns
            assert 'battery_level' in processed_df.columns
            print("    ✅ Data processing successful")

            # Step 2: Test change detection
            mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [existing_robot])
            changes = detect_data_changes(mock_table, [updated_robot], ["robot_sn"])

            assert len(changes) == 1
            change_info = list(changes.values())[0]
            assert change_info['change_type'] == 'update'
            assert 'battery_level' in change_info['changed_fields']
            print("    ✅ Change detection successful")

            # Step 3: Test notification generation
            title, content = generate_individual_notification_content("robot_status", change_info)
            severity, status = get_severity_and_status_for_change("robot_status", change_info)

            # Low battery should generate appropriate notification
            assert "battery" in title.lower() or "battery" in content.lower()
            assert severity in ["warning", "error", "fatal"]  # Depends on exact battery level
            assert status == "warning"
            print("    ✅ Notification generation successful")

            # Step 4: Test notification skipping logic
            should_skip = should_skip_notification("robot_status", change_info)
            assert should_skip == False, "Low battery alerts should not be skipped"
            print("    ✅ Notification skipping logic successful")

            print("  🎉 Complete robot status pipeline PASSED")

    def test_complete_task_pipeline_with_json(self):
        """Test complete task pipeline using JSON task data"""
        print("\n🔄 Testing complete task pipeline with JSON data")

        all_tasks = self.test_data.get_all_tasks_from_task_data()

        if len(all_tasks) > 0:
            # Get a completed task from JSON
            completed_tasks = [t for t in all_tasks if t.get('status') == 'Task Ended']

            if len(completed_tasks) > 0:
                task = completed_tasks[0]

                # Create existing task (in progress) and new task (completed)
                existing_task = task.copy()
                existing_task['status'] = 'In Progress'
                existing_task['progress'] = 50.0

                completed_task = task.copy()

                # Step 1: Test data processing
                task_df = pd.DataFrame([completed_task])
                processed_df = self.app._prepare_df_for_database(task_df, columns_to_remove=['id', 'location_id'])

                assert 'task_name' in processed_df.columns
                assert 'robot_sn' in processed_df.columns
                assert 'status' in processed_df.columns
                print("    ✅ Task data processing successful")

                # Step 2: Test change detection with composite primary keys
                mock_table = self._create_mock_table("mnt_robots_task",
                                                   ["robot_sn", "task_name", "start_time"],
                                                   [existing_task])

                # Add start_time for primary key
                completed_task['start_time'] = '2024-09-01 14:30:00'
                existing_task['start_time'] = '2024-09-01 14:30:00'

                changes = detect_data_changes(mock_table, [completed_task],
                                            ["robot_sn", "task_name", "start_time"])

                assert len(changes) == 1
                change_info = list(changes.values())[0]
                assert change_info['change_type'] == 'update'
                print("    ✅ Task change detection successful")

                # Step 3: Test notification logic for task completion
                title, content = generate_individual_notification_content("robot_task", change_info)
                severity, status = get_severity_and_status_for_change("robot_task", change_info)

                assert "task" in title.lower()
                assert task['task_name'] in content
                assert severity == "success"  # Task completion should be success
                assert status == "completed"
                print("    ✅ Task completion notification successful")

                print("  🎉 Complete task pipeline PASSED")

    def test_complete_event_pipeline_with_json(self):
        """Test complete event pipeline using JSON event data"""
        print("\n🔄 Testing complete event pipeline with JSON data")

        all_events = self.test_data.get_all_events()

        if len(all_events) > 0:
            event = all_events[0]

            # Step 1: Test data processing
            event_df = pd.DataFrame([event])
            processed_df = self.app._prepare_df_for_database(event_df, columns_to_remove=['id', 'location_id'])

            assert 'robot_sn' in processed_df.columns
            assert 'event_type' in processed_df.columns or 'error_type' in processed_df.columns
            print("    ✅ Event data processing successful")

            # Step 2: Test change detection (new event)
            existing_data = {
                'robot_sn': 'test_robot_323',
                'event_id': 'event_001',
                'event_type': 'test_event',
                'event_level': 'error',
                'upload_time': '2024-09-01 14:30:00'
            }
            mock_table = self._create_mock_table("mnt_robot_events", ["robot_sn", "event_id"], [existing_data])

            # Add event_id for primary key
            event_with_id = event.copy()
            event_with_id['event_id'] = event.get('error_id', 'event_001')

            changes = detect_data_changes(mock_table, [event_with_id], ["robot_sn", "event_id"])

            assert len(changes) == 1
            change_info = list(changes.values())[0]
            assert change_info['change_type'] == 'new_record'
            print("    ✅ Event change detection successful")

            # Step 3: Test notification generation
            title, content = generate_individual_notification_content("robot_events", change_info)
            severity, status = get_severity_and_status_for_change("robot_events", change_info)

            assert event.get('event_type', '') in title or event.get('event_type', '') in content

            # Test severity based on event level
            event_level = event.get('event_level', 'info').lower()
            if event_level == 'error':
                assert severity == "error"
            elif event_level == 'warning':
                assert severity == "warning"
            elif event_level == 'fatal':
                assert severity == "fatal"
            else:
                assert severity == "event"

            print("    ✅ Event notification generation successful")
            print("  🎉 Complete event pipeline PASSED")

    def test_complete_charging_pipeline_with_json(self):
        """Test complete charging pipeline using JSON charging data"""
        print("\n🔄 Testing complete charging pipeline with JSON data")

        all_charging = self.test_data.get_all_charging_sessions()

        if len(all_charging) > 0:
            session = all_charging[0]

            # Step 1: Test data processing
            charging_df = pd.DataFrame([session])
            processed_df = self.app._prepare_df_for_database(charging_df, columns_to_remove=['id', 'location_id'])

            assert 'robot_sn' in processed_df.columns
            print("    ✅ Charging data processing successful")

            # Step 2: Test change detection (new charging session)
            mock_table = self._create_mock_table("mnt_robots_charging_sessions",
                                                ["robot_sn", "start_time", "end_time"], [])

            # Ensure required fields for primary key
            session_with_times = session.copy()
            if 'start_time' not in session_with_times:
                session_with_times['start_time'] = '2024-09-01 14:00:00'
            if 'end_time' not in session_with_times:
                session_with_times['end_time'] = '2024-09-01 16:30:00'

            changes = detect_data_changes(mock_table, [session_with_times],
                                        ["robot_sn", "start_time", "end_time"])

            assert len(changes) == 1
            change_info = list(changes.values())[0]
            assert change_info['change_type'] == 'new_record'
            print("    ✅ Charging change detection successful")

            # Step 3: Test notification logic
            # New charging session should not be skipped
            should_skip = should_skip_notification("robot_charging", change_info)
            assert should_skip == False, "New charging sessions should not be skipped"

            # But charging updates should be skipped
            update_change = change_info.copy()
            update_change['change_type'] = 'update'
            update_change['changed_fields'] = ['final_power']

            should_skip_update = should_skip_notification("robot_charging", update_change)
            assert should_skip_update == True, "Charging updates should be skipped"
            print("    ✅ Charging notification logic successful")

            print("  🎉 Complete charging pipeline PASSED")

    def test_mixed_data_types_pipeline_with_json(self):
        """Test pipeline with mixed data types from JSON"""
        print("\n🔄 Testing mixed data types pipeline with JSON data")

        # Get data from all sources
        robots = self.test_data.get_all_robots_from_status_data()[:2]  # Limit for testing
        tasks = self.test_data.get_all_tasks_from_task_data()[:1]
        events = self.test_data.get_all_events()[:1]
        charging = self.test_data.get_all_charging_sessions()[:1]

        total_changes = 0

        # Test processing each data type
        data_types = [
            ("robot_status", robots, ["robot_sn"]),
            ("robot_task", tasks, ["robot_sn", "task_name", "start_time"]),
            ("robot_events", events, ["robot_sn", "event_id"]),
            ("robot_charging", charging, ["robot_sn", "start_time", "end_time"])
        ]

        for data_type, data_list, primary_keys in data_types:
            if len(data_list) > 0:
                # Step 1: Data processing
                df = pd.DataFrame(data_list)
                processed_df = self.app._prepare_df_for_database(df, columns_to_remove=['id', 'location_id'])

                assert isinstance(processed_df, pd.DataFrame)
                assert len(processed_df) == len(data_list)
                print(f"    ✅ {data_type} data processing successful")

                # Step 2: Change detection (assume new records)
                mock_table = self._create_mock_table(f"mnt_{data_type}", primary_keys, [])

                # Add required primary key fields if missing
                processed_data = processed_df.to_dict('records')
                for record in processed_data:
                    if 'start_time' in primary_keys and 'start_time' not in record:
                        record['start_time'] = '2024-09-01 14:30:00'
                    if 'end_time' in primary_keys and 'end_time' not in record:
                        record['end_time'] = '2024-09-01 16:30:00'
                    if 'event_id' in primary_keys and 'event_id' not in record:
                        record['event_id'] = record.get('error_id', 'event_001')

                changes = detect_data_changes(mock_table, processed_data, primary_keys)

                assert len(changes) == len(data_list)
                total_changes += len(changes)
                print(f"    ✅ {data_type} change detection successful ({len(changes)} changes)")

                # Step 3: Test notification for first change
                if changes:
                    first_change = list(changes.values())[0]

                    # Test notification skipping
                    should_skip = should_skip_notification(data_type, first_change)

                    if not should_skip:
                        title, content = generate_individual_notification_content(data_type, first_change)
                        severity, status = get_severity_and_status_for_change(data_type, first_change)

                        assert len(title) > 0, f"{data_type} notification title should not be empty"
                        assert len(content) > 0, f"{data_type} notification content should not be empty"
                        assert severity in ["fatal", "error", "warning", "event", "success", "neutral"]
                        print(f"    ✅ {data_type} notification generation successful")
                    else:
                        print(f"    ℹ️ {data_type} notification skipped (as expected)")

        print(f"  🎉 Mixed data types pipeline PASSED ({total_changes} total changes processed)")

    def test_robot_state_transitions_with_json(self):
        """Test robot state transitions using JSON data"""
        print("\n🔄 Testing robot state transitions with JSON data")

        online_robots = self.test_data.get_robots_by_status("Online")
        offline_robots = self.test_data.get_robots_by_status("Offline")

        # Test online → offline transition
        if len(online_robots) > 0 and len(offline_robots) > 0:
            online_robot = online_robots[0]
            offline_robot = offline_robots[0]
            offline_robot['robot_sn'] = online_robot['robot_sn']  # Same robot

            mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [online_robot])
            changes = detect_data_changes(mock_table, [offline_robot], ["robot_sn"])

            assert len(changes) == 1
            change_info = list(changes.values())[0]
            assert 'status' in change_info['changed_fields']

            # Test notification for status change
            title, content = generate_individual_notification_content("robot_status", change_info)
            severity, status = get_severity_and_status_for_change("robot_status", change_info)

            assert "offline" in title.lower() or "offline" in content.lower()
            assert severity == "error"  # Robot going offline is error
            assert status == "offline"

            print("    ✅ Online → Offline transition successful")

        # Test battery level transitions
        low_battery_robots = self.test_data.get_robots_by_battery_level(max_level=15)
        normal_battery_robots = self.test_data.get_robots_by_battery_level(min_level=80)

        if len(low_battery_robots) > 0 and len(normal_battery_robots) > 0:
            normal_robot = normal_battery_robots[0]
            low_robot = low_battery_robots[0]
            low_robot['robot_sn'] = normal_robot['robot_sn']  # Same robot

            mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [normal_robot])
            changes = detect_data_changes(mock_table, [low_robot], ["robot_sn"])

            assert len(changes) == 1
            change_info = list(changes.values())[0]
            assert 'battery_level' in change_info['changed_fields']

            # Test severity based on battery level
            severity, status = get_severity_and_status_for_change("robot_status", change_info)
            battery_level = low_robot['battery_level']

            if battery_level < 5:
                assert severity == "fatal"
            elif battery_level < 10:
                assert severity == "error"
            elif battery_level < 20:
                assert severity == "warning"

            print(f"    ✅ Battery transition successful ({battery_level}% → {severity})")

    def test_data_consistency_across_pipeline_with_json(self):
        """Test data consistency throughout entire pipeline using JSON data"""
        print("\n🔄 Testing data consistency across pipeline with JSON data")

        # Get comprehensive test data
        all_robots = self.test_data.get_all_robots_from_status_data()

        for robot in all_robots[:2]:  # Test first 2 robots
            robot_sn = robot['robot_sn']

            # Step 1: Original data
            original_robot = robot.copy()

            # Step 2: Data processing
            robot_df = pd.DataFrame([original_robot])
            processed_df = self.app._prepare_df_for_database(robot_df)
            processed_robot = processed_df.iloc[0].to_dict()

            # Step 3: Normalization for change detection
            normalized_robot = normalize_record_for_comparison(processed_robot)

            # Test that essential data is preserved throughout pipeline
            assert normalized_robot['robot_sn'] == original_robot['robot_sn']

            if 'status' in original_robot:
                assert normalized_robot['status'] == original_robot['status']

            # Test that numeric data is handled consistently
            if 'battery_level' in original_robot and original_robot['battery_level'] is not None:
                # Battery level might be normalized for precision
                original_battery = original_robot['battery_level']
                normalized_battery = normalized_robot['battery_level']

                # Should be close (within normalization precision)
                assert abs(normalized_battery - original_battery) < 0.01

            print(f"    ✅ Data consistency maintained for robot {robot_sn}")

    def test_error_handling_throughout_pipeline_with_json(self):
        """Test error handling throughout pipeline using JSON edge cases"""
        print("\n🔄 Testing error handling throughout pipeline with JSON edge cases")

        # Get edge cases from JSON data
        status_edge_cases = self.test_data.get_robot_status_data().get("edge_cases", [])

        for edge_case in status_edge_cases:
            try:
                # Step 1: Data processing should not crash
                edge_df = pd.DataFrame([edge_case])
                processed_df = self.app._prepare_df_for_database(edge_df)
                assert isinstance(processed_df, pd.DataFrame)

                # Step 2: Normalization should not crash
                if len(processed_df) > 0:
                    processed_record = processed_df.iloc[0].to_dict()
                    normalized = normalize_record_for_comparison(processed_record)
                    assert isinstance(normalized, dict)

                # Step 3: Change detection should not crash
                mock_table = self._create_mock_table("test_table", ["robot_sn"], [])
                changes = detect_data_changes(mock_table, [edge_case], ["robot_sn"])
                assert isinstance(changes, dict)

                print(f"    ✅ Edge case handled: {edge_case.get('name', 'unnamed')}")

            except Exception as e:
                print(f"    ❌ Edge case failed: {edge_case.get('name', 'unnamed')} - {e}")
                raise

    def test_performance_with_multiple_json_records(self):
        """Test pipeline performance with multiple records from JSON"""
        print("\n🔄 Testing pipeline performance with multiple JSON records")

        # Get all data for performance testing
        all_robots = self.test_data.get_all_robots_from_status_data()
        all_tasks = self.test_data.get_all_tasks_from_task_data()

        # Test processing multiple robots at once
        if len(all_robots) > 1:
            robot_df = pd.DataFrame(all_robots)
            processed_df = self.app._prepare_df_for_database(robot_df)

            # Should process all robots
            assert len(processed_df) == len(all_robots)

            # Test change detection with multiple records
            mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [])
            changes = detect_data_changes(mock_table, all_robots, ["robot_sn"])

            # Should detect all as new records
            assert len(changes) == len(all_robots)

            print(f"    ✅ Processed {len(all_robots)} robots successfully")

        # Test processing multiple tasks
        if len(all_tasks) > 1:
            # Add required fields for tasks
            tasks_with_times = []
            for i, task in enumerate(all_tasks):
                task_copy = task.copy()
                task_copy['start_time'] = f'2024-09-01 {14+i}:30:00'
                tasks_with_times.append(task_copy)

            task_df = pd.DataFrame(tasks_with_times)
            processed_df = self.app._prepare_df_for_database(task_df)

            assert len(processed_df) == len(tasks_with_times)

            print(f"    ✅ Processed {len(all_tasks)} tasks successfully")

    def test_cross_data_type_relationships_with_json(self):
        """Test relationships between different data types using JSON data"""
        print("\n🔄 Testing cross-data-type relationships with JSON data")

        # Get robot that appears in multiple data types
        robot_sn = '811064412050012'  # This SN appears in multiple JSON files

        robot_data = self.test_data.get_test_robot_by_sn(robot_sn)
        robot_tasks = [t for t in self.test_data.get_all_tasks_from_task_data() if t.get('robot_sn') == robot_sn]
        robot_events = [e for e in self.test_data.get_all_events() if e.get('robot_sn') == robot_sn]
        robot_charging = [c for c in self.test_data.get_all_charging_sessions() if c.get('robot_sn') == robot_sn]

        print(f"    🔍 Found data for robot {robot_sn}:")
        print(f"      - Robot status: {'✅' if robot_data else '❌'}")
        print(f"      - Tasks: {len(robot_tasks)}")
        print(f"      - Events: {len(robot_events)}")
        print(f"      - Charging sessions: {len(robot_charging)}")

        # Test that robot SN is consistent across all data types
        if robot_data:
            assert robot_data['robot_sn'] == robot_sn

        for task in robot_tasks:
            assert task['robot_sn'] == robot_sn

        for event in robot_events:
            assert event['robot_sn'] == robot_sn

        for session in robot_charging:
            assert session['robot_sn'] == robot_sn

        # Test that all data can be processed together
        if robot_data and robot_tasks and robot_events:
            # This robot has comprehensive data - test full pipeline

            # Process robot status
            robot_df = pd.DataFrame([robot_data])
            processed_robot = self.app._prepare_df_for_database(robot_df)

            # Process tasks
            tasks_with_time = []
            for i, task in enumerate(robot_tasks):
                task_copy = task.copy()
                task_copy['start_time'] = f'2024-09-01 {14+i}:30:00'
                tasks_with_time.append(task_copy)

            task_df = pd.DataFrame(tasks_with_time)
            processed_tasks = self.app._prepare_df_for_database(task_df)

            # Both should have same robot_sn
            assert processed_robot.iloc[0]['robot_sn'] == processed_tasks.iloc[0]['robot_sn']

            print(f"    ✅ Cross-data-type consistency maintained for robot {robot_sn}")

    def test_end_to_end_pipeline_simulation_with_json(self):
        """Test end-to-end pipeline simulation using comprehensive JSON data"""
        print("\n🔄 Testing end-to-end pipeline simulation with JSON data")

        # Get comprehensive test scenarios
        comprehensive_data = self.test_data.get_comprehensive_data()
        robot_combinations = comprehensive_data.get("robot_combinations", [])

        for combination in robot_combinations[:1]:  # Test first combination
            robot_sn = combination['robot_sn']
            location_id = combination['location_id']

            print(f"    🤖 Testing end-to-end for robot {robot_sn} at location {location_id}")

            # Step 1: Get all data for this robot
            robot_data = self.test_data.get_test_robot_by_sn(robot_sn)
            if not robot_data:
                # Use first available robot
                robot_data = self.test_data.get_all_robots_from_status_data()[0]
                robot_data['robot_sn'] = robot_sn

            # Step 2: Simulate complete data pipeline
            pipeline_results = {
                'successful_inserts': 0,
                'failed_inserts': 0,
                'notifications_sent': 0,
                'notifications_skipped': 0
            }

            # Process robot status
            robot_df = pd.DataFrame([robot_data])
            processed_robot_df = self.app._prepare_df_for_database(robot_df)

            # Simulate database insert (change detection)
            mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [])
            changes = detect_data_changes(mock_table, [robot_data], ["robot_sn"])

            if changes:
                pipeline_results['successful_inserts'] += 1

                # Test notification flow
                for change_info in changes.values():
                    should_skip = should_skip_notification("robot_status", change_info)

                    if not should_skip:
                        title, content = generate_individual_notification_content("robot_status", change_info)
                        severity, status = get_severity_and_status_for_change("robot_status", change_info)
                        pipeline_results['notifications_sent'] += 1
                    else:
                        pipeline_results['notifications_skipped'] += 1

            # Validate pipeline results
            assert pipeline_results['successful_inserts'] > 0, "Should have at least one successful insert"
            total_notifications = pipeline_results['notifications_sent'] + pipeline_results['notifications_skipped']
            assert total_notifications > 0, "Should process at least one notification decision"

            print(f"    ✅ End-to-end pipeline successful for robot {robot_sn}")
            print(f"      - Inserts: {pipeline_results['successful_inserts']}")
            print(f"      - Notifications sent: {pipeline_results['notifications_sent']}")
            print(f"      - Notifications skipped: {pipeline_results['notifications_skipped']}")

    def _create_mock_table(self, table_name, primary_keys, existing_data):
        """Helper to create mock table that behaves like RDSTable"""
        mock_table = MagicMock()
        mock_table.table_name = table_name
        mock_table.primary_keys = primary_keys
        mock_table.database_name = "test_db"
        mock_table.query_data.return_value = existing_data
        return mock_table

def run_integration_tests():
    """Run all integration tests with JSON data"""
    print("=" * 80)
    print("🔗 RUNNING PIPELINE INTEGRATION TESTS WITH JSON DATA")
    print("=" * 80)

    test_instance = TestPipelineIntegration()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
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
    print("📊 INTEGRATION TESTS SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "No tests")

    if failed == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Complete pipeline flows are working correctly with JSON data")
    else:
        print(f"\n⚠️ {failed} integration test(s) failed")

    return passed, failed

if __name__ == "__main__":
    run_integration_tests()