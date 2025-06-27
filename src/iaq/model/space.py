from dataclasses import dataclass
from typing import Dict, List, Union
import yaml
from pathlib import Path


@dataclass
class ParameterThreshold:
    parameter: str
    ranges: List[Dict[str, Union[tuple, int]]]  # List of {"range": (min, max), "score": value}

@dataclass
class SpaceType:
    name: str
    weights: Dict[str, float]
    square_footage: float
    thresholds: List[ParameterThreshold]

@dataclass
class Zone:
    name: str
    space_type: SpaceType
    sensor_data: Dict[str, float]


class SpaceTypeConfigLoader:
    """Loads space type configurations from YAML files."""
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Auto-detect config directory relative to this file
            # Current file is in src/iaq/model/space.py
            # Config is in src/iaq/configs/space_types/
            current_file = Path(__file__)
            self.config_dir = current_file.parent.parent / "configs" / "space_types"
        else:
            self.config_dir = Path(config_dir)

    def load_space_type(self, yaml_file: str) -> SpaceType:
        """Load a single space type from YAML file."""
        file_path = self.config_dir / yaml_file

        with open(file_path, 'r') as file:
            config = yaml.safe_load(file)

        # Convert threshold ranges to ParameterThreshold objects
        thresholds = []
        for threshold_config in config['thresholds']:
            # Convert range tuples and handle infinity
            ranges = []
            for range_config in threshold_config['ranges']:
                min_val, max_val = range_config['range']
                if max_val == 'inf':
                    max_val = float('inf')
                ranges.append({
                    'range': (min_val, max_val),
                    'score': range_config['score']
                })

            thresholds.append(ParameterThreshold(
                parameter=threshold_config['parameter'],
                ranges=ranges
            ))

        return SpaceType(
            name=config['name'],
            weights=config['weights'],
            square_footage=config['square_footage'],
            thresholds=thresholds
        )

    def load_all_space_types(self) -> List[SpaceType]:
        """Load all space types from YAML files in the config directory."""
        space_types = []

        if not self.config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {self.config_dir}")

        # Load all .yml and .yaml files
        for yaml_file in self.config_dir.glob("*.yml"):
            space_types.append(self.load_space_type(yaml_file.name))

        for yaml_file in self.config_dir.glob("*.yaml"):
            space_types.append(self.load_space_type(yaml_file.name))

        return space_types