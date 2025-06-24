from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from .base_models import BaseDataModel, Location, Alert, Metric


@dataclass
class WorkOrder:
    """Work order data"""
    order_id: str
    created_date: datetime
    scheduled_date: datetime
    completed_date: Optional[datetime]
    location: Location
    task_type: str
    priority: str  # critical, high, medium, low
    status: str  # pending, in_progress, completed, overdue
    assigned_to: str
    duration_minutes: Optional[float] = None
    quality_score: Optional[float] = None
    auto_generated: bool = False
    trigger_reason: Optional[str] = None


@dataclass
class Inspection:
    """Inspection data"""
    inspection_id: str
    template_id: str
    performed_date: datetime
    location: Location
    inspector: str
    overall_score: float
    category_scores: Dict[str, float]
    issues_found: List[str]
    photos_count: int
    duration_minutes: float
    pass_fail: str  # pass, fail, conditional


@dataclass
class TaskOptimization:
    """AI-generated task optimization recommendation"""
    current_task: WorkOrder
    optimization_type: str  # reschedule, reassign, combine, eliminate
    recommendation: str
    expected_savings: float  # in minutes or cost
    confidence_score: float
    impact_areas: List[str]


@dataclass
class SLACompliance:
    """SLA compliance tracking"""
    sla_type: str
    target_value: float
    actual_value: float
    compliance_rate: float
    period: str
    location: Location
    violations: List[Dict[str, Any]]


@dataclass
class TaskPerformanceMetrics:
    """Task performance metrics"""
    location: Location
    period: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float
    avg_completion_time: float
    avg_quality_score: float
    on_time_rate: float
    first_time_fix_rate: float


@dataclass
class RobotPerformance:
    """Autonomous equipment performance"""
    robot_id: str
    robot_type: str
    location: Location
    uptime_percentage: float
    downtime_hours: float
    area_cleaned_sqft: float
    efficiency_score: float
    cost_per_sqft: float
    maintenance_events: int
    battery_cycles: int
    status: str  # online, offline, maintenance


@dataclass
class TaskData(BaseDataModel):
    """Complete task management data model"""
    work_orders: List[WorkOrder]
    inspections: List[Inspection]
    optimizations: List[TaskOptimization]
    sla_compliance: List[SLACompliance]
    performance_metrics: List[TaskPerformanceMetrics]
    robot_performance: List[RobotPerformance]
    alerts: List[Alert]
    metrics: List[Metric]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "work_orders": [vars(w) for w in self.work_orders],
            "inspections": [vars(i) for i in self.inspections],
            "optimizations": [vars(o) for o in self.optimizations],
            "sla_compliance": [vars(s) for s in self.sla_compliance],
            "performance_metrics": [vars(p) for p in self.performance_metrics],
            "robot_performance": [vars(r) for r in self.robot_performance],
            "alerts": [vars(a) for a in self.alerts],
            "metrics": [vars(m) for m in self.metrics]
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Convert work orders to DataFrame"""
        if not self.work_orders:
            return pd.DataFrame()

        data = []
        for order in self.work_orders:
            data.append({
                'order_id': order.order_id,
                'created_date': order.created_date,
                'scheduled_date': order.scheduled_date,
                'completed_date': order.completed_date,
                'location': str(order.location),
                'task_type': order.task_type,
                'priority': order.priority,
                'status': order.status,
                'assigned_to': order.assigned_to,
                'duration_minutes': order.duration_minutes,
                'quality_score': order.quality_score,
                'auto_generated': order.auto_generated
            })
        return pd.DataFrame(data)

    def get_inspection_summary(self) -> Dict[str, Any]:
        """Get inspection summary statistics"""
        if not self.inspections:
            return {}

        df = pd.DataFrame([{
            'score': i.overall_score,
            'pass_fail': i.pass_fail,
            'location': str(i.location)
        } for i in self.inspections])

        return {
            'total_inspections': len(self.inspections),
            'avg_score': df['score'].mean(),
            'pass_rate': (df['pass_fail'] == 'pass').sum() / len(df) * 100,
            'by_location': df.groupby('location')['score'].agg(['mean', 'count']).to_dict()
        }

    def get_sla_violations(self) -> List[Dict[str, Any]]:
        """Get all SLA violations"""
        violations = []
        for sla in self.sla_compliance:
            if sla.compliance_rate < 100:
                for violation in sla.violations:
                    violations.append({
                        'sla_type': sla.sla_type,
                        'location': str(sla.location),
                        'compliance_rate': sla.compliance_rate,
                        'details': violation
                    })
        return violations

    def calculate_robot_roi(self) -> Dict[str, float]:
        """Calculate ROI for autonomous equipment"""
        if not self.robot_performance:
            return {}

        total_area_cleaned = sum(r.area_cleaned_sqft for r in self.robot_performance)
        avg_robot_cost = sum(r.cost_per_sqft * r.area_cleaned_sqft for r in self.robot_performance) / total_area_cleaned

        # Assume manual cleaning cost (this would come from configuration)
        manual_cost_per_sqft = 0.15  # example value

        return {
            'total_area_cleaned_sqft': total_area_cleaned,
            'avg_robot_cost_per_sqft': avg_robot_cost,
            'manual_cost_per_sqft': manual_cost_per_sqft,
            'cost_savings_percentage': ((manual_cost_per_sqft - avg_robot_cost) / manual_cost_per_sqft * 100),
            'monthly_savings': (manual_cost_per_sqft - avg_robot_cost) * total_area_cleaned
        }