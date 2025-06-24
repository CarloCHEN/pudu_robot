from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from .base_models import BaseDataModel, Location, TimeSeriesData, Alert, Metric


@dataclass
class EnvironmentReading(TimeSeriesData):
    """Environmental sensor reading"""
    sensor_type: str  # temperature, humidity, co2, pm2.5, pm10, tvoc, nh3
    sensor_id: str
    unit: str


@dataclass
class EnvironmentScore(TimeSeriesData):
    """Calculated environmental scores"""
    score_type: str  # iaq_score, comfort_score
    components: Dict[str, float] = field(default_factory=dict)


@dataclass
class EnvironmentPattern:
    """Environmental pattern analysis"""
    location: Location
    parameter: str
    hourly_pattern: Dict[int, float]  # hour -> average value
    daily_pattern: Dict[str, float]   # day of week -> average value
    peak_hours: List[int]
    low_hours: List[int]


@dataclass
class EnvironmentForecast:
    """Environmental forecast data"""
    location: Location
    parameter: str
    forecast_values: List[TimeSeriesData]
    confidence_interval: Dict[str, List[float]]
    model_accuracy: float


@dataclass
class EnvironmentData(BaseDataModel):
    """Complete environment data model"""
    readings: List[EnvironmentReading]
    scores: List[EnvironmentScore]
    alerts: List[Alert]
    patterns: List[EnvironmentPattern]
    forecasts: List[EnvironmentForecast]
    metrics: List[Metric]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "readings": [vars(r) for r in self.readings],
            "scores": [vars(s) for s in self.scores],
            "alerts": [vars(a) for a in self.alerts],
            "patterns": [vars(p) for p in self.patterns],
            "forecasts": [vars(f) for f in self.forecasts],
            "metrics": [vars(m) for m in self.metrics]
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Convert readings to DataFrame"""
        if not self.readings:
            return pd.DataFrame()

        data = []
        for reading in self.readings:
            data.append({
                'timestamp': reading.timestamp,
                'location': str(reading.location),
                'sensor_type': reading.sensor_type,
                'value': reading.value,
                'unit': reading.unit,
                'sensor_id': reading.sensor_id
            })
        return pd.DataFrame(data)

    def get_critical_alerts(self) -> List[Alert]:
        """Get only critical severity alerts"""
        return [a for a in self.alerts if a.severity == 'critical']

    def get_summary_by_location(self) -> Dict[str, Dict[str, Any]]:
        """Get summary statistics by location"""
        summary = {}
        df = self.to_dataframe()

        if not df.empty:
            for location in df['location'].unique():
                loc_data = df[df['location'] == location]
                summary[location] = {
                    'avg_values': loc_data.groupby('sensor_type')['value'].mean().to_dict(),
                    'alert_count': len([a for a in self.alerts if str(a.location) == location]),
                    'critical_count': len([a for a in self.alerts if str(a.location) == location and a.severity == 'critical'])
                }

        return summary