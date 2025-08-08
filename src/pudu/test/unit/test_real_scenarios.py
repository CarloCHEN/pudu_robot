"""
Real scenario tests using actual data patterns from your system
Tests complete flows with data that matches your production environment
"""

import sys
sys.path.append('../../')

from pudu.notifications.change_detector import detect_data_changes, normalize_record_for_comparison
from pudu.rds.utils import batch_insert_with_ids
from unittest.mock import MagicMock

class TestRealScenarios:
    """Test with actual data patterns from your robot system"""

    def setup_method(self):
        """Setup for real scenario tests"""
        self.mock_cursor = MagicMock()
        self.mock_cursor.connection = MagicMock()

    def test_your_actual_robot_data_scenario(self):
        """Test with the exact robot data from your example"""
        print("\n🤖 Testing with your actual robot data")

        # Your actual robot data from the example
        new_data = [
            {
                'robot_sn': '1230',
                'robot_type': 'CC1',
                'robot_name': 'demo_UF_demo',
                'location_id': '523670000',
                'water_level': 25,
                'sewage_level': 0,
                'battery_level': 100,
                'x': -0.23293037200521216,
                'y': -0.044921584455721364,
                'z': 0.026269476759686716,
                'status': 'Online',
                'tenant_id': '000000'
            },
            {
                'robot_sn': '1231',
                'robot_type': 'CC1',
                'robot_name': 'LDS-test',
                'location_id': '450270000',
                'water_level': 0,
                'sewage_level': 0,
                'battery_level': 100,
                'x': 0.6546468716153662,
                'y': 0.10216624231873786,
                'z': -0.1855085439150417,
                'status': 'Online',
                'tenant_id': '000000'
            }
        ]

        # Test that these are detected as new records (empty database)
        mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [])
        changes = detect_data_changes(mock_table, new_data, ["robot_sn"])

        # Should detect 2 new records
        assert len(changes) == 2
        assert '1230' in changes
        assert '1231' in changes

        for unique_id, change_info in changes.items():
            assert change_info['change_type'] == 'new_record'
            assert change_info['robot_sn'] in ['1230', '1231']
            assert len(change_info['changed_fields']) > 0

        print("  ✅ New record detection successful")

        # Test batch insert with IDs using your actual primary keys
        self.mock_cursor.fetchone.return_value = ('id',)  # Primary key detection
        self.mock_cursor.fetchall.return_value = [
            (123, '1230'),  # Simulating that robot_sn maps to these IDs in database
            (124, '1231')
        ]

        changed_records = [change_info['new_values'] for change_info in changes.values()]
        ids = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management", changed_records, ["robot_sn"])

        # Should return IDs for both records
        assert len(ids) == 2
        robot_sns_in_results = [data['robot_sn'] for data, _ in ids]
        assert '1230' in robot_sns_in_results
        assert '1231' in robot_sns_in_results

        print("  ✅ Batch insert with actual data successful")
        print("  🎉 Your actual robot data scenario PASSED")

    def test_robot_battery_change_scenario(self):
        """Test robot battery level change with your actual battery monitoring logic"""
        print("\n🔋 Testing robot battery change scenario")

        # Existing robot with normal battery
        existing_robot = {
            'robot_sn': '1230',
            'robot_name': 'demo_UF_demo',
            'battery_level': 85.0,
            'status': 'Online'
        }

        # Updated robot with low battery (critical scenario)
        updated_robot = {
            'robot_sn': '1230',
            'robot_name': 'demo_UF_demo',
            'battery_level': 8.5,  # Low battery
            'status': 'Online'
        }

        # Test change detection
        mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [existing_robot])
        changes = detect_data_changes(mock_table, [updated_robot], ["robot_sn"])

        assert len(changes) == 1
        change_info = list(changes.values())[0]
        assert change_info['change_type'] == 'update'
        assert 'battery_level' in change_info['changed_fields']
        assert change_info['old_values']['battery_level'] == 85.0
        assert change_info['new_values']['battery_level'] == 8.5

        print("  ✅ Battery change detection successful")

        # Test notification logic for low battery
        from pudu.notifications.notification_sender import should_skip_notification
        should_skip = should_skip_notification("robot_status", change_info)
        assert should_skip == False, "Low battery changes should NOT be skipped"

        print("  ✅ Low battery notification logic successful")
        print("  🎉 Battery change scenario PASSED")

    def test_task_status_update_scenario(self):
        """Test task status update with your actual task status codes"""
        print("\n📋 Testing task status update scenario")

        # Task in progress
        existing_task = {
            'robot_sn': '1230',
            'task_name': 'Library Cleaning',
            'start_time': '2024-09-01 14:30:00',
            'status': 1,  # In Progress (your actual status code)
            'progress': 50.0,
            'actual_area': 75.28
        }

        # Task completed
        completed_task = {
            'robot_sn': '1230',
            'task_name': 'Library Cleaning',
            'start_time': '2024-09-01 14:30:00',
            'status': 4,  # Task Ended (your actual status code)
            'progress': 100.0,
            'actual_area': 150.56
        }

        # Test change detection with composite primary keys
        mock_table = self._create_mock_table("mnt_robots_task",
                                           ["robot_sn", "task_name", "start_time"],
                                           [existing_task])
        changes = detect_data_changes(mock_table, [completed_task],
                                    ["robot_sn", "task_name", "start_time"])

        assert len(changes) == 1
        change_info = list(changes.values())[0]
        assert change_info['change_type'] == 'update'
        assert 'status' in change_info['changed_fields']
        assert 'progress' in change_info['changed_fields']
        assert change_info['old_values']['status'] == 1
        assert change_info['new_values']['status'] == 4

        print("  ✅ Task completion detection successful")

        # Test notification generation
        from pudu.notifications.notification_sender import (
            generate_individual_notification_content,
            get_severity_and_status_for_change
        )

        title, content = generate_individual_notification_content("robot_task", change_info)
        severity, status = get_severity_and_status_for_change("robot_task", change_info)

        # Task completion should be success
        assert "task" in title.lower()
        assert "Library Cleaning" in content
        assert severity == "success"
        assert status == "completed"

        print("  ✅ Task completion notification successful")
        print("  🎉 Task status update scenario PASSED")

    def test_decimal_precision_with_your_data(self):
        """Test decimal precision handling with your actual coordinate and measurement data"""
        print("\n📐 Testing decimal precision with your coordinate data")

        # Your actual high-precision coordinates and measurements
        precise_data = {
            'robot_sn': '1230',
            'x': -0.23293037200521216,      # Your actual X coordinate
            'y': -0.044921584455721364,     # Your actual Y coordinate
            'z': 0.026269476759686716,      # Your actual Z coordinate
            'battery_level': 100.567891234, # High precision battery
            'actual_area': 150.555555555,   # Area calculation precision
            'efficiency': 0.123456789012,   # Efficiency calculation precision
        }

        # Test normalization
        normalized = normalize_record_for_comparison(precise_data)

        # Battery level should be normalized (it's in DECIMAL_FIELDS_PRECISION)
        assert normalized['battery_level'] == 100.57

        # Area should be normalized
        assert abs(normalized['actual_area'] - 150.56) < 0.01

        # Efficiency should be normalized
        assert abs(normalized['efficiency'] - 0.12) < 0.01

        # Coordinates (x,y,z) should remain unchanged (not in DECIMAL_FIELDS_PRECISION)
        assert normalized['x'] == -0.23293037200521216
        assert normalized['y'] == -0.044921584455721364
        assert normalized['z'] == 0.026269476759686716

        print("  ✅ Coordinate and measurement precision handling successful")
        print("  🎉 Decimal precision scenario PASSED")

    def test_match_changes_to_db_ids_with_your_data(self):
        """Test the ID matching logic from your main.py with actual data"""
        print("\n🔗 Testing ID matching logic from your main.py")

        # Your changes dictionary structure
        changes = {
            '1230': {
                'robot_sn': '1230',
                'primary_key_values': {'robot_sn': '1230'},
                'change_type': 'new_record',
                'new_values': {
                    'robot_sn': '1230',
                    'robot_type': 'CC1',
                    'robot_name': 'demo_UF_demo',
                    'status': 'Online'
                }
            },
            '1231': {
                'robot_sn': '1231',
                'primary_key_values': {'robot_sn': '1231'},
                'change_type': 'new_record',
                'new_values': {
                    'robot_sn': '1231',
                    'robot_type': 'CC1',
                    'robot_name': 'LDS-test',
                    'status': 'Online'
                }
            }
        }

        # Simulated batch_insert_with_ids results
        ids = [
            ({'robot_sn': '1230', 'robot_type': 'CC1', 'robot_name': 'demo_UF_demo', 'status': 'Online'}, '1230'),
            ({'robot_sn': '1231', 'robot_type': 'CC1', 'robot_name': 'LDS-test', 'status': 'Online'}, '1231')
        ]

        # Your actual ID matching logic from main.py
        pk_to_db_id = {}
        primary_keys = ['robot_sn']
        for original_data, db_id in ids:
            pk_values = tuple(str(original_data.get(pk, '')) for pk in primary_keys)
            pk_to_db_id[pk_values] = db_id

        # Add database_key to changes
        for unique_id, change_info in changes.items():
            pk_values = tuple(str(change_info['primary_key_values'].get(pk, '')) for pk in primary_keys)
            db_id = pk_to_db_id.get(pk_values)
            changes[unique_id]['database_key'] = db_id

        # Verify matching worked correctly
        assert changes['1230']['database_key'] == '1230'
        assert changes['1231']['database_key'] == '1231'

        print("  ✅ ID matching with actual data successful")
        print("  🎉 ID matching scenario PASSED")

    def test_coordinate_data_handling(self):
        """Test handling of robot coordinate data (x,y,z) throughout pipeline"""
        print("\n📍 Testing coordinate data handling")

        # Robot with coordinates (in task)
        robot_with_coords = {
            'robot_sn': '1230',
            'x': -0.23293037200521216,
            'y': -0.044921584455721364,
            'z': 0.026269476759686716,
            'status': 'Online'
        }

        # Robot without coordinates (idle)
        another_robot_snle = {
            'robot_sn': '1231',
            'x': None,
            'y': None,
            'z': None,
            'status': 'Online'
        }

        data_list = [robot_with_coords, another_robot_snle]

        # Test normalization preserves coordinates correctly
        normalized_list = [normalize_record_for_comparison(record) for record in data_list]

        # Coordinates should be preserved exactly (not in DECIMAL_FIELDS_PRECISION)
        assert normalized_list[0]['x'] == -0.23293037200521216
        assert normalized_list[0]['y'] == -0.044921584455721364
        assert normalized_list[0]['z'] == 0.026269476759686716

        # None coordinates should remain None
        assert normalized_list[1]['x'] is None
        assert normalized_list[1]['y'] is None
        assert normalized_list[1]['z'] is None

        print("  ✅ Coordinate preservation successful")

        # Test change detection with coordinate changes
        existing_robot = robot_with_coords.copy()
        existing_robot['x'] = -0.25  # Slightly different coordinate

        mock_table = self._create_mock_table("mnt_robots_work_location", ["robot_sn"], [existing_robot])
        changes = detect_data_changes(mock_table, [robot_with_coords], ["robot_sn"])

        # Should detect coordinate change
        assert len(changes) == 1
        change_info = list(changes.values())[0]
        assert 'x' in change_info['changed_fields']

        print("  ✅ Coordinate change detection successful")
        print("  🎉 Coordinate data handling PASSED")

    def test_tenant_id_and_location_id_handling(self):
        """Test handling of tenant_id and location_id fields from your system"""
        print("\n🏢 Testing tenant and location ID handling")

        # Your actual data structure
        robot_data = {
            'robot_sn': '1230',
            'location_id': '523670000',  # Building/location identifier
            'tenant_id': '000000',       # Tenant identifier
            'robot_name': 'demo_UF_demo',
            'status': 'Online'
        }

        # Test that these IDs are preserved through normalization
        normalized = normalize_record_for_comparison(robot_data)

        assert normalized['location_id'] == '523670000'
        assert normalized['tenant_id'] == '000000'
        assert normalized['robot_sn'] == '1230'

        print("  ✅ ID field preservation successful")

        # Test change detection with ID fields
        existing_data = robot_data.copy()
        existing_data['location_id'] = '999999999'  # Different location

        mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [existing_data])
        changes = detect_data_changes(mock_table, [robot_data], ["robot_sn"])

        # Should detect location change
        assert len(changes) == 1
        change_info = list(changes.values())[0]
        assert 'location_id' in change_info['changed_fields']

        print("  ✅ Location ID change detection successful")
        print("  🎉 Tenant and location ID handling PASSED")

    def test_mixed_data_types_scenario(self):
        """Test scenario with mixed data types that could come from your APIs"""
        print("\n🔀 Testing mixed data types scenario")

        # Mixed data similar to what your APIs might return
        mixed_data = {
            'robot_sn': '1230',                      # String
            'battery_level': 95.567,                 # Float requiring precision
            'water_level': 25,                       # Integer
            'status': 'Online',                      # String
            'location_id': '523670000',              # String (large number)
            'x': -0.23293037200521216,              # High precision float
            'task_count': None,                      # None value
            'last_updated': '2024-09-01 14:30:00'   # Timestamp string
        }

        # Test normalization handles mixed types correctly
        normalized = normalize_record_for_comparison(mixed_data)

        # Verify correct handling of each type
        assert normalized['robot_sn'] == '1230'                    # String unchanged
        assert normalized['battery_level'] == 95.57               # Float normalized
        assert normalized['water_level'] == 25                    # Integer unchanged
        assert normalized['status'] == 'Online'                   # String unchanged
        assert normalized['location_id'] == '523670000'           # String number unchanged
        assert normalized['x'] == -0.23293037200521216           # Coordinate unchanged
        assert normalized['task_count'] is None                   # None preserved
        assert normalized['last_updated'] == '2024-09-01 14:30:00' # Timestamp unchanged

        print("  ✅ Mixed data type handling successful")
        print("  🎉 Mixed data types scenario PASSED")

    def _create_mock_table(self, table_name, primary_keys, existing_data):
        """Helper to create mock table for testing"""
        mock_table = MagicMock()
        mock_table.table_name = table_name
        mock_table.primary_keys = primary_keys
        mock_table.database_name = "test_db"
        mock_table.query_data.return_value = existing_data
        return mock_table

def run_real_scenario_tests():
    """Run all real scenario tests"""
    print("=" * 80)
    print("🎯 TESTING REAL PRODUCTION SCENARIOS")
    print("=" * 80)

    test_instance = TestRealScenarios()
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
    print("📊 REAL SCENARIO TESTS SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "No tests")

    if failed == 0:
        print("\n🎉 ALL REAL SCENARIO TESTS PASSED!")
        print("✅ Your production data patterns work correctly")
    else:
        print(f"\n⚠️ {failed} real scenario test(s) failed")

    return passed, failed

if __name__ == "__main__":
    run_real_scenario_tests()