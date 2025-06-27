from typing import Dict, List, Optional
from .space import SpaceType, Zone, SpaceTypeConfigLoader


class AirQualityCalculator:
    def __init__(self, config_dir: str = None):
        self.loader = SpaceTypeConfigLoader(config_dir)
        space_types = self.loader.load_all_space_types()
        self.space_types = {st.name: st for st in space_types}
        self.zones: List[Zone] = []

    def add_zone(self, name: str, space_type_name: str, sensor_data: Dict[str, float]):
        """Add a zone with its sensor data and space type."""
        space_type = self.space_types.get(space_type_name)
        if not space_type:
            available_types = list(self.space_types.keys())
            raise ValueError(f"Unknown space type: {space_type_name}. Available types: {available_types}")
        zone = Zone(name, space_type, sensor_data)
        self.zones.append(zone)

    def calculate_parameter_score(self, space_type: SpaceType, parameter: str, value: float) -> float:
        """Calculate score for a single parameter based on space type thresholds."""
        for threshold in space_type.thresholds:
            if threshold.parameter == parameter:
                for range_info in threshold.ranges:
                    min_val, max_val = range_info["range"]
                    if min_val <= value < max_val:
                        return range_info["score"]
        return 20  # Default score for out-of-range values

    def calculate_zone_score(self, zone: Zone) -> float:
        """Calculate air quality score for a zone."""
        score = 0.0
        weights = zone.space_type.weights
        total_weight = 0.0

        for param, value in zone.sensor_data.items():
            if param in weights:
                param_score = self.calculate_parameter_score(zone.space_type, param, value)
                score += param_score * weights[param]
                total_weight += weights[param]

        # Normalize by actual weights used (in case some parameters are missing)
        return score / total_weight if total_weight > 0 else 0.0

    def calculate_building_score(self) -> float:
        """Calculate overall building air quality score."""
        total_score = 0.0
        total_sqft = 0.0
        for zone in self.zones:
            zone_score = self.calculate_zone_score(zone)
            total_score += zone_score * zone.space_type.square_footage
            total_sqft += zone.space_type.square_footage
        return total_score / total_sqft if total_sqft > 0 else 0.0

    def get_zone_details(self, zone_name: str) -> Optional[Dict]:
        """Get detailed information about a specific zone."""
        for zone in self.zones:
            if zone.name == zone_name:
                return {
                    "name": zone.name,
                    "space_type": zone.space_type.name,
                    "square_footage": zone.space_type.square_footage,
                    "sensor_data": zone.sensor_data,
                    "score": self.calculate_zone_score(zone),
                    "weights": zone.space_type.weights
                }
        return None

    def list_space_types(self) -> List[str]:
        """Return list of available space types."""
        return list(self.space_types.keys())