"""
Unit tests for database writer functionality
"""

import sys
from pathlib import Path
import os

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


from test.mocks.mock_database import MockDatabaseWriter
from test.utils.test_helpers import TestDataLoader, TestValidator, setup_test_logging


class TestDatabaseWriter:
    """Test database writer operations with mock database"""

    def setup_method(self):
        """Setup for each test"""
        self.db_writer = MockDatabaseWriter()
        self.test_data = TestDataLoader()

    def test_robot_status_writes(self):
        """Test robot status database writes"""
        print("\n🧪 Testing robot status database writes")

        status_data = self.test_data.get_robot_status_data()
        valid_cases = status_data.get("valid_status_changes", [])

        for case in valid_cases[:3]:  # Test first 3 cases
            robot_sn = case["data"]["sn"]
            status_data = {"status": case["data"]["run_status"].lower(), "timestamp": case["data"].get("timestamp")}

            print(f"  Testing status write for robot: {robot_sn}")

            # Clear previous data
            self.db_writer.clear_written_data()

            # Write status using new interface
            database_names, table_names, changes_detected = self.db_writer.write_robot_status(robot_sn, status_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robots_management", robot_sn)

            # Validate changes detected
            assert len(changes_detected) > 0, "Should detect changes for new data"

            print(f"  ✅ Status write validated for {robot_sn}")

    def test_robot_pose_writes(self):
        """Test robot pose database writes"""
        print("\n🧪 Testing robot pose database writes")

        pose_data = self.test_data.get_robot_pose_data()
        normal_cases = pose_data.get("normal_positions", [])

        for case in normal_cases[:3]:  # Test first 3 cases
            robot_sn = case["data"]["sn"]
            pose_data = {
                "x": case["data"]["x"],
                "y": case["data"]["y"],
                "yaw": case["data"]["yaw"],
                "timestamp": case["data"].get("timestamp"),
            }

            print(f"  Testing pose write for robot: {robot_sn}")

            # Clear previous data
            self.db_writer.clear_written_data()

            # Write pose using new interface
            database_names, table_names, changes_detected = self.db_writer.write_robot_pose(robot_sn, pose_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robots_management", robot_sn)

            # Validate changes detected
            assert len(changes_detected) > 0, "Should detect changes for new data"

            print(f"  ✅ Pose write validated for {robot_sn}")

    def test_robot_power_writes(self):
        """Test robot power database writes"""
        print("\n🧪 Testing robot power database writes")

        power_data = self.test_data.get_robot_power_data()
        normal_cases = power_data.get("normal_power_levels", [])

        for case in normal_cases[:3]:  # Test first 3 cases
            robot_sn = case["data"]["sn"]
            power_data = {
                "power": case["data"]["power"],
                "charge_state": case["data"]["charge_state"],
                "timestamp": case["data"].get("timestamp"),
            }

            print(f"  Testing power write for robot: {robot_sn}")

            # Clear previous data
            self.db_writer.clear_written_data()

            # Write power using new interface
            database_names, table_names, changes_detected = self.db_writer.write_robot_power(robot_sn, power_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robots_management", robot_sn)

            # Validate changes detected
            assert len(changes_detected) > 0, "Should detect changes for new data"

            print(f"  ✅ Power write validated for {robot_sn}")

    def test_robot_event_writes(self):
        """Test robot event database writes"""
        print("\n🧪 Testing robot event database writes")

        error_data = self.test_data.get_robot_error_data()

        # Test different error types
        for category_name, cases in error_data.items():
            if category_name == "edge_cases":
                continue

            case = cases[0] if cases else None  # Test first case from each category
            if not case:
                continue

            robot_sn = case["data"]["sn"]
            event_data = {
                "error_id": case["data"]["error_id"],
                "error_level": case["data"]["error_level"],
                "error_type": case["data"]["error_type"],
                "error_detail": case["data"]["error_detail"],
                "timestamp": case["data"].get("timestamp"),
            }

            print(f"  Testing event write for robot: {robot_sn} ({category_name})")

            # Clear previous data
            self.db_writer.clear_written_data()

            # Write event using new interface
            database_names, table_names, changes_detected = self.db_writer.write_robot_event(robot_sn, event_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robot_events", robot_sn)

            # Validate changes detected
            assert len(changes_detected) > 0, "Should detect changes for new data"

            print(f"  ✅ Event write validated for {robot_sn}")

    def test_schema_validation(self):
        """Test database schema validation"""
        print("\n🧪 Testing database schema validation")

        # Test valid data
        valid_status_data = {"robot_sn": "TEST_ROBOT_SCHEMA", "status": "online"}

        result = self.db_writer._validate_data_against_schema("mnt_robots_management", valid_status_data)
        assert result == True
        print("  ✅ Valid schema validation passed")

        # Test missing primary key
        missing_pk_data = {"status": "online"}

        result = self.db_writer._validate_data_against_schema("mnt_robots_management", missing_pk_data)
        assert result == False
        print("  ✅ Missing primary key detection works")

    def test_data_filtering(self):
        """Test that None values are properly filtered"""
        print("\n🧪 Testing data filtering")

        # Test with None values
        data_with_none = {"robot_sn": "TEST_ROBOT_FILTER", "status": "online", "battery_level": None, "x": 10.5, "y": None}

        self.db_writer.clear_written_data()
        database_names, table_names, changes_detected = self.db_writer.write_robot_status("TEST_ROBOT_FILTER", data_with_none)

        written_data = self.db_writer.get_written_data()
        table_data = written_data.get("mnt_robots_management", [])

        if table_data:
            record = table_data[0]
            # Check that None values were filtered out
            assert "battery_level" not in record or record["battery_level"] is not None
            assert "y" not in record or record["y"] is not None
            print("  ✅ None value filtering works correctly")
        else:
            print("  ⚠️ No data written to validate filtering")

    def test_multiple_table_writes(self):
        """Test writing to multiple tables simultaneously"""
        print("\n🧪 Testing multiple table writes")

        robot_sn = "TEST_ROBOT_MULTI"

        # Clear previous data
        self.db_writer.clear_written_data()

        # Write status
        status_db_names, status_table_names, status_changes = self.db_writer.write_robot_status(robot_sn, {"status": "online"})

        # Write event
        event_db_names, event_table_names, event_changes = self.db_writer.write_robot_event(
            robot_sn,
            {
                "error_id": "test_event_001",
                "error_level": "INFO",
                "error_type": "TestEvent",
                "error_detail": "Testing multiple writes",
                "timestamp": 1640995800,
            },
        )

        # Validate both writes
        written_data = self.db_writer.get_written_data()

        assert "mnt_robots_management" in written_data
        assert "mnt_robot_events" in written_data

        status_records = [r for r in written_data["mnt_robots_management"] if r.get("robot_sn") == robot_sn]
        event_records = [r for r in written_data["mnt_robot_events"] if r.get("robot_sn") == robot_sn]

        assert len(status_records) > 0
        assert len(event_records) > 0

        # Validate changes detected for both
        assert len(status_changes) > 0, "Should detect status changes"
        assert len(event_changes) > 0, "Should detect event changes"

        print("  ✅ Multiple table writes validated")

    def test_change_detection_interface(self):
        """Test change detection interface matches expected format"""
        print("\n🧪 Testing change detection interface")

        robot_sn = "TEST_ROBOT_CHANGES"

        # Clear previous data
        self.db_writer.clear_written_data()

        # Write status
        database_names, table_names, changes_detected = self.db_writer.write_robot_status(
            robot_sn, {"status": "online", "timestamp": 1640995800}
        )

        # Validate return format
        assert isinstance(database_names, list), "database_names should be a list"
        assert isinstance(table_names, list), "table_names should be a list"
        assert isinstance(changes_detected, dict), "changes_detected should be a dict"

        # Validate changes format
        for change_id, changes in changes_detected.items():
            for key, change_info in changes.items():
                assert 'robot_sn' in change_info, "Change info should have robot_sn"
                assert 'primary_key_values' in change_info, "Change info should have primary_key_values"
                assert 'change_type' in change_info, "Change info should have change_type"
                assert 'changed_fields' in change_info, "Change info should have changed_fields"
                assert 'old_values' in change_info, "Change info should have old_values"
                assert 'new_values' in change_info, "Change info should have new_values"
                assert 'database_key' in change_info, "Change info should have database_key"

        print("  ✅ Change detection interface validated")

    def test_connection_management(self):
        """Test database connection management"""
        print("\n🧪 Testing connection management")

        # Test connection cleanup
        self.db_writer.close_all_connections()
        assert len(self.db_writer.connections) == 0
        print("  ✅ Connection cleanup works")


# Test runner function
def run_database_tests():
    """Run all database writer tests"""
    setup_test_logging("INFO")

    print("=" * 60)
    print("RUNNING DATABASE WRITER TESTS")
    print("=" * 60)

    test_instance = TestDatabaseWriter()
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
            # Print database summary after each test
            test_instance.db_writer.print_summary()

    print(f"\n{'='*60}")
    print("DATABASE TESTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_database_tests()