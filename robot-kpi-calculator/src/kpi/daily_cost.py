from typing import Dict, Any, List
from .base import BaseKPICalculator


class DailyCostCalculator(BaseKPICalculator):
    """
    Calculator for KPI 1: Total Daily Cost

    Measures the operational cost to run the robot for one day,
    including utilities consumed during cleaning operations.
    """

    def __init__(self):
        super().__init__("Total Daily Cost")

    def get_required_inputs(self) -> Dict[str, str]:
        return {
            'daily_power_consumption_kwh': 'Power consumed by robot per day (kWh/day)',
            'daily_water_consumption_liters': 'Water consumed by robot per day (Liters/day)',
            'electricity_rate_per_kwh': 'Local electricity cost (USD/kWh)',
            'water_rate_per_liter': 'Local water cost (USD/Liter)',
            'additional_daily_costs': 'Additional daily operational costs (USD)'
        }

    def calculate(self, **kwargs) -> Dict[str, Any]:
        """
        Calculate total daily cost

        Formula:
        total_daily_cost = (daily_power_consumption_kwh × electricity_rate_per_kwh) +
                          (daily_water_consumption_liters × water_rate_per_liter) +
                          additional_daily_costs
        """
        if not self.validate_inputs(kwargs):
            raise ValueError("Missing required inputs for daily cost calculation")

        # Extract inputs
        daily_power_kwh = float(kwargs['daily_power_consumption_kwh'])
        daily_water_liters = float(kwargs['daily_water_consumption_liters'])
        electricity_rate = float(kwargs['electricity_rate_per_kwh'])
        water_rate = float(kwargs['water_rate_per_liter'])
        additional_costs = float(kwargs.get('additional_daily_costs', 0))

        # Calculate costs
        daily_power_cost = daily_power_kwh * electricity_rate
        daily_water_cost = daily_water_liters * water_rate
        total_daily_cost = daily_power_cost + daily_water_cost + additional_costs

        self.logger.info(f"Calculated daily cost: ${total_daily_cost:.2f}")

        return {
            'total_daily_cost': total_daily_cost,
            'daily_power_cost': daily_power_cost,
            'daily_water_cost': daily_water_cost,
            'additional_costs': additional_costs,
            'breakdown': {
                'power': {
                    'consumption': daily_power_kwh,
                    'rate': electricity_rate,
                    'cost': daily_power_cost
                },
                'water': {
                    'consumption': daily_water_liters,
                    'rate': water_rate,
                    'cost': daily_water_cost
                }
            }
        }

    def calculate_from_tasks(self, tasks: List[Dict[str, Any]],
                           electricity_rate: float,
                           water_rate: float,
                           additional_daily_costs: float = 0) -> Dict[str, Any]:
        """
        Calculate daily cost from a list of tasks

        Args:
            tasks: List of task dictionaries with consumption and water_consumption
            electricity_rate: USD/kWh
            water_rate: USD/Liter
            additional_daily_costs: Additional daily operational costs
        """
        # Sum up consumption from all tasks
        total_power_kwh = sum(float(task.get('consumption', 0)) for task in tasks)
        total_water_ml = sum(float(task.get('water_consumption', 0)) for task in tasks)
        total_water_liters = total_water_ml / 1000  # Convert mL to L

        return self.calculate(
            daily_power_consumption_kwh=total_power_kwh,
            daily_water_consumption_liters=total_water_liters,
            electricity_rate_per_kwh=electricity_rate,
            water_rate_per_liter=water_rate,
            additional_daily_costs=additional_daily_costs
        )