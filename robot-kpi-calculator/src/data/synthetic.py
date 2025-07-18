from typing import List, Optional
from datetime import datetime, timedelta
import random

from ..models import CostSetting, AdditionalCost, Task


class SyntheticDataGenerator:
    """Generate synthetic data for testing"""

    def generate_cost_setting(self) -> CostSetting:
        """Generate synthetic cost settings"""
        return CostSetting(
            id=1,
            electricity_rate=0.12,
            water_rate=0.002,
            human_hourly_wage=15.0,
            human_cleaning_rate=200.0,
            purchase_price=50000.0,
            expected_lifespan=5,
            annual_maintenance_cost=2000.0
        )

    def generate_additional_costs(self,
                                start_date: datetime,
                                end_date: datetime) -> List[AdditionalCost]:
        """Generate synthetic additional costs"""
        costs = []

        # Generate 3-5 random costs in the period
        num_costs = random.randint(3, 5)
        days_range = (end_date - start_date).days

        cost_types = ['maintenance', 'repair', 'part_replacement', 'upgrade', 'training']

        for i in range(num_costs):
            cost_date = start_date + timedelta(days=random.randint(0, days_range))
            cost_type = random.choice(cost_types)

            # Amount based on type
            if cost_type == 'maintenance':
                amount = random.uniform(100, 500)
            elif cost_type == 'repair':
                amount = random.uniform(200, 1000)
            elif cost_type == 'part_replacement':
                amount = random.uniform(300, 1500)
            elif cost_type == 'upgrade':
                amount = random.uniform(500, 2000)
            else:  # training
                amount = random.uniform(100, 300)

            costs.append(AdditionalCost(
                id=i+1,
                cost_date=cost_date,
                cost_type=cost_type,
                amount=amount,
                description=f"Synthetic {cost_type} cost"
            ))

        return sorted(costs, key=lambda x: x.cost_date)

    def generate_tasks(self,
                      start_date: datetime,
                      end_date: datetime,
                      robot_sn: Optional[str] = None) -> List[Task]:
        """Generate synthetic tasks"""
        tasks = []
        robot_sn = robot_sn or "SYN-ROBOT-001"

        # Generate 2-4 tasks per day
        current_date = start_date
        task_id = 1

        task_names = [
            "Main Floor Cleaning",
            "Lobby Deep Clean",
            "Hallway Maintenance",
            "Conference Room Cleaning",
            "Cafeteria Cleaning"
        ]

        while current_date <= end_date:
            num_tasks = random.randint(2, 4)

            for i in range(num_tasks):
                # Random start time during the day
                hour = random.randint(6, 20)  # 6 AM to 8 PM
                start_time = current_date.replace(hour=hour, minute=0, second=0)

                # Task duration 30-120 minutes
                duration_seconds = random.randint(1800, 7200)
                end_time = start_time + timedelta(seconds=duration_seconds)

                # Area cleaned - 100-500 sqm
                plan_area = random.uniform(100, 500)
                progress = random.uniform(80, 100)  # 80-100% completion
                actual_area = plan_area * (progress / 100)

                # Efficiency: 0.5-1.5 m²/s
                efficiency = random.uniform(0.5, 1.5)

                # Power consumption: 0.5-2.0 kWh
                consumption = random.uniform(0.5, 2.0)

                # Water consumption: 500-5000 mL
                water_consumption = random.uniform(500, 5000)

                tasks.append(Task(
                    id=task_id,
                    robot_sn=robot_sn,
                    task_name=random.choice(task_names),
                    mode="Scrubbing",
                    sub_mode="Standard",
                    type="Deep Clean",
                    vacuum_speed="Medium",
                    vacuum_suction="High",
                    wash_speed="Medium",
                    wash_suction="High",
                    wash_water="Medium",
                    map_name="Building_Floor_1",
                    map_url="https://example.com/map.png",
                    actual_area=actual_area,
                    plan_area=plan_area,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration_seconds,
                    efficiency=efficiency,
                    remaining_time=0,
                    consumption=consumption,
                    water_consumption=water_consumption,
                    progress=progress,
                    status="Done"
                ))

                task_id += 1

            current_date += timedelta(days=1)

        return tasks