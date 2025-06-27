import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta


class EnvironmentalMonitor:
    """
    Environmental monitoring system that collects multiple air quality parameters
    in a single location using various sensors.
    """

    # Define standard parameter sets for different space types
    PARAMETER_SETS = {
        'office': ['PM2.5', 'PM10', 'CO2', 'tVOC', 'HCHO', 'O3', 'Temperature', 'Humidity'],
        'conference': ['PM2.5', 'PM10', 'CO2', 'tVOC', 'HCHO', 'O3', 'Temperature', 'Humidity'],
        'restroom': ['PM2.5', 'PM10', 'NH3', 'H2S', 'tVOC', 'Temperature', 'Humidity'],
        'circulation': ['PM2.5', 'PM10', 'CO2', 'tVOC', 'Temperature', 'Humidity'],
        'cafeteria': ['PM2.5', 'PM10', 'CO2', 'tVOC', 'Temperature', 'Humidity']
    }

    def __init__(self, monitor_id: str, location: str, space_type: str = 'office',
                 data: Optional[pd.DataFrame] = None):
        """
        Initialize environmental monitor.

        Parameters:
        - monitor_id: Unique identifier for this monitoring station
        - location: Physical location (zone name)
        - space_type: Type of space being monitored
        - data: Optional DataFrame with time series data
        """
        self.monitor_id = monitor_id
        self.location = location
        self.space_type = space_type.lower()

        # Get expected parameters for this space type
        self.expected_parameters = self.PARAMETER_SETS.get(
            self.space_type,
            self.PARAMETER_SETS['office']  # Default to office parameters
        )

        if data is not None:
            self.set_data(data)
        else:
            self.data = None

    def set_data(self, data: pd.DataFrame):
        """
        Set monitoring data with validation.

        Parameters:
        - data: DataFrame with 'time' column and parameter columns
        """
        self.data = data.copy()
        self._validate_data()

    def _validate_data(self):
        """Validate the monitoring data."""
        if self.data is None:
            return

        # Check for time column
        if 'time' not in self.data.columns:
            raise ValueError("Data must have a 'time' column")

        # Convert time to datetime
        self.data['time'] = pd.to_datetime(self.data['time'])

        # Sort by time
        self.data = self.data.sort_values('time').reset_index(drop=True)

        # Check for duplicate timestamps
        if self.data['time'].duplicated().any():
            print(f"Warning: Duplicate timestamps found in {self.monitor_id}")

    def get_latest_readings(self) -> Dict[str, float]:
        """Get the most recent reading for each parameter."""
        if self.data is None or self.data.empty:
            return {}

        latest_row = self.data.iloc[-1]
        readings = {}

        for param in self.expected_parameters:
            if param in self.data.columns:
                value = latest_row[param]
                if pd.notna(value):  # Only include non-null values
                    readings[param] = float(value)

        return readings

    def get_parameter_history(self, parameter: str, hours: int = 24) -> pd.DataFrame:
        """
        Get historical data for a specific parameter.

        Parameters:
        - parameter: Parameter name
        - hours: Number of hours of history to return

        Returns:
        - DataFrame with time and parameter columns
        """
        if self.data is None or parameter not in self.data.columns:
            return pd.DataFrame(columns=['time', parameter])

        # Filter to last N hours
        cutoff_time = self.data['time'].max() - timedelta(hours=hours)
        recent_data = self.data[self.data['time'] >= cutoff_time]

        return recent_data[['time', parameter]].copy()

    def get_available_parameters(self) -> List[str]:
        """Get list of parameters that have data."""
        if self.data is None:
            return []

        available = []
        for param in self.expected_parameters:
            if param in self.data.columns and not self.data[param].isna().all():
                available.append(param)

        return available

    def get_missing_parameters(self) -> List[str]:
        """Get list of expected parameters that are missing or have no data."""
        if self.data is None:
            return self.expected_parameters.copy()

        missing = []
        for param in self.expected_parameters:
            if param not in self.data.columns or self.data[param].isna().all():
                missing.append(param)

        return missing

    def get_data_summary(self) -> Dict:
        """Get summary statistics for all parameters."""
        if self.data is None or self.data.empty:
            return {}

        summary = {
            'monitor_id': self.monitor_id,
            'location': self.location,
            'space_type': self.space_type,
            'data_range': {
                'start': self.data['time'].min(),
                'end': self.data['time'].max(),
                'records': len(self.data)
            },
            'parameters': {}
        }

        for param in self.get_available_parameters():
            param_data = self.data[param].dropna()
            if not param_data.empty:
                summary['parameters'][param] = {
                    'latest': float(param_data.iloc[-1]),
                    'mean': float(param_data.mean()),
                    'min': float(param_data.min()),
                    'max': float(param_data.max()),
                    'std': float(param_data.std()),
                    'records': len(param_data)
                }

        return summary

    def add_reading(self, timestamp: Union[datetime, str], readings: Dict[str, float]):
        """
        Add a new reading to the monitoring data.

        Parameters:
        - timestamp: When the reading was taken
        - readings: Dictionary of parameter: value
        """
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)

        # Create new row
        new_row = {'time': timestamp}
        new_row.update(readings)

        if self.data is None:
            # Initialize data
            self.data = pd.DataFrame([new_row])
        else:
            # Append new row
            self.data = pd.concat([self.data, pd.DataFrame([new_row])], ignore_index=True)

        # Re-validate and sort
        self._validate_data()

    def resample_data(self, freq: str = '15min', method: str = 'mean') -> pd.DataFrame:
        """
        Resample data to a different frequency.

        Parameters:
        - freq: Pandas frequency string (e.g., '15min', '1H')
        - method: Aggregation method ('mean', 'median', 'max', 'min')

        Returns:
        - Resampled DataFrame
        """
        if self.data is None or self.data.empty:
            return pd.DataFrame()

        # Set time as index for resampling
        data_indexed = self.data.set_index('time')

        # Resample
        if method == 'mean':
            resampled = data_indexed.resample(freq).mean()
        elif method == 'median':
            resampled = data_indexed.resample(freq).median()
        elif method == 'max':
            resampled = data_indexed.resample(freq).max()
        elif method == 'min':
            resampled = data_indexed.resample(freq).min()
        else:
            raise ValueError(f"Unknown method: {method}")

        # Reset index
        return resampled.reset_index()


