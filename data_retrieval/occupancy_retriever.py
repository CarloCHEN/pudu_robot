from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from models.occupancy_models import (
    OccupancyData, OccupancyReading, OccupancyPattern,
    OccupancyForecast, OccupancyInsight, FlightData, Alert, Metric
)
from models.base_models import Location
from .base_retriever import BaseDataRetriever


class OccupancyDataRetriever(BaseDataRetriever):
    """Retrieves occupancy-related data"""

    def retrieve_data(self, locations: List[Location], start_date: datetime,
                     end_date: datetime, **kwargs) -> OccupancyData:
        """Retrieve occupancy data"""
        if self.use_synthetic_data:
            return self.generate_synthetic_data(locations, start_date, end_date, **kwargs)

        readings = self._get_occupancy_readings(locations, start_date, end_date)
        patterns = self._analyze_patterns(readings)
        forecasts = self._generate_forecasts(readings, patterns)
        alerts = self._get_occupancy_alerts(locations, start_date, end_date)
        insights = self._generate_insights(readings, patterns)
        flight_data = self._get_flight_data(start_date, end_date)
        metrics = self._calculate_metrics(readings, patterns, alerts)

        return OccupancyData(
            readings=readings,
            patterns=patterns,
            forecasts=forecasts,
            alerts=alerts,
            insights=insights,
            flight_data=flight_data,
            metrics=metrics
        )

    def _get_occupancy_readings(self, locations: List[Location],
                              start_date: datetime, end_date: datetime) -> List[OccupancyReading]:
        """Get occupancy sensor readings from ClickHouse"""
        readings = []

        sql = self.get_demo_sql(
            table_name="occupancy_readings",
            columns=["timestamp", "sensor_id", "people_count", "dwell_time_minutes"],
            start_date=start_date,
            end_date=end_date
        )

        # In real implementation, execute SQL
        # df = self.clickhouse_manager.get_historical_data(sql)

        return readings

    def generate_synthetic_data(self, locations: List[Location], start_date: datetime,
                               end_date: datetime, **kwargs) -> OccupancyData:
        """Generate synthetic occupancy data"""
        readings = []
        patterns = []
        insights = []
        alerts = []
        flight_data = []

        timestamps = self.generate_time_series(start_date, end_date, frequency='H')

        for location in locations:
            # Determine location capacity based on floor
            floor_num = int(location.floor.replace('Floor ', '')) if 'Floor' in location.floor else 1
            max_capacity = 100 + (floor_num * 20)  # Higher floors have more capacity

            # Generate occupancy pattern based on location type
            is_office = 'Tower' in location.building
            is_public = 'Main Campus' in location.building

            hourly_values = {}
            daily_values = {}

            for ts in timestamps:
                # Base occupancy pattern
                hour = ts.hour
                weekday = ts.weekday()

                if is_office:
                    # Office pattern: high during work hours on weekdays
                    if weekday < 5:  # Monday to Friday
                        if 9 <= hour <= 17:
                            base_occupancy = 0.7 + 0.2 * np.sin((hour - 9) * np.pi / 8)
                        elif 7 <= hour < 9 or 17 < hour <= 19:
                            base_occupancy = 0.3
                        else:
                            base_occupancy = 0.05
                    else:  # Weekend
                        base_occupancy = 0.1
                else:
                    # Public area pattern: varies throughout the day
                    if 6 <= hour <= 22:
                        base_occupancy = 0.4 + 0.3 * np.sin((hour - 6) * np.pi / 16)
                    else:
                        base_occupancy = 0.1

                # Add randomness
                occupancy_rate = base_occupancy + np.random.normal(0, 0.1)
                occupancy_rate = max(0, min(1, occupancy_rate))  # Clamp between 0 and 1

                people_count = int(max_capacity * occupancy_rate)
                dwell_time = 15 + np.random.exponential(20) if is_public else 240 + np.random.normal(0, 30)

                reading = OccupancyReading(
                    timestamp=ts,
                    value=float(people_count),
                    location=location,
                    people_count=people_count,
                    dwell_time_minutes=max(5, dwell_time),
                    sensor_id=f"OCC_{location.building}_{location.floor}"
                )
                readings.append(reading)

                # Track for patterns
                if hour not in hourly_values:
                    hourly_values[hour] = []
                hourly_values[hour].append(people_count)

                day_name = ts.strftime('%A')
                if day_name not in daily_values:
                    daily_values[day_name] = []
                daily_values[day_name].append(people_count)

                # Generate alerts for overcrowding
                if occupancy_rate > 0.9:
                    alert = Alert(
                        alert_id=f"OCC_ALT_{ts.timestamp()}_{location.building}_{location.floor}",
                        timestamp=ts,
                        location=location,
                        severity='warning' if occupancy_rate < 0.95 else 'critical',
                        category='occupancy',
                        message=f"High occupancy detected: {people_count} people ({occupancy_rate*100:.0f}% capacity)",
                        value=float(people_count),
                        threshold=float(max_capacity * 0.9),
                        resolved=np.random.random() > 0.3
                    )
                    alerts.append(alert)

            # Create pattern
            hourly_pattern = {hour: np.mean(values) for hour, values in hourly_values.items()}
            daily_pattern = {day: np.mean(values) for day, values in daily_values.items()}

            pattern = OccupancyPattern(
                location=location,
                hourly_pattern=hourly_pattern,
                daily_pattern=daily_pattern,
                peak_hours=sorted(hourly_pattern.keys(), key=hourly_pattern.get, reverse=True)[:3],
                low_hours=sorted(hourly_pattern.keys(), key=hourly_pattern.get)[:3],
                avg_dwell_time=np.mean([r.dwell_time_minutes for r in readings if r.location == location]),
                max_capacity=max_capacity
            )
            patterns.append(pattern)

            # Generate insights
            avg_occupancy = np.mean([r.people_count for r in readings if r.location == location])
            utilization_rate = avg_occupancy / max_capacity

            if utilization_rate > 0.8:
                insight = OccupancyInsight(
                    location=location,
                    insight_type='overcrowding',
                    description=f"Area frequently operates above 80% capacity during peak hours",
                    impact_score=85.0,
                    recommended_action="Consider expanding space or redistributing activities"
                )
                insights.append(insight)
            elif utilization_rate < 0.2:
                insight = OccupancyInsight(
                    location=location,
                    insight_type='underutilization',
                    description=f"Area utilization is below 20%, indicating potential for optimization",
                    impact_score=65.0,
                    recommended_action="Consider consolidating spaces or finding alternative uses"
                )
                insights.append(insight)

        # Generate flight data (for airport scenarios)
        if any('Terminal' in loc.building for loc in locations):
            for ts in pd.date_range(start_date, end_date, freq='H'):
                arrivals = np.random.poisson(200) if 6 <= ts.hour <= 22 else np.random.poisson(50)
                departures = np.random.poisson(180) if 6 <= ts.hour <= 22 else np.random.poisson(40)

                flight = FlightData(
                    timestamp=ts,
                    arrival_passengers=arrivals,
                    departure_passengers=departures,
                    total_passengers=arrivals + departures,
                    peak_hour_forecast=ts + timedelta(hours=2)
                )
                flight_data.append(flight)

        # Calculate metrics
        metrics = [
            Metric(
                name="Average Occupancy Rate",
                value=np.mean([r.people_count for r in readings]) / np.mean([p.max_capacity for p in patterns]) * 100,
                unit="%",
                trend="stable",
                change_percentage=2.3,
                period="last 30 days"
            ),
            Metric(
                name="Peak Occupancy",
                value=float(max(r.people_count for r in readings)),
                unit="people",
                trend="up",
                change_percentage=5.1,
                period="last 30 days"
            )
        ]

        return OccupancyData(
            readings=readings,
            patterns=patterns,
            forecasts=[],  # Simplified for demo
            alerts=alerts,
            insights=insights,
            flight_data=flight_data if flight_data else None,
            metrics=metrics
        )

    def _analyze_patterns(self, readings: List[OccupancyReading]) -> List[OccupancyPattern]:
        """Analyze occupancy patterns"""
        # Implementation would analyze actual data
        return []

    def _generate_forecasts(self, readings: List[OccupancyReading],
                          patterns: List[OccupancyPattern]) -> List[OccupancyForecast]:
        """Generate occupancy forecasts"""
        # Implementation would use time series forecasting
        return []

    def _generate_insights(self, readings: List[OccupancyReading],
                         patterns: List[OccupancyPattern]) -> List[OccupancyInsight]:
        """Generate occupancy insights"""
        # Implementation would analyze patterns and generate insights
        return []

    def _get_flight_data(self, start_date: datetime, end_date: datetime) -> List[FlightData]:
        """Get flight data from FlightAware integration"""
        # Implementation would connect to FlightAware API
        return []

    def _get_occupancy_alerts(self, locations: List[Location],
                            start_date: datetime, end_date: datetime) -> List[Alert]:
        """Get occupancy-related alerts"""
        # Implementation would query alerts from database
        return []

    def _calculate_metrics(self, readings: List[OccupancyReading],
                         patterns: List[OccupancyPattern],
                         alerts: List[Alert]) -> List[Metric]:
        """Calculate occupancy metrics"""
        # Implementation would calculate actual metrics
        return []