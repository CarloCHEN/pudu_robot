"""
Unit tests for RDS operations
"""

import pytest
import pandas as pd
from pudu.test.mocks.mock_rds import MockRDSTable, MockRDSDatabase

class TestRDSOperations:
    """Test RDS table and database operations"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_table = MockRDSTable(
            connection_config="test_credentials.yaml",
            database_name="test_db",
            table_name="test_table",
            primary_keys=["robot_sn"]
        )

    def test_batch_insert(self):
        """Test batch insert functionality"""
        test_data = [
            {"robot_sn": "TEST001", "status": "online", "battery_level": 95},
            {"robot_sn": "TEST002", "status": "offline", "battery_level": 20}
        ]

        self.mock_table.batch_insert(test_data)
        stored_data = self.mock_table.get_inserted_data()

        assert len(stored_data) == 2
        assert stored_data[0]["robot_sn"] == "TEST001"
        assert stored_data[1]["robot_sn"] == "TEST002"

    def test_query_data_as_df(self):
        """Test querying data as DataFrame"""
        test_data = [{"robot_sn": "TEST001", "status": "online"}]
        self.mock_table.batch_insert(test_data)

        result = self.mock_table.query_data_as_df()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["robot_sn"] == "TEST001"

    def test_clear_data(self):
        """Test clearing stored data"""
        test_data = [{"robot_sn": "TEST001"}]
        self.mock_table.batch_insert(test_data)

        assert len(self.mock_table.get_inserted_data()) == 1

        self.mock_table.clear_data()
        assert len(self.mock_table.get_inserted_data()) == 0