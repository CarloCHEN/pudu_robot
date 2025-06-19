# =============================================================================
# models/work_order.py
# =============================================================================
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class WorkOrderSource(Enum):
    AI_RECOMMENDED = "ai_recommended"
    SCHEDULED = "scheduled"
    ALERT_BASED = "alert_based"
    MANUAL = "manual"
    EXTERNAL = "external"
    INSPECTION = "inspection"

class Priority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class WorkOrderStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class WorkOrder:
    work_order_id: int
    work_order_name: str
    assignee: str
    start_time: datetime
    end_time: datetime
    location: str
    priority: Priority
    source: WorkOrderSource
    work_order_type: str
    status: WorkOrderStatus = WorkOrderStatus.PENDING
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    template_id: Optional[int] = None
    duration_minutes: Optional[int] = None

    def __post_init__(self):
        if self.duration_minutes is None:
            self.duration_minutes = int((self.end_time - self.start_time).total_seconds() / 60)

@dataclass
class CompletionData:
    work_order_id: int
    quality_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    time_variance_minutes: Optional[int] = None
    resource_usage: Optional[str] = None
    completion_notes: Optional[str] = None