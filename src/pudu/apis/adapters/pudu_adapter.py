"""
普渡API适配器 - 包含完整的数据处理逻辑
将pudu_api.py的函数调用和foxx_api.py中的数据处理逻辑整合到适配器中
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
    """普渡API适配器 - 包含完整的数据处理逻辑"""

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

    def get_robot_status(self, sn: str) -> Dict[str, Any]:
        return self.client.get_robot_details(sn)

    def get_list_stores(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return self.client.get_list_stores(limit=limit, offset=offset)

    def get_list_robots(self, shop_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return self.client.get_list_robots(shop_id=shop_id, limit=limit, offset=offset)

    # ==================== Enhanced Methods with Data Processing ====================

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
        包含完整的Pudu数据处理逻辑
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

                # Use the same start_time and end_time as the charging record query
                battery_data = self.client.get_battery_health_list(start_time, end_time, sn=record['sn'])

                soh = None
                cycles = None
                if battery_data and "list" in battery_data and battery_data["list"]:
                    latest_record = max(battery_data["list"], key=lambda x: x.get("upload_time", ""))
                    soh = latest_record.get('soh', None)
                    cycles = latest_record.get('cycle', None)

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

                # Get battery health
                end_time = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                start_time = (datetime.datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

                battery_data = self.client.get_battery_health_list(start_time, end_time, sn=sn)

                soh = None
                cycles = None
                if battery_data and "list" in battery_data and battery_data["list"]:
                    latest_record = max(battery_data["list"], key=lambda x: x.get("upload_time", ""))
                    soh = latest_record.get('soh', None)
                    cycles = latest_record.get('cycle', None)

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
        包含完整的Pudu数据处理逻辑
        """
        # This method requires get_robot_status which has complex logic
        # For now, return empty DataFrame with correct columns
        # Will implement in next iteration
        return pd.DataFrame(columns=[
            'location_id', 'task_name', 'task_id', 'robot_sn', 'map_name', 'is_report', 'map_url',
            'actual_area', 'plan_area', 'start_time', 'end_time', 'duration',
            'efficiency', 'remaining_time', 'battery_usage', 'consumption', 'water_consumption', 'progress', 'status',
            'mode', 'sub_mode', 'type', 'vacuum_speed', 'vacuum_suction',
            'wash_speed', 'wash_suction', 'wash_water'
        ])

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