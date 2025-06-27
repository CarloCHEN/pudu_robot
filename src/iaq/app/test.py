import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))
sys.path.append('/home/ec2-user/iaq_score/src')

from iaq.model import AirQualityCalculator
from iaq.data.environmentalMonitor import EnvironmentalMonitor, EnvironmentalDataGenerator


def create_environmental_monitors(zones_config: list) -> dict:
    """
    Create environmental monitors for different zones.

    Parameters:
    - zones_config: List of (zone_name, space_type) tuples

    Returns:
    - Dictionary of zone_name: EnvironmentalMonitor
    """
    monitors = {}

    for zone_name, space_type in zones_config:
        # Create monitor ID from zone name
        monitor_id = ''.join([c.upper() for c in zone_name if c.isalnum()])[:8]

        # Map space type names to monitor space types
        space_type_mapping = {
            "Office/Cubicle": "office",
            "Conference/Meeting Rooms": "conference",
            "Restrooms": "restroom",
            "Office Circulation/Walkways": "circulation",
            "Corridors/Common Areas": "circulation",
            "Cafeteria/Dining Area": "cafeteria"
        }

        monitor_space_type = space_type_mapping.get(space_type, "office")

        # Create monitor
        monitor = EnvironmentalMonitor(
            monitor_id=monitor_id,
            location=zone_name,
            space_type=monitor_space_type
        )

        # Generate synthetic data
        synthetic_data = EnvironmentalDataGenerator.generate_synthetic_data(
            space_type=monitor_space_type,
            hours=24,
            interval_minutes=15
        )

        # Set data
        monitor.set_data(synthetic_data)
        monitors[zone_name] = monitor

    return monitors


