from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from models.base_models import Location


class BaseDataRetriever(ABC):
    """Abstract base class for all data retrievers"""

    def __init__(self, clickhouse_manager=None, rds_manager=None):
        self.clickhouse_manager = clickhouse_manager
        self.rds_manager = rds_manager
        self.use_synthetic_data = clickhouse_manager is None and rds_manager is None

    @abstractmethod
    def retrieve_data(self, locations: List[Location], start_date: datetime,
                     end_date: datetime, **kwargs) -> Any:
        """Retrieve data for specified locations and time range"""
        pass

    def generate_synthetic_data(self, locations: List[Location], start_date: datetime,
                               end_date: datetime, **kwargs) -> Any:
        """Generate synthetic data for testing"""
        pass

    def get_demo_sql(self, table_name: str, columns: List[str],
                    start_date: datetime, end_date: datetime,
                    location_filter: Optional[Dict[str, str]] = None) -> str:
        """Generate demo SQL query"""
        column_str = ", ".join(columns)
        where_clauses = [
            f"timestamp >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'",
            f"timestamp <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        ]

        if location_filter:
            for key, value in location_filter.items():
                if value and value != "All":
                    where_clauses.append(f"{key} = '{value}'")

        where_str = " AND ".join(where_clauses)

        return f"""
        SELECT {column_str}
        FROM {table_name}
        WHERE {where_str}
        ORDER BY timestamp
        """

    def generate_time_series(self, start_date: datetime, end_date: datetime,
                           frequency: str = 'H') -> pd.DatetimeIndex:
        """Generate time series index"""
        return pd.date_range(start=start_date, end=end_date, freq=frequency)

    def add_noise(self, base_value: float, noise_percentage: float = 0.1) -> float:
        """Add random noise to a value"""
        noise = np.random.normal(0, base_value * noise_percentage)
        return base_value + noise

    def generate_pattern(self, timestamps: pd.DatetimeIndex,
                        pattern_type: str = 'daily') -> np.ndarray:
        """Generate pattern-based values"""
        values = np.zeros(len(timestamps))

        if pattern_type == 'daily':
            # Peak during business hours
            for i, ts in enumerate(timestamps):
                hour = ts.hour
                if 9 <= hour <= 17:
                    values[i] = 0.8 + 0.2 * np.sin((hour - 9) * np.pi / 8)
                else:
                    values[i] = 0.2 + 0.1 * np.random.random()

        elif pattern_type == 'weekly':
            # Lower on weekends
            for i, ts in enumerate(timestamps):
                if ts.weekday() < 5:  # Weekday
                    values[i] = 0.8 + 0.2 * np.random.random()
                else:  # Weekend
                    values[i] = 0.3 + 0.1 * np.random.random()

        return values