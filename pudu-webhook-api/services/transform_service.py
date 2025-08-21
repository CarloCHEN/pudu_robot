# src/pudu/services/transform_service.py
import logging
import numpy as np
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import cv2
import json
import io
from PIL import Image
from typing import Dict, List, Tuple, Optional, Any
import concurrent.futures
import threading
from rds.rdsTable import RDSTable

logger = logging.getLogger(__name__)

class TransformService:
    """
    Service for transforming robot coordinates and task maps with S3 integration.

    This service handles:
    1. Robot position transformation: x,y,z coordinates → floor plan coordinates (new_x, new_y)
    """

    def __init__(self, config):
        """Initialize transform service with database configuration and S3 service"""
        self.config = config
        self.supported_databases = self.config.get_transform_supported_databases()
        self._map_info_cache = {}
        self._cache_lock = threading.Lock()

    def transform_robot_coordinates_batch(self, location_data: dict) -> dict:
        """
        Transform robot coordinates in batch and add new_x, new_y columns.

        Args:
            work_location_data: DataFrame with robot work location data including x, y, z coordinates

        Returns:
            DataFrame with added new_x, new_y columns
        """
        # Add new coordinate columns initialized to None
        result_data = location_data.copy()
        result_data['new_x'] = None
        result_data['new_y'] = None

        # Filter robots that need transformation and are in supported databases
        robots_to_transform = self._filter_robots_for_coordinate_transformation(result_data)

        if robots_to_transform.empty:
            logger.info("No robots need coordinate transformation")
            return result_data

        logger.info(f"Transforming coordinates for {len(robots_to_transform)} robots")

        # Transform coordinates for each robot
        for _, robot_row in robots_to_transform.iterrows():
            try:
                robot_sn = robot_row['robot_sn']
                database_name = self._get_database_for_robot(robot_sn)
                if database_name not in self.supported_databases:
                    logger.warning(f"Database {database_name} not supported for coordinate transformation of robot {robot_sn}")
                    continue
                map_name = robot_row['map_name']
                x = float(robot_row['x'])
                y = float(robot_row['y'])

                # Transform coordinates
                new_x, new_y = self._transform_robot_position(map_name, x, y)

                if new_x is not None and new_y is not None:
                    # Update the result DataFrame
                    mask = result_data['robot_sn'] == robot_sn
                    result_data.loc[mask, 'new_x'] = new_x
                    result_data.loc[mask, 'new_y'] = new_y
                    logger.debug(f"✅ Transformed robot {robot_sn}: ({x}, {y}) → ({new_x}, {new_y})")
                else:
                    logger.debug(f"⚠️ Could not transform coordinates for robot {robot_sn}")

            except Exception as e:
                logger.warning(f"⚠️ Error transforming robot {robot_row.get('robot_sn', 'unknown')}: {e}")

        transformed_count = len(result_data[result_data['new_x'].notna()])
        logger.info(f"🤖 Coordinate transformations completed: {transformed_count} transformed")
        return result_data

    def _get_current_map_for_robot(self, robot_sn: str) -> Optional[str]:
        """Get current map for a robot using the config resolver"""
        database_name = self._get_database_for_robot(robot_sn)
        if database_name not in self.supported_databases:
            return None
        table = RDSTable(
            connection_config="credentials.yaml",
            database_name=database_name,
            table_name="work_location",
            fields=None,
            primary_keys=["robot_sn"]
        )
        query = f"""
            SELECT map_name FROM work_location WHERE robot_sn = '{robot_sn}' AND status != 'idle' ORDER BY update_time DESC LIMIT 1
        """
        result = table.query_data(query)
        table.close()
        return result[0][0] if result else None

    def _get_database_for_robot(self, robot_sn: str) -> Optional[str]:
        """Get database name for a robot using the config resolver"""
        try:
            robot_to_db = self.config.resolver.get_robot_database_mapping([robot_sn])
            return robot_to_db.get(robot_sn)
        except Exception as e:
            logger.warning(f"Error getting database for robot {robot_sn}: {e}")
            return None

    def _filter_robots_for_coordinate_transformation(self, robot_data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter robots that need coordinate transformation and are in supported databases.
        """
        if robot_data.empty:
            return robot_data

        # First apply basic filtering (same as before)
        valid_mask = (
            # Not (x=0 and y=0 and status=idle)
            ~(
                (robot_data['x'].fillna(0) == 0) &
                (robot_data['y'].fillna(0) == 0) &
                (robot_data['status'].str.lower() == 'idle')
            ) &
            # Have valid coordinates
            (robot_data['x'].notna()) &
            (robot_data['y'].notna()) &
            (robot_data['z'].notna()) &
            # Have valid map_name
            (robot_data['map_name'].notna()) &
            (robot_data['map_name'].str.strip() != '')
        )

        basic_valid_robots = robot_data[valid_mask].copy()

        if basic_valid_robots.empty:
            return basic_valid_robots

        # Filter by transform support
        robot_sns = basic_valid_robots['robot_sn'].tolist()
        supported_robots, _ = self.config.filter_robots_for_transform_support(robot_sns)

        final_valid_robots = basic_valid_robots[
            basic_valid_robots['robot_sn'].isin(supported_robots)
        ].copy()

        logger.info(f"Filtered {len(final_valid_robots)} robots for coordinate transformation "
                   f"(from {len(robot_data)} total, {len(supported_robots)} in supported databases)")

        return final_valid_robots

    def _transform_robot_position(self, map_name: str, x: float, y: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Transform robot position from robot coordinates to floor plan coordinates.
        Based on the position_to_pixel method from the original code.
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
        Based on the fetch_map_info method from the original code.
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
                        primary_keys=["robot_map_name"],
                        reuse_connection=True
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

    def close(self):
        """Close database connections and cleanup"""
        pass  # Config is managed externally