import logging
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from alert.data_source.base_data_source import BaseDataSource
from alert.clickhouse.clickhouse_manager import ClickHouseManager
from alert.generator import AlertGenerator

logger = logging.getLogger(__name__)


class AlertPipeline:
    """
    Pipeline for processing alert generation on sensor/score data.
    Handles data fetching, violation detection, and alert generation.
    """

    def __init__(self, data_source: BaseDataSource, alert_params: Dict[str, Any]):
        """
        Initialize the alert pipeline.

        Args:
            data_source: Data source object containing sensor/score information
            alert_params: Dictionary containing alert configuration parameters
        """
        self.data_source = data_source
        self.alert_params = alert_params

        # Validate alert parameters
        self._validate_alert_params()

    def _validate_alert_params(self):
        """Validate that required alert parameters are present."""
        required_params = [
            'lower_threshold', 'upper_threshold', 'duration', 'duration_unit',
            'frequency', 'time_window', 'time_window_unit'
        ]

        missing_params = [param for param in required_params if param not in self.alert_params]
        if missing_params:
            raise ValueError(f"Missing required alert parameters: {missing_params}")

    def run(self, ch_manager: ClickHouseManager) -> Tuple[List[Dict], Optional[datetime]]:
        """
        Execute the alert pipeline.

        Args:
            ch_manager: ClickHouse manager for data fetching

        Returns:
            Tuple containing:
            - List of generated alerts
            - Next monitoring timestamp for this data source
        """
        try:
            logger.info(f"Starting alert pipeline for {self.data_source.sensor_id} - {self.data_source.data_type}")

            # 1. Fetch historical data from ClickHouse
            self._fetch_data(ch_manager)

            # 2. Check if we have sufficient data
            if self.data_source.data.empty:
                logger.warning(f"No data available for {self.data_source.sensor_id} - {self.data_source.data_type}")
                return [], None

            logger.info(f"Fetched {len(self.data_source.data)} records for alert analysis")

            # 3. Calculate statistical metrics needed for severity assessment
            self._calculate_statistical_metrics()

            # 4. Create alert generator
            alert_generator = self._create_alert_generator()

            # 5. Detect violations
            raw_violations = alert_generator.detect_violations()
            logger.info(f"Detected {len(raw_violations)} raw violations")

            # 6. Generate alarms from violations
            violations, alarms = alert_generator.raise_alarms(raw_violations)
            logger.info(f"Generated {len(alarms)} alarms from {len(violations)} qualified violations")

            # 7. Find next monitoring start point
            next_start_time = alert_generator.find_next_start_point(raw_violations, violations, alarms)

            # 8. Generate final alerts
            alerts = list(alert_generator.make_alert(alarms))
            logger.info(f"Created {len(alerts)} final alerts")

            # 9. Log alert summary
            if alerts:
                self._log_alert_summary(alerts)

            return alerts, next_start_time

        except Exception as e:
            logger.error(f"Error in alert pipeline for {self.data_source.sensor_id}: {e}")
            raise

    def _fetch_data(self, ch_manager: ClickHouseManager):
        """Fetch historical data using the data source."""
        try:
            # Use the data source's method to get historical data
            self.data_source.get_historical_data(ch_manager, sensorID_col='devEUI')

        except Exception as e:
            logger.error(f"Error fetching data for {self.data_source.sensor_id}: {e}")
            raise

        #TODO: get industry standard from rds
        # set industry standard
        self.data_source.industry_standard = self.data_source.config.get('industry_standard', None)

    def _calculate_statistical_metrics(self):
        """Calculate statistical metrics needed for alert severity assessment."""
        try:
            data_column = self.data_source.data_type
            values = self.data_source.data[data_column].dropna()

            if values.empty:
                logger.warning(f"No valid values found for statistical calculation")
                # Set default values
                self.data_source.percentile_10th = 0
                self.data_source.percentile_25th = 0
                self.data_source.percentile_50th = 0
                self.data_source.percentile_75th = 0
                self.data_source.percentile_90th = 0
                return

            # Calculate percentiles
            self.data_source.percentile_10th = values.quantile(0.10)
            self.data_source.percentile_25th = values.quantile(0.25)
            self.data_source.percentile_50th = values.quantile(0.50)
            self.data_source.percentile_75th = values.quantile(0.75)
            self.data_source.percentile_90th = values.quantile(0.90)

            logger.debug(f"Statistical metrics calculated for {self.data_source.sensor_id}")
            logger.debug(f"  P10: {self.data_source.percentile_10th:.2f}")
            logger.debug(f"  P25: {self.data_source.percentile_25th:.2f}")
            logger.debug(f"  P50: {self.data_source.percentile_50th:.2f}")
            logger.debug(f"  P75: {self.data_source.percentile_75th:.2f}")
            logger.debug(f"  P90: {self.data_source.percentile_90th:.2f}")

        except Exception as e:
            logger.error(f"Error calculating statistical metrics: {e}")
            raise

    def _create_alert_generator(self) -> AlertGenerator:
        """Create and configure the alert generator."""
        try:
            alert_generator = AlertGenerator(
                data_source=self.data_source,
                threshold=[self.alert_params['lower_threshold'], self.alert_params['upper_threshold']],
                duration=self.alert_params['duration'],
                duration_unit=self.alert_params['duration_unit'],
                frequency=self.alert_params['frequency'],
                time_window=self.alert_params['time_window'],
                time_window_unit=self.alert_params['time_window_unit']
            )

            logger.debug(f"Alert generator created with thresholds: "
                        f"[{self.alert_params['lower_threshold']}, {self.alert_params['upper_threshold']}]")
            logger.debug(f"Duration: {self.alert_params['duration']} {self.alert_params['duration_unit']}")
            logger.debug(f"Frequency: {self.alert_params['frequency']} violations")
            logger.debug(f"Time window: {self.alert_params['time_window']} {self.alert_params['time_window_unit']}")

            return alert_generator

        except Exception as e:
            logger.error(f"Error creating alert generator: {e}")
            raise

    def _log_alert_summary(self, alerts: List[Dict]):
        """Log a summary of generated alerts."""
        if not alerts:
            return

        # Count alerts by type and severity
        alert_types = {}
        severities = {}

        for alert in alerts:
            alert_type = alert.get('alarm_type', 'unknown')
            severity = alert.get('severity', 'unknown')

            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
            severities[severity] = severities.get(severity, 0) + 1

        logger.info(f"Alert Summary for {self.data_source.sensor_id}:")
        logger.info(f"  Total alerts: {len(alerts)}")
        logger.info(f"  By type: {alert_types}")
        logger.info(f"  By severity: {severities}")

        # Log time range
        start_times = [alert['start_timestamp'] for alert in alerts]
        end_times = [alert['end_timestamp'] for alert in alerts]

        if start_times and end_times:
            earliest = min(start_times)
            latest = max(end_times)
            logger.info(f"  Time range: {earliest} to {latest}")


class AlertPipelineFactory:
    """Factory for creating alert pipelines with different configurations."""

    @staticmethod
    def create_sensor_alert_pipeline(data_source: BaseDataSource,
                                   alert_config: Dict[str, Any]) -> AlertPipeline:
        """
        Create an alert pipeline for sensor data.

        Args:
            data_source: Sensor data source
            alert_config: Alert configuration parameters

        Returns:
            Configured AlertPipeline instance
        """
        # Add sensor-specific alert parameters if needed
        sensor_alert_params = {
            **alert_config,
            # Add any sensor-specific defaults here
        }

        return AlertPipeline(data_source, sensor_alert_params)

    @staticmethod
    def create_score_alert_pipeline(data_source: BaseDataSource,
                                  alert_config: Dict[str, Any]) -> AlertPipeline:
        """
        Create an alert pipeline for score data.

        Args:
            data_source: Score data source
            alert_config: Alert configuration parameters

        Returns:
            Configured AlertPipeline instance
        """
        # Add score-specific alert parameters if needed
        score_alert_params = {
            **alert_config,
            # Add any score-specific defaults here
        }

        return AlertPipeline(data_source, score_alert_params)