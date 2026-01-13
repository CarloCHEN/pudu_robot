"""
PUDU API Adapter - Contains complete data processing logic
Integrates function calls from pudu_api.py and data processing logic from foxx_api.py into the adapter
"""

import pandas as pd
import ast
from typing import Dict, List, Optional, Any
import datetime
from datetime import timedelta, timezone
from ..core.api_interface import RobotAPIInterface
from ..raw.pudu_api import create_pudu_api_client


API_NAME = "pudu"


class PuduAdapter(RobotAPIInterface):
    """PUDU API Adapter - Contains complete data processing logic"""

    # Pudu-specific mappings
    STATUS_MAPPING = {
        0: "Not Started",
        1: "In Progress",
        2: "Task Suspended",
        3: "Task Interrupted",
        4: "Task Ended",
        5: "Task Abnormal",
        6: "Task Cancelled"
    }

    MODE_MAPPING = {
        1: "Scrubbing",
        2: "Sweeping"
    }

    SUBMODE_MAPPING = {
        "Sweeping": {
            0: "Custom",
            1: "Carpet Vacuum",
            3: "Silent Dust Push"
        },
        "Scrubbing": {
            0: "Custom",
            1: "Suction Mode",
            11: "Scrubbing Suction",
            12: "Brushing Suction",
            13: "Scrubbing",
            14: "Dry Brushing",
        }
    }

    TYPE_MAPPING = {
        0: "Custom",
        1: "Carpet Vacuuming",
        2: "Silent Dust Pushing"
    }

    VACUUM_SPEED_MAPPING = {
        0: "Off",
        1: "Energy Saving",
        2: "Standard",
        3: "High"
    }

    VACUUM_SUCTION_MAPPING = {
        0: "Off",
        1: "Low",
        2: "Medium",
        3: "High"
    }

    WASH_SPEED_MAPPING = {
        0: "Off",
        1: "Energy Saving",
        2: "Standard",
        3: "High"
    }

    WASH_SUCTION_MAPPING = {
        0: "Off",
        1: "Low",
        2: "Medium",
        3: "High"
    }

    WASH_WATER_MAPPING = {
        0: "Off",
        1: "Low",
        2: "Medium",
        3: "High"
    }

    BATTERY_CAPACITY = 1228.8 / 1000  # kWh

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Create Pudu API client with credentials from config
        api_app_key = self.config.get('api_app_key')
        api_app_secret = self.config.get('api_app_secret')
        self.client = create_pudu_api_client(api_app_key, api_app_secret)

    # ==================== Basic API Methods ====================

    def get_robot_details(self, sn: str) -> Dict[str, Any]:
        return self.client.get_robot_details(sn)

    def get_list_stores(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return self.client.get_list_stores(limit=limit, offset=offset)

    def get_list_robots(self, shop_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return self.client.get_list_robots(shop_id=shop_id, limit=limit, offset=offset)

    # ==================== Helper Methods ====================

    def _get_battery_health_for_shop(self, shop_id: str, start_time: str, end_time: str) -> Dict[str, Dict]:
        """
        Fetch battery health data for ALL robots in a shop at once (single API call)
        Returns a dictionary mapping robot_sn -> battery_health_data

        This dramatically reduces API calls from N (one per robot) to 1 (per shop)
        """
        try:
            # Fetch battery health for entire shop (no sn parameter = all robots)
            battery_data = self.client.get_battery_health_list(
                start_time,
                end_time,
                shop_id=shop_id,
                sn=None  # Don't filter by sn - get all robots
            )

            # Build a lookup dictionary: robot_sn -> latest battery health record
            battery_lookup = {}

            if battery_data and "list" in battery_data and battery_data["list"]:
                # Group records by robot SN and get the latest one
                for record in battery_data["list"]:
                    sn = record.get('sn')
                    if not sn:
                        continue

                    # Keep the record with the latest upload_time for each robot
                    if sn not in battery_lookup:
                        battery_lookup[sn] = record
                    else:
                        # Compare upload times and keep the latest
                        current_time = battery_lookup[sn].get('upload_time', '')
                        new_time = record.get('upload_time', '')
                        if new_time > current_time:
                            battery_lookup[sn] = record

            return battery_lookup

        except Exception as e:
            print(f"Error fetching battery health for shop {shop_id}: {e}")
            return {}

    # ==================== Enhanced Methods with Data Processing ====================
    def get_robot_status(self, sn: str) -> dict:
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
        # Mapping dictionaries (same as in get_schedule_table)
        status_mapping = {
            0: "Not Started",
            1: "In Progress",
            2: "Task Suspended",
            3: "Task Interrupted",
            4: "Task Ended",
            5: "Task Abnormal",
            6: "Task Cancelled"
        }

        mode_mapping = {
            1: "Scrubbing",
            2: "Sweeping"
        }

        submode_mapping = {
            "Sweeping": {
                0: "Custom",
                1: "Carpet Vacuum",
                3: "Silent Dust Push"
            },
            "Scrubbing": {
                0: "Custom",
                1: "Suction Mode",
                11: "Scrubbing Suction",
                12: "Brushing Suction",
                13: "Scrubbing",
                14: "Dry Brushing",
            }
        }

        type_mapping = {
            0: "Custom",
            1: "Carpet Vacuuming",
            2: "Silent Dust Pushing"
        }

        vacuum_speed_mapping = {
            0: "Off",
            1: "Energy Saving",
            2: "Standard",
            3: "High"
        }

        vacuum_suction_mapping = {
            0: "Off",
            1: "Low",
            2: "Medium",
            3: "High"
        }

        wash_speed_mapping = {
            0: "Off",
            1: "Energy Saving",
            2: "Standard",
            3: "High"
        }

        wash_suction_mapping = {
            0: "Off",
            1: "Low",
            2: "Medium",
            3: "High"
        }

        wash_water_mapping = {
            0: "Off",
            1: "Low",
            2: "Medium",
            3: "High"
        }

        try:
            # Call the robot API
            response = self.client.get_robot_details(sn)

            # Check if response is valid
            if not response:
                return {
                    'is_in_task': False,
                    'task_info': None,
                    'position': None
                }

            data = response

            # Extract position (always available)
            position = data.get('position', {})

            # Check if robot is in task
            cleanbot = data.get('cleanbot', {})
            clean_data = cleanbot.get('clean')

            # Robot is in task if clean data exists and is not None/empty
            is_in_task = clean_data is not None and clean_data != {}

            task_info = None
            if is_in_task:
                # Extract basic task information
                task_data = clean_data.get('task', {})
                result_data = clean_data.get('result', {})
                config_data = clean_data.get('config', {})
                map_data = clean_data.get('map', {})

                # Get mode information
                mode_id = clean_data.get('mode', 1)
                mode = mode_mapping.get(mode_id, 'Unknown')

                # Get sub mode (from config)
                sub_mode_id = config_data.get('sub_mode') if config_data else None
                sub_mode = submode_mapping.get(mode, {}).get(sub_mode_id, 'Unknown') if sub_mode_id is not None else 'Unknown'

                # Calculate actual area from plan area and percentage
                plan_area = result_data.get('task_area', 0)
                percentage = result_data.get('percentage', 0)
                actual_area = round(plan_area * (percentage / 100), 2) if plan_area and percentage else 0

                # Calculate efficiency (area per second * 3600 to get per hour)
                clean_time = result_data.get('time', 0)
                if clean_time > 0 and actual_area > 0:
                    efficiency = round((actual_area / clean_time) * 3600, 2)
                else:
                    efficiency = 0

                # Infer start and end time
                current_time = pd.Timestamp.now()
                estimated_start_time = current_time - pd.Timedelta(seconds=clean_time) if clean_time > 0 else current_time
                # Calculate estimated end_time based on remaining time
                remaining_time = result_data.get('remaining_time', 0)
                estimated_end_time = current_time + pd.Timedelta(seconds=remaining_time) if remaining_time > 0 else current_time

                # Convert timestamp to format: 2025-08-15 10:00:00 by flooring to seconds (pd.Timestamp)
                estimated_start_time = estimated_start_time.floor('s')
                estimated_end_time = estimated_end_time.floor('s')

                # Calculate consumption
                battery_capacity = 1228.8 / 1000  # kWh
                cost_battery = result_data.get('cost_battery', 0)
                consumption = round((cost_battery / 100) * battery_capacity, 5) if cost_battery else 0

                # Get status
                status_code = result_data.get('status', 1)
                status = status_mapping.get(status_code, f"Unknown ({status_code})")

                # Extract comprehensive task information with snake_case naming
                task_info = {
                    # Snake_case column names:
                    'location_id': data.get('shop', {}).get('id'),
                    'task_name': task_data.get('name'),
                    'task_id': task_data.get('task_id'),
                    'robot_sn': sn,
                    'map_name': map_data.get('name'),
                    'map_url': '',  # Not available from current API call
                    'actual_area': actual_area,
                    'plan_area': round(plan_area, 2) if plan_area else 0,
                    'start_time': estimated_start_time,  # Not available from current API call
                    'end_time': estimated_end_time,  # Not available from current API call
                    'duration': clean_time,
                    'efficiency': efficiency,
                    'remaining_time': result_data.get('remaining_time', 0),
                    'consumption': consumption,
                    'battery_usage': cost_battery,
                    'water_consumption': result_data.get('cost_water', 0),
                    'progress': round(percentage, 2) if percentage else 0,
                    'status': status,
                    'mode': mode,
                    'sub_mode': sub_mode,
                    'type': type_mapping.get(config_data.get('type', 0), 'Unknown') if config_data else 'Unknown',
                    'vacuum_speed': vacuum_speed_mapping.get(config_data.get('vacuum_speed', 0), 'Unknown') if config_data else 'Unknown',
                    'vacuum_suction': vacuum_suction_mapping.get(config_data.get('vacuum_suction', 0), 'Unknown') if config_data else 'Unknown',
                    'wash_speed': wash_speed_mapping.get(config_data.get('wash_speed', 0), 'Unknown') if config_data else 'Unknown',
                    'wash_suction': wash_suction_mapping.get(config_data.get('wash_suction', 0), 'Unknown') if config_data else 'Unknown',
                    'wash_water': wash_water_mapping.get(config_data.get('wash_water', 0), 'Unknown') if config_data else 'Unknown',

                    # Additional fields for backward compatibility and extra info
                    'map': {
                        'name': map_data.get('name'),
                        'lv': map_data.get('lv'),
                        'floor': map_data.get('floor')
                    }
                }

            return {
                'is_in_task': is_in_task,
                'task_info': task_info,
                'position': position
            }

        except Exception as e:
            # Handle any errors gracefully
            print(f"Error getting robot status: {e}")
            return {
                'is_in_task': False,
                'task_info': None,
                'position': None
            }

    def get_schedule_table(self, start_time: str, end_time: str, location_id: Optional[str] = None,
                          robot_sn: Optional[str] = None, timezone_offset: int = 0) -> pd.DataFrame:
        """
        Get the schedule table for a specified time period, location, and robot
        包含完整的Pudu数据处理逻辑
        """
        # Initialize empty DataFrame with columns
        schedule_df = pd.DataFrame(columns=[
            'Location ID', 'Task Name', 'Task ID', 'Robot SN', 'Map Name', 'Is Report', 'Map URL',
            'Actual Area', 'Plan Area', 'Start Time', 'End Time', 'Duration',
            'Efficiency', 'Remaining Time', 'Consumption', 'Battery Usage', 'Water Consumption', 'Progress', 'Status',
            'Mode', 'Sub Mode', 'Type', 'Vacuum Speed', 'Vacuum Suction',
            'Wash Speed', 'Wash Suction', 'Wash Water'
        ])

        # Get list of stores and filter by location_id if provided
        stores = [shop for shop in self.client.get_list_stores()['list']
                  if location_id is None or shop['shop_id'] == location_id]

        for shop in stores:
            shop_id, shop_name = shop['shop_id'], shop['shop_name']

            # Get all robots for this shop
            shop_robots = self.client.get_list_robots(shop_id=shop_id)['list']
            shop_robots = [robot['sn'] for robot in shop_robots if 'sn' in robot]

            # Filter robots by robot_sn if provided
            if robot_sn is not None:
                shop_robots = [robotSN for robotSN in shop_robots if robotSN == robot_sn]

            # Track which robots have tasks
            robots_with_tasks = set()

            # Get cleaning reports for this shop for the entire period
            results = self.client.get_cleaning_report_list(start_time, end_time, shop_id,
                                               timezone_offset=timezone_offset)['list']

            # Filter by robot_sn if provided
            if robot_sn is not None:
                results = [task for task in results if task['sn'] == robot_sn]

            results = [task for task in results if task['sn'] in shop_robots]

            # Create a dictionary where keys are (task_name, task_id) tuples
            task_report_dict = {}

            for task in results:
                try:
                    # Extract basic task info
                    mode = self.MODE_MAPPING.get(int(task['mode']), 'Unknown')
                    sub_mode = self.SUBMODE_MAPPING.get(mode, {}).get(int(task['sub_mode']), 'Unknown')
                    report_id = task['report_id']
                    task_name = task['task_name']
                    sn = task['sn']

                    # Add to set of robots with tasks
                    robots_with_tasks.add(sn)

                    # Convert times to datetime objects
                    task_start_time = pd.to_datetime(task['start_time'], unit='s')
                    task_end_time = pd.to_datetime(task['end_time'], unit='s')

                    # Get detailed cleaning report
                    report = self.client.get_cleaning_report_detail(
                        start_time, end_time, sn, report_id, shop_id, timezone_offset=timezone_offset
                    )
                    task_id = report['task_id']

                    # Create a unique key combining task name and id
                    task_key = (sn, task_name, task_start_time)

                    # Parse floor list safely
                    try:
                        floor_list = ast.literal_eval(report['floor_list'])
                        floor_area_list = [i['result']['area'] for i in floor_list if 'result' in i and 'area' in i['result']]
                        map_name = floor_list[-1].get('map_name', 'Unknown') if floor_list else 'Unknown'
                        task_result_url = floor_list[-1].get('task_result_url', '') if floor_list else ''
                    except (SyntaxError, ValueError, IndexError, KeyError):
                        floor_area_list = []
                        map_name = 'Unknown'
                        task_result_url = ''

                    # Parse configs
                    try:
                        configs = ast.literal_eval(report['config'])
                        type_val = self.TYPE_MAPPING.get(int(configs.get('type', -1)), 'Unknown')
                        vacuum_speed = self.VACUUM_SPEED_MAPPING.get(int(configs.get('vacuum_speed', -1)), 'Unknown')
                        vacuum_suction = self.VACUUM_SUCTION_MAPPING.get(int(configs.get('vacuum_suction', -1)), 'Unknown')
                        wash_speed = self.WASH_SPEED_MAPPING.get(int(configs.get('wash_speed', -1)), 'Unknown')
                        wash_suction = self.WASH_SUCTION_MAPPING.get(int(configs.get('wash_suction', -1)), 'Unknown')
                        wash_water = self.WASH_WATER_MAPPING.get(int(configs.get('wash_wash', -1)), 'Unknown')
                        if wash_water == 'Unknown':
                            wash_water = self.WASH_WATER_MAPPING.get(int(configs.get('wash_water', -1)), 'Unknown')
                    except (SyntaxError, ValueError, KeyError):
                        type_val = 'Unknown'
                        vacuum_speed = 'Unknown'
                        vacuum_suction = 'Unknown'
                        wash_speed = 'Unknown'
                        wash_suction = 'Unknown'
                        wash_water = 'Unknown'

                    # Create task data entry
                    task_data = pd.DataFrame({
                        'status': [task['status']],
                        'sn': [sn],
                        'task_id': [task_id],
                        'report_id': [report_id],
                        'start_time': [task_start_time],
                        'end_time': [task_end_time],
                        'task_area': [report['task_area']],
                        'clean_area': [task['clean_area']],
                        'report_clean_area': [report['clean_area']],
                        'clean_time': [task['clean_time']],
                        'average_area': [report['average_area']],
                        'percentage': [report['percentage']],
                        'remaining_time': [report['remaining_time']],
                        'cost_water': [report['cost_water']],
                        'cost_battery': [report['cost_battery']],
                        'floor_area_list': [floor_area_list],
                        'map_name': [map_name],
                        'task_result_url': [task_result_url],
                        'mode': [mode],
                        'sub_mode': [sub_mode],
                        'type': [type_val],
                        'vacuum_speed': [vacuum_speed],
                        'vacuum_suction': [vacuum_suction],
                        'wash_speed': [wash_speed],
                        'wash_suction': [wash_suction],
                        'wash_water': [wash_water]
                    })

                    # Add to the task dictionary using the composite key
                    if task_key in task_report_dict:
                        task_report_dict[task_key] = pd.concat([task_report_dict[task_key], task_data])
                    else:
                        task_report_dict[task_key] = task_data

                except Exception as e:
                    print(f"Error processing task: {e}")
                    continue

            # Process each task group and add to the main DataFrame
            for (sn, task_name, task_start_time), task_df in task_report_dict.items():
                try:
                    if task_df.empty:
                        continue

                    # Get the task with the highest completion percentage
                    latest_task = task_df.sort_values(by='percentage', ascending=False).iloc[0]

                    # Format remaining time
                    remaining_time = latest_task['remaining_time']

                    # Format consumption
                    consumption = round((latest_task['cost_battery'] / 100) * self.BATTERY_CAPACITY, 5)
                    water_consumption = latest_task['cost_water']

                    # Format progress as percentage
                    progress = round(latest_task['percentage'], 2)

                    # Map numeric status to string description
                    status_code = latest_task['status']
                    status_str = self.STATUS_MAPPING.get(status_code, f"Unknown ({status_code})")

                    # Format area values
                    plan_area = round(latest_task['task_area'], 2)
                    actual_area = round(plan_area * (latest_task['percentage'] / 100), 2)

                    # Calculate efficiency
                    clean_time = latest_task['clean_time']
                    if clean_time > 0:
                        efficiency_value = (actual_area / clean_time) * 3600
                        efficiency = round(efficiency_value, 2)
                    else:
                        efficiency = 0

                    task_result_url = latest_task['task_result_url']

                    # Create a new entry for this task
                    new_entry = pd.DataFrame({
                        'Location ID': [shop_id],
                        'Task Name': [task_name],
                        'Task ID': [latest_task['task_id']],
                        'Robot SN': [latest_task['sn']],
                        'Map Name': [latest_task['map_name']],
                        'Is Report': [1],
                        'Map URL': [task_result_url],
                        'Actual Area': [actual_area],
                        'Plan Area': [plan_area],
                        'Start Time': [latest_task['start_time']],
                        'End Time': [latest_task['end_time']],
                        'Duration': [clean_time],
                        'Efficiency': [efficiency],
                        'Remaining Time': [remaining_time],
                        'Consumption': [consumption],
                        'Battery Usage': [latest_task['cost_battery']],
                        'Water Consumption': [water_consumption],
                        'Progress': [progress],
                        'Status': [status_str],
                        'Mode': [latest_task['mode']],
                        'Sub Mode': [latest_task['sub_mode']],
                        'Type': [latest_task['type']],
                        'Vacuum Speed': [latest_task['vacuum_speed']],
                        'Vacuum Suction': [latest_task['vacuum_suction']],
                        'Wash Speed': [latest_task['wash_speed']],
                        'Wash Suction': [latest_task['wash_suction']],
                        'Wash Water': [latest_task['wash_water']]
                    })
                    schedule_df = pd.concat([schedule_df, new_entry], ignore_index=True)

                except Exception as e:
                    print(f"Error processing task group {task_name}: {e}")
                    continue

        return schedule_df

    def get_charging_table(self, start_time: str, end_time: str, location_id: Optional[str] = None,
                          robot_sn: Optional[str] = None, timezone_offset: int = 0) -> pd.DataFrame:
        """
        Get charging records for robots within a specified time period and location
        Contains complete PUDU data processing logic

        OPTIMIZED: Fetches battery health data once per shop instead of once per charging record
        """
        # Initialize empty DataFrame
        charging_df = pd.DataFrame(columns=[
            'Location ID', 'Robot Name', 'Robot SN', 'Location',
            'Start Time', 'End Time', 'Duration',
            'Initial Power', 'Final Power', 'Power Gain', 'Battery SOH', 'Battery Cycles', 'Status'
        ])

        # Get list of stores and filter by location_id if provided
        stores = [shop for shop in self.client.get_list_stores()['list']
                  if location_id is None or shop['shop_id'] == location_id]

        for shop in stores:
            shop_id, shop_name = shop['shop_id'], shop['shop_name']

            # Get list of robots in this shop
            shop_robots = self.client.get_list_robots(shop_id=shop_id)['list']
            shop_robots = [robot['sn'] for robot in shop_robots if 'sn' in robot]

            # Get charging records for this shop
            results = self.client.get_charging_record_list(start_time, end_time, shop_id, timezone_offset=timezone_offset)['list']
            results = [record for record in results if 'sn' in record and record['sn'] in shop_robots]

            # ✅ OPTIMIZATION: Fetch battery health for ALL robots in this shop at once (1 API call)
            battery_health_lookup = self._get_battery_health_for_shop(shop_id, start_time, end_time)

            # Process each charging record
            for record in results:
                # Skip if record is outside the specified time范围
                if record['task_time'] > end_time or record['task_time'] < start_time:
                    continue

                # Skip if SN filter is applied and doesn't match
                if robot_sn is not None and record['sn'] != robot_sn:
                    continue

                # Calculate timing information
                task_start_time = pd.to_datetime(record['task_time'])
                duration_seconds = record['charge_duration']
                task_end_time = task_start_time + pd.Timedelta(seconds=duration_seconds)

                # Calculate power information
                initial_power = record['min_power_percent']
                final_power = record['max_power_percent']
                power_gain = final_power - initial_power

                # Get robot name
                robot_details = self.client.get_robot_details(record['sn'])
                robot_name = robot_details.get('nickname', f"{shop_name}_{record['product_code']}")

                # ✅ OPTIMIZATION: Look up battery health from cached data (no API call)
                soh = None
                cycles = None
                robot_battery_data = battery_health_lookup.get(record['sn'])
                if robot_battery_data:
                    soh = robot_battery_data.get('soh', None)
                    cycles = robot_battery_data.get('cycle', None)

                # Create a new entry for this charging record
                new_entry = pd.DataFrame({
                    'Location ID': [shop_id],
                    'Robot Name': [robot_name],
                    'Robot SN': [record['sn']],
                    'Location': [shop_name],
                    'Start Time': [task_start_time],
                    'End Time': [task_end_time],
                    'Duration': [duration_seconds],
                    'Initial Power': [f"{initial_power}%"],
                    'Final Power': [f"{final_power}%"],
                    'Power Gain': [f"+{power_gain}%"],
                    'Battery SOH': [f"{soh}%" if soh is not None else None],
                    'Battery Cycles': [cycles],
                    'Status': ['Done']
                })

                charging_df = pd.concat([charging_df, new_entry], ignore_index=True)

        return charging_df.drop(columns=['Location ID', 'Location'])

    def get_events_table(self, start_time: str, end_time: str, location_id: Optional[str] = None,
                        robot_sn: Optional[str] = None, error_levels: Optional[str] = None,
                        error_types: Optional[str] = None, timezone_offset: int = 0) -> pd.DataFrame:
        """
        Get the events table for robots within a specified time period
        包含完整的Pudu数据处理逻辑
        """
        from ..utils import convert_technical_string

        # Initialize empty DataFrame
        events_df = pd.DataFrame(columns=[
            'Location ID', 'Robot SN', 'Robot Name', 'Location', 'Event Level', 'Event Type',
            'Event Detail', 'Error ID', 'Task Time', 'Upload Time', 'Product Code',
            'MAC Address', 'Software Version', 'Hardware Version', 'OS Version', 'Event UUID'
        ])

        # Get list of stores and filter by location_id if provided
        all_shops = self.client.get_list_stores()['list']
        stores = [shop for shop in all_shops if location_id is None or shop['shop_id'] == location_id]

        all_events = []

        for shop in stores:
            shop_id, shop_name = shop['shop_id'], shop['shop_name']

            # Get list of robots in this shop
            try:
                shop_robots = self.client.get_list_robots(shop_id=shop_id)['list']
                shop_robots_sn = [robot['sn'] for robot in shop_robots if 'sn' in robot]

                # Filter by robot_sn if provided
                if robot_sn is not None:
                    shop_robots_sn = [sn for sn in shop_robots_sn if sn == robot_sn]
                    shop_robots = [robot for robot in shop_robots if robot.get('sn') == robot_sn]

                # Skip if no robots match our criteria
                if not shop_robots_sn:
                    continue

            except Exception as e:
                print(f"Error getting robots for shop {shop_id}: {e}")
                continue

            # Get events for this shop
            try:
                events_response = self.client.get_event_list(
                    start_time=start_time,
                    end_time=end_time,
                    shop_id=shop_id,
                    error_levels=error_levels,
                    error_types=error_types,
                    timezone_offset=timezone_offset
                )

                events_list = events_response.get('list', [])

                # Filter events by robot_sn if specified
                if robot_sn is not None:
                    events_list = [event for event in events_list if event.get('sn') == robot_sn]
                else:
                    # Filter events to only include robots from this shop
                    events_list = [event for event in events_list if event.get('sn') in shop_robots_sn]

                # Process each event
                for event in events_list:
                    try:
                        # Map event level to UI format and convert to lowercase
                        error_level = event.get('error_level', 'INFO').lower()

                        # Create event entry
                        event_entry = {
                            'Location ID': shop_id,
                            'Location': shop_name,
                            'Robot SN': event.get('sn', ''),
                            'Event Level': error_level,
                            'Event Type': convert_technical_string(event.get('error_type', '')),
                            'Event Detail': convert_technical_string(event.get('error_detail', '')),
                            'Task Time': event.get('task_time', ''),
                            'Upload Time': event.get('upload_time', ''),
                            'Product Code': event.get('product_code', ''),
                            'MAC Address': event.get('mac', ''),
                            'Software Version': event.get('soft_version', ''),
                            'Hardware Version': event.get('hard_version', 'Not specified'),
                            'OS Version': event.get('os_version', ''),
                            'Error ID': event.get('error_id', ''),
                            'Event ID': event.get('id', '')
                        }

                        all_events.append(event_entry)

                    except Exception as e:
                        print(f"Error processing event: {e}")
                        continue

            except Exception as e:
                print(f"Error getting events for shop {shop_id}: {e}")
                continue

        # Create DataFrame from all events
        if all_events:
            events_df = pd.DataFrame(all_events)
            # Sort by upload time (most recent first)
            events_df = events_df.sort_values('Upload Time', ascending=False).reset_index(drop=True)

        return events_df.drop(columns=['Location', 'Location ID'])

    def get_robot_status_table(self, location_id: Optional[str] = None, robot_sn: Optional[str] = None) -> pd.DataFrame:
        """
        Get a simplified table for robots with basic information

        OPTIMIZED: Fetches battery health data once per shop instead of once per robot
        """
        robot_df = pd.DataFrame(columns=['Robot SN', 'Water Level', 'Sewage Level', 'Battery Level', 'Battery SOH', 'Battery Cycles',
                                        'Status', 'Timestamp UTC'])
        all_shops = self.client.get_list_stores()['list']

        for shop in all_shops:
            shop_id, shop_name = shop['shop_id'], shop['shop_name']

            # Skip if location_id is specified and doesn't match current shop
            if location_id is not None and shop_id != location_id:
                continue

            # Get the list of robots for this shop
            shop_robots = self.client.get_list_robots(shop_id=shop_id)['list']

            # ✅ OPTIMIZATION: Fetch battery health for ALL robots in this shop at once (1 API call)
            end_time = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            start_time = (datetime.datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            battery_health_lookup = self._get_battery_health_for_shop(shop_id, start_time, end_time)

            # Process each robot in the shop
            for robot in shop_robots:
                sn = robot['sn']

                # Skip if robot_sn is specified and doesn't match current robot
                if robot_sn is not None and sn != robot_sn:
                    continue

                # Get robot details
                robot_details = self.client.get_robot_details(sn)

                # Get robot status
                is_online = str(robot_details.get('online', '')).strip().lower() == 'true'
                status = 'Online' if is_online else 'Offline'

                # Get battery percentage
                battery_percentage = robot_details.get('battery', None)

                # Get water and sewage percentage
                water_percentage, sewage_percentage = None, None
                if 'cleanbot' in robot_details:
                    water_percentage = robot_details['cleanbot'].get('rising', None)
                    sewage_percentage = robot_details['cleanbot'].get('sewage', None)

                # Get robot name (nickname)
                robot_name = robot_details.get('nickname', f"{shop_name}_{sn}")

                # ✅ OPTIMIZATION: Look up battery health from cached data (no API call)
                soh = None
                cycles = None
                robot_battery_data = battery_health_lookup.get(sn)
                if robot_battery_data:
                    soh = robot_battery_data.get('soh', None)
                    cycles = robot_battery_data.get('cycle', None)

                # Create a row for this robot
                robot_row = pd.DataFrame({
                    'Robot SN': [sn],
                    'Water Level': [water_percentage],
                    'Sewage Level': [sewage_percentage],
                    'Battery Level': [battery_percentage],
                    'Battery SOH': [f"{soh}%" if soh is not None else None],
                    'Battery Cycles': [cycles],
                    'Status': [status],
                    'Timestamp UTC': [pd.Timestamp.now(tz='UTC')]
                })

                # Add to the main dataframe
                robot_df = pd.concat([robot_df, robot_row], ignore_index=True)

        return robot_df

    def get_ongoing_tasks_table(self, location_id: Optional[str] = None, robot_sn: Optional[str] = None) -> pd.DataFrame:
        """
        Get ongoing tasks for all robots
        """
        ongoing_tasks_df = pd.DataFrame(columns=[
            'location_id', 'task_name', 'task_id', 'robot_sn', 'map_name', 'is_report', 'map_url',
            'actual_area', 'plan_area', 'start_time', 'end_time', 'duration',
            'efficiency', 'remaining_time', 'battery_usage', 'consumption', 'water_consumption', 'progress', 'status',
            'mode', 'sub_mode', 'type', 'vacuum_speed', 'vacuum_suction',
            'wash_speed', 'wash_suction', 'wash_water'
        ])

        # Get all stores
        all_shops = self.client.get_list_stores()['list']

        for shop in all_shops:
            shop_id = shop['shop_id']

            # Skip if location_id is specified and doesn't match current shop
            if location_id is not None and shop_id != location_id:
                continue

            try:
                # Get robots for this shop
                shop_robots = self.client.get_list_robots(shop_id=shop_id)['list']

                for robot in shop_robots:
                    sn = robot.get('sn')
                    if not sn:
                        continue
                    # Skip if robot_sn is specified and doesn't match current robot
                    if robot_sn is not None and sn != robot_sn:
                        continue
                    try:
                        # Get robot status including task information
                        robot_status = self.get_robot_status(sn)

                        if robot_status['is_in_task'] and robot_status['task_info']:
                            task_info = robot_status['task_info']

                            # Add ongoing task to DataFrame with is_report=0
                            ongoing_task_row = pd.DataFrame({
                                'location_id': [task_info.get('location_id')],
                                'task_name': [task_info.get('task_name')],
                                'task_id': [task_info.get('task_id')],
                                'robot_sn': [task_info.get('robot_sn')],
                                'map_name': [task_info.get('map_name')],
                                'is_report': [0],  # Mark as ongoing task
                                'map_url': [task_info.get('map_url', '')],  # Empty for ongoing tasks
                                'actual_area': [task_info.get('actual_area')],
                                'plan_area': [task_info.get('plan_area')],
                                'start_time': [task_info.get('start_time')],
                                'end_time': [task_info.get('end_time')],
                                'duration': [task_info.get('duration')],
                                'efficiency': [task_info.get('efficiency')],
                                'remaining_time': [task_info.get('remaining_time')],
                                'battery_usage': [task_info.get('battery_usage')],
                                'consumption': [task_info.get('consumption')],
                                'water_consumption': [task_info.get('water_consumption')],
                                'progress': [task_info.get('progress')],
                                'status': [task_info.get('status')],
                                'mode': [task_info.get('mode')],
                                'sub_mode': [task_info.get('sub_mode')],
                                'type': [task_info.get('type')],
                                'vacuum_speed': [task_info.get('vacuum_speed')],
                                'vacuum_suction': [task_info.get('vacuum_suction')],
                                'wash_speed': [task_info.get('wash_speed')],
                                'wash_suction': [task_info.get('wash_suction')],
                                'wash_water': [task_info.get('wash_water')]
                            })
                            ongoing_tasks_df = pd.concat([ongoing_tasks_df, ongoing_task_row], ignore_index=True)

                    except Exception as e:
                        continue

            except Exception as e:
                continue

        return ongoing_tasks_df

    def get_robot_work_location_and_mapping_data(self) -> tuple:
        """
        Get robot work location data and map floor mapping data in a single pass
        包含完整的Pudu数据处理逻辑

        Returns:
            tuple: (work_location_df, mapping_df)
        """
        # Use lists to collect data instead of repeated concatenation
        work_location_rows = []
        map_floor_data = {}
        current_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

        # Get all stores
        all_shops = self.client.get_list_stores()['list']

        for shop in all_shops:
            shop_id = shop['shop_id']

            try:
                shop_robots = self.client.get_list_robots(shop_id=shop_id)['list']

                for robot in shop_robots:
                    sn = robot.get('sn')
                    if not sn:
                        continue

                    try:
                        robot_details = self.client.get_robot_details(sn)

                        if not robot_details:
                            continue

                        # Check if robot is in task
                        cleanbot = robot_details.get('cleanbot', {})
                        clean_data = cleanbot.get('clean')
                        is_in_task = clean_data is not None and clean_data != {}

                        if is_in_task:
                            map_data = clean_data.get('map', {})
                            position = robot_details.get('position', {})

                            map_name = map_data.get('name')
                            floor_number = map_data.get('floor')
                            x = position.get('x')
                            y = position.get('y')
                            z = position.get('z')

                            if map_name and x is not None and y is not None and z is not None:
                                # Append to list
                                work_location_rows.append({
                                    'robot_sn': sn,
                                    'map_name': map_name,
                                    'x': x,
                                    'y': y,
                                    'z': z,
                                    'status': 'normal',
                                    'update_time': current_time
                                })

                            if map_name and floor_number:
                                map_floor_data[map_name] = floor_number
                        else:
                            # Append idle status
                            work_location_rows.append({
                                'robot_sn': sn,
                                'map_name': None,
                                'x': None,
                                'y': None,
                                'z': None,
                                'status': 'idle',
                                'update_time': current_time
                            })

                    except Exception as e:
                        continue

            except Exception as e:
                continue

        # Create DataFrames from collected data
        work_location_df = pd.DataFrame(work_location_rows)

        # Handle mapping data
        mapping_rows = [{'map_name': map_name, 'floor_number': floor_number}
                       for map_name, floor_number in map_floor_data.items()]
        mapping_df = pd.DataFrame(mapping_rows)

        return work_location_df, mapping_df


def create_adapter(config: Optional[Dict[str, Any]] = None) -> PuduAdapter:
    """创建普渡API适配器实例"""
    return PuduAdapter(config)