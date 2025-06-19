from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class RecommendationSource(Enum):
    PATTERN_BASED = "pattern_based"
    ALERT_TRIGGERED = "alert_triggered"
    METRIC_DRIVEN = "metric_driven"
    PERFORMANCE_DRIVEN = "performance_driven"
    PREVENTIVE = "preventive"
    REACTIVE = "reactive"

class RecommendationPriority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

class RecommendationStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"

@dataclass
class TaskRecommendation:
    recommendation_id: str
    template_id: Optional[int]
    recommended_name: str
    recommended_assignee: str
    recommended_location: str
    recommended_start_time: datetime
    recommended_end_time: datetime
    recommended_priority: RecommendationPriority
    source: RecommendationSource
    work_order_type: str
    confidence_score: float
    reasoning: str
    business_impact: str
    estimated_cost: float
    estimated_duration_minutes: int
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    status: RecommendationStatus = RecommendationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

@dataclass
class RecommendationCriteria:
    location_id: str
    work_order_type: str
    min_confidence: float = 0.7
    max_lookback_days: int = 30
    pattern_threshold: int = 3  # Minimum occurrences to establish pattern
    alert_severity_threshold: str = "severe"
    metric_variance_threshold: float = 0.2
