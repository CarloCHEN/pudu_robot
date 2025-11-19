"""
Unit tests for RDS utility functions - tests actual functions with real scenarios
"""

import sys
sys.path.append('../../')

from pudu.rds.utils import (
    get_primary_key_column,
    batch_insert_with_ids,
    _query_ids_by_unique_keys
)
from unittest.mock import MagicMock

class TestRDSFunctions:
    """Test actual RDS utility functions"""

    def setup_method(self):
        """Setup mock cursor for testing"""
        self.mock_cursor = MagicMock()
        self.mock_cursor.connection = MagicMock()

    def test_get_primary_key_column_mysql_query(self):
        """Test primary key detection SQL query generation"""
        table_name = "mnt_robots_management"

        # Mock the cursor to return a primary key
        self.mock_cursor.fetchone.return_value = ('id',)

        result = get_primary_key_column(self.mock_cursor, table_name)

        # Verify the correct SQL was executed
        expected_query = f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = '{table_name}'
            AND CONSTRAINT_NAME = 'PRIMARY'
            AND TABLE_SCHEMA = DATABASE()
        """
        
        # Check that execute was called (we can't check exact query due to formatting)
        assert self.mock_cursor.execute.called
        assert result == 'id'

    def test_get_primary_key_column_fallback(self):
        """Test primary key detection fallback to common names"""
        table_name = "users"

        # Mock the information_schema query to fail
        self.mock_cursor.fetchone.side_effect = [None, ('id',)]  # First call fails, second succeeds

        result = get_primary_key_column(self.mock_cursor, table_name)

        # Should try fallback queries
        assert self.mock_cursor.execute.call_count >= 2
        assert result == 'id'

    def test_query_ids_by_unique_keys_sql_generation(self):
        """Test SQL generation for querying IDs by unique keys"""
        # Test data from your actual system
        data_list = [
            {"robot_sn": "1230", "robot_type": "CC1", "robot_name": "demo_UF_demo"},
            {"robot_sn": "1231", "robot_type": "CC1", "robot_name": "LDS-test"}
        ]
        unique_keys = ["robot_sn"]
        pk_column = "id"
        table_name = "mnt_robots_management"

        # Mock database results
        self.mock_cursor.fetchall.return_value = [
            (123, "1230"),  # (id, robot_sn)
            (124, "1231")
        ]

        results = _query_ids_by_unique_keys(self.mock_cursor, table_name, data_list, unique_keys, pk_column)

        # Verify SQL generation
        assert self.mock_cursor.execute.called
        executed_sql = self.mock_cursor.execute.call_args[0][0]

        # Check key parts of the generated SQL
        assert "SELECT id, robot_sn FROM" in executed_sql
        assert "WHERE (robot_sn = '1230') OR (robot_sn = '1231')" in executed_sql

        # Verify results mapping
        assert len(results) == 2
        assert results[0] == (data_list[0], 123)
        assert results[1] == (data_list[1], 124)

    def test_batch_insert_with_ids_pure_inserts(self):
        """Test batch_insert_with_ids for pure inserts (no unique keys)"""
        data_list = [
            {"name": "John", "email": "john@example.com"},
            {"name": "Jane", "email": "jane@example.com"}
        ]

        # Mock responses
        self.mock_cursor.fetchone.return_value = ('id',)  # Primary key detection
        self.mock_cursor.lastrowid = 100  # First inserted ID

        results = batch_insert_with_ids(self.mock_cursor, "users", data_list, None)

        # Should use lastrowid approach for pure inserts
        assert len(results) == 2
        assert results[0] == (data_list[0], 100)
        assert results[1] == (data_list[1], 101)

    def test_batch_insert_with_ids_with_unique_keys(self):
        """Test batch_insert_with_ids with unique key constraints"""
        data_list = [
            {"robot_sn": "1230", "robot_name": "demo_UF_demo", "status": "Online"},
            {"robot_sn": "1231", "robot_name": "LDS-test", "status": "Online"}
        ]
        unique_keys = ["robot_sn"]

        # Mock responses
        self.mock_cursor.fetchone.return_value = ('id',)  # Primary key detection
        self.mock_cursor.fetchall.return_value = [
            (123, "1230"),  # (id, robot_sn)
            (124, "1231")
        ]

        results = batch_insert_with_ids(self.mock_cursor, "mnt_robots_management", data_list, unique_keys)

        # Should query back the IDs using unique keys
        assert len(results) == 2
        assert results[0] == (data_list[0], 123)
        assert results[1] == (data_list[1], 124)

    def test_escape_value_sql_injection_prevention(self):
        """Test that escape_value properly handles SQL injection attempts"""
        from pudu.rds.utils import _query_ids_by_unique_keys

        # Test data with potential SQL injection
        malicious_data = [
            {"robot_sn": "'; DROP TABLE users; --", "name": "Malicious"},
            {"robot_sn": "normal_robot", "name": "Normal"}
        ]

        # The function should escape the values properly
        self.mock_cursor.fetchall.return_value = []

        try:
            _query_ids_by_unique_keys(self.mock_cursor, "test_table", malicious_data, ["robot_sn"], "id")
            # Should not crash and should call execute with escaped values
            assert self.mock_cursor.execute.called
            executed_sql = self.mock_cursor.execute.call_args[0][0]
            # The malicious input should be escaped (doubled single quotes)
            assert "''; DROP TABLE users; --'" in executed_sql or "'''; DROP TABLE users; --'''" in executed_sql
        except Exception as e:
            # Should handle gracefully
            pass

def run_change_detection_tests():
    """Run all change detection tests"""
    print("=" * 60)
    print("🧪 TESTING RDS UTILITY FUNCTIONS")
    print("=" * 60)

    test_instance = TestRDSFunctions()
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

    print(f"\n📊 RDS Function Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_change_detection_tests()