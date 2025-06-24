from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from .base_models import BaseDataModel, Location, TimeSeriesData, Alert, Metric


@dataclass
class ConsumableReading(TimeSeriesData):
    """Consumable sensor reading"""
    consumable_type: str  # toilet_paper, hand_soap, paper_towel, sanitizer
    remaining_percentage: float
    consumption_rate: float  # units per hour
    sensor_id: str
    dispenser_id: str

    @property
    def value(self) -> float:
        return self.remaining_percentage


@dataclass
class WasteReading(TimeSeriesData):
    """Waste bin sensor reading"""
    bin_type: str  # general, recycling, organic
    fill_percentage: float
    fill_rate: float  # percentage per hour
    sensor_id: str
    bin_id: str

    @property
    def value(self) -> float:
        return self.fill_percentage


@dataclass
class ConsumablePattern:
    """Consumable usage pattern"""
    location: Location
    consumable_type: str
    hourly_consumption: Dict[int, float]  # hour -> consumption rate
    daily_consumption: Dict[str, float]   # day -> consumption rate
    peak_hours: List[int]
    avg_daily_usage: float
    days_until_empty: float


@dataclass
class ConsumableForecast:
    """Consumable depletion forecast"""
    location: Location
    consumable_type: str
    dispenser_id: str
    current_level: float
    predicted_empty_time: datetime
    confidence: float
    recommended_refill_time: datetime


@dataclass
class SustainabilityMetric:
    """Sustainability tracking"""
    metric_type: str  # waste_diverted, recycling_rate, consumption_reduction
    value: float
    target: float
    trend: str
    location: Location
    period: str


@dataclass
class ConsumableData(BaseDataModel):
    """Complete consumable and waste data model"""
    consumable_readings: List[ConsumableReading]
    waste_readings: List[WasteReading]
    patterns: List[ConsumablePattern]
    forecasts: List[ConsumableForecast]
    alerts: List[Alert]
    sustainability_metrics: List[SustainabilityMetric]
    metrics: List[Metric]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consumable_readings": [vars(r) for r in self.consumable_readings],
            "waste_readings": [vars(r) for r in self.waste_readings],
            "patterns": [vars(p) for p in self.patterns],
            "forecasts": [vars(f) for f in self.forecasts],
            "alerts": [vars(a) for a in self.alerts],
            "sustainability_metrics": [vars(s) for s in self.sustainability_metrics],
            "metrics": [vars(m) for m in self.metrics]
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Convert consumable readings to DataFrame"""
        if not self.consumable_readings:
            return pd.DataFrame()

        data = []
        for reading in self.consumable_readings:
            data.append({
                'timestamp': reading.timestamp,
                'location': str(reading.location),
                'type': reading.consumable_type,
                'remaining_pct': reading.remaining_percentage,
                'consumption_rate': reading.consumption_rate,
                'dispenser_id': reading.dispenser_id
            })
        return pd.DataFrame(data)

    def get_critical_consumables(self, threshold: float = 20.0) -> List[Dict[str, Any]]:
        """Get consumables below critical threshold"""
        critical = []
        for reading in self.consumable_readings:
            if reading.remaining_percentage < threshold:
                critical.append({
                    'location': str(reading.location),
                    'type': reading.consumable_type,
                    'remaining': reading.remaining_percentage,
                    'dispenser_id': reading.dispenser_id,
                    'urgency': 'critical' if reading.remaining_percentage < 10 else 'warning'
                })
        return sorted(critical, key=lambda x: x['remaining'])

    def get_waste_issues(self, threshold: float = 80.0) -> List[Dict[str, Any]]:
        """Get waste bins above critical threshold"""
        issues = []
        for reading in self.waste_readings:
            if reading.fill_percentage > threshold:
                issues.append({
                    'location': str(reading.location),
                    'bin_type': reading.bin_type,
                    'fill_level': reading.fill_percentage,
                    'bin_id': reading.bin_id,
                    'urgency': 'critical' if reading.fill_percentage > 90 else 'warning'
                })
        return sorted(issues, key=lambda x: x['fill_level'], reverse=True)

    def calculate_sustainability_score(self) -> float:
        """Calculate overall sustainability score"""
        if not self.sustainability_metrics:
            return 0.0

        scores = []
        for metric in self.sustainability_metrics:
            if metric.target > 0:
                achievement_rate = min(metric.value / metric.target * 100, 100)
                scores.append(achievement_rate)

        return sum(scores) / len(scores) if scores else 0.0