from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime


class BaseModel(ABC):
    """Base class for all data models"""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        pass

    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model from dictionary"""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}({self.to_dict()})"