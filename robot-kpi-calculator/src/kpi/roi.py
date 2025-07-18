from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base import BaseKPICalculator


class ROICalculator(BaseKPICalculator):
    """
    Calculator for KPI 3: Return on Investment (ROI)

    Measures the cumulative financial return from robot investment over time,
    comparing total savings against total investment costs.
    """

    def __init__(self):
        super().__init__("Return on Investment")

    def get_required_inputs(self) -> Dict[str, str]:
        return {
            'robot_purchase_price': 'Initial robot cost (USD)',
            'annual_maintenance_cost': 'Yearly maintenance (USD/year)',
            'robot_lifespan_years': 'Expected robot life (Years)',
            'human_hourly_wage': 'Human cleaner wage (USD/hour)',
            'days_elapsed': 'Days since deployment (Days)',
            'daily_savings': 'Daily savings (USD/day)',
            'additional_costs': 'Total additional costs (USD)'
        }

    def calculate(self, **kwargs) -> Dict[str, Any]:
        """
        Calculate ROI percentage

        Main Formula:
        roi_percentage = (cumulative_savings ÷ total_robot_investment) × 100

        Where:
        - total_robot_investment = purchase_price + (maintenance × lifespan) + additional_costs
        - cumulative_savings = daily_savings × days_elapsed
        - daily_savings = daily_human_cost - robot_daily_cost
        """
        # For simplified calculation when daily_savings is provided
        if 'daily_savings' in kwargs and 'days_elapsed' in kwargs:
            return self._calculate_simple_roi(**kwargs)

        # For full calculation
        return self._calculate_full_roi(**kwargs)

    def _calculate_simple_roi(self, **kwargs) -> Dict[str, Any]:
        """Calculate ROI when daily savings is already known"""
        # Total investment
        purchase_price = float(kwargs['robot_purchase_price'])
        annual_maintenance = float(kwargs['annual_maintenance_cost'])
        lifespan_years = float(kwargs['robot_lifespan_years'])
        additional_costs = float(kwargs.get('additional_costs', 0))

        total_investment = purchase_price + (annual_maintenance * lifespan_years) + additional_costs

        # Cumulative savings
        daily_savings = float(kwargs['daily_savings'])
        days_elapsed = float(kwargs['days_elapsed'])
        cumulative_savings = daily_savings * days_elapsed

        # ROI calculation
        roi_percentage = (cumulative_savings / total_investment * 100) if total_investment > 0 else 0

        # Payback period
        payback_days = total_investment / daily_savings if daily_savings > 0 else float('inf')
        payback_years = payback_days / 365

        return {
            'roi_percentage': roi_percentage,
            'total_investment': total_investment,
            'cumulative_savings': cumulative_savings,
            'daily_savings': daily_savings,
            'days_elapsed': days_elapsed,
            'payback_period_days': payback_days,
            'payback_period_years': payback_years,
            'investment_breakdown': {
                'purchase_price': purchase_price,
                'total_maintenance': annual_maintenance * lifespan_years,
                'additional_costs': additional_costs
            }
        }

    def _calculate_full_roi(self, **kwargs) -> Dict[str, Any]:
        """Calculate ROI from scratch including daily savings calculation"""
        # Calculate daily human cost
        human_hours_daily = float(kwargs['human_hours_daily'])
        human_hourly_wage = float(kwargs['human_hourly_wage'])
        daily_human_cost = human_hours_daily * human_hourly_wage

        # Get robot daily cost
        robot_daily_cost = float(kwargs['robot_daily_cost'])

        # Calculate daily savings
        daily_savings = daily_human_cost - robot_daily_cost

        # Add to kwargs and use simple calculation
        kwargs['daily_savings'] = daily_savings
        result = self._calculate_simple_roi(**kwargs)

        # Add additional details
        result['daily_human_cost'] = daily_human_cost
        result['robot_daily_cost'] = robot_daily_cost

        return result

    def calculate_from_cost_data(self,
                               cost_setting: Dict[str, Any],
                               additional_costs: List[Dict[str, Any]],
                               daily_cost: float,
                               hours_saved_daily: float,
                               deployment_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculate ROI from cost settings and operational data

        Args:
            cost_setting: Cost settings from database
            additional_costs: List of additional cost records
            daily_cost: Robot daily operational cost
            hours_saved_daily: Hours saved per day
            deployment_date: When robot was deployed (for days_elapsed)
        """
        # Sum additional costs
        total_additional_costs = sum(float(cost['amount']) for cost in additional_costs)

        # Calculate days elapsed
        if deployment_date:
            days_elapsed = (datetime.now() - deployment_date).days
        else:
            # Assume deployment was when first task was run or 30 days ago
            days_elapsed = 30

        # Calculate daily human cost
        daily_human_cost = hours_saved_daily * float(cost_setting['human_hourly_wage'])
        daily_savings = daily_human_cost - daily_cost

        return self.calculate(
            robot_purchase_price=cost_setting['purchase_price'],
            annual_maintenance_cost=cost_setting['annual_maintenance_cost'],
            robot_lifespan_years=cost_setting['expected_lifespan'],
            human_hourly_wage=cost_setting['human_hourly_wage'],
            days_elapsed=days_elapsed,
            daily_savings=daily_savings,
            additional_costs=total_additional_costs
        )