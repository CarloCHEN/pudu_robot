from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class ZoneType(Enum):
    OFFICE = "office"
    RESTROOM = "restroom"
    LOBBY = "lobby"
    CONFERENCE_ROOM = "conference_room"
    BREAK_ROOM = "break_room"
    LABORATORY = "laboratory"
    WAREHOUSE = "warehouse"
    PARKING = "parking"
    KITCHEN = "kitchen"
    STORAGE = "storage"

class CleaningPriorityLevel(Enum):
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5
    CRITICAL = 6

@dataclass
class Zone:
    zone_id: str
    zone_name: str
    building: str
    floor: int
    zone_type: ZoneType
    cleaning_priority_score: float  # 1.0-10.0 scale
    area_sqft: Optional[float] = None
    max_occupancy: Optional[int] = None
    access_level: str = "public"  # public, restricted, private
    special_requirements: List[str] = None

    def __post_init__(self):
        if self.special_requirements is None:
            self.special_requirements = []

    def get_priority_level(self) -> CleaningPriorityLevel:
        """Convert numeric score to priority level"""
        if self.cleaning_priority_score >= 9.0:
            return CleaningPriorityLevel.CRITICAL
        elif self.cleaning_priority_score >= 8.0:
            return CleaningPriorityLevel.VERY_HIGH
        elif self.cleaning_priority_score >= 6.5:
            return CleaningPriorityLevel.HIGH
        elif self.cleaning_priority_score >= 4.5:
            return CleaningPriorityLevel.MEDIUM
        elif self.cleaning_priority_score >= 2.5:
            return CleaningPriorityLevel.LOW
        else:
            return CleaningPriorityLevel.VERY_LOW

    def get_cleaning_frequency_multiplier(self) -> float:
        """Get frequency multiplier based on zone type and priority"""
        base_multipliers = {
            ZoneType.RESTROOM: 2.0,
            ZoneType.KITCHEN: 1.8,
            ZoneType.LABORATORY: 1.6,
            ZoneType.LOBBY: 1.4,
            ZoneType.BREAK_ROOM: 1.3,
            ZoneType.CONFERENCE_ROOM: 1.1,
            ZoneType.OFFICE: 1.0,
            ZoneType.STORAGE: 0.8,
            ZoneType.WAREHOUSE: 0.7,
            ZoneType.PARKING: 0.5
        }

        priority_multiplier = self.cleaning_priority_score / 5.0  # Normalize to ~1.0
        return base_multipliers.get(self.zone_type, 1.0) * priority_multiplier

@dataclass
class Location:
    location_id: str
    location_name: str
    zone_id: str
    building: str
    floor: int
    zone_type: ZoneType
    cleaning_priority_score: float
    coordinates: Optional[Dict[str, float]] = None
    equipment_available: List[str] = None
    access_requirements: List[str] = None

    def __post_init__(self):
        if self.coordinates is None:
            self.coordinates = {"x": 0.0, "y": 0.0}
        if self.equipment_available is None:
            self.equipment_available = []
        if self.access_requirements is None:
            self.access_requirements = []

    def calculate_distance_to(self, other_location: 'Location') -> float:
        """Calculate distance to another location (simplified)"""
        if self.building != other_location.building:
            return 1000.0  # High penalty for different buildings

        if self.floor != other_location.floor:
            return 100.0 + abs(self.floor - other_location.floor) * 50.0

        # Same floor - calculate coordinate distance
        dx = self.coordinates["x"] - other_location.coordinates["x"]
        dy = self.coordinates["y"] - other_location.coordinates["y"]
        return (dx**2 + dy**2)**0.5