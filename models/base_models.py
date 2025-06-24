from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import pandas as pd


@dataclass
class Location:
    """Represents a hierarchical location"""
    country: str
    city: str
    building: str
    floor: str
    area: Optional[str] = None

    def __str__(self):
        parts = [self.country, self.city, self.building, self.floor]
        if self.area:
            parts.append(self.area)
        return " > ".join(parts)


@dataclass
class TimeSeriesData:
    """Base class for time series data"""
    timestamp: datetime
    value: float
    location: Location
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Represents an alert/issue"""
    alert_id: str
    timestamp: datetime
    location: Location
    severity: str  # critical, warning, info
    category: str
    message: str
    value: float
    threshold: float
    resolved: bool = False


@dataclass
class Metric:
    """Represents a calculated metric"""
    name: str
    value: float
    unit: str
    trend: str  # up, down, stable
    change_percentage: float
    period: str


class BaseDataModel(ABC):
    """Abstract base class for all data models"""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        pass

    @abstractmethod
    def to_dataframe(self) -> pd.DataFrame:
        """Convert model to pandas DataFrame"""
        pass


@dataclass
class ReportSection:
    """Represents a section in the report"""
    title: str
    content_type: str  # text, table, chart, metric
    data: Any
    summary: Optional[str] = None
    recommendations: Optional[List[str]] = None