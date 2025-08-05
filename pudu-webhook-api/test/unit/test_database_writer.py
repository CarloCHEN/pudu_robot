"""
Unit tests for database writer functionality
"""

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

            # Write status
            database_names, table_names = self.db_writer.write_robot_status(robot_sn, status_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robots_management", robot_sn)

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

            # Write pose
            database_names, table_names = self.db_writer.write_robot_pose(robot_sn, pose_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robots_management", robot_sn)

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

            # Write power
            database_names, table_names = self.db_writer.write_robot_power(robot_sn, power_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robots_management", robot_sn)

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

            # Write event
            database_names, table_names = self.db_writer.write_robot_event(robot_sn, event_data)

            # Validate write
            written_data = self.db_writer.get_written_data()
            assert TestValidator.validate_database_write(written_data, "mnt_robot_events", robot_sn)

            print(f"  ✅ Event write validated for {robot_sn}")

    def test_schema_validation(self):
        """Test database schema validation"""
        print("\n🧪 Testing database schema validation")

        # Test valid data
        valid_status_data = {"robot_sn": "TEST_ROBOT_SCHEMA", "status": "online"}

        result = self.db_writer._validate_data_against_schema("mnt_robots_management", valid_status_data)
        assert result == True
        print("  ✅ Valid schema validation passed")

        # Test invalid field
        invalid_data = {"robot_sn": "TEST_ROBOT_SCHEMA", "invalid_field": "value"}

        result = self.db_writer._validate_data_against_schema("mnt_robots_management", invalid_data)
        assert result == False
        print("  ✅ Invalid field detection works")

        # Test missing primary key
        missing_pk_data = {"status": "online"}

        result = self.db_writer._validate_data_against_schema("mnt_robots_management", missing_pk_data)
        assert result == False
        print("  ✅ Missing primary key detection works")

    def test_configuration_consistency(self):
        """Test that configuration matches expected schemas"""
        print("\n🧪 Testing configuration consistency")

        # Test robot status table config
        result = self.db_writer._validate_config_consistency("robot_status")
        assert result == True
        print("  ✅ Robot status config consistency validated")

        # Test robot events table config
        result = self.db_writer._validate_config_consistency("robot_events")
        assert result == True
        print("  ✅ Robot events config consistency validated")

    def test_data_filtering(self):
        """Test that None values are properly filtered"""
        print("\n🧪 Testing data filtering")

        # Test with None values
        data_with_none = {"robot_sn": "TEST_ROBOT_FILTER", "status": "online", "battery_level": None, "x": 10.5, "y": None}

        self.db_writer.clear_written_data()
        self.db_writer.write_robot_status("TEST_ROBOT_FILTER", data_with_none)

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
        self.db_writer.write_robot_status(robot_sn, {"status": "online"})

        # Write event
        self.db_writer.write_robot_event(
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

        print("  ✅ Multiple table writes validated")

    def test_connection_management(self):
        """Test database connection management"""
        print("\n🧪 Testing connection management")

        # Test connection creation
        conn = self.db_writer._get_connection("test_database")
        assert conn is not None
        assert "connection" in conn
        assert "cursor" in conn
        print("  ✅ Connection creation works")

        # Test connection reuse
        conn2 = self.db_writer._get_connection("test_database")
        assert conn is conn2  # Should be the same connection
        print("  ✅ Connection reuse works")

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
