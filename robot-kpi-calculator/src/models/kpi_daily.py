from typing import Dict, Any, Optional
from datetime import datetime, date
from .base import BaseModel


class KPIDaily(BaseModel):
    """Model for daily KPI records"""

    def __init__(self,
                 id: Optional[int] = None,
                 calculation_date: Optional[date] = None,
                 robot_sn: Optional[str] = None,
                 # KPI 1: Daily Cost
                 total_daily_cost: float = 0.0,
                 daily_power_cost: float = 0.0,
                 daily_water_cost: float = 0.0,
                 daily_additional_cost: float = 0.0,
                 power_consumption_kwh: float = 0.0,
                 water_consumption_liters: float = 0.0,
                 # KPI 2: Hours Saved
                 hours_saved_daily: float = 0.0,
                 human_hours_needed: float = 0.0,
                 robot_hours_needed: float = 0.0,
                 area_cleaned_sqm: float = 0.0,
                 # KPI 3: ROI
                 roi_percentage: float = 0.0,
                 cumulative_savings: float = 0.0,
                 total_investment: float = 0.0,
                 days_since_deployment: int = 0,
                 payback_period_days: Optional[int] = None,
                 # Metadata
                 tasks_count: int = 0,
                 calculation_timestamp: Optional[datetime] = None,
                 create_time: Optional[datetime] = None,
                 update_time: Optional[datetime] = None):

        self.id = id
        self.calculation_date = calculation_date or date.today()
        self.robot_sn = robot_sn
        # KPI 1
        self.total_daily_cost = total_daily_cost
        self.daily_power_cost = daily_power_cost
        self.daily_water_cost = daily_water_cost
        self.daily_additional_cost = daily_additional_cost
        self.power_consumption_kwh = power_consumption_kwh
        self.water_consumption_liters = water_consumption_liters
        # KPI 2
        self.hours_saved_daily = hours_saved_daily
        self.human_hours_needed = human_hours_needed
        self.robot_hours_needed = robot_hours_needed
        self.area_cleaned_sqm = area_cleaned_sqm
        # KPI 3
        self.roi_percentage = roi_percentage
        self.cumulative_savings = cumulative_savings
        self.total_investment = total_investment
        self.days_since_deployment = days_since_deployment
        self.payback_period_days = payback_period_days
        # Metadata
        self.tasks_count = tasks_count
        self.calculation_timestamp = calculation_timestamp or datetime.now()
        self.create_time = create_time or datetime.now()
        self.update_time = update_time or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'calculation_date': self.calculation_date,
            'robot_sn': self.robot_sn,
            'total_daily_cost': round(self.total_daily_cost, 2),
            'daily_power_cost': round(self.daily_power_cost, 2),
            'daily_water_cost': round(self.daily_water_cost, 2),
            'daily_additional_cost': round(self.daily_additional_cost, 2),
            'power_consumption_kwh': round(self.power_consumption_kwh, 3),
            'water_consumption_liters': round(self.water_consumption_liters, 3),
            'hours_saved_daily': round(self.hours_saved_daily, 2),
            'human_hours_needed': round(self.human_hours_needed, 2),
            'robot_hours_needed': round(self.robot_hours_needed, 2),
            'area_cleaned_sqm': round(self.area_cleaned_sqm, 2),
            'roi_percentage': round(self.roi_percentage, 2),
            'cumulative_savings': round(self.cumulative_savings, 2),
            'total_investment': round(self.total_investment, 2),
            'days_since_deployment': self.days_since_deployment,
            'payback_period_days': self.payback_period_days,
            'tasks_count': self.tasks_count,
            'calculation_timestamp': self.calculation_timestamp,
            'create_time': self.create_time,
            'update_time': self.update_time
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KPIDaily':
        return cls(**data)

    @classmethod
    def from_kpi_results(cls,
                        kpi_results: Dict[str, Any],
                        calculation_date: date,
                        robot_sn: Optional[str] = None) -> 'KPIDaily':
        """Create KPIDaily from calculator results"""
        daily_cost = kpi_results['kpis']['daily_cost']
        hours_saved = kpi_results['kpis']['hours_saved']
        roi = kpi_results['kpis']['roi']

        # Handle infinite payback period
        payback_days = roi['payback_period_days']
        if payback_days == float('inf'):
            payback_days = None
        else:
            payback_days = int(payback_days)

        return cls(
            calculation_date=calculation_date,
            robot_sn=robot_sn,
            # KPI 1
            total_daily_cost=daily_cost['total_daily_cost'],
            daily_power_cost=daily_cost['daily_power_cost'],
            daily_water_cost=daily_cost['daily_water_cost'],
            daily_additional_cost=daily_cost['additional_costs'],
            power_consumption_kwh=daily_cost['breakdown']['power']['consumption'],
            water_consumption_liters=daily_cost['breakdown']['water']['consumption'],
            # KPI 2
            hours_saved_daily=hours_saved['hours_saved_daily'],
            human_hours_needed=hours_saved['human_hours_needed'],
            robot_hours_needed=hours_saved['robot_hours_needed'],
            area_cleaned_sqm=hours_saved['area_cleaned'],
            # KPI 3
            roi_percentage=roi['roi_percentage'],
            cumulative_savings=roi['cumulative_savings'],
            total_investment=roi['total_investment'],
            days_since_deployment=roi['days_elapsed'],
            payback_period_days=payback_days,
            # Metadata
            tasks_count=kpi_results['tasks_analyzed']
        )