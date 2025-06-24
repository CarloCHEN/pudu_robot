from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from models.environment_models import (
    EnvironmentData, EnvironmentReading, EnvironmentScore,
    EnvironmentPattern, EnvironmentForecast, Alert, Metric
)
from models.base_models import Location
from .base_retriever import BaseDataRetriever


class EnvironmentDataRetriever(BaseDataRetriever):
    """Retrieves environment-related data"""

    SENSOR_TYPES = {
        'temperature': {'unit': '°C', 'normal_range': (20, 25), 'critical_range': (15, 30)},
        'humidity': {'unit': '%', 'normal_range': (40, 60), 'critical_range': (30, 70)},
        'co2': {'unit': 'ppm', 'normal_range': (400, 800), 'critical_range': (350, 1000)},
        'pm2.5': {'unit': 'μg/m³', 'normal_range': (0, 25), 'critical_range': (0, 50)},
        'pm10': {'unit': 'μg/m³', 'normal_range': (0, 50), 'critical_range': (0, 100)},
        'tvoc': {'unit': 'ppb', 'normal_range': (0, 500), 'critical_range': (0, 1000)},
        'nh3': {'unit': 'ppm', 'normal_range': (0, 25), 'critical_range': (0, 50)}
    }

    def retrieve_data(self, locations: List[Location], start_date: datetime,
                     end_date: datetime, **kwargs) -> EnvironmentData:
        """Retrieve environment data"""
        if self.use_synthetic_data:
            return self.generate_synthetic_data(locations, start_date, end_date, **kwargs)

        readings = self._get_sensor_readings(locations, start_date, end_date)
        scores = self._get_environment_scores(locations, start_date, end_date)
        alerts = self._get_environment_alerts(locations, start_date, end_date)
        patterns = self._analyze_patterns(readings)
        forecasts = self._generate_forecasts(readings, patterns)
        metrics = self._calculate_metrics(readings, scores, alerts)

        return EnvironmentData(
            readings=readings,
            scores=scores,
            alerts=alerts,
            patterns=patterns,
            forecasts=forecasts,
            metrics=metrics
        )

    def _get_sensor_readings(self, locations: List[Location],
                           start_date: datetime, end_date: datetime) -> List[EnvironmentReading]:
        """Get sensor readings from ClickHouse"""
        readings = []

        for location in locations:
            sql = self.get_demo_sql(
                table_name="sensor_readings",
                columns=["timestamp", "sensor_id", "sensor_type", "value", "unit"],
                start_date=start_date,
                end_date=end_date,
                location_filter={
                    "country": location.country,
                    "city": location.city,
                    "building": location.building,
                    "floor": location.floor
                }
            )

            # In real implementation, execute SQL
            # df = self.clickhouse_manager.get_historical_data(sql)

        return readings

    def _get_environment_scores(self, locations: List[Location],
                              start_date: datetime, end_date: datetime) -> List[EnvironmentScore]:
        """Get calculated environment scores"""
        scores = []

        sql = self.get_demo_sql(
            table_name="environment_scores",
            columns=["timestamp", "score_type", "score_value", "components"],
            start_date=start_date,
            end_date=end_date
        )

        return scores

    def _get_environment_alerts(self, locations: List[Location],
                              start_date: datetime, end_date: datetime) -> List[Alert]:
        """Get environment-related alerts"""
        alerts = []

        sql = """
        SELECT alert_id, timestamp, location_id, severity, category,
               message, value, threshold, resolved
        FROM environment_alerts
        WHERE timestamp >= :start_date AND timestamp <= :end_date
        ORDER BY timestamp DESC
        """

        return alerts

    def generate_synthetic_data(self, locations: List[Location], start_date: datetime,
                               end_date: datetime, **kwargs) -> EnvironmentData:
        """Generate synthetic environment data"""
        readings = []
        scores = []
        alerts = []
        patterns = []
        forecasts = []

        timestamps = self.generate_time_series(start_date, end_date, frequency='H')

        for location in locations:
            # Generate readings for each sensor type
            for sensor_type, config in self.SENSOR_TYPES.items():
                sensor_id = f"ENV_{location.building}_{location.floor}_{sensor_type.upper()}"
                normal_min, normal_max = config['normal_range']
                base_value = (normal_min + normal_max) / 2

                # Generate pattern-based values
                pattern_values = self.generate_pattern(timestamps, 'daily')

                for i, ts in enumerate(timestamps):
                    # Add some randomness and pattern
                    value = base_value + (normal_max - normal_min) * 0.3 * pattern_values[i]
                    value = self.add_noise(value, 0.1)

                    reading = EnvironmentReading(
                        timestamp=ts,
                        value=value,
                        location=location,
                        sensor_type=sensor_type,
                        sensor_id=sensor_id,
                        unit=config['unit']
                    )
                    readings.append(reading)

                    # Generate alerts for out-of-range values
                    critical_min, critical_max = config['critical_range']
                    if value < critical_min or value > critical_max:
                        alert = Alert(
                            alert_id=f"ALT_{ts.timestamp()}_{sensor_id}",
                            timestamp=ts,
                            location=location,
                            severity='critical' if value < critical_min * 0.8 or value > critical_max * 1.2 else 'warning',
                            category='environment',
                            message=f"{sensor_type} out of range: {value:.1f} {config['unit']}",
                            value=value,
                            threshold=critical_max if value > critical_max else critical_min,
                            resolved=np.random.random() > 0.3
                        )
                        alerts.append(alert)

            # Generate environment scores
            for ts in timestamps:
                # IAQ Score
                iaq_score = EnvironmentScore(
                    timestamp=ts,
                    value=75 + 20 * np.random.random(),
                    location=location,
                    score_type='iaq_score',
                    components={
                        'co2': 0.3,
                        'pm2.5': 0.3,
                        'tvoc': 0.2,
                        'humidity': 0.2
                    }
                )
                scores.append(iaq_score)

                # Comfort Score
                comfort_score = EnvironmentScore(
                    timestamp=ts,
                    value=80 + 15 * np.random.random(),
                    location=location,
                    score_type='comfort_score',
                    components={
                        'temperature': 0.5,
                        'humidity': 0.3,
                        'co2': 0.2
                    }
                )
                scores.append(comfort_score)

            # Generate patterns
            for sensor_type in self.SENSOR_TYPES:
                hourly_pattern = {}
                daily_pattern = {}

                # Calculate average by hour
                for hour in range(24):
                    hour_readings = [r.value for r in readings
                                   if r.location == location and
                                   r.sensor_type == sensor_type and
                                   r.timestamp.hour == hour]
                    if hour_readings:
                        hourly_pattern[hour] = np.mean(hour_readings)

                # Calculate average by day
                for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                    day_readings = [r.value for r in readings
                                  if r.location == location and
                                  r.sensor_type == sensor_type and
                                  r.timestamp.strftime('%A') == day]
                    if day_readings:
                        daily_pattern[day] = np.mean(day_readings)

                pattern = EnvironmentPattern(
                    location=location,
                    parameter=sensor_type,
                    hourly_pattern=hourly_pattern,
                    daily_pattern=daily_pattern,
                    peak_hours=sorted(hourly_pattern.keys(), key=hourly_pattern.get, reverse=True)[:3],
                    low_hours=sorted(hourly_pattern.keys(), key=hourly_pattern.get)[:3]
                )
                patterns.append(pattern)

        # Calculate metrics
        metrics = [
            Metric(
                name="Average IAQ Score",
                value=np.mean([s.value for s in scores if s.score_type == 'iaq_score']),
                unit="points",
                trend="stable",
                change_percentage=2.5,
                period="last 30 days"
            ),
            Metric(
                name="Critical Alerts",
                value=len([a for a in alerts if a.severity == 'critical']),
                unit="count",
                trend="down",
                change_percentage=-15.0,
                period="last 30 days"
            )
        ]

        return EnvironmentData(
            readings=readings,
            scores=scores,
            alerts=alerts,
            patterns=patterns,
            forecasts=forecasts,
            metrics=metrics
        )

    def _analyze_patterns(self, readings: List[EnvironmentReading]) -> List[EnvironmentPattern]:
        """Analyze patterns in sensor readings"""
        # Implementation would analyze actual data
        return []

    def _generate_forecasts(self, readings: List[EnvironmentReading],
                          patterns: List[EnvironmentPattern]) -> List[EnvironmentForecast]:
        """Generate forecasts based on historical data and patterns"""
        # Implementation would use time series forecasting
        return []

    def _calculate_metrics(self, readings: List[EnvironmentReading],
                         scores: List[EnvironmentScore],
                         alerts: List[Alert]) -> List[Metric]:
        """Calculate summary metrics"""
        # Implementation would calculate actual metrics
        return []