# pudu-webhook-api/services/transform_service.py
import logging
import numpy as np
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import json
import io
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any
import threading
from rds.rdsTable import RDSTable

logger = logging.getLogger(__name__)

class TransformService:
    """
    Service for transforming robot coordinates in webhook callbacks.

    This service handles:
    1. Robot position transformation: x,y,z coordinates → floor plan coordinates (new_x, new_y)
    2. Map lookup for robots when map_name is not provided in callback
    """

    def __init__(self, config):
        """Initialize transform service with database configuration"""
        self.config = config
        self.supported_databases = self._get_transform_supported_databases()
        self._map_info_cache = {}
        self._cache_lock = threading.Lock()

    def _get_transform_supported_databases(self) -> List[str]:
        """Get list of databases that support transformations"""
        try:
            return self.config.config.get('transform_supported_databases', [])
        except Exception as e:
            logger.warning(f"Could not get transform supported databases: {e}")
            return []

    def transform_robot_coordinates_single(self, robot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform robot coordinates for a single robot and add new_x, new_y fields.

        Args:
            robot_data: Dict with robot data including robot_sn, x, y, z coordinates

        Returns:
            Dict with added new_x, new_y fields (None if transformation failed)
        """
        result_data = robot_data.copy()
        result_data['new_x'] = None
        result_data['new_y'] = None

        try:
            robot_sn = robot_data.get('robot_sn')
            if not robot_sn:
                logger.warning("No robot_sn provided for coordinate transformation")
                return result_data

            # Check if robot is in a supported database
            database_name = self._get_database_for_robot(robot_sn)
            if not database_name or database_name not in self.supported_databases:
                logger.debug(f"Robot {robot_sn} not in transform-supported database: {database_name}")
                return result_data

            # Check if we have valid coordinates
            x = robot_data.get('x')
            y = robot_data.get('y')
            z = robot_data.get('z')

            if x is None or y is None:
                logger.debug(f"Missing coordinates for robot {robot_sn}: x={x}, y={y}, z={z}")
                return result_data

            # Skip if robot is idle at origin (0,0)
            if float(x) == 0 and float(y) == 0:
                logger.debug(f"Robot {robot_sn} at origin (0,0), skipping transformation")
                return result_data

            # Get map name (either from data or lookup)
            map_name = robot_data.get('map_name')
            if not map_name:
                map_name = self._get_current_map_for_robot(robot_sn, database_name)

            if not map_name:
                logger.debug(f"No map_name found for robot {robot_sn}")
                return result_data

            # Transform coordinates
            new_x, new_y = self._transform_robot_position(map_name, float(x), float(y))

            if new_x is not None and new_y is not None:
                result_data['new_x'] = new_x
                result_data['new_y'] = new_y
                logger.debug(f"✅ Transformed robot {robot_sn}: ({x}, {y}) → ({new_x}, {new_y})")
            else:
                logger.debug(f"⚠️ Could not transform coordinates for robot {robot_sn}")

        except Exception as e:
            logger.warning(f"⚠️ Error transforming robot {robot_data.get('robot_sn', 'unknown')}: {e}")

        return result_data

    def _get_current_map_for_robot(self, robot_sn: str, database_name: str) -> Optional[str]:
        """
        Get current map for a robot from the work_location table

        Args:
            robot_sn: Robot serial number

        Returns:
            Current map name if found, None otherwise
        """
        try:
            table = RDSTable(
                connection_config="credentials.yaml",
                database_name=database_name,
                table_name="mnt_robots_work_location",
                fields=None,
                primary_keys=["robot_sn"]
            )

            # Get the most recent work location record for this robot
            query = f"""
                SELECT map_name FROM mnt_robots_work_location
                WHERE robot_sn = '{robot_sn}'
                AND map_name IS NOT NULL
                AND map_name != ''
                ORDER BY update_time DESC
                LIMIT 1
            """

            result = table.query_data(query)
            table.close()

            if result and len(result) > 0:
                map_name = result[0][0] if isinstance(result[0], tuple) else result[0].get('map_name')
                if map_name and str(map_name).strip():
                    logger.debug(f"Found map_name for robot {robot_sn}: {map_name}")
                    return str(map_name).strip()

            logger.debug(f"No map_name found in work_location for robot {robot_sn}")
            return None

        except Exception as e:
            logger.warning(f"Error getting current map for robot {robot_sn}: {e}")
            return None

    def _get_database_for_robot(self, robot_sn: str) -> Optional[str]:
        """Get database name for a robot using the config resolver"""
        try:
            robot_to_db = self.config.resolver.get_robot_database_mapping([robot_sn])
            return robot_to_db.get(robot_sn)
        except Exception as e:
            logger.warning(f"Error getting database for robot {robot_sn}: {e}")
            return None

    def _transform_robot_position(self, map_name: str, x: float, y: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Transform robot position from robot coordinates to floor plan coordinates.
        """
        try:
            # Get map info (cached)
            map_info = self._get_map_info(map_name)
            if not map_info:
                return None, None

            # Get robot map and transform
            robot_map_xml = map_info.get('robot_map_xml')
            transform_robot_to_floor = map_info.get('transform_robot_to_floor')

            if not robot_map_xml or transform_robot_to_floor is None:
                return None, None

            # Parse robot map XML to get resolution and origin
            root = ET.fromstring(robot_map_xml)
            resolution_element = root.find('resolution')
            origin_element = root.find('origin')

            if resolution_element is None or origin_element is None:
                return None, None

            resolution = float(resolution_element.text)
            origin = list(map(float, origin_element.text.split()))

            # Get robot map image to determine dimensions
            robot_map_png_bytes = self._fetch_png_from_url(map_info['robot_map'])
            if not robot_map_png_bytes:
                return None, None

            robot_map_rgb = np.array(Image.open(io.BytesIO(robot_map_png_bytes)).convert('RGB'))

            # Transform robot position to robot map pixel coordinates
            robot_map_u = int((x - origin[0]) / resolution)
            robot_map_v = int(robot_map_rgb.shape[0] - (y - origin[1]) / resolution)

            # Transform robot map coordinates to floor plan coordinates
            robot_position_on_floor = transform_robot_to_floor @ np.array([robot_map_u, robot_map_v, 1])
            floor_plan_u = int(robot_position_on_floor[0])
            floor_plan_v = int(robot_position_on_floor[1])

            return float(floor_plan_u), float(floor_plan_v)

        except Exception as e:
            logger.debug(f"Error transforming position for map {map_name}: {e}")
            return None, None

    def _get_map_info(self, map_name: str) -> Optional[Dict[str, Any]]:
        """
        Get map information from database with caching.
        """
        with self._cache_lock:
            if map_name in self._map_info_cache:
                return self._map_info_cache[map_name]

        try:
            # Query map info from transform-supported databases only
            for db_name in self.supported_databases:
                try:
                    table = RDSTable(
                        connection_config="credentials.yaml",
                        database_name=db_name,
                        table_name="pro_floor_info",
                        fields=None,
                        primary_keys=["robot_map_name"]
                    )

                    query = f"""
                        SELECT transform_robot_to_floor, transform_task_to_floor, floor_map, robot_map, robot_map_xml
                        FROM pro_floor_info
                        WHERE robot_map_name = '{map_name}'
                    """

                    result = table.query_data(query)
                    table.close()

                    if result:
                        row = result[0]
                        if isinstance(row, tuple):
                            transform_robot_to_floor_str, transform_task_to_floor_str, floor_map, robot_map, robot_map_xml = row
                        else:
                            transform_robot_to_floor_str = row.get('transform_robot_to_floor')
                            transform_task_to_floor_str = row.get('transform_task_to_floor')
                            floor_map = row.get('floor_map')
                            robot_map = row.get('robot_map')
                            robot_map_xml = row.get('robot_map_xml')

                        map_info = {
                            'transform_robot_to_floor': np.array(json.loads(transform_robot_to_floor_str)).reshape(3, 3) if transform_robot_to_floor_str else None,
                            'transform_task_to_floor': np.array(json.loads(transform_task_to_floor_str)).reshape(3, 3) if transform_task_to_floor_str else None,
                            'floor_map': floor_map,
                            'robot_map': robot_map,
                            'robot_map_xml': robot_map_xml
                        }

                        # Cache the result
                        with self._cache_lock:
                            self._map_info_cache[map_name] = map_info

                        return map_info

                except Exception as e:
                    logger.debug(f"Error querying map info from {db_name}: {e}")
                    continue

            # If not found in any supported database, cache None to avoid repeated queries
            with self._cache_lock:
                self._map_info_cache[map_name] = None

            return None

        except Exception as e:
            logger.debug(f"Error getting map info for {map_name}: {e}")
            return None

    def _fetch_png_from_url(self, url: str) -> Optional[bytes]:
        """Fetch PNG image from URL."""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                logger.debug(f'Failed to fetch PNG from {url}, status code: {response.status_code}')
                return None
        except Exception as e:
            logger.debug(f'Error fetching PNG from {url}: {e}')
            return None

    def close(self):
        """Close database connections and cleanup"""
        pass  # Config is managed externally