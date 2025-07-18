from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseModel


class Task(BaseModel):
    """Model for robot cleaning tasks"""

    def __init__(self,
                 id: Optional[int] = None,
                 robot_sn: str = '',
                 task_name: str = '',
                 mode: Optional[str] = None,
                 sub_mode: Optional[str] = None,
                 type: Optional[str] = None,
                 vacuum_speed: Optional[str] = None,
                 vacuum_suction: Optional[str] = None,
                 wash_speed: Optional[str] = None,
                 wash_suction: Optional[str] = None,
                 wash_water: Optional[str] = None,
                 map_name: Optional[str] = None,
                 map_url: Optional[str] = None,
                 actual_area: float = 0.0,
                 plan_area: float = 0.0,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 duration: int = 0,
                 efficiency: float = 0.0,
                 remaining_time: int = 0,
                 consumption: float = 0.0,
                 water_consumption: float = 0.0,
                 progress: float = 0.0,
                 status: str = '',
                 create_time: Optional[datetime] = None,
                 update_time: Optional[datetime] = None,
                 tenant_id: Optional[int] = None):
        self.id = id
        self.robot_sn = robot_sn
        self.task_name = task_name
        self.mode = mode
        self.sub_mode = sub_mode
        self.type = type
        self.vacuum_speed = vacuum_speed
        self.vacuum_suction = vacuum_suction
        self.wash_speed = wash_speed
        self.wash_suction = wash_suction
        self.wash_water = wash_water
        self.map_name = map_name
        self.map_url = map_url
        self.actual_area = actual_area
        self.plan_area = plan_area
        self.start_time = start_time or datetime.now()
        self.end_time = end_time or datetime.now()
        self.duration = duration
        self.efficiency = efficiency
        self.remaining_time = remaining_time
        self.consumption = consumption
        self.water_consumption = water_consumption
        self.progress = progress
        self.status = status
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()
        self.tenant_id = tenant_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'robot_sn': self.robot_sn,
            'task_name': self.task_name,
            'mode': self.mode,
            'sub_mode': self.sub_mode,
            'type': self.type,
            'vacuum_speed': self.vacuum_speed,
            'vacuum_suction': self.vacuum_suction,
            'wash_speed': self.wash_speed,
            'wash_suction': self.wash_suction,
            'wash_water': self.wash_water,
            'map_name': self.map_name,
            'map_url': self.map_url,
            'actual_area': self.actual_area,
            'plan_area': self.plan_area,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'efficiency': self.efficiency,
            'remaining_time': self.remaining_time,
            'consumption': self.consumption,
            'water_consumption': self.water_consumption,
            'progress': self.progress,
            'status': self.status,
            'create_time': self.create_time,
            'update_time': self.update_time,
            'tenant_id': self.tenant_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(**data)

    @property
    def duration_hours(self) -> float:
        """Get duration in hours"""
        return self.duration / 3600 if self.duration else 0

    @property
    def water_consumption_liters(self) -> float:
        """Get water consumption in liters (from mL)"""
        return self.water_consumption / 1000 if self.water_consumption else 0