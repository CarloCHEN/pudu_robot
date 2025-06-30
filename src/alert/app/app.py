import logging
from typing import Dict, Any, List
import concurrent.futures
from multiprocessing import Pool, cpu_count
from datetime import datetime
import pandas as pd

from alert.rds import RDSManager
from alert.clickhouse import ClickHouseManager
from alert.data_source import DataSourceFactory
from .alert_pipeline import AlertPipeline

logger = logging.getLogger(__name__)
alert_setting_table_name = "mnt_sensor_alarm_setting"
alert_table_name = "mnt_sensor_alarm"


class AlertApp:
    """
    Optimized alert application with batch processing and parallel execution.
    Processes sensor/score data to generate alerts using configurable thresholds and rules.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rds_manager = RDSManager(config['database']['rds']['config_dir'])
        self.ch_manager = ClickHouseManager(config['database']['clickhouse']['config_dir'])

        # Optimization settings
        self.batch_size = config.get('optimization', {}).get('batch_size', 50)
        self.max_workers = config.get('optimization', {}).get('max_workers', min(8, cpu_count()))
        self.use_multiprocessing = config.get('optimization', {}).get('use_multiprocessing', False)
        self.batch_db_operations = config.get('optimization', {}).get('batch_db_operations', True)

    def run(self):
        """
        Executes the optimized alert workflow with batching and parallel processing.
        """
        logger.info("Starting optimized alert service run.")

        # 1. Get all alert targets (sensors/scores with alert enabled)
        targets = self.rds_manager.get_alert_targets()
        if not targets:
            logger.warning("No alert targets found in RDS. Exiting.")
            return

        logger.info(f"Found {len(targets)} alert targets.")

        # 2. Group targets for batch processing
        target_batches = self._create_target_batches(targets)
        logger.info(f"Created {len(target_batches)} batches with max size {self.batch_size}")

        # 3. Process batches
        all_alert_results = []
        all_next_timestamps = {}

        for i, batch in enumerate(target_batches):
            logger.info(f"Processing batch {i+1}/{len(target_batches)} with {len(batch)} targets")

            batch_alert_results, batch_next_timestamps = self._process_batch(batch)

            if batch_alert_results:
                all_alert_results.extend(batch_alert_results)

            # Collect next timestamps for updating alert settings
            all_next_timestamps.update(batch_next_timestamps)

        # 4. Batch save all results at once
        if self.batch_db_operations:
            self._batch_save_results(all_alert_results, all_next_timestamps)

        logger.info(f"Alert service completed. Generated {len(all_alert_results)} alerts.")

    def _create_target_batches(self, targets: List[Dict]) -> List[List[Dict]]:
        """Create batches of targets for processing."""
        batches = []
        for i in range(0, len(targets), self.batch_size):
            batch = targets[i:i + self.batch_size]
            batches.append(batch)
        return batches

    def _process_batch(self, batch: List[Dict]) -> tuple:
        """Process a batch of targets using parallel execution."""
        if self.use_multiprocessing:
            return self._process_batch_multiprocessing(batch)
        else:
            return self._process_batch_threading(batch)

    def _process_batch_threading(self, batch: List[Dict]) -> tuple:
        """Process batch using ThreadPoolExecutor (good for I/O bound tasks)."""
        alert_results = []
        next_timestamps = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_target = {
                executor.submit(self._process_single_target, target_config): target_config
                for target_config in batch
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_target):
                target_config = future_to_target[future]
                try:
                    alerts, next_timestamp = future.result(timeout=300)  # 5 minute timeout
                    if alerts:
                        alert_results.extend(alerts)
                        logger.info(f"Generated {len(alerts)} alerts for {target_config.get('sensor_id', 'unknown')}")

                    # Store next timestamp for this target
                    target_key = f"{target_config.get('sensor_id')}_{target_config.get('data_type')}"
                    next_timestamps[target_key] = {
                        'sensor_id': target_config.get('sensor_id'),
                        'data_type': target_config.get('data_type'),
                        'next_timestamp': next_timestamp
                    }

                except concurrent.futures.TimeoutError:
                    logger.error(f"Timeout processing target: {target_config}")
                except Exception as e:
                    logger.error(f"Error processing target {target_config}: {e}")

        return alert_results, next_timestamps

    def _process_batch_multiprocessing(self, batch: List[Dict]) -> tuple:
        """Process batch using multiprocessing (good for CPU bound tasks)."""
        alert_results = []
        next_timestamps = {}

        # Prepare arguments for multiprocessing
        process_args = [
            (target_config, self.config) for target_config in batch
        ]

        with Pool(processes=self.max_workers) as pool:
            try:
                results = pool.starmap(process_target_standalone, process_args)

                for alerts, next_timestamp, target_info in results:
                    if alerts:
                        alert_results.extend(alerts)
                        logger.info(f"Generated {len(alerts)} alerts for {target_info.get('sensor_id', 'unknown')}")

                    # Store next timestamp
                    target_key = f"{target_info.get('sensor_id')}_{target_info.get('data_type')}"
                    next_timestamps[target_key] = {
                        'sensor_id': target_info.get('sensor_id'),
                        'data_type': target_info.get('data_type'),
                        'next_timestamp': next_timestamp
                    }

            except Exception as e:
                logger.error(f"Error in multiprocessing batch: {e}")

        return alert_results, next_timestamps

    def _process_single_target(self, target_config: Dict) -> tuple:
        """Process a single target configuration."""
        try:
            # Create data source
            data_source = DataSourceFactory.create_data_source(target_config)
            if not data_source:
                logger.error(f"Could not create data source for config: {target_config}")
                return [], None

            # Extract alert parameters from target config
            alert_params = self._extract_alert_params(target_config)

            # Create alert pipeline
            pipeline = AlertPipeline(data_source, alert_params)

            # Use a separate ClickHouse connection for thread safety
            ch_manager = ClickHouseManager(self.config['database']['clickhouse']['config_dir'])

            # Run pipeline
            alerts, next_timestamp = pipeline.run(ch_manager)
            ch_manager.close()

            return alerts, next_timestamp

        except Exception as e:
            logger.error(f"Error processing target {target_config}: {e}")
            return [], None

    def _extract_alert_params(self, target_config: Dict) -> Dict[str, Any]:
        """Extract alert parameters from target configuration."""
        alert_params = {
            'lower_threshold': target_config.get('lower_threshold'),
            'upper_threshold': target_config.get('upper_threshold'),
            'duration': target_config.get('duration'),
            'duration_unit': target_config.get('duration_unit'),
            'frequency': target_config.get('frequency'),
            'time_window': target_config.get('time_window'),
            'time_window_unit': target_config.get('time_window_unit'),
        }

        # Validate required parameters
        required_params = ['lower_threshold', 'upper_threshold', 'duration', 'duration_unit',
                          'frequency', 'time_window', 'time_window_unit']
        missing_params = [param for param in required_params if alert_params.get(param) is None]

        if missing_params:
            raise ValueError(f"Missing alert parameters for {target_config.get('sensor_id')}: {missing_params}")

        return alert_params

    def _batch_save_results(self, alert_results: List[Dict], next_timestamps: Dict):
        """Save all results in batches to improve database performance."""

        # 1. Save alerts
        if alert_results:
            logger.info(f"Batch saving {len(alert_results)} alert results")
            chunk_size = 1000
            for i in range(0, len(alert_results), chunk_size):
                chunk = alert_results[i:i + chunk_size]
                try:
                    print('saving alert results: ', chunk[0])
                    # self.rds_manager.save_alert_results(
                    #     alert_table_name, chunk, ['sensor_id', 'data_type', 'end_timestamp']
                    # )
                    logger.info(f"Saved alert chunk {i//chunk_size + 1} ({len(chunk)} alerts)")
                except Exception as e:
                    logger.error(f"Error saving alert results chunk {i//chunk_size + 1}: {e}")

        # 2. Update next monitoring timestamps
        if next_timestamps:
            logger.info(f"Updating {len(next_timestamps)} next monitoring timestamps")
            for target_key, timestamp_info in next_timestamps.items():
                try:
                    if timestamp_info['next_timestamp']:
                        print('updating timestamp: ', timestamp_info)
                        # self.rds_manager.update_alert_start_timestamp(
                        #     alert_setting_table_name,
                        #     timestamp_info['sensor_id'],
                        #     timestamp_info['data_type'],
                        #     timestamp_info['next_timestamp']
                        # )
                except Exception as e:
                    logger.error(f"Error updating timestamp for {target_key}: {e}")

    def cleanup(self):
        """Closes all database connections."""
        self.rds_manager.close()
        self.ch_manager.close()


def process_target_standalone(target_config: Dict, config: Dict) -> tuple:
    """
    Standalone function for multiprocessing.
    Each process gets its own database connections.
    """
    try:
        # Create fresh connections for this process
        ch_manager = ClickHouseManager(config['database']['clickhouse']['config_dir'])

        # Create data source
        data_source = DataSourceFactory.create_data_source(target_config)
        if not data_source:
            return [], None, target_config

        # Extract alert parameters
        alert_params = {
            'lower_threshold': target_config.get('lower_threshold'),
            'upper_threshold': target_config.get('upper_threshold'),
            'duration': target_config.get('duration'),
            'duration_unit': target_config.get('duration_unit'),
            'frequency': target_config.get('frequency'),
            'time_window': target_config.get('time_window'),
            'time_window_unit': target_config.get('time_window_unit'),
        }

        # Create and run pipeline
        pipeline = AlertPipeline(data_source, alert_params)
        alerts, next_timestamp = pipeline.run(ch_manager)

        # Close connections
        ch_manager.close()

        return alerts, next_timestamp, target_config

    except Exception as e:
        logger.error(f"Error in standalone process for target {target_config}: {e}")
        return [], None, target_config