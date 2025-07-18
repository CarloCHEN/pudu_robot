from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import logging

from ..rds import RDSTable
from ..models.kpi_daily import KPIDaily

logger = logging.getLogger(__name__)


class DataSaver:
    """Handles saving calculated KPIs to database"""

    def __init__(self, config_path: str = "src/configs/database_config.yaml"):
        self.config_path = config_path
        self._init_tables()

    def _init_tables(self):
        """Initialize RDS table connections for KPI storage"""
        try:
            # Daily KPI table
            self.kpi_daily_table = RDSTable(
                connection_config="src/rds/credentials.yaml",
                database_name="foxx_irvine_office_test",
                table_name="mnt_robot_kpi_daily",
                fields=None,
                primary_keys=['calculation_date', 'robot_sn']
            )

            logger.info("Successfully initialized KPI storage tables")

        except Exception as e:
            logger.error(f"Error initializing KPI storage tables: {e}")
            self.kpi_daily_table = None

    def save_daily_kpi(self, kpi_daily: KPIDaily) -> bool:
        """
        Save or update daily KPI record

        Args:
            kpi_daily: KPIDaily object to save

        Returns:
            bool: True if successful, False otherwise
        """
        if self.kpi_daily_table is None:
            logger.error("KPI daily table not initialized")
            return False

        try:
            # Convert to dict and remove None values
            data = kpi_daily.to_dict()
            data = {k: v for k, v in data.items() if v is not None}

            # Remove id field for insert/update
            data.pop('id', None)

            # Insert or update using ON DUPLICATE KEY UPDATE
            self.kpi_daily_table.insert_data(data)

            logger.info(f"Successfully saved daily KPI for {kpi_daily.calculation_date} "
                       f"robot: {kpi_daily.robot_sn or 'ALL'}")
            return True

        except Exception as e:
            logger.error(f"Error saving daily KPI: {e}")
            return False

    def save_kpi_results(self,
                        kpi_results: Dict[str, Any],
                        calculation_date: date,
                        robot_sn: Optional[str] = None) -> bool:
        """
        Save KPI calculation results to database

        Args:
            kpi_results: Results from KPICalculator.calculate_all_kpis()
            calculation_date: Date for the KPI calculation
            robot_sn: Optional robot serial number

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create KPIDaily from results
            kpi_daily = KPIDaily.from_kpi_results(
                kpi_results,
                calculation_date,
                robot_sn
            )

            # Save to database
            return self.save_daily_kpi(kpi_daily)

        except Exception as e:
            logger.error(f"Error converting and saving KPI results: {e}")
            return False

    def get_historical_kpis(self,
                           start_date: date,
                           end_date: date,
                           robot_sn: Optional[str] = None) -> List[KPIDaily]:
        """
        Retrieve historical KPI data

        Args:
            start_date: Start date
            end_date: End date
            robot_sn: Optional robot filter

        Returns:
            List of KPIDaily objects
        """
        if self.kpi_daily_table is None:
            logger.error("KPI daily table not initialized")
            return []

        try:
            query = f"""
                SELECT * FROM mnt_robot_kpi_daily
                WHERE calculation_date BETWEEN '{start_date}' AND '{end_date}'
            """

            if robot_sn:
                query += f" AND robot_sn = '{robot_sn}'"
            else:
                query += " AND robot_sn IS NULL"

            query += " ORDER BY calculation_date"

            results = self.kpi_daily_table.query_data(query)

            return [KPIDaily.from_dict(r) for r in results]

        except Exception as e:
            logger.error(f"Error retrieving historical KPIs: {e}")
            return []

    def close(self):
        """Close database connections"""
        if self.kpi_daily_table:
            self.kpi_daily_table.close()