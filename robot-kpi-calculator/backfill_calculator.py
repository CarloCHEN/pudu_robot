#!/usr/bin/env python3
"""
Backfill Historical KPIs

This script calculates and saves KPIs for a historical date range.
Useful for initial population or fixing missing data.
"""

import argparse
import logging
import sys
from datetime import datetime, date, timedelta

from src.kpi import KPICalculator
from src.data import DataLoader
from src.data.saver import DataSaver


def main():
    """Main entry point for backfilling KPIs"""
    parser = argparse.ArgumentParser(
        description='Backfill historical robot KPIs'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='Start date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='End date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--robot-sn',
        type=str,
        help='Robot serial number (optional)',
        default=None
    )

    parser.add_argument(
        '--use-synthetic-data',
        action='store_true',
        help='Use synthetic data'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Parse dates
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()

        logger.info(f"Backfilling KPIs from {start_date} to {end_date}")

        # Initialize components
        data_loader = DataLoader()
        data_saver = DataSaver()
        calculator = KPICalculator(data_loader)
        calculator.data_saver = data_saver

        # Calculate for each day
        results = calculator.calculate_daily_kpis_batch(
            start_date=start_date,
            end_date=end_date,
            robot_sn=args.robot_sn,
            use_synthetic_data=args.use_synthetic_data,
            save_to_db=True
        )

        # Summary
        successful_days = sum(1 for r in results if r['results'].get('saved_to_db', False))
        total_days = len(results)

        logger.info(f"Backfill completed: {successful_days}/{total_days} days processed successfully")

        # Clean up
        data_loader.close()
        data_saver.close()

    except Exception as e:
        logger.error(f"Error in backfill: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()