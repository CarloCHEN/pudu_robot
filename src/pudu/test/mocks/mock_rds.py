"""
Mock RDS/Database services for testing
"""

import logging
from typing import List, Dict, Any
from unittest.mock import MagicMock
import pandas as pd

logger = logging.getLogger(__name__)

class MockRDSTable:
    """Mock RDS table that simulates database operations"""

    def __init__(self, connection_config: str, database_name: str,
                 table_name: str, fields=None, primary_keys=None):
        self.connection_config = connection_config
        self.database_name = database_name
        self.table_name = table_name
        self.fields = fields
        self.primary_keys = primary_keys or []
        self.data = []  # Store inserted data
        self.queries_executed = []

        logger.info(f"Created mock table: {database_name}.{table_name}")

    def batch_insert(self, data_list: List[Dict[str, Any]]):
        """Mock batch insert that stores data"""
        self.data.extend(data_list)
        logger.info(f"Mock inserted {len(data_list)} records into {self.table_name}")

    def query_data(self, query: str = None):
        """Mock query that returns stored data"""
        self.queries_executed.append(query)
        return self.data

    def query_data_as_df(self, query: str = None):
        """Mock query that returns DataFrame"""
        if self.data:
            return pd.DataFrame(self.data)
        return pd.DataFrame()

    def close(self):
        """Mock close connection"""
        logger.info(f"Mock closed connection to {self.table_name}")

    def get_inserted_data(self):
        """Get all data that was inserted"""
        return self.data

    def clear_data(self):
        """Clear all stored data"""
        self.data.clear()
        self.queries_executed.clear()

class MockRDSDatabase:
    """Mock RDS database for testing"""

    def __init__(self, connection_config: str, database_name: str):
        self.connection_config = connection_config
        self.database_name = database_name
        self.queries_executed = []

    def query_data(self, query: str):
        """Mock query execution"""
        self.queries_executed.append(query)
        return []

    def execute_query(self, query: str):
        """Mock query execution returning DataFrame"""
        self.queries_executed.append(query)
        return pd.DataFrame()

    def close(self):
        """Mock close connection"""
        pass