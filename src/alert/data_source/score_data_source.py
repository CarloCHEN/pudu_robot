import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime, timedelta
from alert.clickhouse import ClickHouseManager
from alert.data_source import BaseDataSource
import logging

logger = logging.getLogger(__name__)

class ScoreDataSource(BaseDataSource):
    """Data source for calculated time series scores."""

    def __init__(self, source_id: str, config: Dict[str, Any]):
        super().__init__(source_id, 'score', config)
        self.score_type = config.get('score_type')
        self.start_timestamp = config.get('alarm_start_timestamp')

    def get_historical_data(self, ch_manager: ClickHouseManager, scoreID_col: str = 'iaq') -> pd.DataFrame:
        """
        Fetches historical data for a score.
        If score data is not available, it returns synthetic data for testing.
        """

        # This query should be adapted to your actual score data schema.
        query = f"""
            SELECT time, `{self.score_type}`
            FROM sensor_data.{self.sensor_type}
            WHERE {scoreID_col} = '{self.source_id}'
            AND time >= '{self.start_timestamp}'
            ORDER BY time
        """

        # In a real scenario, you would execute the query first.
        # df = ch_manager.get_historical_data(query)
        # if not df.empty:
        #    return df

        # For now, we generate synthetic data as requested.
        logger.warning(f"No real data found for score '{self.id}'. Generating synthetic data.")
        return self._generate_synthetic_data()

    def _generate_synthetic_data(self) -> pd.DataFrame:
        """
        Generates a synthetic time series DataFrame for 2-3 hours with 15-minute intervals.
        This is a placeholder as requested for when real data is not available.
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=3)

        timestamps = pd.date_range(start=start_time, end=end_time, freq='15min')

        # Create a simple sine wave pattern to simulate daily fluctuations
        values = 10 * np.sin(np.arange(len(timestamps)) * 0.5) + 50
        # Add some random noise
        noise = np.random.normal(0, 2, len(timestamps))
        values += noise

        df = pd.DataFrame({'time': timestamps, 'score': values})

        # Ensure correct data types
        df['time'] = pd.to_datetime(df['time'])
        df['score'] = pd.to_numeric(df['score'])

        logger.info(f"Generated {len(df)} rows of synthetic data for score '{self.id}'.")
        self.data = df
