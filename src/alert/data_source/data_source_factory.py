from typing import Dict, Any, Optional
from .base_data_source import BaseDataSource
from .sensor_data_source import SensorDataSource
from .score_data_source import ScoreDataSource
import logging

logger = logging.getLogger(__name__)

class DataSourceFactory:
    """A factory for creating data source objects."""

    _creators = {
        "sensor": SensorDataSource,
        "score": ScoreDataSource,
    }

    @classmethod
    def create_data_source(cls, source_config: Dict[str, Any]) -> Optional[BaseDataSource]:
        """
        Creates a data source instance based on the provided configuration.

        Args:
            source_config: A dictionary containing the source's 'id' and 'source_type'.

        Returns:
            An instance of a BaseDataSource subclass, or None if the type is unknown.
        """
        source_type = source_config.get("source_type").str.lower() # sensor or score

        if not source_type:
            logger.error("Source configuration must include 'source_type'.")
            return None

        creator = cls._creators.get(source_type)

        if not creator:
            logger.error(f"Unknown data source type: {source_type}")
            return None

        if source_type == 'sensor':
            source_id = source_config.get("sensor_id")

        elif 'score' in source_type:
            source_id = source_config.get("score_id")

        else:
            logger.error(f"Unknown data source type: {source_type}")
            return None

        return creator(source_id=source_id, config=source_config)