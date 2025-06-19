from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class TaskTemplate:
    template_id: int
    template_name: str
    work_order_type: str
    default_duration_minutes: int
    required_skills: List[str]
    optimal_assignees: List[str]
    location_types: List[str]
    frequency_pattern: Optional[str] = None  # daily, weekly, monthly
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    performance_benchmarks: Dict[str, float] = field(default_factory=dict)
    cost_estimates: Dict[str, float] = field(default_factory=dict)

@dataclass
class CompletionPattern:
    template_id: int
    location_id: str
    avg_frequency_days: float
    success_rate: float
    avg_quality_score: float
    avg_efficiency_score: float
    common_assignees: List[str]
    last_completion: datetime
    trend_direction: str  # improving, declining, stable