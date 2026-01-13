"""
高斯API适配器 - 包含完整的数据处理逻辑
将gas_api.py的类方法调用和Gas特定的数据处理逻辑整合到适配器中
"""

import json
import re
import pandas as pd
import datetime
from typing import Dict, List, Optional, Any, Union
from ..core.api_interface import RobotAPIInterface
from ..raw.gas_api import create_gaussian_api_client

API_NAME = "gas"

GS_robot_battery_capacity = {'S': 0.96, '40': 1.44}

class GasAdapter(RobotAPIInterface):
    """GS robot API adapter"""

    # Gas-specific mappings (may differ from Pudu)
    STATUS_MAPPING = {
        -1: "Unknown",
        0: "Task Ended",
        1: "Manual",
        2: "Task Abnormal",
        3: "Task Failed"
    }

    # MODE_MAPPING = {
    #     1: "Scrubbing",
    #     2: "Sweeping"
    # }

    # Gas API uses completionPercentage (0.0 to 1.0) instead of status codes
    # We map completion to status

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Extract credentials from config
        client_id = self.config.get('client_id', 'muryFD4sL4XsVanqsHwX')
        client_secret = self.config.get('client_secret', 'sWYjrp0D9X7gnkHLP727SeR5lJ1MFbUpOIumN6rt6tHwExvOOJk')
        open_access_key = self.config.get('open_access_key', '5d810a147b55ca9978afa82819b9625d')
        base_url = self.config.get('base_url', 'https://openapi.gs-robot.com')

        # 创建高斯API客户端
        self.client = create_gaussian_api_client(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            open_access_key=open_access_key
        )

        # Get OAuth token
        try:
            token_response = self.client.get_oauth_token()
            if 'access_token' not in token_response:
                print(f"Warning: Failed to get OAuth token: {token_response}")
        except Exception as e:
            print(f"Warning: Failed to get OAuth token: {e}")

    # ==================== Basic API Methods ====================

    def get_robot_details(self, sn: Union[str, List[str]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """获取机器人详细信息 - 匹配pudu格式"""

        def translate_soh_status(soh_status):
            soh_mapping = {
                '健康': 'Healthy',
                '良好': 'Good',
                '一般': 'Fair',
                '差': 'Poor',
                '未知': 'Unknown'
            }

            if not soh_status:
                return 'Unknown'

            soh_status = str(soh_status).strip()

            if soh_status.lower() in ['healthy', 'good', 'fair', 'poor', 'unknown']:
                return soh_status

            if soh_status in soh_mapping:
                return soh_mapping[soh_status]

            return 'Unknown'


        try:
            # Handle batch request for list of serial numbers
            if isinstance(sn, list):
                batch_status = self.client.batch_get_robot_status(sn)
                list_robots = self.get_list_robots()['list']

                results = []
                for status in batch_status.get('robotStatuses', []):
                    serial_number = status.get('serialNumber')
                    if not serial_number:
                        continue

                    robot_info = next((robot for robot in list_robots if robot.get('sn') == serial_number), None)

                    # Extract battery info
                    battery_info = status.get('battery', {})
                    battery_percentage = int(battery_info.get('powerPercentage', 0))
                    soh = translate_soh_status(battery_info.get('soh', None))
                    cycles = battery_info.get('cycleTimes', None)

                    # Extract localization info
                    localization_info = status.get('localizationInfo', {})
                    map_info = localization_info.get('map', {})
                    map_position = localization_info.get('mapPosition', {})

                    # emergencyStop
                    emergency_stop_enabled = status.get('emergencyStop', {}).get('enabled', False)

                    # get clean water and dirty water percentage
                    clean_water_percentage = status.get('device', {}).get('cleanWaterTank', {}).get('level', 0)
                    dirty_water_percentage = status.get('device', {}).get('recoveryWaterTank', {}).get('level', 0)

                    # Transform to pudu format
                    robot_details = {
                        'mac': '',
                        'modelTypeCode': robot_info.get('modelTypeCode', '') if robot_info else '',
                        'modelFamilyCode': robot_info.get('modelFamilyCode', '') if robot_info else '',
                        'softwareVersion': robot_info.get('softwareVersion', '') if robot_info else '',
                        'hardwareVersion': robot_info.get('hardwareVersion', '') if robot_info else '',
                        'nickname': robot_info.get('name', serial_number) if robot_info else serial_number,
                        'taskState': status.get('taskState', ''), # OTHER, IDLE, WORKING, PAUSED, etc.
                        'online': status.get('online', False),
                        'battery': battery_percentage,
                        'battery_info': battery_info,
                        'soh': soh,
                        'cycles': cycles,
                        'map': {
                            'name': map_info.get('name', '')
                        },
                        'position': {
                            'x': map_position.get('x', 0),
                            'y': map_position.get('y', 0),
                            'z': map_position.get('angle', 0)
                        },
                        'executingTask': status.get('executingTask', {}),
                        'emergencyStopEnabled': emergency_stop_enabled,
                        'cleanWaterPercentage': clean_water_percentage,
                        'dirtyWaterPercentage': dirty_water_percentage,
                        'sn': serial_number
                    }
                    results.append(robot_details)

                return results

            # Handle single robot request (original logic)
            else:
                gas_status = self.client.get_robot_status(sn)
                list_robots = self.get_list_robots()['list']
                robot_info = next((robot for robot in list_robots if robot.get('sn') == sn), None)

                if not gas_status or 'error' in gas_status:
                    print(f"Error getting gas robot status: {gas_status}")
                    return {}

                # Extract battery info
                battery_info = gas_status.get('battery', {})
                battery_percentage = int(battery_info.get('powerPercentage', 0))
                soh = translate_soh_status(battery_info.get('soh', None))
                cycles = battery_info.get('cycleTimes', None)
                # Extract localization info
                localization_info = gas_status.get('localizationInfo', {})
                map_info = localization_info.get('map', {})
                map_position = localization_info.get('mapPosition', {})

                # emergencyStop
                emergency_stop_enabled = gas_status.get('emergencyStop', {}).get('enabled', False)

                # get clean water and dirty water percentage
                clean_water_percentage = gas_status.get('device', {}).get('cleanWaterTank', {}).get('level', 0)
                dirty_water_percentage = gas_status.get('device', {}).get('recoveryWaterTank', {}).get('level', 0)

                # Transform to pudu format
                return {
                    'mac': '',
                    'modelTypeCode': robot_info.get('modelTypeCode', ''),
                    'modelFamilyCode': robot_info.get('modelFamilyCode', ''),
                    'softwareVersion': robot_info.get('softwareVersion', ''),
                    'hardwareVersion': robot_info.get('hardwareVersion', ''),
                    'nickname': robot_info.get('name', sn),
                    'taskState': gas_status.get('taskState', ''), # OTHER, IDLE, WORKING, PAUSED, etc.
                    'online': gas_status.get('online', False),
                    'battery': battery_percentage,
                    'battery_info': battery_info,
                    'soh': soh,
                    'cycles': cycles,
                    'map': {
                        'name': map_info.get('name', '')
                    },
                    'position': {
                        'x': map_position.get('x', 0),
                        'y': map_position.get('y', 0),
                        'z': map_position.get('angle', 0)
                    },
                    'executingTask': gas_status.get('executingTask', {}),
                    'emergencyStopEnabled': emergency_stop_enabled,
                    'cleanWaterPercentage': clean_water_percentage,
                    'dirtyWaterPercentage': dirty_water_percentage,
                    'sn': sn
                }
        except Exception as e:
            print(f"Error getting robot details for {sn}: {e}")
            import traceback
            traceback.print_exc()
            return {} if isinstance(sn, str) else []

    def get_robot_status(self, sn: str) -> Dict[str, Any]:
        """获取机器人状态 - 直接返回gas格式"""
        return self.client.get_robot_status(sn)

    def get_list_stores(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取门店列表"""
        stores = [{
            'company_id': '',
            'company_name': '',
            'shop_id': '',
            'shop_name': ''
        }]

        if offset:
            stores = stores[offset:]
        if limit:
            stores = stores[:limit]

        return {
            'total': 1,
            'list': stores
        }

    def get_list_robots(self, location_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取机器人列表"""
        try:
            page = (offset // (limit or 10)) + 1 if offset else 1
            page_size = limit or 200

            response = self.client.list_robots(page=page, page_size=page_size)

            if not response or 'error' in response:
                print(f"Error listing robots: {response}")
                return {'total': 0, 'list': []}

            # GS API returns {'robots': [...], 'total': '2'} NOT {'data': {'list': [...]}}
            robots_data = response.get('robots', [])
            total = response.get('total', '0')

            # Convert string total to int
            try:
                total = int(total) if isinstance(total, str) else total
            except:
                total = len(robots_data)

            robots = []
            for robot in robots_data:
                robots.append({
                    'sn': robot.get('serialNumber', ''),
                    'name': robot.get('displayName', ''),
                    'modelFamilyCode': robot.get('modelFamilyCode', ''),
                    'modelTypeCode': robot.get('modelTypeCode', ''),
                    'online': robot.get('online', False),
                    'softwareVersion': robot.get('softwareVersion', ''),
                    'hardwareVersion': robot.get('hardwareVersion', '')
                })

            return {
                'total': total,
                'list': robots
            }
        except Exception as e:
            print(f"Error listing robots: {e}")
            import traceback
            traceback.print_exc()
            return {'total': 0, 'list': []}

    def get_schedule_table(self, start_time: str, end_time: str, location_id: Optional[str] = None,
                          robot_sn: Optional[str] = None, timezone_offset: int = 0) -> pd.DataFrame:
        """
        Get the schedule table for Gas robots

        STATUS: verified
        """
        # Initialize empty DataFrame with same columns as Pudu
        schedule_df = pd.DataFrame(columns=[
            'Location ID', 'Task Name', 'Task ID', 'Robot SN', 'Map Name', 'Is Report', 'Map URL',
            'Actual Area', 'Plan Area', 'Start Time', 'End Time', 'Duration',
            'Efficiency', 'Remaining Time', 'Consumption', 'Battery Usage', 'Water Consumption', 'Progress', 'Status',
            'Mode', 'Sub Mode', 'Type', 'Vacuum Speed', 'Vacuum Suction',
            'Wash Speed', 'Wash Suction', 'Wash Water', 'Extra Fields'
        ])

        # Chinese to English cleaning mode mapping
        CLEANING_MODE_TRANSLATION = {
            # Common cleaning modes
            '清洗': 'Cleaning',
            '清洁': 'Cleaning',
            '洗地': 'Mopping',
            '清扫': 'Sweeping',
            '扫洗': 'Sweep and Wash',
            '尘推': 'Dust Push',
            '吸尘': 'Vacuuming',
            '拖地': 'Mopping',
            '抛光': 'Polishing',

            # Strength/Intensity modes
            '强劲清洗': 'Strong Cleaning',
            '强力清洗': 'Powerful Cleaning',
            '标准清洗': 'Standard Cleaning',
            '轻柔清洗': 'Gentle Cleaning',
            '静音清洗': 'Quiet Cleaning',

            # Special modes
            '长续航清洗': 'Long Endurance Cleaning',
            '节能清洗': 'Energy Saving Cleaning',
            '快速清洗': 'Quick Cleaning',
            '深度清洗': 'Deep Cleaning',
            '日常清洗': 'Daily Cleaning',

            # Custom modes
            '自定义清洗': 'Custom Cleaning',
            '定制清洗': 'Customized Cleaning',

            # Area-specific modes
            '边缘清洗': 'Edge Cleaning',
            '定点清洗': 'Spot Cleaning',
            '区域清洗': 'Zone Cleaning',

            # Brush/Rolling modes
            '滚刷': 'Rolling Brush',
            '边刷': 'Side Brush',

            # Combined modes
            '扫洗一体': 'Integrated Sweep and Wash',
            '吸拖一体': 'Integrated Vacuum and Mop',

            # Cleaning type
            '地毯清洁': 'Carpet Cleaning',
            '木地板清洁': 'Wood Floor Cleaning',
            '瓷砖清洁': 'Tile Cleaning',
            '大理石清洁': 'Marble Cleaning'
        }

        def translate_cleaning_mode(chinese_mode: str) -> str:
            """Translate Chinese cleaning mode to English and clean the text"""
            if not chinese_mode or not isinstance(chinese_mode, str):
                return ''

            # Remove underscores, dashes, and other symbols
            cleaned_mode = chinese_mode.replace('_', ' ').replace('-', ' ').replace('__', ' ')

            # Remove any remaining non-alphanumeric characters except spaces
            cleaned_mode = re.sub(r'[^\w\s]', '', cleaned_mode)

            # Remove extra spaces
            cleaned_mode = ' '.join(cleaned_mode.split())

            # Try exact match first
            if cleaned_mode in CLEANING_MODE_TRANSLATION:
                return CLEANING_MODE_TRANSLATION[cleaned_mode]

            # Try partial matches for combined modes
            for chinese, english in CLEANING_MODE_TRANSLATION.items():
                if chinese in cleaned_mode:
                    # Replace the Chinese part with English
                    result = cleaned_mode.replace(chinese, english)
                    # Clean up any double spaces that might have been created
                    return ' '.join(result.split())

            # If no translation found, return the cleaned Chinese text
            return cleaned_mode

        # Get robots
        robots_response = self.get_list_robots(location_id=location_id)
        robots = robots_response.get('list', [])

        # Filter by robot_sn if specified
        if robot_sn is not None:
            robots = [r for r in robots if r.get('sn') == robot_sn]

        # Process each robot
        for robot in robots:
            sn = robot.get('sn')
            robot_type = robot.get('modelTypeCode', '')

            if not sn:
                continue

            try:
                # Get task reports from Gas API
                response = self.client.get_task_reports(
                    serial_number=sn,
                    startTimeUtcFloor=start_time,
                    startTimeUtcUpper=end_time,
                    page=1,
                    page_size=200
                )

                if not response or 'error' in response:
                    continue

                # Gas API might return {'data': {'robotTaskReports': [...]}} or directly {'robotTaskReports': [...]}
                # Check both structures
                if 'data' in response:
                    reports = response.get('data', {}).get('robotTaskReports', [])
                else:
                    reports = response.get('robotTaskReports', [])

                # Process each report
                for report in reports:
                    try:
                        # Parse timestamps - note these are robot local time not UTC
                        start_timestamp = self._parse_timestamp(report.get('startTime', ''))
                        end_timestamp = self._parse_timestamp(report.get('endTime', ''))
                        start_dt = pd.to_datetime(start_timestamp, unit='s') if start_timestamp else None
                        end_dt = pd.to_datetime(end_timestamp, unit='s') if end_timestamp else None

                        # Calculate areas and completion
                        plan_area = report.get('plannedCleaningAreaSquareMeter', 0)
                        actual_area = report.get('actualCleaningAreaSquareMeter', 0)
                        completion_percentage = report.get('completionPercentage', 0)
                        progress = int(completion_percentage * 100) if completion_percentage else 0

                        # Get task status and map to string
                        status = self.STATUS_MAPPING.get(report.get('taskEndStatus', -1), 'Unknown')

                        # Calculate duration and efficiency
                        duration = report.get('durationSeconds', 0)
                        if duration > 0 and actual_area > 0:
                            efficiency = round((actual_area / duration) * 3600, 2)  # m²/hour
                        else:
                            efficiency = 0

                        # Calculate battery consumption
                        start_battery = report.get('startBatteryPercentage', 100)
                        end_battery = report.get('endBatteryPercentage', 100)
                        battery_usage = max(0, start_battery - end_battery)

                        # Gas doesn't provide detailed consumption in kWh, estimate from battery percentage
                        # check if robot_type contains 'S' or '40'
                        if 'S' in robot_type and '40' not in robot_type:
                            robot_battery_capacity = GS_robot_battery_capacity['S']
                        elif '40' in robot_type:
                            robot_battery_capacity = GS_robot_battery_capacity['40']
                        else:
                            robot_battery_capacity = 0

                        consumption = round((battery_usage / 100) * robot_battery_capacity, 5)


                        # Water consumption
                        water_consumption = int(report.get('waterConsumptionLiter', 0) * 1000)  # Convert L to mL

                        # Get and translate cleaning mode
                        raw_mode = report.get('cleaningMode', '')
                        mode = translate_cleaning_mode(raw_mode)

                        # Process subtasks to get map names
                        subtasks = report.get('subTasks', [])
                        map_names = []

                        if subtasks:
                            # Extract map names from subtasks
                            map_names = [subtask.get('mapName', '') for subtask in subtasks if subtask.get('mapName')]

                        # Create map name string
                        if len(map_names) == 1:
                            map_name = map_names[0]
                        elif len(map_names) > 1:
                            map_name = ', '.join(map_names)
                        else:
                            map_name = ''

                        # Create extra_fields with all non-standard fields
                        extra_field_names = {
                            'id', 'robot', 'operator', 'areaNameList', 'efficiencySquareMeterPerHour',
                            'plannedPolishingAreaSquareMeter', 'actualPolishingAreaSquareMeter',
                            'startBatteryPercentage', 'endBatteryPercentage',
                            'consumablesResidualPercentage', 'subTasks'
                        }

                        # Include subtasks in extra_fields for detailed area mapping
                        extra_fields = {}
                        for key, value in report.items():
                            if key in extra_field_names:
                                extra_fields[key] = value

                        # Convert to JSON string for database storage
                        extra_fields_json = json.dumps(extra_fields, ensure_ascii=False, default=str)

                        # Create entry
                        new_entry = pd.DataFrame({
                            'Location ID': [''],
                            'Task Name': [report.get('displayName', '')],
                            'Task ID': [report.get('taskId', '')],
                            'Robot SN': [sn],
                            'Map Name': [map_name],
                            'Is Report': [1],
                            'Map URL': [report.get('taskReportPngUri', '')],  # Use taskReportPngUri if available
                            'Actual Area': [round(actual_area, 2)],
                            'Plan Area': [round(plan_area, 2)],
                            'Start Time': [start_dt],
                            'End Time': [end_dt],
                            'Duration': [duration],
                            'Efficiency': [efficiency],
                            'Remaining Time': [0],  # Gas doesn't provide remaining time for completed tasks
                            'Consumption': [consumption],
                            'Battery Usage': [battery_usage],
                            'Water Consumption': [water_consumption],
                            'Progress': [progress],
                            'Status': [status],
                            'Mode': [mode],
                            'Sub Mode': [''],  # Gas doesn't provide sub mode
                            'Type': [''],
                            'Vacuum Speed': [''],
                            'Vacuum Suction': [''],
                            'Wash Speed': [''],
                            'Wash Suction': [''],
                            'Wash Water': [''],
                            'Extra Fields': [extra_fields_json]
                        })

                        schedule_df = pd.concat([schedule_df, new_entry], ignore_index=True)

                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        continue

            except Exception as e:
                import traceback
                traceback.print_exc()
                continue

        return schedule_df

    def get_charging_table(self, start_time: str, end_time: str, location_id: Optional[str] = None,
                          robot_sn: Optional[str] = None, timezone_offset: int = 0) -> pd.DataFrame:
        """
        Get charging records for Gas robots
        Gas API没有充电记录接口，返回空DataFrame
        """
        return pd.DataFrame(columns=[
            'Robot Name', 'Robot SN',
            'Start Time', 'End Time', 'Duration',
            'Initial Power', 'Final Power', 'Power Gain', 'Battery SOH', 'Battery Cycles', 'Status'
        ])

    def get_events_table(self, start_time: str, end_time: str, location_id: Optional[str] = None,
                        robot_sn: Optional[str] = None, error_levels: Optional[str] = None,
                        error_types: Optional[str] = None, timezone_offset: int = 0) -> pd.DataFrame:
        """
        Get the events table for Gas robots
        Gas API没有事件记录接口，返回空DataFrame
        """
        return pd.DataFrame(columns=[
            'Robot SN', 'Robot Name', 'Event Level', 'Event Type',
            'Event Detail', 'Error ID', 'Task Time', 'Upload Time', 'Product Code',
            'MAC Address', 'Software Version', 'Hardware Version', 'OS Version', 'Event UUID'
        ])

    def get_robot_status_table(self, location_id: Optional[str] = None, robot_sn: Optional[str] = None) -> pd.DataFrame:
        """
        Get a simplified table for Gas robots with basic information
        """
        robot_df = pd.DataFrame(columns=['Robot SN', 'Water Level', 'Sewage Level', 'Battery Level', 'Battery SOH', 'Battery Cycles',
                                         'Status', 'Timestamp UTC'])
        # Get all robots
        robots_response = self.get_list_robots(location_id=location_id)
        robots = robots_response.get('list', [])

        # Filter by robot_sn if specified
        if robot_sn is not None:
            robots = [r for r in robots if r.get('sn') == robot_sn]

        # Extract all serial numbers for batch processing
        serial_numbers = [robot.get('sn') for robot in robots if robot.get('sn')]

        if not serial_numbers:
            return robot_df

        try:
            # Get robot details in batch
            robot_details_list = self.get_robot_details(serial_numbers)

            # Create a mapping from SN to robot info for easy lookup
            robot_info_map = {robot.get('sn'): robot for robot in robots}

            # Process all robots from batch response
            for robot_details in robot_details_list:
                sn = robot_details.get('sn')
                if not sn:
                    continue

                # Get robot info from original list
                robot_info = robot_info_map.get(sn, {})

                # Get status
                is_online = robot_details.get('online', False)
                status = 'Online' if is_online else 'Offline'

                # Get battery percentage
                battery_percentage = robot_details.get('battery', None)
                soh = robot_details.get('soh', None)
                cycles = robot_details.get('cycles', None)
                # Gas doesn't provide water and sewage levels
                water_percentage = robot_details.get('cleanWaterPercentage', None)
                sewage_percentage = robot_details.get('dirtyWaterPercentage', None)

                # Get robot name - prefer nickname from details, fall back to name from info
                robot_name = robot_details.get('nickname', robot_info.get('name', sn))

                # Get position
                position = robot_details.get('position', {})

                # Get robot type - prefer modelTypeCode from details, fall back to info
                robot_type = robot_details.get('modelTypeCode', robot_info.get('modelTypeCode', ''))

                # Create row
                robot_row = pd.DataFrame({
                    'Robot SN': [sn],
                    'Water Level': [water_percentage],
                    'Sewage Level': [sewage_percentage],
                    'Battery Level': [battery_percentage],
                    'Battery SOH': [soh],
                    'Battery Cycles': [cycles],
                    'Status': [status],
                    'Timestamp UTC': [pd.Timestamp.now()]  # Add current timestamp
                })

                robot_df = pd.concat([robot_df, robot_row], ignore_index=True)

        except Exception as e:
            for robot in robots:
                sn = robot.get('sn')
                if not sn:
                    continue

                try:
                    # Get robot details individually
                    robot_details = self.get_robot_details(sn)

                    if not robot_details:
                        continue

                    # Get status
                    is_online = robot_details.get('online', False)
                    status = 'Online' if is_online else 'Offline'

                    # Get battery percentage
                    battery_percentage = robot_details.get('battery', None)
                    soh = robot_details.get('soh', None)
                    cycles = robot_details.get('cycles', None)

                    # Gas doesn't provide water and sewage levels
                    water_percentage = robot_details.get('cleanWaterPercentage', None)
                    sewage_percentage = robot_details.get('dirtyWaterPercentage', None)

                    # Get robot name
                    robot_name = robot_details.get('nickname', sn)

                    # Get position
                    position = robot_details.get('position', {})

                    # Get robot type
                    robot_type = robot_details.get('modelTypeCode', '')

                    # Create row
                    robot_row = pd.DataFrame({
                        'Robot SN': [sn],
                        'Water Level': [water_percentage],
                        'Sewage Level': [sewage_percentage],
                        'Battery Level': [battery_percentage],
                        'Battery SOH': [soh],
                        'Battery Cycles': [cycles],
                        'Status': [status],
                        'Timestamp UTC': [pd.Timestamp.now()]  # Add current timestamp
                    })

                    robot_df = pd.concat([robot_df, robot_row], ignore_index=True)

                except Exception as e2:
                    continue

        return robot_df

    def get_ongoing_tasks_table(self, location_id: Optional[str] = None, robot_sn: Optional[str] = None) -> pd.DataFrame:
        """
        TODO: pending completion
        Get ongoing tasks for Gas robots
        """
        ongoing_tasks_df = pd.DataFrame(columns=[
            'location_id', 'task_name', 'task_id', 'robot_sn', 'map_name', 'is_report', 'map_url',
            'actual_area', 'plan_area', 'start_time', 'end_time', 'duration',
            'efficiency', 'remaining_time', 'battery_usage', 'consumption', 'water_consumption', 'progress', 'status',
            'mode', 'sub_mode', 'type', 'vacuum_speed', 'vacuum_suction',
            'wash_speed', 'wash_suction', 'wash_water', 'extra_fields'
        ])

        def estimate_duration(progress: float, time_remaining: int) -> int:
            """Estimate duration with better edge case handling"""
            progress_decimal = progress / 100.0

            # Handle edge cases
            if progress_decimal <= 0:
                return 0  # Task just started
            elif progress_decimal >= 1:
                return time_remaining  # Task should be complete
            elif time_remaining <= 0:
                return 0  # Invalid time remaining

            try:
                # Main estimation formula
                total_estimated = time_remaining / (1 - progress_decimal)
                duration_so_far = int(total_estimated * progress_decimal)
                return max(0, duration_so_far)
            except ZeroDivisionError:
                return 0

        # Get robots
        robots_response = self.get_list_robots(location_id=location_id)
        robots = robots_response.get('list', [])

        # Filter by robot_sn if specified
        if robot_sn is not None:
            robots = [r for r in robots if r.get('sn') == robot_sn]

        # Process each robot to check for ongoing tasks
        for robot in robots:
            sn = robot.get('sn')
            if not sn:
                continue

            try:
                # Get robot status to check if executing task
                gas_status = self.client.get_robot_status(sn)

                if not gas_status or 'error' in gas_status:
                    continue

                executing_task = gas_status.get('executingTask')

                if executing_task and executing_task.get('name'):
                    # Robot has an ongoing task
                    task_name = executing_task.get('name', '')
                    progress = executing_task.get('progress', 0)
                    timeRemaining = executing_task.get('timeRemaining', 0)
                    # estimate the duration which means the start to now using progress and timeRemaining
                    duration = estimate_duration(
                        progress=executing_task.get('progress', 0),
                        time_remaining=executing_task.get('timeRemaining', 0)
                    )

                    # Estimate progress and other metrics from current status
                    # Gas API doesn't provide detailed ongoing task metrics

                    ongoing_task_row = pd.DataFrame({
                        'location_id': [''],
                        'task_name': [task_name],
                        'task_id': [''],  # Not available for ongoing tasks
                        'robot_sn': [sn],
                        'map_name': [gas_status.get('localizationInfo', {}).get('map', {}).get('name', '')],
                        'is_report': [0],  # Mark as ongoing task
                        'map_url': [''],
                        'actual_area': [None],
                        'plan_area': [None],
                        'start_time': [pd.Timestamp.now() - datetime.timedelta(seconds=duration)],  # Approximation
                        'end_time': [pd.Timestamp.now() + datetime.timedelta(seconds=timeRemaining)],
                        'duration': [duration],
                        'efficiency': [None],
                        'remaining_time': [timeRemaining],
                        'battery_usage': [None],
                        'consumption': [None],
                        'water_consumption': [None],
                        'progress': [progress],
                        'status': ['In Progress'],
                        'mode': ['Scrubbing'],
                        'sub_mode': ['Custom'],
                        'type': ['Custom'],
                        'vacuum_speed': ['Standard'],
                        'vacuum_suction': ['Standard'],
                        'wash_speed': ['Standard'],
                        'wash_suction': ['Standard'],
                        'wash_water': ['Standard'],
                        'extra_fields': [None]
                    })

                    ongoing_tasks_df = pd.concat([ongoing_tasks_df, ongoing_task_row], ignore_index=True)

            except Exception as e:
                print(f"Error checking ongoing tasks for robot {sn}: {e}")
                continue

        return pd.DataFrame() # ongoing_tasks_df

    def get_robot_work_location_and_mapping_data(self) -> tuple:
        """
        TODO: try to get floor number from map name
        Get robot work location data and map floor mapping data in a single pass
        包含完整的Gas数据处理逻辑

        Returns:
            tuple: (work_location_df, mapping_df)
        """
        work_location_rows = []
        map_floor_data = {}
        current_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

        # Get all robots
        robots_response = self.get_list_robots()
        robots = robots_response.get('list', [])

        for robot in robots:
            sn = robot.get('sn')
            if not sn:
                continue

            try:
                # Get robot status
                gas_status = self.get_robot_status(sn)

                if not gas_status or 'error' in gas_status:
                    # Append idle status if can't get status
                    work_location_rows.append({
                        'robot_sn': sn,
                        'map_name': None,
                        'x': None,
                        'y': None,
                        'z': None,
                        'status': 'idle',
                        'update_time': current_time
                    })
                    continue

                # Check if robot is executing a task
                executing_task = gas_status.get('executingTask') # could not none-existing
                is_in_task = executing_task and executing_task.get('name')

                if is_in_task:
                    # Get localization info
                    localization_info = gas_status.get('localizationInfo', {})
                    map_info = localization_info.get('map', {})
                    map_position = localization_info.get('mapPosition', {})
                    map_id = map_info.get('id')
                    map_name = map_info.get('name')

                    # Gas API doesn't provide floor number directly, use map name as approximation
                    site_info = self.client.get_site_info(sn)
                    buildings = site_info.get('buildings', [])
                    floor_number = None
                    for building in buildings:
                        floors = building.get('floors', [])
                        for floor in floors:
                            maps = floor.get('maps', [])
                            for map in maps:
                                if map.get('id') == map_id:
                                    floor_number = floor.get('index')
                                    break
                                else:
                                    floor_number = -1
                                    break

                    x = map_position.get('x')
                    y = map_position.get('y')
                    z = map_position.get('angle')  # Gas uses angle instead of z

                    if map_name and x is not None and y is not None:
                        # Append to list
                        work_location_rows.append({
                            'robot_sn': sn,
                            'map_name': map_name,
                            'x': x,
                            'y': y,
                            'z': z if z is not None else 0,
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
                print(f"Error processing robot {sn}: {e}")
                # Append idle status on error
                work_location_rows.append({
                    'robot_sn': sn,
                    'map_name': None,
                    'x': None,
                    'y': None,
                    'z': None,
                    'status': 'idle',
                    'update_time': current_time
                })
                continue

        # Create DataFrames from collected data
        work_location_df = pd.DataFrame(work_location_rows)

        # Handle mapping data
        mapping_rows = [{'map_name': map_name, 'floor_number': floor_number}
                       for map_name, floor_number in map_floor_data.items()]
        mapping_df = pd.DataFrame(mapping_rows)

        return work_location_df, mapping_df

    # ==================== Helper Methods ====================

    def _parse_timestamp(self, time_str: str) -> int:
        """Parse ISO timestamp to Unix timestamp (seconds)"""
        if not time_str:
            return 0
        try:
            dt = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except Exception as e:
            print(f"Error parsing timestamp '{time_str}': {e}")
            return 0

    # ==================== Gas API独有功能 ====================

    def batch_get_robot_statuses(self, serial_numbers: List[str]) -> Dict[str, Any]:
        """批量获取机器人状态 - 高仙API独有"""
        return self.client.batch_get_robot_statuses(serial_numbers)

    def generate_robot_task_report_png(self, serial_number: str, task_report_id: str, **kwargs) -> Dict[str, Any]:
        """生成机器人任务报告PNG - 高仙API独有"""
        return self.client.generate_robot_task_report_png(serial_number, task_report_id, **kwargs)

    def get_map_download_uri(self, serial_number: str, map_id: str) -> Dict[str, Any]:
        """获取地图下载链接 - 高仙API独有"""
        return self.client.get_map_download_uri(serial_number, map_id)

    def upload_robot_map(self, serial_number: str, map_file: str) -> Dict[str, Any]:
        """上传机器人地图 - 高仙API独有"""
        return self.client.upload_robot_map(serial_number, map_file)

    def get_upload_status(self, serial_number: str, record_id: str) -> Dict[str, Any]:
        """获取上传状态 - 高仙API独有"""
        return self.client.get_upload_status(serial_number, record_id)

    def list_robot_commands(self, serial_number: str, page: int = 1, page_size: int = 5, **kwargs) -> Dict[str, Any]:
        """获取机器人命令列表 - 高仙API独有"""
        return self.client.list_robot_commands(serial_number, page, page_size, **kwargs)

    def get_robot_command(self, serial_number: str, command_id: str) -> Dict[str, Any]:
        """获取机器人命令详情 - 高仙API独有"""
        return self.client.get_robot_command(serial_number, command_id)

    def create_remote_task_command(self, serial_number: str, command_type: str, **kwargs) -> Dict[str, Any]:
        """创建远程任务命令 - 高仙API独有"""
        return self.client.create_remote_task_command(serial_number, command_type, **kwargs)

    def create_remote_navigation_command(self, serial_number: str, command_type: str, **kwargs) -> Dict[str, Any]:
        """创建远程导航命令 - 高仙API独有"""
        return self.client.create_remote_navigation_command(serial_number, command_type, **kwargs)


def create_adapter(config: Optional[Dict[str, Any]] = None) -> GasAdapter:
    """创建高斯API适配器实例"""
    return GasAdapter(config)