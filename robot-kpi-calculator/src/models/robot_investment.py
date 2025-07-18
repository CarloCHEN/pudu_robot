from typing import Dict, Any, Optional
from datetime import datetime, date
from .base import BaseModel


class RobotInvestment(BaseModel):
    """Model for individual robot investment tracking"""

    def __init__(self,
                 id: Optional[int] = None,
                 robot_sn: str = '',
                 purchase_price: float = 50000.0,
                 purchase_date: Optional[date] = None,
                 expected_lifespan_years: int = 5,
                 annual_maintenance_cost: float = 2000.0,
                 deployment_date: Optional[date] = None,
                 retirement_date: Optional[date] = None,
                 status: str = 'active',
                 create_time: Optional[datetime] = None,
                 update_time: Optional[datetime] = None):

        self.id = id
        self.robot_sn = robot_sn
        self.purchase_price = purchase_price
        self.purchase_date = purchase_date or date.today()
        self.expected_lifespan_years = expected_lifespan_years
        self.annual_maintenance_cost = annual_maintenance_cost
        self.deployment_date = deployment_date
        self.retirement_date = retirement_date
        self.status = status
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'robot_sn': self.robot_sn,
            'purchase_price': self.purchase_price,
            'purchase_date': self.purchase_date,
            'expected_lifespan_years': self.expected_lifespan_years,
            'annual_maintenance_cost': self.annual_maintenance_cost,
            'deployment_date': self.deployment_date,
            'retirement_date': self.retirement_date,
            'status': self.status,
            'create_time': self.create_time,
            'update_time': self.update_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RobotInvestment':
        return cls(**data)

    @property
    def total_investment(self) -> float:
        """Calculate total investment for this robot"""
        return self.purchase_price + (self.annual_maintenance_cost * self.expected_lifespan_years)

    @property
    def days_since_deployment(self) -> int:
        """Calculate days since deployment"""
        if self.deployment_date:
            return (date.today() - self.deployment_date).days
        return 0