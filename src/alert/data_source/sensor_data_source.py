import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime, timedelta
from alert.clickhouse import ClickHouseManager
from alert.data_source import BaseDataSource

class SensorDataSource(BaseDataSource):
    """Data source for physical sensors."""

    def __init__(self, source_id: str, config: Dict[str, Any]):
        super().__init__(source_id, 'sensor', config)
        # Sensor-specific attributes
        self.sensor_id = config.get('sensor_id')
        self.data_type = config.get('data_type')
        self.sensor_type = config.get('sensor_type')
        self.start_timestamp = config.get('alarm_start_timestamp')

    def get_historical_data(self, ch_manager: ClickHouseManager, sensorID_col: str = 'devEUI') -> pd.DataFrame:
        """
        Constructs a query and fetches historical data for a specific sensor.
        """

        query = f"""
            SELECT time, {sensorID_col}, `{self.data_type}`
            FROM sensor_data.{self.sensor_type}
            WHERE {sensorID_col} = '{self.sensor_id}'
            AND time >= '{self.start_timestamp}'
            ORDER BY time
        """

        df = ch_manager.get_historical_data(query)

        if df.empty:
            return pd.DataFrame({'time': [], f'{sensorID_col}': [], f'{self.data_type}': []})

        # Ensure correct data types for Prophet
        df['time'] = pd.to_datetime(df['time'])
        df[f'{self.data_type}'] = pd.to_numeric(df[f'{self.data_type}'])
        self.data = df