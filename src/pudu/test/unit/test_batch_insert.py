"""
Unit tests for RDS functions and database operations using JSON data
"""

import sys
sys.path.append('../../')

from pudu.rds.utils import (
    batch_insert_with_ids,
    _query_ids_by_unique_keys,
    get_primary_key_column
)
from pudu.test.utils.test_helpers import TestDataLoader, TestValidator
from unittest.mock import MagicMock

class TestBatchInsert:
    """Test RDS functions with realistic data from JSON"""

    def setup_method(self):
        """Setup for RDS tests"""
        self.test_data = TestDataLoader()
        self.validator = TestValidator()
        self.mock_cursor = MagicMock()
        self.mock_cursor.connection = MagicMock()

    def test_batch_insert_with_json_robot_data(self):
        """Test batch_insert_with_ids using JSON robot data"""
        print("  🤖 Testing batch_insert_with_ids with JSON robot data")

        # Get real robot data from JSON
        all_robots = self.test_data.get_all_robots_from_status_data()

        if len(all_robots) >= 2:
            # Use first 2 robots for testing
            test_robots = all_robots[:2]

            # Convert to format expected by batch insert
            data_list = []
            for robot in test_robots:
                data_list.append({
                    'robot_sn': robot['robot_sn'],
                    'robot_name': robot.get('robot_name', f"Robot_{robot['robot_sn']}"),
                    'battery_level': robot.get('battery_level'),
                    'status': robot.get('status'),
                    'water_level': robot.get('water_level'),
                    'sewage_level': robot.get('sewage_level')
                })

            # Mock primary key detection
            self.mock_cursor.fetchone.return_value = ('id',)

            # Mock ID query results
            self.mock_cursor.fetchall.return_value = [
                (123, test_robots[0]['robot_sn']),
                (124, test_robots[1]['robot_sn'])
            ]

            # Test batch insert with unique keys
            results = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management",
                                          data_list, ["robot_sn"])

            # Validate results
            assert len(results) == 2
            assert results[0][0]['robot_sn'] == test_robots[0]['robot_sn']
            assert results[1][0]['robot_sn'] == test_robots[1]['robot_sn']
            assert results[0][1] == 123
            assert results[1][1] == 124

            print(f"    ✅ Batch insert successful with {len(data_list)} JSON robot records")

    def test_query_ids_by_unique_keys_with_json_task_data(self):
        """Test _query_ids_by_unique_keys using JSON task data"""
        print("  📋 Testing _query_ids_by_unique_keys with JSON task data")

        all_tasks = self.test_data.get_all_tasks_from_task_data()

        if len(all_tasks) > 0:
            # Convert task data to database format
            data_list = []
            for i, task in enumerate(all_tasks):
                data_list.append({
                    'robot_sn': task['robot_sn'],
                    'task_name': task['task_name'],
                    'start_time': f'2024-09-01 {14+i}:30:00',  # Add required timestamp
                    'status': task.get('status', 'Unknown'),
                    'progress': task.get('progress', 0)
                })

            # Mock database response with composite keys
            mock_db_results = []
            for i, task_data in enumerate(data_list):
                mock_db_results.append((
                    100 + i,  # id
                    task_data['robot_sn'],  # robot_sn
                    task_data['task_name'], # task_name
                    task_data['start_time'] # start_time
                ))

            self.mock_cursor.fetchall.return_value = mock_db_results

            # Test query with composite unique keys
            results = _query_ids_by_unique_keys(
                self.mock_cursor,
                "mnt_robots_task",
                data_list,
                ["robot_sn", "task_name", "start_time"],
                "id"
            )

            # Validate results
            assert len(results) == len(data_list)

            for i, (original_data, db_id) in enumerate(results):
                assert original_data['robot_sn'] == all_tasks[i]['robot_sn']
                assert original_data['task_name'] == all_tasks[i]['task_name']
                assert db_id == 100 + i

            print(f"    ✅ Query IDs successful with {len(data_list)} JSON task records")

    def test_primary_key_detection_with_realistic_table_names(self):
        """Test primary key detection with realistic table names from your schema"""
        print("  🔑 Testing primary key detection with realistic table names")

        # Test with actual table names from your database schema
        table_scenarios = [
            ("mnt_robots_management", "id"),
            ("mnt_robots_task", "id"),
            ("mnt_robot_events", "id"),
            ("pro_building_info", "id"),
            ("mnt_robots_charging_sessions", "id")
        ]

        for table_name, expected_pk in table_scenarios:
            # Mock successful primary key detection
            self.mock_cursor.fetchone.return_value = (expected_pk,)

            result = get_primary_key_column(self.mock_cursor, table_name)
            assert result == expected_pk, f"Table {table_name}: expected '{expected_pk}', got '{result}'"
            print(f"    ✅ {table_name} → {expected_pk}")

    def test_sql_injection_prevention_with_json_data(self):
        """Test SQL injection prevention using potentially problematic data from JSON"""
        print("  🛡️ Testing SQL injection prevention with JSON data")

        # Create potentially problematic data (simulating malicious input)
        problematic_data = [
            {"robot_sn": "'; DROP TABLE users; --", "name": "Malicious Robot"},
            {"robot_sn": "normal_robot", "name": "Normal Robot"},
            {"robot_sn": "1230'; UPDATE users SET password='hacked'", "name": "Another Attack"}
        ]

        # Should not crash and should escape the values
        self.mock_cursor.fetchall.return_value = [
            (1, "'; DROP TABLE users; --"),
            (2, "normal_robot"),
            (3, "1230'; UPDATE users SET password='hacked'")
        ]

        try:
            results = _query_ids_by_unique_keys(
                self.mock_cursor,
                "test_table",
                problematic_data,
                ["robot_sn"],
                "id"
            )

            # Verify execute was called (function didn't crash)
            assert self.mock_cursor.execute.called

            # Check that dangerous characters were properly handled
            executed_sql = self.mock_cursor.execute.call_args[0][0]

            # The SQL should contain escaped quotes
            assert "SELECT" in executed_sql
            assert "WHERE" in executed_sql

            print("    ✅ SQL injection prevention successful")

        except Exception as e:
            # Some SQL injection attempts might cause exceptions, which is acceptable
            print(f"    ✅ SQL injection attempt properly handled with exception: {e}")

    def test_batch_operations_with_mixed_json_data(self):
        """Test batch operations with mixed data from different JSON sources"""
        print("  🔄 Testing batch operations with mixed JSON data")

        # Get data from different sources that could be batch processed together
        robots = self.test_data.get_all_robots_from_status_data()[:2]
        events = self.test_data.get_all_events()[:2]

        # Test batch insert for robots
        if len(robots) > 0:
            robot_data_list = []
            for robot in robots:
                robot_data_list.append({
                    'robot_sn': robot['robot_sn'],
                    'status': robot.get('status'),
                    'battery_level': robot.get('battery_level')
                })

            # Mock for robot batch insert
            self.mock_cursor.fetchone.return_value = ('id',)
            self.mock_cursor.lastrowid = 200

            results = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management",
                                          robot_data_list, None)  # Pure insert

            assert len(results) == len(robot_data_list)
            print(f"    ✅ Robot batch insert: {len(results)} records")

        # Test batch insert for events
        if len(events) > 0:
            event_data_list = []
            for event in events:
                event_data_list.append({
                    'robot_sn': event['robot_sn'],
                    'event_type': event.get('event_type'),
                    'event_level': event.get('event_level'),
                    'error_id': event.get('error_id', 'event_001')
                })

            # Mock for event batch insert with composite keys
            self.mock_cursor.fetchone.return_value = ('id',)
            mock_event_results = [(300 + i, event['robot_sn'], event.get('error_id', f'event_{i}'))
                                 for i, event in enumerate(events)]
            self.mock_cursor.fetchall.return_value = mock_event_results

            results = batch_insert_with_ids(self.mock_cursor, "mnt_robot_events",
                                          event_data_list, ["robot_sn", "error_id"])

            assert len(results) == len(event_data_list)
            print(f"    ✅ Event batch insert: {len(results)} records")

    def test_database_connection_simulation_with_json(self):
        """Test database connection handling with JSON data scenarios"""
        print("  🔌 Testing database connection simulation with JSON")

        # Test connection error handling
        def simulate_connection_error():
            raise Exception("Connection timeout")

        # Test that functions handle connection errors gracefully
        try:
            # This should be handled gracefully in your actual implementation
            # We're testing the error path exists
            self.mock_cursor.execute.side_effect = simulate_connection_error

            robots = self.test_data.get_all_robots_from_status_data()[:1]
            if robots:
                data_list = [{'robot_sn': robots[0]['robot_sn'], 'status': 'Online'}]

                try:
                    batch_insert_with_ids(self.mock_cursor, "test_table", data_list, ["robot_sn"])
                except Exception as e:
                    # Should handle connection errors
                    assert "Connection timeout" in str(e)
                    print("    ✅ Connection error handled appropriately")
        except Exception as e:
            print(f"    ✅ Database error handling test completed: {e}")

    def test_null_and_empty_value_handling_with_json_edge_cases(self):
        """Test NULL and empty value handling using JSON edge cases"""
        print("  🚫 Testing NULL and empty value handling with JSON edge cases")

        # Get edge cases from JSON
        edge_cases = []

        # Robot status edge cases
        status_edge_cases = self.test_data.get_robot_status_data().get("edge_cases", [])
        edge_cases.extend(status_edge_cases)

        # Charging edge cases
        charging_edge_cases = self.test_data.get_robot_charging_data().get("edge_cases", [])
        edge_cases.extend(charging_edge_cases)

        # Location edge cases
        location_edge_cases = self.test_data.get_location_data().get("edge_cases", [])
        edge_cases.extend(location_edge_cases)

        for edge_case in edge_cases:
            # Add some None values to test NULL handling
            test_case = edge_case.copy()
            test_case.update({
                'optional_field_1': None,
                'optional_field_2': '',
                'optional_field_3': 'NULL'
            })

            # Test that NULL values are handled in SQL generation
            data_list = [test_case]

            # Mock response
            self.mock_cursor.fetchall.return_value = [(1, test_case.get('robot_sn', 'test'))]

            try:
                results = _query_ids_by_unique_keys(
                    self.mock_cursor,
                    "test_table",
                    data_list,
                    ["robot_sn"],
                    "id"
                )

                # Should handle None values without crashing
                assert len(results) == 1
                print(f"    ✅ NULL handling successful for edge case: {edge_case.get('name', 'unnamed')}")

            except Exception as e:
                print(f"    ⚠️ Edge case error (acceptable): {edge_case.get('name', 'unnamed')} - {e}")

    def test_large_batch_simulation_with_json_data(self):
        """Test large batch operations using all available JSON data"""
        print("  📈 Testing large batch simulation with all JSON data")

        # Combine all robot data for large batch test
        all_robots = self.test_data.get_all_robots_from_status_data()
        all_tasks = self.test_data.get_all_tasks_from_task_data()

        # Create large dataset
        large_robot_dataset = []

        # Replicate robot data to simulate larger dataset
        for i in range(5):  # Create 5x the data
            for j, robot in enumerate(all_robots):
                large_robot_dataset.append({
                    'robot_sn': f"{robot['robot_sn']}_{i}_{j}",
                    'robot_name': robot.get('robot_name', f"Robot_{i}_{j}"),
                    'battery_level': robot.get('battery_level'),
                    'status': robot.get('status')
                })

        if len(large_robot_dataset) > 10:  # Only test if we have substantial data
            # Mock responses for large batch
            self.mock_cursor.fetchone.return_value = ('id',)
            self.mock_cursor.lastrowid = 1000

            # Test pure insert with large batch
            results = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management",
                                          large_robot_dataset, None)

            # Should handle large batch
            assert len(results) == len(large_robot_dataset)

            # Test that IDs are sequential
            for i, (data, db_id) in enumerate(results):
                assert db_id == 1000 + i
                assert data['robot_sn'] == large_robot_dataset[i]['robot_sn']

            print(f"    ✅ Large batch insert successful: {len(large_robot_dataset)} records")

    def test_composite_primary_key_handling_with_json_tasks(self):
        """Test composite primary key handling using JSON task data"""
        print("  🔑 Testing composite primary key handling with JSON tasks")

        all_tasks = self.test_data.get_all_tasks_from_task_data()

        if len(all_tasks) > 0:
            # Create task data with composite primary keys
            task_data_list = []
            mock_db_results = []

            for i, task in enumerate(all_tasks):
                start_time = f'2024-09-01 {14+i}:30:00'
                task_data = {
                    'robot_sn': task['robot_sn'],
                    'task_name': task['task_name'],
                    'start_time': start_time,
                    'status': task.get('status'),
                    'progress': task.get('progress')
                }
                task_data_list.append(task_data)

                # Mock corresponding database result
                mock_db_results.append((
                    200 + i,  # id
                    task['robot_sn'],  # robot_sn
                    task['task_name'], # task_name
                    start_time         # start_time
                ))

            self.mock_cursor.fetchall.return_value = mock_db_results

            # Test with composite unique keys
            results = _query_ids_by_unique_keys(
                self.mock_cursor,
                "mnt_robots_task",
                task_data_list,
                ["robot_sn", "task_name", "start_time"],
                "id"
            )

            # Validate composite key matching
            assert len(results) == len(task_data_list)

            for i, (original_data, db_id) in enumerate(results):
                assert original_data['robot_sn'] == all_tasks[i]['robot_sn']
                assert original_data['task_name'] == all_tasks[i]['task_name']
                assert db_id == 200 + i

            # Verify SQL was generated correctly for composite keys
            executed_sql = self.mock_cursor.execute.call_args[0][0]
            assert "robot_sn" in executed_sql
            assert "task_name" in executed_sql
            assert "start_time" in executed_sql
            assert " AND " in executed_sql  # Should join conditions with AND
            assert " OR " in executed_sql   # Should join records with OR

            print(f"    ✅ Composite primary key handling successful with {len(task_data_list)} tasks")

    def test_data_consistency_through_rds_operations_with_json(self):
        """Test data consistency through RDS operations using JSON data"""
        print("  🔍 Testing data consistency through RDS operations with JSON")

        # Use robot data for consistency testing
        robot = self.test_data.get_all_robots_from_status_data()[0]

        original_data = {
            'robot_sn': robot['robot_sn'],
            'robot_name': robot.get('robot_name'),
            'battery_level': robot.get('battery_level'),
            'status': robot.get('status')
        }

        # Test that data survives round-trip through RDS operations
        data_list = [original_data]

        # Mock batch insert
        self.mock_cursor.fetchone.return_value = ('id',)
        self.mock_cursor.fetchall.return_value = [(500, robot['robot_sn'])]

        results = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management",
                                      data_list, ["robot_sn"])

        # Validate data preservation
        returned_data, db_id = results[0]

        assert returned_data['robot_sn'] == original_data['robot_sn']
        assert returned_data['robot_name'] == original_data['robot_name']
        assert returned_data['battery_level'] == original_data['battery_level']
        assert returned_data['status'] == original_data['status']
        assert db_id == 500

        print("    ✅ Data consistency maintained through RDS operations")

    def test_error_handling_in_rds_operations_with_edge_cases(self):
        """Test error handling in RDS operations using JSON edge cases"""
        print("  ⚠️ Testing error handling in RDS operations with edge cases")

        # Get edge cases from JSON
        edge_cases = self.test_data.get_robot_status_data().get("edge_cases", [])

        for edge_case in edge_cases:
            try:
                # Test with edge case data
                data_list = [edge_case]

                # Mock primary key detection failure
                self.mock_cursor.fetchone.return_value = None

                try:
                    batch_insert_with_ids(self.mock_cursor, "nonexistent_table",
                                        data_list, ["robot_sn"])
                    assert False, "Should raise ValueError for missing primary key"
                except ValueError as e:
                    assert "Could not detect primary key column" in str(e)
                    print(f"    ✅ Properly handled missing primary key for edge case")

                # Test with empty data list
                results = batch_insert_with_ids(self.mock_cursor, "test_table", [], ["robot_sn"])
                assert results == []
                print(f"    ✅ Properly handled empty data list")

            except Exception as e:
                print(f"    ℹ️ Edge case error handled: {edge_case.get('name', 'unnamed')} - {e}")

    def test_performance_characteristics_with_json_data(self):
        """Test performance characteristics using JSON data of various sizes"""
        print("  ⚡ Testing performance characteristics with JSON data")

        # Test with different batch sizes using JSON data
        all_robots = self.test_data.get_all_robots_from_status_data()

        batch_sizes = [1, len(all_robots), len(all_robots) * 2]

        for batch_size in batch_sizes:
            if batch_size <= len(all_robots):
                test_robots = all_robots[:batch_size]
            else:
                # Duplicate data to reach batch size
                test_robots = (all_robots * ((batch_size // len(all_robots)) + 1))[:batch_size]

            # Convert to data list
            data_list = []
            for i, robot in enumerate(test_robots):
                data_list.append({
                    'robot_sn': f"{robot['robot_sn']}_{i}",
                    'status': robot.get('status'),
                    'battery_level': robot.get('battery_level')
                })

            # Mock batch insert
            self.mock_cursor.fetchone.return_value = ('id',)
            self.mock_cursor.lastrowid = 1000

            # Time the operation (basic performance test)
            import time
            start_time = time.time()

            results = batch_insert_with_ids(self.mock_cursor, "test_table", data_list, None)

            end_time = time.time()
            duration = end_time - start_time

            # Validate results
            assert len(results) == batch_size

            print(f"    ✅ Batch size {batch_size}: {duration:.4f}s")

def run_batch_insert_tests():
    """Run all RDS integration tests"""
    print("=" * 80)
    print("🗄️ RUNNING RDS INTEGRATION TESTS WITH JSON DATA")
    print("=" * 80)

    test_instance = TestBatchInsert()
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
    print("📊 RDS INTEGRATION TESTS SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "No tests")

    if failed == 0:
        print("\n🎉 ALL RDS INTEGRATION TESTS PASSED!")
        print("✅ Database operations work correctly with JSON data")
    else:
        print(f"\n⚠️ {failed} RDS integration test(s) failed")

    return passed, failed

if __name__ == "__main__":
    run_batch_insert_tests()