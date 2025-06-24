from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from models.consumable_models import (
    ConsumableData, ConsumableReading, WasteReading,
    ConsumablePattern, ConsumableForecast, SustainabilityMetric,
    Alert, Metric
)
from models.base_models import Location
from .base_retriever import BaseDataRetriever


class ConsumableDataRetriever(BaseDataRetriever):
    """Retrieves consumable and waste-related data"""

    CONSUMABLE_TYPES = {
        'toilet_paper': {'unit': 'rolls', 'refill_threshold': 20, 'consumption_rate': 2.5},
        'hand_soap': {'unit': 'ml', 'refill_threshold': 25, 'consumption_rate': 50},
        'paper_towel': {'unit': 'sheets', 'refill_threshold': 15, 'consumption_rate': 100},
        'sanitizer': {'unit': 'ml', 'refill_threshold': 30, 'consumption_rate': 30}
    }

    WASTE_TYPES = {
        'general': {'capacity': 100, 'fill_rate': 5.0},
        'recycling': {'capacity': 100, 'fill_rate': 3.0},
        'organic': {'capacity': 50, 'fill_rate': 2.0}
    }

    def retrieve_data(self, locations: List[Location], start_date: datetime,
                     end_date: datetime, **kwargs) -> ConsumableData:
        """Retrieve consumable and waste data"""
        if self.use_synthetic_data:
            return self.generate_synthetic_data(locations, start_date, end_date, **kwargs)

        consumable_readings = self._get_consumable_readings(locations, start_date, end_date)
        waste_readings = self._get_waste_readings(locations, start_date, end_date)
        patterns = self._analyze_patterns(consumable_readings, waste_readings)
        forecasts = self._generate_forecasts(consumable_readings, patterns)
        alerts = self._get_consumable_alerts(locations, start_date, end_date)
        sustainability_metrics = self._calculate_sustainability_metrics(waste_readings)
        metrics = self._calculate_metrics(consumable_readings, waste_readings, alerts)

        return ConsumableData(
            consumable_readings=consumable_readings,
            waste_readings=waste_readings,
            patterns=patterns,
            forecasts=forecasts,
            alerts=alerts,
            sustainability_metrics=sustainability_metrics,
            metrics=metrics
        )

    def generate_synthetic_data(self, locations: List[Location], start_date: datetime,
                               end_date: datetime, **kwargs) -> ConsumableData:
        """Generate synthetic consumable and waste data"""
        consumable_readings = []
        waste_readings = []
        patterns = []
        forecasts = []
        alerts = []
        sustainability_metrics = []

        timestamps = self.generate_time_series(start_date, end_date, frequency='H')

        for location in locations:
            # Generate consumable readings
            for consumable_type, config in self.CONSUMABLE_TYPES.items():
                dispenser_id = f"DISP_{location.building}_{location.floor}_{consumable_type.upper()}"
                sensor_id = f"CONS_{dispenser_id}"

                # Start with full dispenser
                current_level = 100.0
                last_refill = start_date

                for ts in timestamps:
                    # Calculate consumption based on time and location
                    hour = ts.hour
                    weekday = ts.weekday()

                    # Higher consumption during business hours
                    if weekday < 5 and 8 <= hour <= 18:
                        consumption_multiplier = 1.5 + 0.5 * np.random.random()
                    else:
                        consumption_multiplier = 0.3 + 0.2 * np.random.random()

                    # Location-based multiplier (higher floors = less traffic)
                    floor_num = int(location.floor.replace('Floor ', '')) if 'Floor' in location.floor else 1
                    location_multiplier = 1.0 - (floor_num - 1) * 0.1

                    # Calculate hourly consumption
                    hourly_consumption = (config['consumption_rate'] *
                                        consumption_multiplier *
                                        location_multiplier)

                    # Update level
                    current_level -= hourly_consumption / 10  # Convert to percentage

                    # Refill if below threshold
                    if current_level <= config['refill_threshold']:
                        current_level = 100.0
                        last_refill = ts

                    current_level = max(0, min(100, current_level))

                    reading = ConsumableReading(
                        timestamp=ts,
                        value=current_level,
                        location=location,
                        consumable_type=consumable_type,
                        remaining_percentage=current_level,
                        consumption_rate=hourly_consumption,
                        sensor_id=sensor_id,
                        dispenser_id=dispenser_id
                    )
                    consumable_readings.append(reading)

                    # Generate alerts for low levels
                    if current_level < config['refill_threshold']:
                        alert = Alert(
                            alert_id=f"CONS_ALT_{ts.timestamp()}_{dispenser_id}",
                            timestamp=ts,
                            location=location,
                            severity='critical' if current_level < 10 else 'warning',
                            category='consumable',
                            message=f"Low {consumable_type.replace('_', ' ')}: {current_level:.0f}% remaining",
                            value=current_level,
                            threshold=config['refill_threshold'],
                            resolved=current_level == 100.0
                        )
                        alerts.append(alert)

                # Generate pattern for this consumable
                hourly_consumption = {}
                for reading in consumable_readings:
                    if (reading.location == location and
                        reading.consumable_type == consumable_type):
                        hour = reading.timestamp.hour
                        if hour not in hourly_consumption:
                            hourly_consumption[hour] = []
                        hourly_consumption[hour].append(reading.consumption_rate)

                if hourly_consumption:
                    pattern = ConsumablePattern(
                        location=location,
                        consumable_type=consumable_type,
                        hourly_consumption={h: np.mean(v) for h, v in hourly_consumption.items()},
                        daily_consumption={},  # Simplified for demo
                        peak_hours=sorted(hourly_consumption.keys(),
                                        key=lambda h: np.mean(hourly_consumption[h]),
                                        reverse=True)[:3],
                        avg_daily_usage=sum(np.mean(v) for v in hourly_consumption.values()),
                        days_until_empty=current_level / (sum(np.mean(v) for v in hourly_consumption.values()) / 24)
                    )
                    patterns.append(pattern)

                # Generate forecast
                if current_level < 50:
                    hours_until_empty = current_level / (config['consumption_rate'] * 1.2)
                    forecast = ConsumableForecast(
                        location=location,
                        consumable_type=consumable_type,
                        dispenser_id=dispenser_id,
                        current_level=current_level,
                        predicted_empty_time=timestamps[-1] + timedelta(hours=hours_until_empty),
                        confidence=0.85,
                        recommended_refill_time=timestamps[-1] + timedelta(hours=hours_until_empty * 0.8)
                    )
                    forecasts.append(forecast)

            # Generate waste readings
            for waste_type, config in self.WASTE_TYPES.items():
                bin_id = f"BIN_{location.building}_{location.floor}_{waste_type.upper()}"
                sensor_id = f"WASTE_{bin_id}"

                # Start with empty bin
                current_fill = 0.0
                last_empty = start_date

                for ts in timestamps:
                    # Calculate fill rate based on time and location
                    hour = ts.hour
                    weekday = ts.weekday()

                    # Higher fill rate during business hours
                    if weekday < 5 and 8 <= hour <= 18:
                        fill_multiplier = 1.5 + 0.5 * np.random.random()
                    else:
                        fill_multiplier = 0.3 + 0.2 * np.random.random()

                    # Calculate hourly fill
                    hourly_fill = config['fill_rate'] * fill_multiplier

                    # Update fill level
                    current_fill += hourly_fill

                    # Empty if above 90%
                    if current_fill >= 90:
                        current_fill = 0.0
                        last_empty = ts

                    current_fill = max(0, min(100, current_fill))

                    reading = WasteReading(
                        timestamp=ts,
                        value=current_fill,
                        location=location,
                        bin_type=waste_type,
                        fill_percentage=current_fill,
                        fill_rate=hourly_fill,
                        sensor_id=sensor_id,
                        bin_id=bin_id
                    )
                    waste_readings.append(reading)

                    # Generate alerts for high fill levels
                    if current_fill > 80:
                        alert = Alert(
                            alert_id=f"WASTE_ALT_{ts.timestamp()}_{bin_id}",
                            timestamp=ts,
                            location=location,
                            severity='critical' if current_fill > 90 else 'warning',
                            category='waste',
                            message=f"{waste_type.title()} bin {current_fill:.0f}% full",
                            value=current_fill,
                            threshold=80.0,
                            resolved=current_fill == 0.0
                        )
                        alerts.append(alert)

        # Calculate sustainability metrics
        total_waste = sum(r.fill_rate for r in waste_readings if r.bin_type == 'general')
        recycling_waste = sum(r.fill_rate for r in waste_readings if r.bin_type == 'recycling')

        sustainability_metrics = [
            SustainabilityMetric(
                metric_type='recycling_rate',
                value=recycling_waste / (total_waste + recycling_waste) * 100 if total_waste > 0 else 0,
                target=40.0,
                trend='up',
                location=locations[0],  # Simplified
                period='last 30 days'
            ),
            SustainabilityMetric(
                metric_type='waste_diverted',
                value=recycling_waste * 2.5,  # kg diverted
                target=1000.0,
                trend='stable',
                location=locations[0],
                period='last 30 days'
            )
        ]

        # Calculate overall metrics
        metrics = [
            Metric(
                name="Critical Consumables",
                value=float(len([r for r in consumable_readings if r.remaining_percentage < 20])),
                unit="items",
                trend="down",
                change_percentage=-10.5,
                period="last 30 days"
            ),
            Metric(
                name="Waste Diversion Rate",
                value=sustainability_metrics[0].value if sustainability_metrics else 0,
                unit="%",
                trend="up",
                change_percentage=5.2,
                period="last 30 days"
            )
        ]

        return ConsumableData(
            consumable_readings=consumable_readings,
            waste_readings=waste_readings,
            patterns=patterns,
            forecasts=forecasts,
            alerts=alerts,
            sustainability_metrics=sustainability_metrics,
            metrics=metrics
        )

    def _get_consumable_readings(self, locations: List[Location],
                               start_date: datetime, end_date: datetime) -> List[ConsumableReading]:
        """Get consumable readings from database"""
        return []

    def _get_waste_readings(self, locations: List[Location],
                          start_date: datetime, end_date: datetime) -> List[WasteReading]:
        """Get waste readings from database"""
        return []

    def _analyze_patterns(self, consumable_readings: List[ConsumableReading],
                        waste_readings: List[WasteReading]) -> List[ConsumablePattern]:
        """Analyze consumption patterns"""
        return []

    def _generate_forecasts(self, readings: List[ConsumableReading],
                          patterns: List[ConsumablePattern]) -> List[ConsumableForecast]:
        """Generate consumption forecasts"""
        return []

    def _get_consumable_alerts(self, locations: List[Location],
                             start_date: datetime, end_date: datetime) -> List[Alert]:
        """Get consumable-related alerts"""
        return []

    def _calculate_sustainability_metrics(self, waste_readings: List[WasteReading]) -> List[SustainabilityMetric]:
        """Calculate sustainability metrics"""
        return []

    def _calculate_metrics(self, consumable_readings: List[ConsumableReading],
                         waste_readings: List[WasteReading],
                         alerts: List[Alert]) -> List[Metric]:
        """Calculate overall metrics"""
        return []