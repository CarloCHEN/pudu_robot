from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from .base_models import BaseDataModel, Location, Metric


@dataclass
class ProblemHotspot:
    """Location with high alert frequency"""
    location: Location
    alert_count: int
    critical_count: int
    warning_count: int
    top_issues: List[Tuple[str, int]]  # (issue_type, count)
    trend: str  # increasing, decreasing, stable
    priority_score: float


@dataclass
class CleaningPriority:
    """Cleaning priority calculation"""
    location: Location
    priority_score: float  # 0-100
    contributing_factors: Dict[str, float]  # factor -> weight
    recommended_frequency: str
    current_frequency: str
    adjustment_needed: bool


@dataclass
class CorrelationInsight:
    """Correlation between different variables"""
    variable1: str
    variable1_location: Location
    variable2: str
    variable2_location: Location
    correlation_coefficient: float
    relationship_type: str  # positive, negative, non-linear
    strength: str  # strong, moderate, weak
    lag_hours: int  # time lag between cause and effect


@dataclass
class Recommendation:
    """AI-generated recommendation"""
    recommendation_id: str
    category: str  # efficiency, cost_saving, quality, sustainability
    title: str
    description: str
    expected_impact: str
    implementation_effort: str  # low, medium, high
    priority: int  # 1-5
    locations_affected: List[Location]
    estimated_savings: Optional[float] = None


@dataclass
class ExecutiveSummary:
    """High-level executive summary"""
    reporting_period: str
    key_achievements: List[str]
    critical_issues: List[str]
    cost_savings: float
    efficiency_improvements: float
    customer_satisfaction_score: float
    sustainability_score: float
    top_recommendations: List[str]


@dataclass
class ServiceHighlight:
    """Service delivery highlights"""
    highlight_type: str  # achievement, improvement, innovation
    title: str
    description: str
    metrics: Dict[str, float]
    impact: str


@dataclass
class InsightsData(BaseDataModel):
    """Complete insights data model"""
    problem_hotspots: List[ProblemHotspot]
    cleaning_priorities: List[CleaningPriority]
    correlations: List[CorrelationInsight]
    recommendations: List[Recommendation]
    executive_summary: Optional[ExecutiveSummary] = None
    service_highlights: Optional[List[ServiceHighlight]] = None
    metrics: List[Metric] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_hotspots": [vars(h) for h in self.problem_hotspots],
            "cleaning_priorities": [vars(c) for c in self.cleaning_priorities],
            "correlations": [vars(corr) for corr in self.correlations],
            "recommendations": [vars(r) for r in self.recommendations],
            "executive_summary": vars(self.executive_summary) if self.executive_summary else None,
            "service_highlights": [vars(s) for s in self.service_highlights] if self.service_highlights else [],
            "metrics": [vars(m) for m in self.metrics]
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Convert problem hotspots to DataFrame for analysis"""
        if not self.problem_hotspots:
            return pd.DataFrame()

        data = []
        for hotspot in self.problem_hotspots:
            data.append({
                'location': str(hotspot.location),
                'alert_count': hotspot.alert_count,
                'critical_count': hotspot.critical_count,
                'priority_score': hotspot.priority_score,
                'trend': hotspot.trend
            })
        return pd.DataFrame(data)

    def get_top_hotspots(self, n: int = 5) -> List[ProblemHotspot]:
        """Get top N problem hotspots by priority score"""
        return sorted(self.problem_hotspots, key=lambda x: x.priority_score, reverse=True)[:n]

    def get_strong_correlations(self, threshold: float = 0.7) -> List[CorrelationInsight]:
        """Get correlations above threshold"""
        return [c for c in self.correlations
                if abs(c.correlation_coefficient) >= threshold]

    def get_high_priority_recommendations(self, priority: int = 3) -> List[Recommendation]:
        """Get recommendations with priority >= threshold"""
        return [r for r in self.recommendations if r.priority >= priority]

    def get_cleaning_adjustments_needed(self) -> List[CleaningPriority]:
        """Get locations needing frequency adjustments"""
        return [cp for cp in self.cleaning_priorities if cp.adjustment_needed]