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


def get_robot_api(robot_type="pudu", customer_name=None):
    """
    根据机器人类型和客户获取对应的API适配器实例

    Args:
        robot_type: 机器人类型 ("pudu" 或 "gas")
        customer_name: 客户名称，如果不提供则使用当前客户

    Returns:
        API适配器实例，如果robot_type未启用则返回None
    """
    # Get customer name FIRST, before any validation
    customer = customer_name or _api_factory.get_current_customer()

    # FIXED: Pass customer to validation check
    enabled_apis = _api_factory.list_enabled_apis_for_customer(customer)  # Pass customer here!
    if robot_type not in enabled_apis:
        return None

    # Create cache key with customer name
    cache_key = f"{robot_type}_{customer}"

    if cache_key not in _api_cache:
        # IMPORTANT: Pass customer_name (not customer) to maintain None vs explicit difference
        _api_cache[cache_key] = _api_factory.create_api(robot_type, customer)  # Pass customer here!

    return _api_cache[cache_key]

def set_customer(customer_name: str):
    """
    设置当前客户并清除缓存

    Args:
        customer_name: 客户名称
    """
    _api_factory.set_customer(customer_name)
    _api_cache.clear()  # Clear cache when switching customers

def get_current_customer() -> str:
    """获取当前客户名称"""
    return _api_factory.get_current_customer()

def list_customers() -> list:
    """列出所有可用的客户"""
    return _api_factory.list_customers()

# ==================== 5 Critical Functions ====================

def get_schedule_table(start_time: str, end_time: str, location_id: Optional[str] = None,
                      robot_sn: Optional[str] = None, timezone_offset: int = 0,
                      robot_type: str = "pudu", customer_name: Optional[str] = None) -> pd.DataFrame:
    """
    Get the schedule table for a specified time period, location, and robot

    Args:
        start_time: Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time: End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        timezone_offset: Timezone offset in hours
        robot_type: Robot type ("pudu" or "gas")
        customer_name: Customer name (single customer only)

    Returns:
        DataFrame with schedule data
    """
    adapter = get_robot_api(robot_type, customer_name)
    return adapter.get_schedule_table(start_time, end_time, location_id, robot_sn, timezone_offset)


def get_charging_table(start_time: str, end_time: str, location_id: Optional[str] = None,
                      robot_sn: Optional[str] = None, timezone_offset: int = 0,
                      robot_type: str = "pudu", customer_name: Optional[str] = None) -> pd.DataFrame:
    """
    Get charging records for robots within a specified time period and location

    Args:
        start_time: Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time: End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        timezone_offset: Timezone offset in hours
        robot_type: Robot type ("pudu" or "gas")
        customer_name: Customer name, if not provided uses current customer

    Returns:
        DataFrame with charging data
    """
    adapter = get_robot_api(robot_type, customer_name)
    return adapter.get_charging_table(start_time, end_time, location_id, robot_sn, timezone_offset)


