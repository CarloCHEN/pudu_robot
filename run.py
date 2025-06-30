#!/usr/bin/env python3
"""
Alert Service - Main Entry Point

A high-performance alert generation service that processes sensor/score data
to detect violations and generate alerts using configurable thresholds.
"""

import yaml
import os
import logging
import sys
import time
from datetime import datetime

# Add the src directory to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.alert.app.app import AlertApp


def setup_logging(level=logging.INFO):
    """Configures the root logger."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )


def load_config(config_path: str) -> dict:
    """Loads the main YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found at: {config_path}")
        raise
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        raise


def adjust_paths_for_local_development(config: dict) -> dict:
    """Adjust configuration paths for local development environment."""
    # Prepend 'src/' to database config paths for local development
    config['database']['rds']['config_dir'] = 'src/' + config['database']['rds']['config_dir']
    config['database']['clickhouse']['config_dir'] = 'src/' + config['database']['clickhouse']['config_dir']
    return config


def main():
    """
    Main entry point for the alert service application.
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    # The config path is relative to the project root
    config_path = os.path.join(os.path.dirname(__file__), 'src', 'alert', 'config', 'config.yaml')
    logger.info(f"Loading configuration from {config_path}")

    try:
        # Load configuration
        config = load_config(config_path)

        # Adjust paths for local development
        config = adjust_paths_for_local_development(config)

        # Log configuration summary
        logger.info("Alert Service Configuration:")
        logger.info(f"  Batch size: {config.get('optimization', {}).get('batch_size', 50)}")
        logger.info(f"  Max workers: {config.get('optimization', {}).get('max_workers', 8)}")
        logger.info(f"  Use multiprocessing: {config.get('optimization', {}).get('use_multiprocessing', False)}")

        # Start timing
        start_time = time.time()

        # Initialize and run the alert application
        app = None
        try:
            logger.info("🚀 Starting Alert Service...")
            app = AlertApp(config)
            app.run()

            end_time = time.time()
            duration = end_time - start_time

            logger.info("✅ Alert service completed successfully!")
            logger.info(f"⏱️  Total processing time: {duration:.2f} seconds")

        except KeyboardInterrupt:
            logger.info("🛑 Alert service interrupted by user")
        except Exception as e:
            logger.error(f"❌ Alert service failed: {e}", exc_info=True)
            raise
        finally:
            if app:
                logger.info("🧹 Cleaning up resources...")
                app.cleanup()

    except Exception as e:
        logger.critical(f"💥 Critical error in alert service: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())