def main():
    """Main function to demonstrate the IAQ scoring system with EnvironmentalMonitor."""

    print("=== IAQ Scoring System with Environmental Monitors ===\n")

    # Initialize the air quality calculator
    try:
        calculator = AirQualityCalculator()
        print(f"✓ Initialized calculator with space types: {calculator.list_space_types()}\n")
    except Exception as e:
        print(f"✗ Error initializing calculator: {e}")
        return

    # Define zones to monitor
    zones_config = [
        ("Office Zone A", "Office/Cubicle"),
        ("Conference Room 1", "Conference/Meeting Rooms"),
        ("Restroom Floor 1", "Restrooms")
    ]

    # Create environmental monitors
    print("Creating environmental monitors...")
    monitors = create_environmental_monitors(zones_config)

    # Display monitor information and add zones to calculator
    for zone_name, monitor in monitors.items():
        print(f"\n--- {monitor.location} ---")
        print(f"Monitor ID: {monitor.monitor_id}")
        print(f"Space Type: {monitor.space_type}")
        print(f"Available Parameters: {monitor.get_available_parameters()}")

        missing = monitor.get_missing_parameters()
        if missing:
            print(f"Missing Parameters: {missing}")

        # Get latest readings for IAQ scoring
        latest_readings = monitor.get_latest_readings()
        print(f"Latest Readings ({len(latest_readings)} parameters):")
        for param, value in latest_readings.items():
            print(f"  {param}: {value:.3f}")

        # Add zone to calculator
        try:
            # Find matching space type name for calculator
            space_type_name = None
            for calc_space_type in calculator.list_space_types():
                if any(keyword in calc_space_type.lower() for keyword in [
                    zone_name.split()[0].lower(),
                    monitor.space_type
                ]):
                    space_type_name = calc_space_type
                    break

            # If no match found, try direct mapping
            if space_type_name is None:
                space_type_mapping = {
                    "office": "Office/Cubicle",
                    "conference": "Conference/Meeting Rooms",
                    "restroom": "Restrooms"
                }
                space_type_name = space_type_mapping.get(monitor.space_type)

            if space_type_name:
                calculator.add_zone(zone_name, space_type_name, latest_readings)
                print(f"✓ Added to calculator as '{space_type_name}'")
            else:
                print(f"✗ Could not find matching space type in calculator")
                print(f"  Available: {calculator.list_space_types()}")

        except Exception as e:
            print(f"✗ Error adding zone to calculator: {e}")

    # Calculate and display scores
    print("\n" + "="*60)
    print("SCORING RESULTS")
    print("="*60)

    if not calculator.zones:
        print("No zones were successfully added to calculator")
        return

    # Individual zone scores
    print("\n--- Zone Scores ---")
    for zone in calculator.zones:
        score = calculator.calculate_zone_score(zone)

        # Determine status
        if score >= 90:
            status = "Excellent"
        elif score >= 80:
            status = "Good"
        elif score >= 60:
            status = "Moderate"
        elif score >= 40:
            status = "Poor"
        else:
            status = "Very Poor"

        print(f"\n{zone.name}: {score:.1f} ({status})")

        # Get zone details
        details = calculator.get_zone_details(zone.name)
        print(f"  Space Type: {details['space_type']}")
        print(f"  Square Footage: {details['square_footage']:,}")

        # Show parameter contributions to score
        weights = details['weights']
        sensor_data = details['sensor_data']
        print("  Parameter Contributions:")

        total_weighted_score = 0
        total_weight = 0

        for param, weight in weights.items():
            if param in sensor_data:
                param_score = calculator.calculate_parameter_score(
                    zone.space_type, param, sensor_data[param]
                )
                contribution = param_score * weight
                total_weighted_score += contribution
                total_weight += weight
                print(f"    {param:12s}: {sensor_data[param]:8.3f} → {param_score:5.1f} × {weight:5.1%} = {contribution:5.1f}")

        print(f"    {'Total':12s}: {total_weighted_score:41.1f}")

    # Overall building score
    building_score = calculator.calculate_building_score()
    if building_score >= 90:
        building_status = "Excellent"
    elif building_score >= 80:
        building_status = "Good"
    elif building_score >= 60:
        building_status = "Moderate"
    elif building_score >= 40:
        building_status = "Poor"
    else:
        building_status = "Very Poor"

    print(f"\n--- Building Summary ---")
    print(f"Overall Building Score: {building_score:.1f} ({building_status})")
    print(f"Total Zones: {len(calculator.zones)}")

    # Calculate square footage weighted breakdown
    total_sqft = sum(zone.space_type.square_footage for zone in calculator.zones)
    print(f"Total Square Footage: {total_sqft:,}")

    print("\nZone Contributions to Building Score:")
    for zone in calculator.zones:
        zone_score = calculator.calculate_zone_score(zone)
        zone_sqft = zone.space_type.square_footage
        weight_pct = (zone_sqft / total_sqft) * 100
        contribution = (zone_score * zone_sqft) / total_sqft
        print(f"  {zone.name:20s}: {zone_score:5.1f} × {weight_pct:5.1f}% = {contribution:5.1f}")

    # Show some sample time series data
    print("\n--- Sample Time Series Data ---")
    if monitors:
        first_zone = list(monitors.keys())[0]
        first_monitor = monitors[first_zone]

        print(f"Last 5 readings from {first_monitor.location}:")

        # Get recent data for a few key parameters
        key_params = ['PM2.5', 'CO2', 'Temperature']
        available_params = [p for p in key_params if p in first_monitor.get_available_parameters()]

        if available_params and first_monitor.data is not None:
            recent_data = first_monitor.data.tail(5)
            print(f"{'Time':20s} " + " ".join([f"{p:>10s}" for p in available_params]))
            print("-" * (20 + len(available_params) * 11))

            for _, row in recent_data.iterrows():
                time_str = row['time'].strftime('%Y-%m-%d %H:%M')
                param_strs = [f"{row[p]:10.3f}" for p in available_params]
                print(f"{time_str:20s} " + " ".join(param_strs))

        # Show data summary for first monitor
        print(f"\n--- Data Summary for {first_monitor.location} ---")
        summary = first_monitor.get_data_summary()
        data_range = summary['data_range']
        print(f"Data Period: {data_range['start'].strftime('%Y-%m-%d %H:%M')} to {data_range['end'].strftime('%Y-%m-%d %H:%M')}")
        print(f"Total Records: {data_range['records']}")

        print("\nParameter Statistics:")
        for param, stats in summary['parameters'].items():
            print(f"  {param:12s}: Latest={stats['latest']:7.3f}, "
                  f"Mean={stats['mean']:7.3f}, "
                  f"Range=[{stats['min']:6.3f}, {stats['max']:6.3f}]")


if __name__ == "__main__":
    main()