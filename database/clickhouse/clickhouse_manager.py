import clickhouse_connect
import yaml
import os
import pandas as pd
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ClickHouseManager:
    """Manages all interactions with the ClickHouse database."""

    def __init__(self, config_dir: str):
        """
        Initializes the ClickHouseManager.

        Args:
            config_dir: The path to the directory containing 'credentials.yaml'.
        """
        self.config_path = os.path.join(config_dir, "credentials.yaml")
        self.client = self._connect()

    def _connect(self) -> clickhouse_connect.driver.client.Client:
        """Establishes a connection to the ClickHouse instance."""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)['database']

            return clickhouse_connect.get_client(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                secure=config.get('secure', True) # Default to secure connection
            )
        except FileNotFoundError:
            logger.error(f"ClickHouse credentials file not found at: {self.config_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def get_historical_data(self, query: str) -> pd.DataFrame:
        """
        Queries ClickHouse for historical data and returns a DataFrame.

        Args:
            query: The SQL query to execute.

        Returns:
            A pandas DataFrame with the query results.
        """
        try:
            return self.client.query_df(query)
        except Exception as e:
            logger.error(f"ClickHouse query failed: {e}")
            # Return empty dataframe on failure
            return pd.DataFrame()

    def close(self):
        """Closes the ClickHouse client connection."""
        if self.client:
            self.client.close()
            logger.info("ClickHouse connection closed.")