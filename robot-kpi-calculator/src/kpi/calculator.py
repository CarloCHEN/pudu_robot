from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
import logging

from .daily_cost import DailyCostCalculator
from .hours_saved import HoursSavedCalculator
from .roi import ROICalculator
from ..data.loader import DataLoader
from ..models.cost_setting import CostSetting
from ..models.additional_cost import AdditionalCost
from ..models.task import Task

logger = logging.getLogger(__name__)


class KPICalculator:
    """
    Main KPI Calculator that orchestrates all KPI calculations
    """

    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader
        self.daily_cost_calc = DailyCostCalculator()
        self.hours_saved_calc = HoursSavedCalculator()
        self.roi_calc = ROICalculator()
        self.logger = logger

    def calculate_all_kpis(self,
                          start_date: datetime,
                          end_date: datetime,
                          robot_sn: Optional[str] = None,
                          use_synthetic_data: bool = False) -> Dict[str, Any]:
        """
        Calculate all KPIs for a given time period and optional robot

        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            robot_sn: Optional robot serial number to filter by
            use_synthetic_data: Whether to use synthetic data

        Returns:
            Dictionary containing all KPI results
        """
        self.logger.info(f"Calculating KPIs from {start_date} to {end_date}")
        if robot_sn:
            self.logger.info(f"Filtering for robot: {robot_sn}")

        # Load data
        cost_setting = self.data_loader.load_cost_settings(use_synthetic=use_synthetic_data)
        additional_costs = self.data_loader.load_additional_costs(
            start_date, end_date, use_synthetic=use_synthetic_data
        )
        tasks = self.data_loader.load_tasks(
            start_date, end_date, robot_sn, use_synthetic=use_synthetic_data
        )

        if not tasks:
            self.logger.warning("No tasks found for the specified period")
            return self._empty_results()

        # Calculate KPI 1: Daily Cost
        daily_cost_result = self._calculate_daily_cost(tasks, cost_setting, additional_costs)

        # Calculate KPI 2: Hours Saved
        hours_saved_result = self._calculate_hours_saved(tasks, cost_setting)

        # Calculate KPI 3: ROI
        roi_result = self._calculate_roi(
            cost_setting,
            additional_costs,
            daily_cost_result['total_daily_cost'],
            hours_saved_result['hours_saved_daily'],
            start_date
        )

        # Compile results
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days + 1
            },
            'robot_sn': robot_sn,
            'tasks_analyzed': len(tasks),
            'kpis': {
                'daily_cost': daily_cost_result,
                'hours_saved': hours_saved_result,
                'roi': roi_result
            },
            'summary': self._generate_summary(daily_cost_result, hours_saved_result, roi_result)
        }

    def _calculate_daily_cost(self,
                            tasks: List[Task],
                            cost_setting: CostSetting,
                            additional_costs: List[AdditionalCost]) -> Dict[str, Any]:
        """Calculate daily cost KPI"""
        # Calculate additional daily costs
        total_additional = sum(cost.amount for cost in additional_costs)
        days_in_period = max(1, len(set(task.start_time.date() for task in tasks)))
        additional_daily = total_additional / days_in_period

        # Use calculator
        return self.daily_cost_calc.calculate_from_tasks(
            [task.to_dict() for task in tasks],
            cost_setting.electricity_rate,
            cost_setting.water_rate,
            additional_daily
        )

    def _calculate_hours_saved(self,
                             tasks: List[Task],
                             cost_setting: CostSetting) -> Dict[str, Any]:
        """Calculate hours saved KPI"""
        return self.hours_saved_calc.calculate_from_tasks(
            [task.to_dict() for task in tasks],
            cost_setting.human_cleaning_rate
        )

    def _calculate_roi(self,
                      cost_setting: CostSetting,
                      additional_costs: List[AdditionalCost],
                      daily_cost: float,
                      hours_saved_daily: float,
                      start_date: datetime) -> Dict[str, Any]:
        """Calculate ROI KPI"""
        # Estimate deployment date (could be enhanced with actual deployment tracking)
        deployment_date = start_date - timedelta(days=30)  # Assume 30 days ago

        return self.roi_calc.calculate_from_cost_data(
            cost_setting.to_dict(),
            [cost.to_dict() for cost in additional_costs],
            daily_cost,
            hours_saved_daily,
            deployment_date
        )

    def _generate_summary(self,
                         daily_cost: Dict[str, Any],
                         hours_saved: Dict[str, Any],
                         roi: Dict[str, Any]) -> Dict[str, str]:
        """Generate human-readable summary"""
        return {
            'daily_cost': f"${daily_cost['total_daily_cost']:.2f} per day",
            'hours_saved': f"{hours_saved['hours_saved_daily']:.1f} hours saved daily",
            'roi': f"{roi['roi_percentage']:.1f}% ROI",
            'payback_period': f"{roi['payback_period_years']:.1f} years to payback"
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure"""
        return {
            'period': {},
            'robot_sn': None,
            'tasks_analyzed': 0,
            'kpis': {
                'daily_cost': {'total_daily_cost': 0, 'daily_power_cost': 0, 'daily_water_cost': 0},
                'hours_saved': {'hours_saved_daily': 0, 'human_hours_needed': 0, 'robot_hours_needed': 0},
                'roi': {'roi_percentage': 0, 'total_investment': 0, 'cumulative_savings': 0}
            },
            'summary': {
                'daily_cost': '$0.00 per day',
                'hours_saved': '0.0 hours saved daily',
                'roi': '0.0% ROI',
                'payback_period': 'N/A'
            }
        }
    def calculate_daily_kpis(self,
                            target_date: date,
                            robot_sn: Optional[str] = None,
                            use_synthetic_data: bool = False,
                            save_to_db: bool = True) -> Dict[str, Any]:
        """
        Calculate KPIs for a single day

        Args:
            target_date: The date to calculate KPIs for
            robot_sn: Optional robot serial number
            use_synthetic_data: Whether to use synthetic data
            save_to_db: Whether to save results to database

        Returns:
            Dictionary containing KPI results
        """
        # Set time range to full day
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        # Calculate KPIs
        results = self.calculate_all_kpis(
            start_date=start_datetime,
            end_date=end_datetime,
            robot_sn=robot_sn,
            use_synthetic_data=use_synthetic_data
        )

        # Save to database if requested
        if save_to_db and hasattr(self, 'data_saver'):
            success = self.data_saver.save_kpi_results(
                results,
                target_date,
                robot_sn
            )
            results['saved_to_db'] = success

        return results

    def calculate_daily_kpis_batch(self,
                                  start_date: date,
                                  end_date: date,
                                  robot_sn: Optional[str] = None,
                                  use_synthetic_data: bool = False,
                                  save_to_db: bool = True) -> List[Dict[str, Any]]:
        """
        Calculate daily KPIs for a date range

        Args:
            start_date: Start date
            end_date: End date
            robot_sn: Optional robot serial number
            use_synthetic_data: Whether to use synthetic data
            save_to_db: Whether to save results to database

        Returns:
            List of daily KPI results
        """
        results = []
        current_date = start_date

        while current_date <= end_date:
            self.logger.info(f"Calculating KPIs for {current_date}")

            daily_result = self.calculate_daily_kpis(
                target_date=current_date,
                robot_sn=robot_sn,
                use_synthetic_data=use_synthetic_data,
                save_to_db=save_to_db
            )

            results.append({
                'date': current_date,
                'results': daily_result
            })

            current_date += timedelta(days=1)

        return results