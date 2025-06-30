from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from alert.clickhouse import ClickHouseManager

class BaseDataSource(ABC):
    """
    Abstract base class for a data source to be forecasted.
    This can be a sensor, a calculated score, or any other time series.
    """

    def __init__(self, source_id: str, source_type: str, config: Dict[str, Any]):
        """
        Initializes the data source.

        Args:
            source_id: The unique identifier for this data source (e.g., sensor_uuid, score_name).
            source_type: The general type of the source (e.g., 'sensor', 'score').
            config: A dictionary containing specific configuration for this source.
        """
        self.id = source_id
        self.type = source_type
        self.config = config
        self.name = config.get('name', source_id)
        self.forecast_horization_hours = config.get('forecast_horization_hours', 7*24)
        self.historical_data_days = config.get('historical_data_days', 60)

    @abstractmethod
    def get_historical_data(self, ch_manager: ClickHouseManager) -> pd.DataFrame:
        """
        Retrieves historical data for this source from ClickHouse.

        Args:
            ch_manager: An instance of the ClickHouseManager.

        Returns:
            A pandas DataFrame with 'ds' (datetime) and 'y' (value) columns.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Returns a dictionary of metadata about this source."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "config": self.config
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.id}', type='{self.type}')"