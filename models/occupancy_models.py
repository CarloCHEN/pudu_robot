from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from .base_models import BaseDataModel, Location, TimeSeriesData, Alert, Metric


@dataclass
class OccupancyReading(TimeSeriesData):
    """Occupancy sensor reading"""
    people_count: int
    dwell_time_minutes: float
    sensor_id: str

    @property
    def value(self) -> float:
        return float(self.people_count)


@dataclass
class OccupancyPattern:
    """Occupancy pattern analysis"""
    location: Location
    hourly_pattern: Dict[int, float]  # hour -> average people count
    daily_pattern: Dict[str, float]   # day of week -> average people count
    peak_hours: List[int]
    low_hours: List[int]
    avg_dwell_time: float
    max_capacity: int


@dataclass
class OccupancyForecast:
    """Occupancy forecast data"""
    location: Location
    forecast_values: List[TimeSeriesData]
    confidence_interval: Dict[str, List[float]]
    model_accuracy: float


@dataclass
class FlightData:
    """Flight-aware integration data"""
    timestamp: datetime
    arrival_passengers: int
    departure_passengers: int
    total_passengers: int
    peak_hour_forecast: datetime


@dataclass
class OccupancyInsight:
    """Key occupancy insights"""
    location: Location
    insight_type: str  # overcrowding, underutilization, pattern_change
    description: str
    impact_score: float  # 0-100
    recommended_action: str


@dataclass
class OccupancyData(BaseDataModel):
    """Complete occupancy data model"""
    readings: List[OccupancyReading]
    patterns: List[OccupancyPattern]
    forecasts: List[OccupancyForecast]
    alerts: List[Alert]
    insights: List[OccupancyInsight]
    flight_data: Optional[List[FlightData]] = None
    metrics: List[Metric] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "readings": [vars(r) for r in self.readings],
            "patterns": [vars(p) for p in self.patterns],
            "forecasts": [vars(f) for f in self.forecasts],
            "alerts": [vars(a) for a in self.alerts],
            "insights": [vars(i) for i in self.insights],
            "flight_data": [vars(f) for f in self.flight_data] if self.flight_data else [],
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
                'people_count': reading.people_count,
                'dwell_time_minutes': reading.dwell_time_minutes,
                'sensor_id': reading.sensor_id
            })
        return pd.DataFrame(data)

    def get_peak_locations(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get locations with highest average occupancy"""
        df = self.to_dataframe()
        if df.empty:
            return []

        avg_occupancy = df.groupby('location')['people_count'].agg(['mean', 'max']).round(1)
        top_locations = avg_occupancy.nlargest(top_n, 'mean')

        return [
            {
                'location': loc,
                'avg_occupancy': row['mean'],
                'max_occupancy': row['max']
            }
            for loc, row in top_locations.iterrows()
        ]

    def get_utilization_metrics(self) -> Dict[str, float]:
        """Calculate space utilization metrics"""
        if not self.patterns:
            return {}

        total_capacity = sum(p.max_capacity for p in self.patterns)
        avg_occupancy = sum(sum(p.hourly_pattern.values()) / len(p.hourly_pattern)
                           for p in self.patterns if p.hourly_pattern)

        return {
            'total_capacity': total_capacity,
            'avg_utilization_rate': (avg_occupancy / total_capacity * 100) if total_capacity > 0 else 0,
            'peak_utilization_rate': max((max(p.hourly_pattern.values()) / p.max_capacity * 100)
                                        for p in self.patterns if p.hourly_pattern and p.max_capacity > 0)
        }