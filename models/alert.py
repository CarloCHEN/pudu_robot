from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class AlertSeverity(Enum):
    WARNING = "warning"
    SEVERE = "severe"
    VERY_SEVERE = "very_severe"
    CRITICAL = "critical"

class AlertStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"

@dataclass
class Alert:
    alert_id: int
    zone_id: str
    location_id: str
    data_type: str  # temperature, humidity, air_quality, noise, occupancy, etc.
    severity: AlertSeverity
    value: float
    threshold: float
    timestamp: datetime
    duration_minutes: int
    status: AlertStatus = AlertStatus.ACTIVE
    work_order_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    description: Optional[str] = None

    def get_severity_value(self) -> float:
        """Convert severity to numeric score for calculations"""
        severity_scores = {
            AlertSeverity.WARNING: 3.0,
            AlertSeverity.SEVERE: 7.0,
            AlertSeverity.VERY_SEVERE: 9.0,
            AlertSeverity.CRITICAL: 10.0
        }
        return severity_scores[self.severity]

    def get_urgency_multiplier(self) -> float:
        """Get urgency multiplier for work order prioritization"""
        multipliers = {
            AlertSeverity.WARNING: 1.0,
            AlertSeverity.SEVERE: 1.5,
            AlertSeverity.VERY_SEVERE: 2.0,
            AlertSeverity.CRITICAL: 3.0
        }
        return multipliers[self.severity]

@dataclass
class Metric:
    metric_id: int
    work_order_id: int
    location_id: str
    data_type: str
    value_before: Optional[float] = None
    value_after: Optional[float] = None
    timestamp_before: Optional[datetime] = None
    timestamp_after: Optional[datetime] = None
    improvement_percentage: Optional[float] = None
    target_value: Optional[float] = None

    def calculate_improvement(self) -> float:
        """Calculate improvement percentage"""
        if self.value_before and self.value_after:
            improvement = ((self.value_after - self.value_before) / self.value_before) * 100
            self.improvement_percentage = improvement
            return improvement
        return 0.0