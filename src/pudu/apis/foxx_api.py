import pandas as pd
import ast
from .pudu_api import *
from .utils import convert_technical_string

# 5 api functions: get_location_table, get_robot_status_table, get_robot_table (deprecated), get_events_table, get_schedule_table, get_charging_table, get_task_overview_data (deprecated)

def get_robot_status(sn):
    """
    Get robot status and comprehensive task information.

    Args:
        sn: Robot serial number

    Returns:
        dict: {
            'is_in_task': bool,
            'task_info': dict or None,
            'position': dict
        }
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
        response = get_robot_details(sn)

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
            estimated_end_time = current_time + pd.Timedelta(seconds=result_data.get('remaining_time', 0)) if result_data.get('remaining_time', 0) > 0 else None
            # Convert timestamp to format: 2025-08-15 10:00:00
            estimated_start_time = estimated_start_time.strftime('%Y-%m-%d %H:%M:%S')
            estimated_end_time = estimated_end_time.strftime('%Y-%m-%d %H:%M:%S')

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

def get_ongoing_tasks_table(location_id=None, robot_sn=None):
    """
    Get ongoing tasks for all robots by calling get_robot_status for each robot.
    Returns a DataFrame with ongoing task information with is_report=0.
    """
    ongoing_tasks_df = pd.DataFrame(columns=[
        'location_id', 'task_name', 'task_id', 'robot_sn', 'map_name', 'is_report', 'map_url',
        'actual_area', 'plan_area', 'start_time', 'end_time', 'duration',
        'efficiency', 'remaining_time', 'battery_usage', 'consumption', 'water_consumption', 'progress', 'status',
        'mode', 'sub_mode', 'type', 'vacuum_speed', 'vacuum_suction',
        'wash_speed', 'wash_suction', 'wash_water'
    ])

    # Get all stores
    all_shops = get_list_stores()['list']

    for shop in all_shops:
        shop_id = shop['shop_id']

        # Skip if location_id is specified and doesn't match current shop
        if location_id is not None and shop_id != location_id:
            continue

        try:
            # Get robots for this shop
            shop_robots = get_list_robots(shop_id=shop_id)['list']

            for robot in shop_robots:
                sn = robot.get('sn')
                if not sn:
                    continue
                # Skip if robot_sn is specified and doesn't match current robot
                if robot_sn is not None and sn != robot_sn:
                    continue
                try:
                    # Get robot status including task information
                    robot_status = get_robot_status(sn)

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

def get_robot_work_location_and_mapping_data():
    """
    Get robot work location data, map floor mapping data, and current task schedule data in a single pass.
    """
    # Use lists to collect data instead of repeated concatenation
    work_location_rows = []
    map_floor_data = {}
    current_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

    # Get all stores
    all_shops = get_list_stores()['list']

    for shop in all_shops:
        shop_id = shop['shop_id']

        try:
            shop_robots = get_list_robots(shop_id=shop_id)['list']

            for robot in shop_robots:
                sn = robot.get('sn')
                if not sn:
                    continue

                try:
                    robot_status = get_robot_status(sn)

                    if robot_status['is_in_task'] and robot_status['task_info']:
                        task_info = robot_status['task_info']
                        position = robot_status['position']

                        if task_info.get('map') and position:
                            map_name = task_info['map'].get('name')
                            floor_number = task_info['map'].get('floor')
                            x = position.get('x')
                            y = position.get('y')
                            z = position.get('z')

                            if map_name and x is not None and y is not None and z is not None:
                                # Append to list instead of concatenating
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

def get_location_table():
    """
    Get the table for locations with location_id and location_name.
    """
    location_df = pd.DataFrame(columns=['Building ID', 'Building Name'])
    all_shops = get_list_stores()['list']
    for shop in all_shops:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']
        location_df = pd.concat([location_df, pd.DataFrame({'Building ID': [shop_id], 'Building Name': [shop_name]})], ignore_index=True)
    return location_df

def get_robot_status_table(location_id=None, robot_sn=None):
    """
    Get a simplified table for robots with basic information.
    Only uses get_robot_details() to get robot SN, nickname, status, and location info.
    """
    robot_df = pd.DataFrame(columns=['Location ID', 'Robot SN', 'Robot Name', 'Robot Type', 'Water Level', 'Sewage Level', 'Battery Level', 'x', 'y', 'z', 'Status'])
    all_shops = get_list_stores()['list']

    for shop in all_shops:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']

        # Skip if location_id is specified and doesn't match current shop
        if location_id is not None and shop_id != location_id:
            continue

        # Get the list of robots for this shop
        shop_robots = get_list_robots(shop_id=shop_id)['list']

        # Process each robot in the shop
        for robot in shop_robots:
            sn = robot['sn']

            # Skip if robot_sn is specified and doesn't match current robot
            if robot_sn is not None and sn != robot_sn:
                continue

            # Get robot details
            robot_details = get_robot_details(sn)

            # Get robot status
            is_online = str(robot_details.get('online', '')).strip().lower() == 'true'
            status = 'Online' if is_online else 'Offline'
            # get battery percentage
            battery_percentage = robot_details.get('battery', None)
            # get water and sewage percentage
            water_percentage, sewage_percentage = None, None
            if 'cleanbot' in robot_details:
                water_percentage = robot_details['cleanbot'].get('rising', None)
                sewage_percentage = robot_details['cleanbot'].get('sewage', None)

            # Get robot name (nickname)
            robot_name = robot_details.get('nickname', f"{shop_name}_{sn}")

            # Create a row for this robot
            robot_row = pd.DataFrame({
                'Location ID': [shop_id],
                'Robot SN': [sn],
                'Robot Name': [robot_name],
                'Robot Type': ['CC1'],
                'Water Level': [water_percentage],
                'Sewage Level': [sewage_percentage],
                'Battery Level': [battery_percentage],
                'x': [robot_details.get('position', {}).get('x', None)],
                'y': [robot_details.get('position', {}).get('y', None)],
                'z': [robot_details.get('position', {}).get('z', None)],
                'Status': [status]
            })

            # Add to the main dataframe
            robot_df = pd.concat([robot_df, robot_row], ignore_index=True)

    # If robot_sn was specified but not found in the data, return empty DataFrame with same columns
    if robot_sn is not None and robot_df.empty:
        return pd.DataFrame(columns=['Location ID', 'Robot SN', 'Robot Name', 'Robot Type', 'Water Level', 'Sewage Level', 'Battery Level', 'Status'])

    return robot_df

def get_robot_table(start_time, end_time, location_id=None, robot_sn=None, timezone_offset=0):
    """
    Get the table for robots.
    get_machine_run_analytics_list() is used to get the running hours, mileage, and task count of the robot.
    get_robot_details() is used to get the water level, sewage level, and battery level of the robot.
    get_cleaning_report_list() is used to get the area of the robot.
    """
    task_status_mapping = {
        0: "Not Started",
        1: "In Progress",
        2: "Task Suspended",
        3: "Task Interrupted",
        4: "Task Ended",
        5: "Task Abnormal",
        6: "Task Cancelled"
    }
    robot_df = pd.DataFrame(columns=['Location ID', 'Robot Type', 'Robot Name', 'Robot SN', 'Current Task', 'Total Task', 'Total Running Hours', \
                                     'Total Mileage', 'Total Area', 'Water Level', 'Sewage Level', 'Battery Level', 'Status'])
    all_shops = get_list_stores()['list']

    for shop in all_shops:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']

        # Skip if location_id is specified and doesn't match current shop
        if location_id is not None and shop_id != location_id:
            continue

        location = shop_name

        # Get the list of robots for this shop
        shop_robots = get_list_robots(shop_id=shop_id)['list']

        # Get analytics data for this shop
        analytics_data = get_machine_run_analytics_list(start_time=start_time, end_time=end_time, shop_id=shop_id, time_unit='day', timezone_offset=0)['list']

        # Group analytics data by SN
        sn_groups = {}
        for entry in analytics_data:
            if entry['shop_id'] != shop_id:
                continue
            if entry['sn'] not in sn_groups:
                sn_groups[entry['sn']] = []
            sn_groups[entry['sn']].append(entry)

        # Process each robot in the shop
        for robot in shop_robots:
            sn = robot['sn']

            # Skip if robot_sn is specified and doesn't match current robot
            if robot_sn is not None and sn != robot_sn:
                continue

            # get robot details
            robot_details = get_robot_details(sn)
            # get robot status

            is_online = str(robot_details.get('online', '')).strip().lower() == 'true'
            status = 'Online' if is_online else 'Offline'
            # get battery percentage
            battery_percentage = robot_details.get('battery', None)
            # get water and sewage percentage
            water_percentage, sewage_percentage = None, None
            if 'cleanbot' in robot_details:
                water_percentage = robot_details['cleanbot'].get('rising', None)
                sewage_percentage = robot_details['cleanbot'].get('sewage', None)

            # Check if we have analytics data for this robot
            if sn in sn_groups and sn_groups[sn]:
                info_list = sn_groups[sn]
                robot_type = info_list[0]['product_code']
                total_run_hours = sum([i['duration'] for i in info_list])
                total_mileage_km = sum([i['mileage'] for i in info_list])
                total_task = sum([i['task_count'] for i in info_list])
            else:
                # No analytics data, use defaults
                robot_type = "CC1"  # Or try to get from other API if available
                total_run_hours = 0
                total_mileage_km = 0
                total_task = 0
            # get robot name
            robot_name = robot_details.get('nickname', f"{shop_name}_{robot_type}")
            # Get cleaning reports for this SN
            try:
                clean_reports = get_cleaning_report_list(start_time=start_time, end_time=end_time,
                                                        shop_id=shop_id, sn=sn,
                                                        timezone_offset=timezone_offset)['list']

                # Filter reports within time range and sort by creation time
                filtered_reports = [r for r in clean_reports if start_time <= r['create_time'] <= end_time and r['sn'] == sn]
                sorted_reports = sorted(filtered_reports, key=lambda x: x['create_time'], reverse=True)
            except Exception:
                filtered_reports = []
                sorted_reports = []

            # Set defaults
            current_task = 'No Task'
            total_area = 0

            # Calculate area and time, get most recent task
            if sorted_reports:

                total_area = sum([r['clean_area'] for r in sorted_reports])
                current_task_status = task_status_mapping.get(sorted_reports[0]['status'], 'Unknown')
                if current_task_status == 'In Progress':
                    current_task = sorted_reports[0]['task_name']

            # Create a row for this robot
            robot_row = pd.DataFrame({
                'Location ID': [shop_id],
                'Robot Type': [robot_type],
                'Robot Name': [robot_name],
                'Robot SN': [sn],
                'Current Task': [current_task],
                'Total Task': [total_task],
                'Total Running Hours': [total_run_hours], # h
                'Total Mileage': [total_mileage_km], # km
                'Total Area': [total_area], # m²
                'Water Level': [water_percentage], # %
                'Sewage Level': [sewage_percentage], # %
                'Battery Level': [battery_percentage], # %
                'Status': [status] # Online, Offline
            })

            # Add to the main dataframe
            robot_df = pd.concat([robot_df, robot_row], ignore_index=True)

    # If robot_sn was specified but not found in the data, return empty DataFrame with same columns
    if robot_sn is not None and robot_df.empty:
        return pd.DataFrame(columns=['Location ID', 'Robot Type', 'Robot Name', 'Robot SN', 'Current Task', 'Total Task', 'Total Running Hours', 'Total Mileage', 'Total Area', 'Status'])

    return robot_df

def get_events_table(start_time, end_time, location_id=None, robot_sn=None, error_levels=None, error_types=None, timezone_offset=0):
    """
    Get the events table for robots within a specified time period.

    Parameters:
        start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id (int, optional): The location ID. Defaults to None.
        robot_sn (str, optional): The robot serial number. Defaults to None.
        error_levels (str, optional): Comma-separated error levels (e.g., 'WARNING,ERROR'). Defaults to None.
        error_types (str, optional): Comma-separated error types (e.g., 'LostLocalization'). Defaults to None.
        timezone_offset (int, optional): Timezone offset in hours. Defaults to 0.

    Returns:
        pd.DataFrame: DataFrame with event data ready for database insertion
    """
    # Initialize empty DataFrame
    events_df = pd.DataFrame(columns=[
        'Location ID', 'Robot SN', 'Robot Name', 'Location', 'Event Level', 'Event Type',
        'Event Detail', 'Error ID', 'Task Time', 'Upload Time', 'Product Code',
        'MAC Address', 'Software Version', 'Hardware Version', 'OS Version', 'Event UUID'
    ])

    # Get list of stores and filter by location_id if provided
    all_shops = get_list_stores()['list']
    stores = [shop for shop in all_shops if location_id is None or shop['shop_id'] == location_id]

    all_events = []

    for shop in stores:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']

        # Get list of robots in this shop
        try:
            shop_robots = get_list_robots(shop_id=shop_id)['list']
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
            events_response = get_event_list(
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

def get_schedule_table(start_time, end_time, location_id=None, robot_sn=None, timezone_offset=0):
    '''
    Get the schedule table for a specified time period, location, and robot

    Parameters:
        start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id (int, optional): The location ID. Defaults to None.
        robot_sn (str, optional): The robot serial number. Defaults to None.
        timezone_offset (int, optional): The timezone offset in hours. Defaults to 0.

    Returns:
        pd.DataFrame: The schedule table
    '''
    # Map status codes to descriptive strings
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
        "Sweeping" : {
            0: "Custom",
            1: "Carpet Vacuum",
            3: "Silent Dust Push"
        },
        "Scrubbing" : {
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


    # Initialize empty DataFrame with columns
    schedule_df = pd.DataFrame(columns=[
        'Location ID', 'Task Name', 'Task ID', 'Robot SN', 'Map Name', 'Is Report', 'Map URL',
        'Actual Area', 'Plan Area', 'Start Time', 'End Time', 'Duration',
        'Efficiency', 'Remaining Time', 'Consumption', 'Battery Usage', 'Water Consumption', 'Progress', 'Status',
        'Mode', 'Sub Mode', 'Type', 'Vacuum Speed', 'Vacuum Suction',
        'Wash Speed', 'Wash Suction', 'Wash Water'
    ])

    # Get list of stores and filter by location_id if provided
    stores = [shop for shop in get_list_stores()['list']
              if location_id is None or shop['shop_id'] == location_id]

    for shop in stores:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']

        # Get all robots for this shop
        shop_robots = get_list_robots(shop_id=shop_id)['list']
        shop_robots = [robot['sn'] for robot in shop_robots if 'sn' in robot]


        # Filter robots by robot_sn if provided
        if robot_sn is not None:
            shop_robots = [robotSN for robotSN in shop_robots if robotSN == robot_sn]

        # Track which robots have tasks
        robots_with_tasks = set()

        # Get cleaning reports for this shop for the entire period
        results = get_cleaning_report_list(start_time, end_time, shop_id,
                                           timezone_offset=timezone_offset)['list']

        # Filter by robot_sn if provided (redundant but keeping for safety)
        if robot_sn is not None:
            results = [task for task in results if task['sn'] == robot_sn]

        results = [task for task in results if task['sn'] in shop_robots]

        # Create a dictionary where keys are (task_name, task_id) tuples
        # This ensures tasks with the same name on different days remain separate
        task_report_dict = {}

        for task in results:
            try:
                # Extract basic task info
                mode = mode_mapping.get(int(task['mode']), 'Unknown')
                sub_mode = submode_mapping.get(mode, {}).get(int(task['sub_mode']), 'Unknown')
                report_id = task['report_id']
                task_name = task['task_name']
                sn = task['sn']

                # Add to set of robots with tasks
                robots_with_tasks.add(sn)

                # Convert times to datetime objects
                task_start_time = pd.to_datetime(task['start_time'], unit='s')
                task_end_time = pd.to_datetime(task['end_time'], unit='s')

                # Get detailed cleaning report
                report = get_cleaning_report_detail(
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
                    type = type_mapping.get(int(configs.get('type', -1)), 'Unknown')
                    vacuum_speed = vacuum_speed_mapping.get(int(configs.get('vacuum_speed', -1)), 'Unknown')
                    vacuum_suction = vacuum_suction_mapping.get(int(configs.get('vacuum_suction', -1)), 'Unknown')
                    wash_speed = wash_speed_mapping.get(int(configs.get('wash_speed', -1)), 'Unknown')
                    wash_suction = wash_suction_mapping.get(int(configs.get('wash_suction', -1)), 'Unknown')
                    wash_water = wash_water_mapping.get(int(configs.get('wash_wash', -1)), 'Unknown')
                    if wash_water == 'Unknown':
                        wash_water = wash_water_mapping.get(int(configs.get('wash_water', -1)), 'Unknown')
                except (SyntaxError, ValueError, KeyError):
                    type = 'Unknown'
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
                    'type': [type],
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
                # Log error and continue with next task
                print(f"Error processing task: {e}")
                continue

        # Process each task group and add to the main DataFrame
        for (sn, task_name, task_start_time), task_df in task_report_dict.items():
            try:
                # Skip empty dataframes
                if task_df.empty:
                    continue

                # Get the task with the highest completion percentage
                latest_task = task_df.sort_values(by='percentage', ascending=False).iloc[0]

                # Format remaining time as Xh YYmin
                remaining_time = latest_task['remaining_time']

                # Format consumption (already in %)
                battery_capacity = 1228.8 / 1000 # kWh
                consumption = round((latest_task['cost_battery'] / 100)* battery_capacity, 5)  # kWh

                water_consumption = latest_task['cost_water'] # mL

                # Format progress as percentage
                progress = round(latest_task['percentage'], 2)

                # Map numeric status to string description
                status_code = latest_task['status']
                status_str = status_mapping.get(status_code, f"Unknown ({status_code})")

                # Format area values
                plan_area = round(latest_task['task_area'], 2)
                actual_area = round(plan_area * (latest_task['percentage'] / 100), 2) #round(latest_task['clean_area'], 2)

                # Calculate efficiency in 100m²/h format:
                # Convert m² to 100m² and convert seconds to hours
                clean_time = latest_task['clean_time']
                if clean_time > 0:
                    # m² per second * 3600 seconds/hour / 100 = 100m²/h
                    efficiency_value = (actual_area / clean_time) * 3600 #(latest_task['clean_area'] / clean_time) * 3600
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
                # Add to main DataFrame
                schedule_df = pd.concat([schedule_df, new_entry], ignore_index=True)

            except Exception as e:
                # Log error and continue with next task group
                print(f"Error processing task group {task_name}: {e}")
                continue
    return schedule_df

def get_charging_table(start_time, end_time, location_id=None, robot_sn=None, timezone_offset=0):
    """
    Get charging records for robots within a specified time period and location.

    Parameters:
        start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id (int or None): The location ID to filter by, or None for all locations
        sn (str or None): The robot serial number to filter by, or None for all robots

    Returns:
        pd.DataFrame: DataFrame containing charging records with battery health data
    """
    # Initialize empty DataFrame with columns including battery health data
    charging_df = pd.DataFrame(columns=[
        'Location ID', 'Robot Name', 'Robot SN', 'Location',
        'Start Time', 'End Time', 'Duration',
        'Initial Power', 'Final Power', 'Power Gain'
        # 'Battery Cycle', 'SOH'
    ])

    # Get list of stores and filter by location_id if provided
    stores = [shop for shop in get_list_stores()['list']
              if location_id is None or shop['shop_id'] == location_id]

    for shop in stores:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']
        # Get list of robots in this shop
        shop_robots = get_list_robots(shop_id=shop_id)['list']
        shop_robots = [robot['sn'] for robot in shop_robots if 'sn' in robot]

        # Get charging records for this shop
        results = get_charging_record_list(start_time, end_time, shop_id, timezone_offset=timezone_offset)['list']
        results = [record for record in results if 'sn' in record and record['sn'] in shop_robots]

        # Get battery health data for this shop
        try:
            battery_health_data = get_battery_health_list(start_time, end_time, shop_id, timezone_offset=timezone_offset)['list']
            # Create a dictionary for quick lookup by sn and task_time
            battery_health_dict = {}
            for health_record in battery_health_data:
                key = health_record['sn']
                battery_health_dict[key] = {
                    'cycle': health_record.get('cycle', None),
                    'soh': health_record.get('soh', None)
                }
        except Exception as e:
            print(f"Error getting battery health data for shop {shop_id}: {e}")
            battery_health_dict = {}

        # Process each charging record
        for record in results:
            # Skip if record is outside the specified time range
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

            # Format duration as hours and minutes
            hours = int(duration_seconds / 3600)
            minutes = int((duration_seconds % 3600) / 60)
            formatted_duration = f"{hours}h {minutes:02d}min"

            # Get battery health data for this record
            health_key = record['sn']
            battery_health = battery_health_dict.get(health_key, {'cycle': None, 'soh': None})

            robot_details = get_robot_details(record['sn'])
            robot_name = robot_details.get('nickname', f"{shop_name}_{record['product_code']}")

            # Create a new entry for this charging record
            new_entry = pd.DataFrame({
                'Location ID': [shop_id],  # Using shop_id as part of the identifier
                'Robot Name': [robot_name],
                'Robot SN': [record['sn']],
                'Location': [shop_name],
                'Start Time': [task_start_time],
                'End Time': [task_end_time],
                'Duration': [formatted_duration],
                'Initial Power': [f"{initial_power}%"],
                'Final Power': [f"{final_power}%"],
                'Power Gain': [f"+{power_gain}%"],
                'Status': ['Done']
                # 'Battery Cycle': [battery_health['cycle']],
                # 'SOH': [battery_health['soh']]
            })

            # Add to main DataFrame
            charging_df = pd.concat([charging_df, new_entry], ignore_index=True)

    # Return filtered DataFrame if sn is provided, otherwise return all records
    # Note: This filtering is actually redundant since we already filter during processing
    return charging_df.drop(columns=['Location ID', 'Location'])

def get_data(start_time, end_time, location_id=None, robot_sn=None, timezone_offset=0):
    '''
    Get the percentage of area cleaned by robots within a specified time period.

    Parameters:
        start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id (int or None): The location ID to filter by, or None for all locations
        robot_sn (str or None): The robot serial number to filter by, or None for all robots
        timezone_offset (int): Timezone offset in hours (default: 0)

    Returns:
        pd.DataFrame: DataFrame containing cleaning data
    '''
    # Initialize empty DataFrame
    df = pd.DataFrame(columns=[
        'Task Name', 'Task Date', 'End Time', 'Location ID', 'Location',
        'Robot Name', 'Robot SN', 'Actual Area', 'Plan Area', 'Cost Water',
        'Cost Battery', 'Duration', 'Efficiency'
    ])
    # Filter stores by location_id
    stores = [shop for shop in get_list_stores()['list']
              if location_id is None or shop['shop_id'] == location_id]
    battery_capacity = 1228.8 / 1000 # kWh

    # Process each store
    for shop in stores:
        shop_id, shop_name = shop['shop_id'], shop['shop_name']

        # Get list of robots in this shop
        shop_robots = get_list_robots(shop_id=shop_id)['list']
        shop_robots_sn = [robot['sn'] for robot in shop_robots if 'sn' in robot]

        # Filter robots by robot_sn if provided
        if robot_sn is not None:
            shop_robots_sn = [sn for sn in shop_robots_sn if sn == robot_sn]
            shop_robots = [robot for robot in shop_robots if robot.get('sn') == robot_sn]

        # Skip if no robots match our criteria
        if not shop_robots_sn:
            continue

        # Get cleaning reports for this shop for the entire period
        results = get_cleaning_report_list(start_time, end_time, shop_id, timezone_offset=timezone_offset)['list']
        results = [task for task in results if task['sn'] in shop_robots_sn]

        # Track which robots have tasks
        robots_with_tasks = set()

        # Create a dictionary where keys are (task_name, task_date) tuples
        # This ensures tasks with the same name on different days remain separate
        task_report_dict = {}

        # Process each cleaning task
        for task in results:
            # Skip tasks outside the time range
            task_end_timestamp = task['end_time']
            if task_end_timestamp < pd.Timestamp(start_time).timestamp() or task_end_timestamp > pd.Timestamp(end_time).timestamp():
                continue

            sn = task['sn']
            robots_with_tasks.add(sn)
            report_id = task['report_id']
            task_name = task['task_name']

            # Get task details
            task_end_time = pd.to_datetime(task_end_timestamp, unit='s')

            # Extract date part for task grouping
            task_date = task_end_time.strftime('%Y-%m-%d')

            # Create a unique key combining task name and date
            task_key = (task_name, task_date)

            # Get detailed cleaning report
            try:
                report = get_cleaning_report_detail(
                    start_time, end_time, sn, report_id, shop_id, timezone_offset=timezone_offset
                )

                # Create task data entry
                task_data = pd.DataFrame({
                    'location_id': [shop_id],
                    'location_name': [shop_name],
                    'status': [task['status']],
                    'end_time': [task_end_time],
                    'percentage': [report['percentage']],
                    'sn': [sn],
                    'report_id': [report_id],
                    'clean_time': [task['clean_time']],
                    'plan_area': [report['task_area']],
                    'actual_area': [report['clean_area']],
                    'cost_water': [report['cost_water']],
                    'cost_battery': [report['cost_battery']],
                    'task_date': [task_date]  # Store the date for reference
                })

                # Add to task dictionary using the composite key
                if task_key in task_report_dict:
                    task_report_dict[task_key] = pd.concat([task_report_dict[task_key], task_data])
                else:
                    task_report_dict[task_key] = task_data

            except Exception as e:
                # Log error and continue with next task
                print(f"Error getting details for task {report_id}: {e}")
                continue

        # Process each task group and add to main DataFrame
        for (task_name, task_date), task_df in task_report_dict.items():
            # Get the task with the highest completion percentage
            if len(task_df) > 0:
                latest_task = task_df.sort_values(by='percentage', ascending=False).iloc[0]

                # Create a new entry for this task
                new_entry = pd.DataFrame({
                    'Task Name': [task_name],
                    'End Time': [latest_task['end_time']],
                    'Location ID': [shop_id],
                    'Location': [shop_name],
                    'Robot Name': [f"{shop_name}_CC1"],
                    'Robot SN': [latest_task['sn']],
                    'Actual Area': [round(latest_task['plan_area'] * (latest_task['percentage'] / 100), 2)], #round(latest_task['actual_area'], 2)
                    'Plan Area': [round(latest_task['plan_area'], 2)],
                    'Cost Water': [round(latest_task['cost_water'], 2)],
                    'Cost Battery': [round(latest_task['cost_battery'] * battery_capacity, 2)],
                    'Duration': [latest_task['clean_time']],
                    'Efficiency': [round(latest_task['plan_area'] * (latest_task['percentage'] / 100) / latest_task['clean_time'], 2)
                                 if latest_task['clean_time'] > 0 else 0] #round(latest_task['actual_area'] / latest_task['clean_time'], 2)
                })

                # Add to main DataFrame
                df = pd.concat([df, new_entry], ignore_index=True)

    return df

def get_task_overview_data(start_time, end_time, location_id=None, robot_sn=None, timezone_offset=0):
    '''
    Get task overview data aggregated by robot_sn, day, and hour

    Parameters:
        start_time (str): Start time in format 'YYYY-MM-DD HH:MM:SS'
        end_time (str): End time in format 'YYYY-MM-DD HH:MM:SS'
        location_id (int or None): The location ID to filter by, or None for all locations
        robot_sn (str or None): The robot serial number to filter by, or None for all robots
        timezone_offset (int): Timezone offset in hours (default: 0)

    Returns:
        pd.DataFrame: Aggregated task data by robot_sn, day, and hour
        units for area: m²
        units for duration: seconds
        units for cost: kWh for battery and L for water
        units for efficiency: m²/s
    '''
    # Get the raw data
    df = get_data(start_time, end_time, location_id, robot_sn, timezone_offset)

    # Prepare empty DataFrame structure with expected columns
    empty_df = pd.DataFrame(columns=[
        'Location ID', 'Location', 'Robot Name', 'Robot SN',
        'Actual Area', 'Plan Area', 'Percentage', 'Cost Water',
        'Cost Battery', 'Duration', 'Task Count', 'Efficiency',
        'Day', 'Hour'
    ])

    if df.empty:
        return empty_df

    # Extract time components for valid End Times
    mask = df['End Time'].notna()
    df.loc[mask, 'Hour'] = df.loc[mask, 'End Time'].dt.hour
    df.loc[mask, 'Day'] = df.loc[mask, 'End Time'].dt.strftime('%Y-%m-%d')

    # For NaT End Times, set placeholder values
    df.loc[~mask, 'Hour'] = -1  # Invalid hour to separate from real data
    df.loc[~mask, 'Day'] = "No Data Available"

    # Define aggregation for specific robot_sn, day, and hour combinations
    grouped_df = df.groupby(['Robot SN', 'Day', 'Hour', 'Location ID', 'Location', 'Robot Name']).agg({
        'Actual Area': 'sum',
        'Plan Area': 'sum',
        'Cost Water': 'sum',
        'Cost Battery': 'sum',
        'Duration': 'sum',
        'Task Name': 'count'  # Count tasks for each group
    }).reset_index()

    # Rename the Task Name count column to Task Count
    grouped_df = grouped_df.rename(columns={'Task Name': 'Task Count'})

    # Calculate percentage and efficiency metrics for each aggregated row
    grouped_df['Percentage'] = grouped_df.apply(
        lambda row: round((row['Actual Area'] / row['Plan Area']) * 100, 2)
               if row['Plan Area'] > 0 else 0,
        axis=1
    )

    grouped_df['Efficiency'] = grouped_df.apply(
        lambda row: round(row['Actual Area'] / row['Duration'], 2)
               if row['Duration'] > 0 else 0,
        axis=1
    )

    # Round numeric columns to 2 decimal places
    numeric_cols = ['Actual Area', 'Plan Area', 'Cost Water', 'Cost Battery', 'Percentage', 'Efficiency']
    for col in numeric_cols:
        if col in grouped_df.columns:
            if grouped_df[col].dtype == 'float64':
                grouped_df[col] = grouped_df[col].round(2)

    return grouped_df.drop(columns=['Location ID', 'Location'])