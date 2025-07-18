from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..rds import RDSTable
from ..models import CostSetting, AdditionalCost, Task
from .synthetic import SyntheticDataGenerator

logger = logging.getLogger(__name__)


class DataLoader:
    """Handles loading data from RDS or synthetic sources"""

    def __init__(self, config_path: str = "src/configs/database_config.yaml"):
        self.config_path = config_path
        self.synthetic_gen = SyntheticDataGenerator()
        self._init_tables()

    def _init_tables(self):
        """Initialize RDS table connections"""
        try:
            # Cost settings table
            self.cost_settings_table = RDSTable(
                connection_config="src/rds/credentials.yaml",
                database_name="foxx_irvine_office_test",
                table_name="mnt_robot_cost_setting",
                fields=None,
                primary_keys=['id']
            )

            # Additional costs table
            self.additional_costs_table = RDSTable(
                connection_config="src/rds/credentials.yaml",
                database_name="foxx_irvine_office_test",
                table_name="mnt_robot_additional_costs",
                fields=None,
                primary_keys=['id']
            )

            # Tasks table
            self.tasks_table = RDSTable(
                connection_config="src/rds/credentials.yaml",
                database_name="foxx_irvine_office_test",
                table_name="mnt_robots_task",
                fields=None,
                primary_keys=['id']
            )

            logger.info("Successfully initialized all RDS tables")

        except Exception as e:
            logger.error(f"Error initializing RDS tables: {e}")
            self.cost_settings_table = None
            self.additional_costs_table = None
            self.tasks_table = None

    def load_cost_settings(self, use_synthetic: bool = False) -> CostSetting:
        """Load cost settings from database or synthetic data"""
        if use_synthetic or self.cost_settings_table is None:
            logger.info("Using synthetic cost settings data")
            return self.synthetic_gen.generate_cost_setting()

        try:
            # Query the latest cost settings
            query = """
                SELECT * FROM mnt_robot_cost_setting
                ORDER BY update_time DESC
                LIMIT 1
            """
            result = self.cost_settings_table.query_data(query)

            if result:
                return CostSetting.from_dict(result[0])
            else:
                logger.warning("No cost settings found in database, using synthetic data")
                return self.synthetic_gen.generate_cost_setting()

        except Exception as e:
            logger.error(f"Error loading cost settings: {e}")
            return self.synthetic_gen.generate_cost_setting()

    def load_additional_costs(self,
                            start_date: datetime,
                            end_date: datetime,
                            use_synthetic: bool = False) -> List[AdditionalCost]:
        """Load additional costs from database or synthetic data"""
        if use_synthetic or self.additional_costs_table is None:
            logger.info("Using synthetic additional costs data")
            return self.synthetic_gen.generate_additional_costs(start_date, end_date)

        try:
            # Query additional costs within date range
            query = f"""
                SELECT * FROM mnt_robot_additional_costs
                WHERE cost_date BETWEEN '{start_date.strftime('%Y-%m-%d')}'
                AND '{end_date.strftime('%Y-%m-%d')}'
                ORDER BY cost_date
            """
            results = self.additional_costs_table.query_data(query)

            if results:
                return [AdditionalCost.from_dict(r) for r in results]
            else:
                logger.warning("No additional costs found in database, using synthetic data")
                return self.synthetic_gen.generate_additional_costs(start_date, end_date)

        except Exception as e:
            logger.error(f"Error loading additional costs: {e}")
            return self.synthetic_gen.generate_additional_costs(start_date, end_date)

    def load_tasks(self,
                   start_date: datetime,
                   end_date: datetime,
                   robot_sn: Optional[str] = None,
                   use_synthetic: bool = False) -> List[Task]:
        """Load tasks from database or synthetic data"""
        if use_synthetic or self.tasks_table is None:
            logger.info("Using synthetic tasks data")
            return self.synthetic_gen.generate_tasks(start_date, end_date, robot_sn)

        try:
            # Build query
            query = f"""
                SELECT * FROM mnt_robots_task
                WHERE start_time BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
            """

            if robot_sn:
                query += f" AND robot_sn = '{robot_sn}'"

            query += " ORDER BY start_time"

            results = self.tasks_table.query_data(query)

            if results:
                return [Task.from_dict(r) for r in results]
            else:
                logger.warning("No tasks found in database, using synthetic data")
                return self.synthetic_gen.generate_tasks(start_date, end_date, robot_sn)

        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            return self.synthetic_gen.generate_tasks(start_date, end_date, robot_sn)

    def close(self):
        """Close all database connections"""
        if self.cost_settings_table:
            self.cost_settings_table.close()
        if self.additional_costs_table:
            self.additional_costs_table.close()
        if self.tasks_table:
            self.tasks_table.close()