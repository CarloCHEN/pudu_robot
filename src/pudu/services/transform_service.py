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
from pudu.configs.database_config_loader import DynamicDatabaseConfig

logger = logging.getLogger(__name__)

class TransformService:
    """
    Service for transforming robot coordinates and task maps with parallel processing capabilities.

    This service handles:
    1. Robot position transformation: x,y,z coordinates → floor plan coordinates (new_x, new_y)
    2. Task map conversion: robot task maps → floor plan overlays
    3. Parallel processing for both transformations to improve performance
    """

    def __init__(self, config_path: str = "database_config.yaml"):
        """Initialize transform service with database configuration"""
        self.config = DynamicDatabaseConfig(config_path)
        self._map_info_cache = {}
        self._cache_lock = threading.Lock()

    def run_parallel_transformations(self, robot_status_data: pd.DataFrame,
                                   schedule_data: pd.DataFrame,
                                   max_workers: int = 4) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run parallel transformations for both robot positions and task maps.

        Args:
            robot_status_data: DataFrame with robot status including x,y,z coordinates
            schedule_data: DataFrame with task data including map_url
            max_workers: Maximum number of parallel workers

        Returns:
            Tuple of (transformed_robot_status_data, transformed_schedule_data)
        """
        logger.info("🔄 Starting parallel transformations...")

        transformed_robot_data = pd.DataFrame()
        transformed_schedule_data = pd.DataFrame()

        # Use ThreadPoolExecutor for parallel transformations
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="transform_worker") as executor:
            # Submit both transformation tasks
            futures = {}

            if not robot_status_data.empty:
                robot_future = executor.submit(self._transform_robot_positions_parallel, robot_status_data, max_workers)
                futures['robot_positions'] = robot_future
                logger.info(f"📡 Submitted robot position transformations for {len(robot_status_data)} robots")

            if not schedule_data.empty:
                schedule_future = executor.submit(self._transform_task_maps_parallel, schedule_data, max_workers)
                futures['task_maps'] = schedule_future
                logger.info(f"📡 Submitted task map transformations for {len(schedule_data)} tasks")

            # Collect results as they complete
            for task_name, future in futures.items():
                try:
                    if task_name == 'robot_positions':
                        transformed_robot_data = future.result(timeout=120)
                        logger.info(f"✅ Completed robot position transformations: {len(transformed_robot_data)} records")
                    elif task_name == 'task_maps':
                        transformed_schedule_data = future.result(timeout=180)
                        logger.info(f"✅ Completed task map transformations: {len(transformed_schedule_data)} records")
                except concurrent.futures.TimeoutError:
                    logger.error(f"❌ Timeout in {task_name} transformation")
                except Exception as e:
                    logger.error(f"❌ Error in {task_name} transformation: {e}")

        logger.info("🚀 Parallel transformations completed")
        return transformed_robot_data, transformed_schedule_data

    def _transform_robot_positions_parallel(self, robot_data: pd.DataFrame, max_workers: int) -> pd.DataFrame:
        """
        Transform robot positions in parallel using multiple workers.

        Args:
            robot_data: DataFrame with robot status data
            max_workers: Maximum number of parallel workers

        Returns:
            DataFrame with added new_x, new_y columns
        """
        logger.info(f"🤖 Starting parallel robot position transformations for {len(robot_data)} robots")

        # Filter robots that need transformation
        valid_robots = self._filter_robots_for_transformation(robot_data)

        if valid_robots.empty:
            logger.info("No robots need position transformation")
            # Return original data with new columns set to None
            result_data = robot_data.copy()
            result_data['new_x'] = None
            result_data['new_y'] = None
            return result_data

        # Split robots into chunks for parallel processing
        robot_chunks = self._split_dataframe_into_chunks(valid_robots, max_workers)

        transformed_results = []

        # Process chunks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="robot_transform") as executor:
            future_to_chunk = {}

            for i, chunk in enumerate(robot_chunks):
                future = executor.submit(self._transform_robot_position_chunk, chunk, i)
                future_to_chunk[future] = i

            # Collect results
            for future in concurrent.futures.as_completed(future_to_chunk, timeout=90):
                chunk_id = future_to_chunk[future]
                try:
                    chunk_result = future.result()
                    if not chunk_result.empty:
                        transformed_results.append(chunk_result)
                    logger.debug(f"✅ Completed robot position chunk {chunk_id}: {len(chunk_result)} records")
                except Exception as e:
                    logger.error(f"❌ Error processing robot chunk {chunk_id}: {e}")

        # Combine all results
        if transformed_results:
            combined_transformed = pd.concat(transformed_results, ignore_index=True)
        else:
            combined_transformed = pd.DataFrame()

        # Merge with original data to include robots that didn't need transformation
        result_data = robot_data.copy()
        result_data['new_x'] = None
        result_data['new_y'] = None

        if not combined_transformed.empty:
            # Update the result with transformed coordinates
            for _, row in combined_transformed.iterrows():
                mask = result_data['robot_sn'] == row['robot_sn']
                result_data.loc[mask, 'new_x'] = row['new_x']
                result_data.loc[mask, 'new_y'] = row['new_y']

        logger.info(f"🤖 Robot position transformations completed: {len(combined_transformed)} transformed, {len(result_data)} total")
        return result_data

    def _transform_task_maps_parallel(self, schedule_data: pd.DataFrame, max_workers: int) -> pd.DataFrame:
        """
        Transform task maps in parallel using multiple workers.

        Args:
            schedule_data: DataFrame with task data including map_url
            max_workers: Maximum number of parallel workers

        Returns:
            DataFrame with transformation status added
        """
        logger.info(f"🗺️ Starting parallel task map transformations for {len(schedule_data)} tasks")

        # Filter tasks that need transformation
        valid_tasks = self._filter_tasks_for_transformation(schedule_data)

        if valid_tasks.empty:
            logger.info("No tasks need map transformation")
            result_data = schedule_data.copy()
            result_data['map_transformed'] = False
            return result_data

        # Split tasks into chunks for parallel processing
        task_chunks = self._split_dataframe_into_chunks(valid_tasks, max_workers)

        transformed_results = []

        # Process chunks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="map_transform") as executor:
            future_to_chunk = {}

            for i, chunk in enumerate(task_chunks):
                future = executor.submit(self._transform_task_map_chunk, chunk, i)
                future_to_chunk[future] = i

            # Collect results
            for future in concurrent.futures.as_completed(future_to_chunk, timeout=120):
                chunk_id = future_to_chunk[future]
                try:
                    chunk_result = future.result()
                    if not chunk_result.empty:
                        transformed_results.append(chunk_result)
                    logger.debug(f"✅ Completed task map chunk {chunk_id}: {len(chunk_result)} records")
                except Exception as e:
                    logger.error(f"❌ Error processing task chunk {chunk_id}: {e}")

        # Combine all results
        if transformed_results:
            combined_transformed = pd.concat(transformed_results, ignore_index=True)
        else:
            combined_transformed = pd.DataFrame()

        # Merge with original data
        result_data = schedule_data.copy()
        result_data['map_transformed'] = False

        if not combined_transformed.empty:
            # Update the result with transformation status
            for _, row in combined_transformed.iterrows():
                # Use multiple columns to match tasks since they might not have unique identifiers
                mask = (
                    (result_data['robot_sn'] == row['robot_sn']) &
                    (result_data['task_name'] == row['task_name']) &
                    (result_data['start_time'] == row['start_time'])
                )
                result_data.loc[mask, 'map_transformed'] = row['map_transformed']

        logger.info(f"🗺️ Task map transformations completed: {len(combined_transformed)} processed, {len(result_data)} total")
        return result_data

    def _filter_robots_for_transformation(self, robot_data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter robots that need position transformation.

        Skip robots where:
        1. Both x and y are 0 and status is 'idle' (case insensitive)
        2. x, y, or z coordinates are None/NaN
        3. Robot doesn't have a valid map_name
        """
        if robot_data.empty:
            return robot_data

        # Create boolean mask for valid robots
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
            (robot_data['z'].notna())
        )

        valid_robots = robot_data[valid_mask].copy()

        logger.info(f"Filtered {len(valid_robots)} robots for position transformation (from {len(robot_data)} total)")
        return valid_robots

    def _filter_tasks_for_transformation(self, schedule_data: pd.DataFrame) -> pd.DataFrame:
        """
        Filter tasks that need map transformation.

        Skip tasks where:
        1. map_url is None/null/empty
        2. map_url doesn't start with 'https://'
        3. map_url doesn't end with '.png' or '.jpg'
        """
        if schedule_data.empty:
            return schedule_data

        # Create boolean mask for valid tasks
        valid_mask = (
            # Have non-null map_url
            (schedule_data['map_url'].notna()) &
            (schedule_data['map_url'].str.strip() != '') &
            # Starts with https://
            (schedule_data['map_url'].str.startswith('https://')) &
            # Ends with .png or .jpg
            (schedule_data['map_url'].str.lower().str.endswith(('.png', '.jpg')))
        )

        valid_tasks = schedule_data[valid_mask].copy()

        logger.info(f"Filtered {len(valid_tasks)} tasks for map transformation (from {len(schedule_data)} total)")
        return valid_tasks

    def _split_dataframe_into_chunks(self, df: pd.DataFrame, num_chunks: int) -> List[pd.DataFrame]:
        """Split a DataFrame into roughly equal chunks for parallel processing"""
        if df.empty:
            return []

        chunk_size = max(1, len(df) // num_chunks)
        chunks = []

        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i:i + chunk_size].copy()
            chunks.append(chunk)

        return chunks

    def _transform_robot_position_chunk(self, robot_chunk: pd.DataFrame, chunk_id: int) -> pd.DataFrame:
        """Transform a chunk of robots' positions"""
        logger.debug(f"🔄 Processing robot chunk {chunk_id} with {len(robot_chunk)} robots")

        results = []

        for _, robot_row in robot_chunk.iterrows():
            try:
                robot_sn = robot_row['robot_sn']
                x = float(robot_row['x'])
                y = float(robot_row['y'])

                # Get map_name - this might come from robot_status or we might need to look it up
                map_name = robot_row.get('map_name')
                if not map_name:
                    # Try to get map_name from current task if available
                    map_name = self._get_current_map_for_robot(robot_sn)

                if map_name:
                    new_x, new_y = self._transform_robot_position(map_name, x, y)
                    if new_x is not None and new_y is not None:
                        results.append({
                            'robot_sn': robot_sn,
                            'new_x': new_x,
                            'new_y': new_y
                        })
                        logger.debug(f"✅ Transformed robot {robot_sn}: ({x}, {y}) → ({new_x}, {new_y})")
                    else:
                        logger.debug(f"⚠️ Could not transform position for robot {robot_sn}")
                else:
                    logger.debug(f"⚠️ No map_name found for robot {robot_sn}")

            except Exception as e:
                logger.warning(f"⚠️ Error transforming robot {robot_row.get('robot_sn', 'unknown')}: {e}")

        return pd.DataFrame(results)

    def _transform_task_map_chunk(self, task_chunk: pd.DataFrame, chunk_id: int) -> pd.DataFrame:
        """Transform a chunk of task maps"""
        logger.debug(f"🔄 Processing task map chunk {chunk_id} with {len(task_chunk)} tasks")

        results = []

        for _, task_row in task_chunk.iterrows():
            try:
                map_url = task_row['map_url']
                map_name = task_row['map_name']
                robot_sn = task_row['robot_sn']
                task_name = task_row['task_name']
                start_time = task_row['start_time']

                # Perform map transformation
                transformed_image = self._transform_task_map(map_name, map_url)

                if transformed_image is not None:
                    # For now, we just mark it as transformed
                    # Later we can save to S3 and store the URL
                    results.append({
                        'robot_sn': robot_sn,
                        'task_name': task_name,
                        'start_time': start_time,
                        'map_transformed': True
                    })
                    logger.debug(f"✅ Transformed map for task {task_name} (robot {robot_sn})")
                else:
                    results.append({
                        'robot_sn': robot_sn,
                        'task_name': task_name,
                        'start_time': start_time,
                        'map_transformed': False
                    })
                    logger.debug(f"⚠️ Could not transform map for task {task_name}")

            except Exception as e:
                logger.warning(f"⚠️ Error transforming task map: {e}")

        return pd.DataFrame(results)

    def _get_current_map_for_robot(self, robot_sn: str) -> Optional[str]:
        """
        Get current map name for a robot by querying the database.
        This is a fallback when map_name is not in robot_status data.
        """
        try:
            # Get table configurations for this robot
            table_configs = self.config.get_table_configs_for_robots('robot_work_location', [robot_sn])

            for table_config in table_configs:
                try:
                    table = RDSTable(
                        connection_config="credentials.yaml",
                        database_name=table_config['database'],
                        table_name=table_config['table_name'],
                        fields=table_config.get('fields'),
                        primary_keys=table_config['primary_keys']
                    )

                    query = f"SELECT map_name FROM {table.table_name} WHERE robot_sn = '{robot_sn}' ORDER BY update_time DESC LIMIT 1"
                    result = table.query_data(query)

                    if result:
                        map_name = result[0][0] if isinstance(result[0], tuple) else result[0].get('map_name')
                        table.close()
                        return map_name

                    table.close()
                except Exception as e:
                    logger.debug(f"Error getting map for robot {robot_sn}: {e}")

        except Exception as e:
            logger.debug(f"Error in _get_current_map_for_robot: {e}")

        return None

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
            # Query map info from database
            # We need to find which database contains this map
            all_project_databases = self.config.resolver.get_all_project_databases()

            for db_name in all_project_databases:
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

            # If not found in any database, cache None to avoid repeated queries
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

    def close(self):
        """Close database connections and cleanup"""
        try:
            self.config.close()
        except Exception as e:
            logger.warning(f"Error closing transform service: {e}")


# Factory function for easy integration
def run_parallel_transformations(robot_status_data: pd.DataFrame,
                                schedule_data: pd.DataFrame,
                                config_path: str = "database_config.yaml",
                                max_workers: int = 4) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function to run parallel transformations.

    Args:
        robot_status_data: DataFrame with robot status including x,y,z coordinates
        schedule_data: DataFrame with task data including map_url
        config_path: Path to database configuration
        max_workers: Maximum number of parallel workers

    Returns:
        Tuple of (transformed_robot_status_data, transformed_schedule_data)
    """
    transform_service = TransformService(config_path)
    try:
        return transform_service.run_parallel_transformations(robot_status_data, schedule_data, max_workers)
    finally:
        transform_service.close()