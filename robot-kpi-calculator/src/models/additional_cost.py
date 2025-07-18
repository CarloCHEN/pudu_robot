from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseModel


class AdditionalCost(BaseModel):
    """Model for additional robot costs"""

    def __init__(self,
                 id: Optional[int] = None,
                 cost_date: Optional[datetime] = None,
                 cost_type: str = 'maintenance',
                 amount: float = 0.0,
                 description: str = '',
                 create_time: Optional[datetime] = None,
                 update_time: Optional[datetime] = None):
        self.id = id
        self.cost_date = cost_date or datetime.now()
        self.cost_type = cost_type
        self.amount = amount
        self.description = description
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'cost_date': self.cost_date,
            'cost_type': self.cost_type,
            'amount': self.amount,
            'description': self.description,
            'create_time': self.create_time,
            'update_time': self.update_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdditionalCost':
        return cls(**data)