class EnvironmentalDataGenerator:
    """Helper class to generate synthetic environmental monitoring data."""

    @staticmethod
    def generate_synthetic_data(space_type: str, hours: int = 24,
                                interval_minutes: int = 15) -> pd.DataFrame:
        """
        Generate realistic synthetic environmental data.

        Parameters:
        - space_type: Type of space ('office', 'conference', 'restroom', etc.)
        - hours: Number of hours of data
        - interval_minutes: Sampling interval

        Returns:
        - DataFrame with time and parameter columns
        """
        # Generate time series
        start_time = datetime.now() - timedelta(hours=hours)
        time_points = pd.date_range(
            start=start_time,
            periods=hours * 60 // interval_minutes,
            freq=f'{interval_minutes}min'
        )

        # Get parameters for this space type
        parameters = EnvironmentalMonitor.PARAMETER_SETS.get(
            space_type.lower(),
            EnvironmentalMonitor.PARAMETER_SETS['office']
        )

        data = {'time': time_points}
        n_points = len(time_points)

        # Generate data for each parameter
        for param in parameters:
            if param == 'PM2.5':
                base = 12
                noise = np.random.normal(0, 3, n_points)
                daily_cycle = 5 * np.sin(2 * np.pi * np.arange(n_points) / (24 * 60 / interval_minutes))
                values = np.maximum(0, base + daily_cycle + noise)

            elif param == 'PM10':
                base = 25
                noise = np.random.normal(0, 5, n_points)
                daily_cycle = 8 * np.sin(2 * np.pi * np.arange(n_points) / (24 * 60 / interval_minutes))
                values = np.maximum(0, base + daily_cycle + noise)

            elif param == 'CO2':
                base = 800 if space_type in ['office', 'conference'] else 600
                noise = np.random.normal(0, 50, n_points)
                hour_of_day = (np.arange(n_points) * interval_minutes / 60) % 24
                # Higher during work hours for office/conference spaces
                if space_type in ['office', 'conference']:
                    work_boost = 250 * np.where((hour_of_day >= 8) & (hour_of_day <= 18), 1, 0)
                else:
                    work_boost = 0
                values = np.maximum(400, base + work_boost + noise)

            elif param == 'tVOC':
                base = 350 if space_type == 'restroom' else 280
                noise = np.random.normal(0, 50, n_points)
                values = np.maximum(0, base + noise)

            elif param == 'HCHO':
                base = 0.035
                noise = np.random.normal(0, 0.01, n_points)
                values = np.maximum(0, base + noise)

            elif param == 'O3':
                base = 0.025
                noise = np.random.normal(0, 0.005, n_points)
                values = np.maximum(0, base + noise)

            elif param == 'Temperature':
                base = 22
                noise = np.random.normal(0, 1, n_points)
                daily_cycle = 2 * np.sin(2 * np.pi * np.arange(n_points) / (24 * 60 / interval_minutes))
                values = base + daily_cycle + noise

            elif param == 'Humidity':
                base = 50 if space_type == 'restroom' else 45
                noise = np.random.normal(0, 5, n_points)
                daily_cycle = 10 * np.sin(2 * np.pi * np.arange(n_points) / (24 * 60 / interval_minutes))
                values = np.clip(base + daily_cycle + noise, 20, 80)

            elif param == 'NH3':
                base = 1.2
                noise = np.random.normal(0, 0.4, n_points)
                # Random usage spikes
                spikes = np.random.exponential(0.5, n_points) * np.random.choice([0, 1], n_points, p=[0.9, 0.1])
                values = np.maximum(0, base + noise + spikes)

            elif param == 'H2S':
                base = 0.06
                noise = np.random.normal(0, 0.02, n_points)
                # Random usage spikes
                spikes = np.random.exponential(0.08, n_points) * np.random.choice([0, 1], n_points, p=[0.95, 0.05])
                values = np.maximum(0, base + noise + spikes)

            else:
                # Default: random values
                values = np.random.uniform(0, 100, n_points)

            data[param] = values

        return pd.DataFrame(data)
