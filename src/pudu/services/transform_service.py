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
from pudu.rds.rdsTable import RDSTable
from pudu.services.s3_service import S3TransformService

logger = logging.getLogger(__name__)

class TransformService:
    """
    Service for transforming robot coordinates and task maps with S3 integration.

    This service handles:
    1. Robot position transformation: x,y,z coordinates → floor plan coordinates (new_x, new_y)
    2. Task map conversion: robot task maps → floor plan overlays → S3 upload → public URLs
    3. Parallel processing for both transformations to improve performance
    """

    def __init__(self, config, s3_config: Optional[Dict] = None):
        """Initialize transform service with database configuration and S3 service"""
        self.config = config
        self.supported_databases = self.config.get_transform_supported_databases()
        self._map_info_cache = {}
        self._cache_lock = threading.Lock()

        # Initialize S3 service
        if s3_config:
            region = s3_config.get('region', 'us-east-2')
            bucket_mapping = s3_config.get('buckets', {})
            self.s3_service = S3TransformService(region)
            self.s3_service.update_bucket_mapping(bucket_mapping)
            logger.info(f"Initialized S3 service for region {region} with {len(bucket_mapping)} buckets")
        else:
            self.s3_service = None
            logger.warning("S3 service not initialized - transformed maps will not be uploaded")

    def transform_robot_coordinates_batch(self, work_location_data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform robot coordinates in batch and add new_x, new_y columns.

        Args:
            work_location_data: DataFrame with robot work location data including x, y, z coordinates

        Returns:
            DataFrame with added new_x, new_y columns
        """
        logger.info(f"🤖 Starting robot coordinate transformations for {len(work_location_data)} robots")

        # Add new coordinate columns initialized to None
        result_data = work_location_data.copy()
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

    def transform_task_maps_batch(self, schedule_data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform task maps in batch, upload to S3, and add new_map_url column.

        Args:
            schedule_data: DataFrame with task data including map_url

        Returns:
            DataFrame with added new_map_url column containing S3 URLs
        """
        logger.info(f"🗺️ Starting task map transformations for {len(schedule_data)} tasks")

        # Add new map URL column initialized to empty string
        result_data = schedule_data.copy()
        result_data['new_map_url'] = ''

        # Filter tasks that need transformation and are in supported databases
        tasks_to_transform = self._filter_tasks_for_map_transformation(result_data)

        if tasks_to_transform.empty:
            logger.info("No tasks need map transformation")
            return result_data

        logger.info(f"Transforming maps for {len(tasks_to_transform)} tasks")

        # Transform maps for each task
        for _, task_row in tasks_to_transform.iterrows():
            try:
                map_url = task_row['map_url']
                map_name = task_row['map_name']
                robot_sn = task_row['robot_sn']
                task_name = task_row['task_name']
                task_id = task_row.get('task_id', 'unknown')
                start_time = task_row['start_time']

                # Get database name for this robot
                database_name = self._get_database_for_robot(robot_sn)
                if not database_name:
                    logger.warning(f"Could not determine database for robot {robot_sn}")
                    continue
                if database_name not in self.supported_databases:
                    logger.warning(f"Database {database_name} not supported for map transformation of task {task_name} of robot {robot_sn}")
                    continue

                # Perform map transformation
                transformed_image = self._transform_task_map(map_name, map_url)

                if transformed_image is not None:
                    # Upload to S3 and get public URL (with deduplication)
                    s3_url = self._upload_transformed_image_to_s3(
                        transformed_image, map_name, task_id, robot_sn, database_name, map_url
                    )

                    if s3_url:
                        # Update the result DataFrame with S3 URL
                        mask = (
                            (result_data['robot_sn'] == robot_sn) &
                            (result_data['task_name'] == task_name) &
                            (result_data['start_time'] == start_time)
                        )
                        result_data.loc[mask, 'new_map_url'] = s3_url
                        logger.info(f"✅ Transformed and uploaded map for task {task_name} (robot {robot_sn}): {s3_url}")
                    else:
                        logger.warning(f"⚠️ Failed to upload transformed map for task {task_name} of robot {robot_sn}")
                else:
                    logger.debug(f"⚠️ Could not transform map for task {task_name} of robot {robot_sn}")

            except Exception as e:
                logger.warning(f"⚠️ Error transforming task map for task {task_name} of robot {robot_sn}: {e}")

        uploaded_count = len(result_data[result_data['new_map_url'] != ''])
        logger.info(f"🗺️ Task map transformations completed: {uploaded_count} uploaded to S3")
        return result_data

    def _upload_transformed_image_to_s3(self,
                                       image_array: np.ndarray,
                                       map_name: str,
                                       task_id: str,
                                       robot_sn: str,
                                       database_name: str,
                                       original_map_url: str = None) -> Optional[str]:
        """
        Upload transformed image to S3 and return public URL

        Args:
            image_array: Transformed image as numpy array
            map_name: Name of the map
            task_id: Task ID
            robot_sn: Robot serial number
            database_name: Database name to determine S3 bucket
            original_map_url: Original map URL for deterministic naming

        Returns:
            Public S3 URL if successful, None if failed
        """
        if not self.s3_service:
            logger.warning("S3 service not available - cannot upload transformed image")
            return None

        try:
            return self.s3_service.upload_transformed_image(
                image_array=image_array,
                map_name=map_name,
                task_id=task_id,
                robot_sn=robot_sn,
                database_name=database_name,
                original_map_url=original_map_url
            )
        except Exception as e:
            logger.error(f"Error uploading transformed image to S3: {e}")
            return None

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

    def _filter_tasks_for_map_transformation(self, schedule_data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter tasks that need map transformation and are in supported databases.
        """
        if schedule_data.empty:
            return schedule_data

        # First apply basic filtering (same as before)
        valid_mask = (
            # Have non-null map_url
            (schedule_data['map_url'].notna()) &
            (schedule_data['map_url'].str.strip() != '') &
            # Starts with https://
            (schedule_data['map_url'].str.startswith('https://')) &
            # Ends with .png or .jpg
            (schedule_data['map_url'].str.lower().str.endswith(('.png', '.jpg'))) &
            # Have valid map_name
            (schedule_data['map_name'].notna()) &
            (schedule_data['map_name'].str.strip() != '')
        )

        basic_valid_tasks = schedule_data[valid_mask].copy()

        if basic_valid_tasks.empty:
            return basic_valid_tasks

        # Filter by transform support
        robot_sns = basic_valid_tasks['robot_sn'].tolist()
        supported_robots, _ = self.config.filter_robots_for_transform_support(robot_sns)

        final_valid_tasks = basic_valid_tasks[
            basic_valid_tasks['robot_sn'].isin(supported_robots)
        ].copy()

        logger.info(f"Filtered {len(final_valid_tasks)} tasks for map transformation "
                   f"(from {len(schedule_data)} total, {len(supported_robots)} robots in supported databases)")

        return final_valid_tasks

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

    def _transform_task_map(self, map_name: str, map_url: str) -> Optional[np.ndarray]:
        """
        Transform task map to floor plan overlay.
        Based on the convert_task_report_to_floor_plan method from the original code.
        """
        try:
            # Get map info (cached)
            map_info = self._get_map_info(map_name)
            if not map_info:
                return None

            # Fetch images
            task_report_png_bytes = self._fetch_png_from_url(map_url)
            floor_plan_png_bytes = self._fetch_png_from_url(map_info['floor_map'])

            if not task_report_png_bytes or not floor_plan_png_bytes:
                return None

            # Read as RGB via PIL
            task_img_rgb = np.array(Image.open(io.BytesIO(task_report_png_bytes)).convert('RGB'))
            floor_img_rgb = np.array(Image.open(io.BytesIO(floor_plan_png_bytes)).convert('RGB'))

            # Create green mask in task image (exact color match)
            green = np.array([28, 195, 61], dtype=np.uint8)
            green_mask = np.all(task_img_rgb == green, axis=-1).astype(np.uint8)

            # Load transform (3x3 homography: task -> floor)
            transform_task_to_floor = map_info['transform_task_to_floor']
            if transform_task_to_floor is None:
                return None

            # Warp the green mask into floor-plan coordinates
            h_floor, w_floor = floor_img_rgb.shape[:2]
            warped_mask = cv2.warpPerspective(
                green_mask, transform_task_to_floor, (w_floor, h_floor),
                flags=cv2.INTER_NEAREST
            )

            # Create a colored overlay (green) where the mask is 1
            overlay = floor_img_rgb.copy()
            overlay[warped_mask == 1] = green

            # Alpha blend overlay with the original floor plan
            alpha = 0.5
            blended = (overlay.astype(np.float32) * alpha +
                      floor_img_rgb.astype(np.float32) * (1 - alpha)).astype(np.uint8)

            return blended

        except Exception as e:
            logger.debug(f"Error transforming task map {map_name}: {e}")
            return None

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

    def _fetch_png_from_url(self, url: str) -> Optional[bytes]:
        """
        Fetch PNG image from URL.
        Based on the fetch_png_from_s3_url method from the original code.
        """
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

    def test_s3_connectivity(self) -> Dict[str, bool]:
        """
        Test S3 connectivity for all configured databases

        Returns:
            Dict mapping database names to connectivity status
        """
        if not self.s3_service:
            logger.warning("S3 service not available for connectivity test")
            return {}

        supported_databases = self.config.get_transform_supported_databases()
        connectivity_status = {}

        for database_name in supported_databases:
            try:
                status = self.s3_service.test_bucket_access(database_name)
                connectivity_status[database_name] = status
                logger.info(f"S3 connectivity test for {database_name}: {'✅ PASS' if status else '❌ FAIL'}")
            except Exception as e:
                connectivity_status[database_name] = False
                logger.error(f"S3 connectivity test error for {database_name}: {e}")

        return connectivity_status

    def close(self):
        """Close database connections and cleanup"""
        pass  # Config is managed externally