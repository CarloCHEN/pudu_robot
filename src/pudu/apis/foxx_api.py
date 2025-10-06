"""
Foxx API - Thin routing layer that delegates to robot-specific adapters
Only contains the 5 critical functions and their dependencies
"""

import pandas as pd
from typing import Optional
from .core.api_factory import APIFactory

# Initialize API factory with caching
_api_factory = APIFactory()
_api_cache = {}


def get_robot_api(robot_type="pudu"):
    """
    根据机器人类型获取对应的API适配器实例

    Args:
        robot_type: 机器人类型 ("pudu" 或 "gas")

    Returns:
        API适配器实例
    """
    if robot_type not in _api_cache:
        _api_cache[robot_type] = _api_factory.create_api(robot_type)
    return _api_cache[robot_type]


# ==================== 5 Critical Functions ====================

def get_schedule_table(start_time: str, end_time: str, location_id: Optional[str] = None,
                      robot_sn: Optional[str] = None, timezone_offset: int = 0,
                      robot_type: str = "pudu") -> pd.DataFrame:
    """
    Get the schedule table for a specified time period, location, and robot

    Args:
        start_time: Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time: End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        timezone_offset: Timezone offset in hours
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        DataFrame with schedule data
    """
    adapter = get_robot_api(robot_type)
    return adapter.get_schedule_table(start_time, end_time, location_id, robot_sn, timezone_offset)


def get_charging_table(start_time: str, end_time: str, location_id: Optional[str] = None,
                      robot_sn: Optional[str] = None, timezone_offset: int = 0,
                      robot_type: str = "pudu") -> pd.DataFrame:
    """
    Get charging records for robots within a specified time period and location

    Args:
        start_time: Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time: End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        timezone_offset: Timezone offset in hours
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        DataFrame with charging data
    """
    adapter = get_robot_api(robot_type)
    return adapter.get_charging_table(start_time, end_time, location_id, robot_sn, timezone_offset)


def get_events_table(start_time: str, end_time: str, location_id: Optional[str] = None,
                    robot_sn: Optional[str] = None, error_levels: Optional[str] = None,
                    error_types: Optional[str] = None, timezone_offset: int = 0,
                    robot_type: str = "pudu") -> pd.DataFrame:
    """
    Get the events table for robots within a specified time period

    Args:
        start_time: Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time: End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        error_levels: Comma-separated error levels (e.g., 'WARNING,ERROR')
        error_types: Comma-separated error types (e.g., 'LostLocalization')
        timezone_offset: Timezone offset in hours
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        DataFrame with event data
    """
    adapter = get_robot_api(robot_type)
    return adapter.get_events_table(start_time, end_time, location_id, robot_sn,
                                   error_levels, error_types, timezone_offset)


def get_robot_status_table(location_id: Optional[str] = None, robot_sn: Optional[str] = None,
                           robot_type: str = "pudu") -> pd.DataFrame:
    """
    Get a simplified table for robots with basic information

    Args:
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        DataFrame with robot status data
    """
    adapter = get_robot_api(robot_type)
    return adapter.get_robot_status_table(location_id, robot_sn)


def get_ongoing_tasks_table(location_id: Optional[str] = None, robot_sn: Optional[str] = None,
                            robot_type: str = "pudu") -> pd.DataFrame:
    """
    Get ongoing tasks for all robots
    Returns a DataFrame with ongoing task information with is_report=0

    Args:
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        DataFrame with ongoing task data
    """
    adapter = get_robot_api(robot_type)
    return adapter.get_ongoing_tasks_table(location_id, robot_sn)


def get_robot_work_location_and_mapping_data(robot_type: str = "pudu") -> tuple:
    """
    Get robot work location data and map floor mapping data in a single pass

    Args:
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        tuple: (work_location_df, mapping_df)
            - work_location_df: DataFrame with columns ['robot_sn', 'map_name', 'x', 'y', 'z', 'status', 'update_time']
            - mapping_df: DataFrame with columns ['map_name', 'floor_number']
    """
    adapter = get_robot_api(robot_type)
    return adapter.get_robot_work_location_and_mapping_data()


# ==================== Helper Functions (if needed by external code) ====================

def get_location_table(robot_type: str = "pudu") -> pd.DataFrame:
    """
    Get the table for locations with location_id and location_name

    Args:
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        DataFrame with location data
    """
    adapter = get_robot_api(robot_type)
    stores_response = adapter.get_list_stores()

    location_df = pd.DataFrame(columns=['Building ID', 'Building Name'])
    for shop in stores_response['list']:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']
        location_df = pd.concat([
            location_df,
            pd.DataFrame({'Building ID': [shop_id], 'Building Name': [shop_name]})
        ], ignore_index=True)

    return location_df


def get_robot_status(sn: str, robot_type: str = "pudu") -> dict:
    """
    Get robot status and comprehensive task information
    This is a convenience function that returns detailed status info

    Args:
        sn: Robot serial number
        robot_type: Robot type ("pudu" or "gas")

    Returns:
        dict with keys: 'is_in_task', 'task_info', 'position'
    """
    adapter = get_robot_api(robot_type)

    # Get robot details
    robot_details = adapter.get_robot_details(sn)

    if not robot_details:
        return {
            'is_in_task': False,
            'task_info': None,
            'position': None
        }

    # Extract position
    position = robot_details.get('position', {})

    # Check if robot is in task (Pudu-specific logic)
    if robot_type == "pudu":
        cleanbot = robot_details.get('cleanbot', {})
        clean_data = cleanbot.get('clean')
        is_in_task = clean_data is not None and clean_data != {}

        # For Pudu, we could extract more detailed task info here if needed
        # But for now, just return basic info
        task_info = None
        if is_in_task:
            task_info = {
                'sn': sn,
                'status': 'In Progress'
            }
    else:
        # For Gas robots, check executingTask
        # We'd need to call get_robot_status from the adapter
        gas_status = adapter.get_robot_status(sn)
        executing_task = gas_status.get('executingTask', {}) if gas_status else {}
        is_in_task = bool(executing_task.get('name'))

        task_info = None
        if is_in_task:
            task_info = {
                'sn': sn,
                'task_name': executing_task.get('name', ''),
                'status': 'In Progress'
            }

    return {
        'is_in_task': is_in_task,
        'task_info': task_info,
        'position': position
    }


# ==================== Export Everything ====================

__all__ = [
    'get_schedule_table',
    'get_charging_table',
    'get_events_table',
    'get_robot_status_table',
    'get_ongoing_tasks_table',
    'get_location_table',
    'get_robot_status',
    'get_robot_api'
]