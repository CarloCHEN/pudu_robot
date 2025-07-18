#!/usr/bin/env python3
"""
Robot KPI Calculator - Main Entry Point

Calculate the three main KPIs:
1. Total Daily Cost
2. Hours Saved Daily
3. Return on Investment (ROI)
"""

import argparse
import logging
from datetime import datetime, timedelta
import json
import sys

from src.kpi import KPICalculator
from src.data import DataLoader


def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('robot_kpi_calculator.log')
        ]
    )


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Calculate Robot KPIs (Daily Cost, Hours Saved, ROI)'
    )

    # Date range arguments
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date (YYYY-MM-DD). Default: 7 days ago',
        default=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date (YYYY-MM-DD). Default: today',
        default=datetime.now().strftime('%Y-%m-%d')
    )

    # Robot filter
    parser.add_argument(
        '--robot-sn',
        type=str,
        help='Robot serial number to filter by (optional)',
        default=None
    )

    # Data source
    parser.add_argument(
        '--use-synthetic-data',
        action='store_true',
        help='Use synthetic data instead of database'
    )

    # Output format
    parser.add_argument(
        '--output-format',
        choices=['json', 'text', 'detailed'],
        default='text',
        help='Output format for results'
    )

    # Logging
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    return parser.parse_args()


def format_results(results: dict, format_type: str) -> str:
    """Format results based on output type"""
    if format_type == 'json':
        return json.dumps(results, indent=2, default=str)

    elif format_type == 'text':
        summary = results['summary']
        return f"""
Robot KPI Summary
================
Period: {results['period']['start']} to {results['period']['end']}
Tasks Analyzed: {results['tasks_analyzed']}

KPI Results:
-----------
1. Daily Cost: {summary['daily_cost']}
2. Hours Saved: {summary['hours_saved']}
3. ROI: {summary['roi']}
4. Payback Period: {summary['payback_period']}
"""

    else:  # detailed
        kpis = results['kpis']
        return f"""
Robot KPI Detailed Report
========================
Period: {results['period']['start']} to {results['period']['end']}
Robot SN: {results['robot_sn'] or 'All Robots'}
Tasks Analyzed: {results['tasks_analyzed']}

KPI 1: Total Daily Cost
----------------------
Total Daily Cost: ${kpis['daily_cost']['total_daily_cost']:.2f}
- Power Cost: ${kpis['daily_cost']['daily_power_cost']:.2f}
- Water Cost: ${kpis['daily_cost']['daily_water_cost']:.2f}
- Additional Costs: ${kpis['daily_cost']['additional_costs']:.2f}

Power Consumption: {kpis['daily_cost']['breakdown']['power']['consumption']:.2f} kWh
Water Consumption: {kpis['daily_cost']['breakdown']['water']['consumption']:.2f} L

KPI 2: Hours Saved Daily
-----------------------
Hours Saved: {kpis['hours_saved']['hours_saved_daily']:.2f} hours
Human Hours Needed: {kpis['hours_saved']['human_hours_needed']:.2f} hours
Robot Hours Needed: {kpis['hours_saved']['robot_hours_needed']:.2f} hours
Area Cleaned: {kpis['hours_saved']['area_cleaned']:.2f} m²
Efficiency Ratio: {kpis['hours_saved']['efficiency_ratio']:.2f}x

KPI 3: Return on Investment
---------------------------
ROI: {kpis['roi']['roi_percentage']:.1f}%
Total Investment: ${kpis['roi']['total_investment']:,.2f}
Cumulative Savings: ${kpis['roi']['cumulative_savings']:,.2f}
Daily Savings: ${kpis['roi']['daily_savings']:.2f}
Payback Period: {kpis['roi']['payback_period_years']:.1f} years

Investment Breakdown:
- Purchase Price: ${kpis['roi']['investment_breakdown']['purchase_price']:,.2f}
- Total Maintenance: ${kpis['roi']['investment_breakdown']['total_maintenance']:,.2f}
- Additional Costs: ${kpis['roi']['investment_breakdown']['additional_costs']:,.2f}
"""


def main():
    """Main entry point"""
    args = parse_arguments()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Robot KPI Calculator")

    try:
        # Parse dates
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

        # Initialize components
        logger.info("Initializing data loader...")
        data_loader = DataLoader()

        logger.info("Initializing KPI calculator...")
        calculator = KPICalculator(data_loader)

        # Calculate KPIs
        logger.info(f"Calculating KPIs from {start_date} to {end_date}")
        if args.robot_sn:
            logger.info(f"Filtering for robot: {args.robot_sn}")

        results = calculator.calculate_all_kpis(
            start_date=start_date,
            end_date=end_date,
            robot_sn=args.robot_sn,
            use_synthetic_data=args.use_synthetic_data
        )

        # Format and output results
        output = format_results(results, args.output_format)
        print(output)

        # Save results to file if JSON format
        if args.output_format == 'json':
            filename = f"kpi_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                f.write(output)
            logger.info(f"Results saved to {filename}")

        # Close connections
        data_loader.close()

        logger.info("KPI calculation completed successfully")

    except Exception as e:
        logger.error(f"Error calculating KPIs: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()