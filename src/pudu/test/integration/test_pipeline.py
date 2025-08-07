"""
Integration tests for complete pipeline flows - tests real functions together
"""

import sys
sys.path.append('../../')

from pudu.notifications.change_detector import detect_data_changes, normalize_record_for_comparison
from pudu.notifications.notification_sender import (
    generate_individual_notification_content,
    get_severity_and_status_for_change,
    should_skip_notification
)
from pudu.rds.utils import batch_insert_with_ids, get_primary_key_column
from unittest.mock import MagicMock

class TestPipelineIntegration:
    """Test complete pipeline flows with real functions"""

    def setup_method(self):
        """Setup for integration tests"""
        self.mock_cursor = MagicMock()
        self.mock_cursor.connection = MagicMock()

    def test_complete_robot_status_change_flow(self):
        """Test complete flow: data change detection → batch insert → ID matching → notification"""
        print("\n🔄 Testing complete robot status change flow")

        # Step 1: Setup existing data (simulate database state)
        existing_data = [
            {"robot_sn": "1230", "robot_name": "demo_UF_demo", "battery_level": 50.0, "status": "Online"}
        ]

        # Step 2: New data with changes
        new_data = [
            {"robot_sn": "1230", "robot_name": "demo_UF_demo", "battery_level": 15.5, "status": "Online"}  # Battery changed
        ]

        # Create mock table that simulates your RDSTable
        mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], existing_data)

        # Step 3: Test change detection
        changes = detect_data_changes(mock_table, new_data, ["robot_sn"])

        assert len(changes) == 1, "Should detect one change"
        change_info = list(changes.values())[0]
        assert change_info["change_type"] == "update"
        assert "battery_level" in change_info["changed_fields"]
        assert change_info["new_values"]["battery_level"] == 15.5
        print("  ✅ Change detection successful")

        # Step 4: Test batch insert with IDs
        # Mock the batch insert response
        self.mock_cursor.fetchone.return_value = ('id',)  # Primary key detection
        self.mock_cursor.fetchall.return_value = [(123, "1230")]  # ID query result

        changed_records = [change_info["new_values"] for change_info in changes.values()]
        ids = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management", changed_records, ["robot_sn"])

        assert len(ids) == 1
        assert ids[0] == (changed_records[0], 123)
        print("  ✅ Batch insert with IDs successful")

        # Step 5: Test ID matching to changes
        pk_to_db_id = {}
        for original_data, db_id in ids:
            pk_values = tuple(str(original_data.get(pk, '')) for pk in ["robot_sn"])
            pk_to_db_id[pk_values] = db_id

        # Add database_key to changes
        for unique_id, change_info in changes.items():
            pk_values = tuple(str(change_info['primary_key_values'].get(pk, '')) for pk in ["robot_sn"])
            db_id = pk_to_db_id.get(pk_values)
            changes[unique_id]['database_key'] = db_id

        # Verify matching worked
        updated_change = list(changes.values())[0]
        assert updated_change['database_key'] == 123
        print("  ✅ ID matching successful")

        # Step 6: Test notification generation
        title, content = generate_individual_notification_content("robot_status", updated_change)
        severity, status = get_severity_and_status_for_change("robot_status", updated_change)

        # Low battery should trigger appropriate notification
        assert "battery" in title.lower() or "battery" in content.lower()
        assert severity == "warning"  # 15.5% battery is warning level
        assert status == "warning"
        print("  ✅ Notification generation successful")

        print("  🎉 Complete robot status change flow PASSED")

    def test_complete_task_completion_flow(self):
        """Test complete flow for task completion scenario"""
        print("\n🔄 Testing complete task completion flow")

        # Step 1: Existing task in progress
        existing_task = [
            {
                "robot_sn": "1230",
                "task_name": "Library Cleaning",
                "start_time": "2024-09-01 14:30:00",
                "status": 1,  # In Progress
                "progress": 50.0,
                "actual_area": 75.28
            }
        ]

        # Step 2: Task completion data
        completed_task = [
            {
                "robot_sn": "1230",
                "task_name": "Library Cleaning",
                "start_time": "2024-09-01 14:30:00",
                "status": 4,  # Task Ended
                "progress": 100.0,
                "actual_area": 150.56
            }
        ]

        # Create mock table
        mock_table = self._create_mock_table("mnt_robots_task", ["robot_sn", "task_name", "start_time"], existing_task)

        # Step 3: Detect changes
        changes = detect_data_changes(mock_table, completed_task, ["robot_sn", "task_name", "start_time"])

        assert len(changes) == 1
        change_info = list(changes.values())[0]
        assert change_info["change_type"] == "update"
        assert "status" in change_info["changed_fields"]
        assert "progress" in change_info["changed_fields"]
        print("  ✅ Task completion detection successful")

        # Step 4: Test notification logic
        title, content = generate_individual_notification_content("robot_task", change_info)
        severity, status = get_severity_and_status_for_change("robot_task", change_info)

        # Task completion should be success
        assert "task" in title.lower()
        assert "Library Cleaning" in content
        assert severity == "success"
        assert status == "completed"
        print("  ✅ Task completion notification successful")

        print("  🎉 Complete task completion flow PASSED")

    def test_notification_skipping_integration(self):
        """Test that notification skipping works correctly in complete flow"""
        print("\n🔄 Testing notification skipping integration")

        # Test scenarios that should/shouldn't be skipped
        test_scenarios = [
            # (data_type, change_data, should_skip, description)
            ("robot_charging", {"change_type": "update", "changed_fields": ["final_power"]}, True, "Charging updates"),
            ("robot_status", {"change_type": "update", "changed_fields": ["battery_level"], "new_values": {"battery_level": 80}}, True, "High battery updates"),
            ("robot_status", {"change_type": "update", "changed_fields": ["battery_level"], "new_values": {"battery_level": 8}}, False, "Low battery alerts"),
            ("robot_task", {"change_type": "update", "changed_fields": ["status"]}, False, "Task status changes"),
            ("location", {"change_type": "new_record"}, True, "Location changes"),
        ]

        for data_type, change_info, expected_skip, description in test_scenarios:
            result = should_skip_notification(data_type, change_info)
            assert result == expected_skip, f"{description}: expected skip={expected_skip}, got {result}"
            print(f"  ✅ {description} - skipping logic correct")

        print("  🎉 Notification skipping integration PASSED")

    def test_decimal_normalization_integration(self):
        """Test that decimal normalization works correctly throughout the pipeline"""
        print("\n🔄 Testing decimal normalization integration")

        # Step 1: Raw API data with high precision
        raw_data = [
            {
                "robot_sn": "1230",
                "battery_level": 95.567891234,  # High precision from API
                "actual_area": 150.555555,      # Area calculation precision
                "efficiency": 0.123456789,      # Efficiency calculation
                "progress": 82.999999           # Progress percentage
            }
        ]

        # Step 2: Normalize for comparison
        normalized = [normalize_record_for_comparison(record) for record in raw_data]

        # Verify normalization
        norm_record = normalized[0]
        assert norm_record["battery_level"] == 95.57
        assert norm_record["actual_area"] == 150.56
        assert abs(norm_record["efficiency"] - 0.12) < 0.01
        assert norm_record["progress"] == 83.00
        print("  ✅ Decimal normalization successful")

        # Step 3: Test that normalized values would match database values
        # Simulate database record with same precision
        db_record = {
            "robot_sn": "1230",
            "battery_level": 95.57,  # Already normalized in DB
            "actual_area": 150.56,
            "efficiency": 0.12,
            "progress": 83.00
        }

        mock_table = self._create_mock_table("test_table", ["robot_sn"], [db_record])
        changes = detect_data_changes(mock_table, raw_data, ["robot_sn"])

        # Should detect NO changes because normalized values match
        assert len(changes) == 0, "Normalized values should match database values"
        print("  ✅ Database comparison integration successful")

        print("  🎉 Decimal normalization integration PASSED")

    def test_primary_key_detection_integration(self):
        """Test primary key detection with different table scenarios"""
        print("\n🔄 Testing primary key detection integration")

        # Test different primary key scenarios
        pk_scenarios = [
            ("mnt_robots_management", "id"),
            ("mnt_robots_task", "id"),
            ("pro_building_info", "id"),
            ("users", "id"),  # Common table name
        ]

        for table_name, expected_pk in pk_scenarios:
            # Mock successful primary key detection
            self.mock_cursor.fetchone.return_value = (expected_pk,)

            result = get_primary_key_column(self.mock_cursor, table_name)
            assert result == expected_pk, f"Table {table_name}: expected '{expected_pk}', got '{result}'"
            print(f"  ✅ Primary key detection for {table_name} successful")

        print("  🎉 Primary key detection integration PASSED")

    def _create_mock_table(self, table_name, primary_keys, existing_data):
        """Helper to create mock table that behaves like RDSTable"""
        mock_table = MagicMock()
        mock_table.table_name = table_name
        mock_table.primary_keys = primary_keys
        mock_table.database_name = "test_db"

        # Mock query_data to return existing data
        mock_table.query_data.return_value = existing_data

        return mock_table

def run_integration_tests():
    """Run all integration tests"""
    print("=" * 80)
    print("🔗 RUNNING PIPELINE INTEGRATION TESTS")
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
        print("✅ Complete pipeline flows are working correctly")
    else:
        print(f"\n⚠️ {failed} integration test(s) failed")

    return passed, failed

if __name__ == "__main__":
    run_integration_tests()