def get_events_table(start_time: str, end_time: str, location_id: Optional[str] = None,
                    robot_sn: Optional[str] = None, error_levels: Optional[str] = None,
                    error_types: Optional[str] = None, timezone_offset: int = 0,
                    robot_type: str = "pudu", customer_name: Optional[str] = None) -> pd.DataFrame:
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
        customer_name: Customer name, if not provided uses current customer

    Returns:
        DataFrame with event data
    """
    adapter = get_robot_api(robot_type, customer_name)
    return adapter.get_events_table(start_time, end_time, location_id, robot_sn,
                                   error_levels, error_types, timezone_offset)


def get_robot_status_table(location_id: Optional[str] = None, robot_sn: Optional[str] = None,
                           robot_type: str = "pudu", customer_name: Optional[str] = None) -> pd.DataFrame:
    """
    Get a simplified table for robots with basic information

    Args:
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        robot_type: Robot type ("pudu" or "gas")
        customer_name: Customer name, if not provided uses current customer

    Returns:
        DataFrame with robot status data
    """
    adapter = get_robot_api(robot_type, customer_name)
    return adapter.get_robot_status_table(location_id, robot_sn)


def get_ongoing_tasks_table(location_id: Optional[str] = None, robot_sn: Optional[str] = None,
                            robot_type: str = "pudu", customer_name: Optional[str] = None) -> pd.DataFrame:
    """
    Get ongoing tasks for all robots
    Returns a DataFrame with ongoing task information with is_report=0

    Args:
        location_id: Optional location ID to filter by
        robot_sn: Optional robot serial number to filter by
        robot_type: Robot type ("pudu" or "gas")
        customer_name: Customer name, if not provided uses current customer

    Returns:
        DataFrame with ongoing task data
    """
    adapter = get_robot_api(robot_type, customer_name)
    return adapter.get_ongoing_tasks_table(location_id, robot_sn)


def get_robot_work_location_and_mapping_data(robot_type: str = "pudu",
                                             customer_name: Optional[str] = None) -> tuple:
    """
    Get robot work location data and map floor mapping data in a single pass

    Args:
        robot_type: Robot type ("pudu" or "gas")
        customer_name: Customer name, if not provided uses current customer

    Returns:
        tuple: (work_location_df, mapping_df)
            - work_location_df: DataFrame with columns ['robot_sn', 'map_name', 'x', 'y', 'z', 'status', 'update_time']
            - mapping_df: DataFrame with columns ['map_name', 'floor_number']
    """
    adapter = get_robot_api(robot_type, customer_name)
    return adapter.get_robot_work_location_and_mapping_data()


# ==================== Helper Functions (if needed by external code) ====================

def get_location_table(robot_type: str = "pudu", customer_name: Optional[str] = None) -> pd.DataFrame:
    """
    Get the table for locations with location_id and location_name

    Args:
        robot_type: Robot type ("pudu" or "gas")
        customer_name: Customer name, if not provided uses current customer

    Returns:
        DataFrame with location data
    """
    adapter = get_robot_api(robot_type, customer_name)
    stores_response = adapter.get_list_stores()

    location_df = pd.DataFrame(columns=['Building ID', 'Building Name'])
    for shop in stores_response['list']:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']
        location_df = pd.concat([
            location_df,
            pd.DataFrame({'Building ID': [shop_id], 'Building Name': [shop_name]})
        ], ignore_index=True)

    return location_df

def get_robot_status(sn: str, robot_type: str = "pudu", customer_name: Optional[str] = None) -> dict:
    """
    Get robot status and comprehensive task information
    This is a convenience function that returns detailed status info

    Args:
        sn: Robot serial number
        robot_type: Robot type ("pudu" or "gas")
        customer_name: Customer name, if not provided uses current customer

    Returns:
        dict with keys: 'is_in_task', 'task_info', 'position'
    """
    adapter = get_robot_api(robot_type, customer_name)

    if robot_type == "pudu":
        # For Pudu robots, use get_robot_details as before
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

        return {
            'is_in_task': is_in_task,
            'task_info': task_info,
            'position': position
        }

    else:
        # For Gas robots, directly use get_robot_status which provides all needed info
        gas_status = adapter.get_robot_status(sn)

        if not gas_status:
            return {
                'is_in_task': False,
                'task_info': None,
                'position': None
            }

        # Extract position from localizationInfo
        localization_info = gas_status.get('localizationInfo', {})
        map_position = localization_info.get('mapPosition', {})
        position = {
            'x': map_position.get('x', 0),
            'y': map_position.get('y', 0),
            'z': map_position.get('angle', 0)
        }

        # Check if robot is in task
        executing_task = gas_status.get('executingTask', {})
        task_state = gas_status.get('taskState', '').lower()

        # More comprehensive task detection for Gas robots
        is_in_task = (
            bool(executing_task.get('name')) or
            task_state in ['running', 'working', 'executing'] # or gas_status.get('navStatus', '').lower() == 'navigating'
        )

        task_info = None
        if is_in_task:
            task_info = {
                'sn': sn,
                'task_name': executing_task.get('name', ''),
                'task_id': executing_task.get('id', ''),
                'task_state': task_state,
                'progress': executing_task.get('progress', 0),
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
    'get_robot_api',
    'set_customer',
    'get_current_customer',
    'list_customers'
]