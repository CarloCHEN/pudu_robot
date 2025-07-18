from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseModel


class CostSetting(BaseModel):
    """Model for robot cost settings"""

    def __init__(self,
                 id: Optional[int] = None,
                 electricity_rate: float = 0.12,
                 water_rate: float = 0.002,
                 human_hourly_wage: float = 15.0,
                 human_cleaning_rate: float = 200.0,
                 purchase_price: float = 50000.0,
                 expected_lifespan: int = 5,
                 annual_maintenance_cost: float = 2000.0,
                 create_time: Optional[datetime] = None,
                 update_time: Optional[datetime] = None):
        self.id = id
        self.electricity_rate = electricity_rate
        self.water_rate = water_rate
        self.human_hourly_wage = human_hourly_wage
        self.human_cleaning_rate = human_cleaning_rate
        self.purchase_price = purchase_price
        self.expected_lifespan = expected_lifespan
        self.annual_maintenance_cost = annual_maintenance_cost
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'electricity_rate': self.electricity_rate,
            'water_rate': self.water_rate,
            'human_hourly_wage': self.human_hourly_wage,
            'human_cleaning_rate': self.human_cleaning_rate,
            'purchase_price': self.purchase_price,
            'expected_lifespan': self.expected_lifespan,
            'annual_maintenance_cost': self.annual_maintenance_cost,
            'create_time': self.create_time,
            'update_time': self.update_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CostSetting':
        return cls(**data)