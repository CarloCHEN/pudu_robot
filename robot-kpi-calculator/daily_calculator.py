#!/usr/bin/env python3
"""
Daily KPI Calculator - For scheduled/cron execution

This script is designed to be run daily to calculate and store KPIs
for the previous day or a specific date.
"""

import argparse
import logging
import sys
import os
from datetime import datetime, date, timedelta

from src.kpi import KPICalculator
from src.data import DataLoader
from src.data.saver import DataSaver


def setup_logging():
    """Setup logging for daily execution"""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = f"daily_kpi_{date.today().strftime('%Y%m%d')}.log"
    log_path = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path)
        ]
    )


def main():
    """Main entry point for daily KPI calculation"""
    parser = argparse.ArgumentParser(
        description='Calculate and save daily robot KPIs'
    )

    parser.add_argument(
        '--date',
        type=str,
        help='Date to calculate KPIs for (YYYY-MM-DD). Default: yesterday',
        default=(date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    )

    parser.add_argument(
        '--robot-sn',
        type=str,
        help='Robot serial number (optional, calculates for all if not specified)',
        default=None
    )

    parser.add_argument(
        '--use-synthetic-data',
        action='store_true',
        help='Use synthetic data'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Calculate but do not save to database'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Daily KPI Calculation")
    logger.info("=" * 60)

    try:
        # Parse date
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        logger.info(f"Target date: {target_date}")
        logger.info(f"Robot SN: {args.robot_sn or 'ALL ROBOTS'}")

        # Initialize components
        data_loader = DataLoader()
        data_saver = DataSaver()
        calculator = KPICalculator(data_loader)
        calculator.data_saver = data_saver  # Add saver to calculator

        # Calculate KPIs
        results = calculator.calculate_daily_kpis(
            target_date=target_date,
            robot_sn=args.robot_sn,
            use_synthetic_data=args.use_synthetic_data,
            save_to_db=not args.dry_run
        )

        # Log summary
        if results['tasks_analyzed'] > 0:
            summary = results['summary']
            logger.info("KPI Results:")
            logger.info(f"  - Daily Cost: {summary['daily_cost']}")
            logger.info(f"  - Hours Saved: {summary['hours_saved']}")
            logger.info(f"  - ROI: {summary['roi']}")

            if not args.dry_run:
                if results.get('saved_to_db', False):
                    logger.info("✅ Results saved to database successfully")
                else:
                    logger.error("❌ Failed to save results to database")
        else:
            logger.warning("No tasks found for the specified date")

        # Clean up
        data_loader.close()
        data_saver.close()

        logger.info("Daily KPI calculation completed successfully")

    except Exception as e:
        logger.error(f"Error in daily KPI calculation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()