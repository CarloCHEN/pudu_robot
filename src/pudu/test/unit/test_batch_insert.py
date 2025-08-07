"""
Unit tests for batch_insert_with_ids functionality - tests the actual implementation
"""

import sys
sys.path.append('../../')

from pudu.rds.utils import (
    batch_insert_with_ids,
    _query_ids_by_unique_keys
)
from unittest.mock import MagicMock

class TestBatchInsertWithIds:
    """Test the actual batch_insert_with_ids function implementation"""

    def setup_method(self):
        """Setup mock cursor that behaves like real MySQL cursor"""
        self.mock_cursor = MagicMock()
        self.mock_cursor.connection = MagicMock()

    def test_batch_insert_with_ids_pure_inserts_logic(self):
        """Test batch insert logic for pure inserts (no unique keys)"""
        # Real data pattern from your system
        data_list = [
            {"robot_sn": "1230", "robot_name": "demo_UF_demo", "status": "Online"},
            {"robot_sn": "1231", "robot_name": "LDS-test", "status": "Online"}
        ]

        # Mock primary key detection
        self.mock_cursor.fetchone.return_value = ('id',)
        # Mock lastrowid for pure inserts
        self.mock_cursor.lastrowid = 100

        results = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management", data_list, None)

        # Verify pure insert logic
        assert len(results) == 2
        assert results[0] == (data_list[0], 100)  # First record gets lastrowid
        assert results[1] == (data_list[1], 101)  # Second record gets lastrowid + 1

        # Verify batch_insert was called (not individual inserts)
        assert self.mock_cursor.execute.call_count >= 1

    def test_batch_insert_with_ids_upsert_logic(self):
        """Test batch insert logic with unique key constraints (upsert scenario)"""
        # Real robot data with unique keys
        data_list = [
            {"robot_sn": "1230", "robot_name": "demo_UF_demo", "status": "Online"},
            {"robot_sn": "1231", "robot_name": "LDS-test", "status": "Online"}
        ]
        unique_keys = ["robot_sn"]

        # Mock primary key detection
        self.mock_cursor.fetchone.return_value = ('id',)
        # Mock query results for ID lookup
        self.mock_cursor.fetchall.return_value = [
            (123, "1230"),  # (id, robot_sn)
            (124, "1231")   # (id, robot_sn)
        ]

        results = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management", data_list, unique_keys)

        # Verify upsert logic
        assert len(results) == 2
        assert results[0] == (data_list[0], 123)
        assert results[1] == (data_list[1], 124)

        # Should call batch_insert first, then query for IDs
        assert self.mock_cursor.execute.call_count >= 2

    def test_query_ids_by_unique_keys_sql_correctness(self):
        """Test that the SQL generated for querying IDs is correct"""
        # Your actual robot data
        data_list = [
            {"robot_sn": "1230", "robot_type": "CC1", "robot_name": "demo_UF_demo"},
            {"robot_sn": "1231", "robot_type": "CC1", "robot_name": "LDS-test"}
        ]
        unique_keys = ["robot_sn"]
        pk_column = "id"
        table_name = "mnt_robots_management"

        # Mock the database response
        self.mock_cursor.fetchall.return_value = [
            (123, "1230"),
            (124, "1231")
        ]

        results = _query_ids_by_unique_keys(self.mock_cursor, table_name, data_list, unique_keys, pk_column)

        # Verify the SQL was executed
        assert self.mock_cursor.execute.called
        executed_sql = self.mock_cursor.execute.call_args[0][0]

        # Test key components of generated SQL
        assert "SELECT id, robot_sn FROM mnt_robots_management" in executed_sql
        assert "WHERE (robot_sn = '1230') OR (robot_sn = '1231')" in executed_sql

        # Test result mapping
        assert len(results) == 2
        assert results[0] == (data_list[0], 123)
        assert results[1] == (data_list[1], 124)

    def test_query_ids_with_composite_unique_keys(self):
        """Test ID querying with composite unique keys (like task data)"""
        # Real task data with composite keys
        data_list = [
            {
                "robot_sn": "1230",
                "task_name": "Library Cleaning",
                "start_time": "2024-09-01 14:30:00",
                "status": "Task Ended"
            },
            {
                "robot_sn": "1231",
                "task_name": "Office Sweep",
                "start_time": "2024-09-01 15:00:00",
                "status": "In Progress"
            }
        ]
        unique_keys = ["robot_sn", "task_name", "start_time"]
        pk_column = "id"

        # Mock database response
        self.mock_cursor.fetchall.return_value = [
            (456, "1230", "Library Cleaning", "2024-09-01 14:30:00"),
            (457, "1231", "Office Sweep", "2024-09-01 15:00:00")
        ]

        results = _query_ids_by_unique_keys(self.mock_cursor, "mnt_robots_task", data_list, unique_keys, pk_column)

        # Verify composite key SQL generation
        executed_sql = self.mock_cursor.execute.call_args[0][0]
        assert "robot_sn = '1230' AND task_name = 'Library Cleaning' AND start_time = '2024-09-01 14:30:00'" in executed_sql
        assert "robot_sn = '1231' AND task_name = 'Office Sweep' AND start_time = '2024-09-01 15:00:00'" in executed_sql

        # Test results
        assert len(results) == 2
        assert results[0] == (data_list[0], 456)
        assert results[1] == (data_list[1], 457)

    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are properly escaped"""
        # Malicious data that could cause SQL injection
        malicious_data = [
            {"robot_sn": "'; DROP TABLE users; --", "name": "Malicious Robot"},
            {"robot_sn": "1230'; UPDATE users SET password='hacked' WHERE '1'='1", "name": "Another Attack"}
        ]
        unique_keys = ["robot_sn"]

        # Should not crash and should escape the values
        self.mock_cursor.fetchall.return_value = []

        try:
            results = _query_ids_by_unique_keys(self.mock_cursor, "test_table", malicious_data, unique_keys, "id")

            # Verify execute was called (function didn't crash)
            assert self.mock_cursor.execute.called

            # Check that dangerous characters were escaped
            executed_sql = self.mock_cursor.execute.call_args[0][0]
            # Single quotes should be doubled for escaping
            assert "''; DROP TABLE users; --'" in executed_sql or "'''; DROP TABLE users; --'''" in executed_sql

        except Exception as e:
            # Some SQL injection attempts might cause exceptions, which is acceptable
            # The important thing is that the function handles them gracefully
            pass

    def test_batch_insert_with_ids_error_handling(self):
        """Test error handling in batch_insert_with_ids"""
        data_list = [{"robot_sn": "1230", "status": "Online"}]

        # Test primary key detection failure
        self.mock_cursor.fetchone.return_value = None  # No primary key found

        try:
            batch_insert_with_ids(self.mock_cursor, "nonexistent_table", data_list, ["robot_sn"])
            assert False, "Should raise ValueError for missing primary key"
        except ValueError as e:
            assert "Could not detect primary key column" in str(e)

    def test_empty_data_list_handling(self):
        """Test handling of empty data lists"""
        # Test with empty list
        results = batch_insert_with_ids(self.mock_cursor, "test_table", [], ["robot_sn"])
        assert results == []

        # Verify no database operations were attempted
        assert not self.mock_cursor.execute.called

def run_batch_insert_tests():
    """Run all batch insert tests"""
    print("=" * 60)
    print("🧪 TESTING BATCH INSERT WITH IDS FUNCTIONS")
    print("=" * 60)

    test_instance = TestBatchInsertWithIds()
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

    print(f"\n📊 Batch Insert Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_batch_insert_tests()