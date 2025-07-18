from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseKPICalculator(ABC):
    """Base class for all KPI calculators"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def calculate(self, **kwargs) -> Dict[str, Any]:
        """Calculate the KPI and return results"""
        pass

    @abstractmethod
    def get_required_inputs(self) -> Dict[str, str]:
        """Return required inputs and their descriptions"""
        pass

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate that all required inputs are present"""
        required = self.get_required_inputs()
        missing = []

        for key in required:
            if key not in inputs or inputs[key] is None:
                missing.append(key)

        if missing:
            self.logger.error(f"Missing required inputs: {missing}")
            return False

        return True

    def format_result(self, value: float, unit: str = "") -> str:
        """Format the result for display"""
        if unit:
            return f"{value:,.2f} {unit}"
        return f"{value:,.2f}"