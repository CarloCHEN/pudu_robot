import json
from dataclasses import dataclass
from typing import Dict, List, Optional

# Placeholder for sensor data (replace with actual sensor input)
SENSOR_DATA = {
    "office_1": {
        "PM2.5": 10,  # μg/m³
        "PM10": 20,   # μg/m³
        "CO2": 600,   # ppm
        "tVOC": 200,  # μg/m³
        "HCHO": 0.02, # mg/m³
        "O3": 0.01,   # ppm
        "Temperature": 22,  # °C
        "Humidity": 45      # %RH
    },
    "restroom_1": {
        "PM2.5": 5,
        "PM10": 10,
        "NH3": 0.5,   # ppm
        "H2S": 0.02,  # ppm
        "tVOC": 300,
        "Temperature": 20,
        "Humidity": 50
    }
    # Add more rooms as needed
}

# Model for Space Type with parameter weights and square footage
@dataclass
class SpaceType:
    name: str
    weights: Dict[str, float]
    square_footage: float

# Space types configuration (replacing SPACE_WEIGHTS dictionary)
SPACE_TYPES = [
    SpaceType(
        name="Office/Cubicle",
        weights={
            "PM2.5": 0.15,
            "PM10": 0.10,
            "CO2": 0.25,
            "tVOC": 0.15,
            "HCHO": 0.05,
            "O3": 0.05,
            "Temperature": 0.15,
            "Humidity": 0.10
        },
        square_footage=275000
    ),
    SpaceType(
        name="Restroom",
        weights={
            "PM2.5": 0.05,
            "PM10": 0.05,
            "NH3": 0.25,
            "H2S": 0.25,
            "tVOC": 0.15,
            "Temperature": 0.10,
            "Humidity": 0.15
        },
        square_footage=12500
    )
    # Add more space types as needed
]

# Placeholder for parameter thresholds
THRESHOLDS = {
    "PM2.5": [
        {"range": (0, 10), "score": 100},
        {"range": (10, 12), "score": 90},
        {"range": (12, 15), "score": 80},
        {"range": (15, 25), "score": 60},
        {"range": (25, 35), "score": 40},
        {"range": (35, float("inf")), "score": 20}
    ],
    "PM10": [
        {"range": (0, 20), "score": 100},
        {"range": (20, 30), "score": 90},
        {"range": (30, 50), "score": 80},
        {"range": (50, 75), "score": 60},
        {"range": (75, 100), "score": 40},
        {"range": (100, float("inf")), "score": 20}
    ],
    # Add thresholds for CO2, tVOC, HCHO, O3, NH3, H2S, Temperature, Humidity
}

@dataclass
class Room:
    name: str
    space_type: str
    sensor_data: Dict[str, float]
    square_footage: float

class AirQualityCalculator:
    def __init__(self, thresholds: Dict, space_types: List[SpaceType]):
        self.thresholds = thresholds
        self.space_types = {st.name: st for st in space_types}  # Map space type names to objects
        self.rooms: List[Room] = []

    def add_room(self, name: str, space_type: str, sensor_data: Dict[str, float]):
        """Add a room with its sensor data and space type."""
        space_type_obj = self.space_types.get(space_type)
        square_footage = space_type_obj.square_footage if space_type_obj else 1000
        room = Room(name, space_type, sensor_data, square_footage)
        self.rooms.append(room)

    def calculate_parameter_score(self, parameter: str, value: float) -> float:
        """Calculate score for a single parameter based on thresholds."""
        for threshold in self.thresholds.get(parameter, []):
            min_val, max_val = threshold["range"]
            if min_val <= value < max_val:
                return threshold["score"]
        return 20  # Default score for out-of-range values

    def calculate_room_score(self, room: Room) -> float:
        """Calculate air quality score for a room."""
        space_type_obj = self.space_types.get(room.space_type, {})
        weights = space_type_obj.weights if space_type_obj else {}
        score = 0.0
        for param, value in room.sensor_data.items():
            if param in weights and param in self.thresholds:
                param_score = self.calculate_parameter_score(param, value)
                score += param_score * weights[param]
        return score

    def calculate_building_score(self) -> float:
        """Calculate overall building air quality score."""
        total_score = 0.0
        total_sqft = 0.0
        for room in self.rooms:
            room_score = self.calculate_room_score(room)
            total_score += room_score * room.square_footage
            total_sqft += room.square_footage
        return total_score / total_sqft if total_sqft > 0 else 0.0

    def generate_cleaning_tasks(self, room: Room) -> Optional[Dict]:
        """Generate cleaning tasks based on room score and space type."""
        score = self.calculate_room_score(room)
        tasks = {"room": room.name, "actions": [], "priority": "Low"}

        # Placeholder logic for task generation
        if room.space_type == "Office/Cubicle":
            if score < 40:
                tasks["actions"] = ["Immediate deep cleaning", "Source investigation"]
                tasks["priority"] = "Urgent"
            elif score < 50:
                tasks["actions"] = ["Deep cleaning", "Ventilation check"]
                tasks["priority"] = "High"
            elif score < 70:
                tasks["actions"] = ["Enhanced cleaning"]
                tasks["priority"] = "Medium"
        elif room.space_type == "Restroom":
            if score < 40:
                tasks["actions"] = ["Immediate servicing", "Plumbing check"]
                tasks["priority"] = "Urgent"
            elif score < 50:
                tasks["actions"] = ["Deep cleaning", "Ventilation boost"]
                tasks["priority"] = "High"
            elif score < 70:
                tasks["actions"] = ["Additional cleaning"]
                tasks["priority"] = "Medium"
        # Add more space types as needed

        return tasks if tasks["actions"] else None

def main():
    # Initialize calculator
    calculator = AirQualityCalculator(THRESHOLDS, SPACE_TYPES)

    # Load sensor data (replace with actual sensor data source)
    for room_name, sensor_data in SENSOR_DATA.items():
        space_type = "Office/Cubicle" if "office" in room_name.lower() else "Restroom"
        calculator.add_room(room_name, space_type, sensor_data)

    # Calculate scores
    for room in calculator.rooms:
        score = calculator.calculate_room_score(room)
        print(f"Room: {room.name}, Score: {score:.2f}")

        # Generate cleaning tasks
        tasks = calculator.generate_cleaning_tasks(room)
        if tasks:
            print(f"Tasks for {room.name}: {tasks}")

    # Calculate building score
    building_score = calculator.calculate_building_score()
    print(f"Overall Building Score: {building_score:.2f}")

if __name__ == "__main__":
    main()