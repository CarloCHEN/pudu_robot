from typing import Dict, Any, List
from .base import BaseKPICalculator


class HoursSavedCalculator(BaseKPICalculator):
    """
    Calculator for KPI 2: Hours Saved Daily

    Measures how many labor hours are saved daily by using a robot
    instead of human cleaners to clean the same area.
    """

    def __init__(self):
        super().__init__("Hours Saved Daily")

    def get_required_inputs(self) -> Dict[str, str]:
        return {
            'actual_area_sqm': 'Total area cleaned per day (square meters)',
            'human_cleaning_rate_sqm_per_hour': 'Human cleaning speed (sqm/hour)',
            'robot_cleaning_rate_sqm_per_hour': 'Robot cleaning speed (sqm/hour)'
        }

    def calculate(self, **kwargs) -> Dict[str, Any]:
        """
        Calculate hours saved daily

        Formula:
        hours_saved_daily = (actual_area_sqm ÷ human_cleaning_rate_sqm_per_hour) -
                           (actual_area_sqm ÷ robot_cleaning_rate_sqm_per_hour)

        Simplified (when we don't track robot hours separately):
        hours_saved_daily = actual_area_sqm ÷ human_cleaning_rate_sqm_per_hour
        """
        if not self.validate_inputs(kwargs):
            raise ValueError("Missing required inputs for hours saved calculation")

        # Extract inputs
        area_sqm = float(kwargs['actual_area_sqm'])
        human_rate = float(kwargs['human_cleaning_rate_sqm_per_hour'])
        robot_rate = float(kwargs.get('robot_cleaning_rate_sqm_per_hour', 800))  # Default 800 sqm/hr

        # Calculate hours
        human_hours_needed = area_sqm / human_rate if human_rate > 0 else 0
        robot_hours_needed = area_sqm / robot_rate if robot_rate > 0 else 0
        hours_saved = human_hours_needed - robot_hours_needed

        self.logger.info(f"Calculated hours saved: {hours_saved:.2f} hours")

        return {
            'hours_saved_daily': hours_saved,
            'human_hours_needed': human_hours_needed,
            'robot_hours_needed': robot_hours_needed,
            'area_cleaned': area_sqm,
            'efficiency_ratio': human_hours_needed / robot_hours_needed if robot_hours_needed > 0 else 0
        }

    def calculate_from_tasks(self, tasks: List[Dict[str, Any]],
                           human_cleaning_rate: float,
                           robot_cleaning_rate: float = None) -> Dict[str, Any]:
        """
        Calculate hours saved from a list of tasks

        Args:
            tasks: List of task dictionaries with actual_area
            human_cleaning_rate: Human cleaning speed (sqm/hour)
            robot_cleaning_rate: Robot cleaning speed (sqm/hour), if None calculate from tasks
        """
        # Sum up area from all tasks
        total_area_sqm = sum(float(task.get('actual_area', 0)) for task in tasks)

        # If robot rate not provided, calculate from task efficiency
        if robot_cleaning_rate is None and tasks:
            # Calculate average efficiency from tasks (m²/s to m²/hr)
            valid_tasks = [t for t in tasks if float(t.get('efficiency', 0)) > 0]
            if valid_tasks:
                avg_efficiency_m2_per_sec = sum(float(t['efficiency']) for t in valid_tasks) / len(valid_tasks)
                robot_cleaning_rate = avg_efficiency_m2_per_sec * 3600  # Convert to m²/hr
            else:
                robot_cleaning_rate = 800  # Default

        return self.calculate(
            actual_area_sqm=total_area_sqm,
            human_cleaning_rate_sqm_per_hour=human_cleaning_rate,
            robot_cleaning_rate_sqm_per_hour=robot_cleaning_rate
        )