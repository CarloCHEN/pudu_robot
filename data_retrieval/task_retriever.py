from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from models.task_models import (
    TaskData, WorkOrder, Inspection, TaskOptimization,
    SLACompliance, TaskPerformanceMetrics, RobotPerformance,
    Alert, Metric
)
from models.base_models import Location
from .base_retriever import BaseDataRetriever


class TaskDataRetriever(BaseDataRetriever):
    """Retrieves task management and robot performance data"""

    TASK_TYPES = [
        'routine_cleaning', 'deep_cleaning', 'inspection',
        'consumable_refill', 'waste_removal', 'emergency_cleanup'
    ]

    ROBOT_TYPES = {
        'floor_scrubber': {'coverage_sqft_hour': 5000, 'battery_hours': 4},
        'vacuum_robot': {'coverage_sqft_hour': 3000, 'battery_hours': 6},
        'uv_disinfection': {'coverage_sqft_hour': 2000, 'battery_hours': 3}
    }

    def retrieve_data(self, locations: List[Location], start_date: datetime,
                     end_date: datetime, **kwargs) -> TaskData:
        """Retrieve task and robot data"""
        if self.use_synthetic_data:
            return self.generate_synthetic_data(locations, start_date, end_date, **kwargs)

        work_orders = self._get_work_orders(locations, start_date, end_date)
        inspections = self._get_inspections(locations, start_date, end_date)
        optimizations = self._generate_optimizations(work_orders)
        sla_compliance = self._calculate_sla_compliance(work_orders, inspections)
        performance_metrics = self._calculate_performance_metrics(work_orders, inspections)
        robot_performance = self._get_robot_performance(locations, start_date, end_date)
        alerts = self._get_task_alerts(locations, start_date, end_date)
        metrics = self._calculate_metrics(work_orders, inspections, robot_performance)

        return TaskData(
            work_orders=work_orders,
            inspections=inspections,
            optimizations=optimizations,
            sla_compliance=sla_compliance,
            performance_metrics=performance_metrics,
            robot_performance=robot_performance,
            alerts=alerts,
            metrics=metrics
        )

    def generate_synthetic_data(self, locations: List[Location], start_date: datetime,
                               end_date: datetime, **kwargs) -> TaskData:
        """Generate synthetic task and robot data"""
        work_orders = []
        inspections = []
        optimizations = []
        sla_compliance = []
        performance_metrics = []
        robot_performance = []
        alerts = []

        # Generate work orders
        order_id = 1000
        for location in locations:
            # Calculate number of orders based on location size
            floor_num = int(location.floor.replace('Floor ', '')) if 'Floor' in location.floor else 1
            daily_orders = 3 + floor_num  # More orders for higher floors

            current_date = start_date
            while current_date <= end_date:
                for _ in range(daily_orders):
                    # Random task type
                    task_type = np.random.choice(self.TASK_TYPES)

                    # Set priority based on task type
                    if task_type == 'emergency_cleanup':
                        priority = 'critical'
                    elif task_type in ['deep_cleaning', 'inspection']:
                        priority = 'high'
                    else:
                        priority = np.random.choice(['medium', 'low'], p=[0.7, 0.3])

                    # Schedule time
                    scheduled_hour = np.random.choice(range(6, 20))  # 6 AM to 8 PM
                    scheduled_date = current_date + timedelta(hours=scheduled_hour)

                    # Completion status and time
                    is_completed = np.random.random() > 0.1  # 90% completion rate
                    is_overdue = False

                    if is_completed:
                        # Add some variance to completion time
                        completion_delay = np.random.normal(0, 2)  # hours
                        completed_date = scheduled_date + timedelta(hours=max(0, completion_delay))
                        status = 'completed'
                        if completed_date > scheduled_date + timedelta(hours=4):
                            is_overdue = True
                            status = 'overdue'
                    else:
                        completed_date = None
                        status = 'pending' if scheduled_date > datetime.now() else 'overdue'
                        is_overdue = status == 'overdue'

                    # Duration and quality
                    base_duration = {'routine_cleaning': 30, 'deep_cleaning': 120,
                                   'inspection':