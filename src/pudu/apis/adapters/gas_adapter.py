"""
高斯API适配器 - 包含完整的数据处理逻辑
将gas_api.py的类方法调用和Gas特定的数据处理逻辑整合到适配器中
"""

import pandas as pd
import datetime
from typing import Dict, List, Optional, Any
from ..core.api_interface import RobotAPIInterface
from ..gas_api import GaussianRobotAPI, create_gaussian_api_client


API_NAME = "gas"


# Shop ID mapping - maps client credentials to location IDs
SHOP_ID_MAPPING = {
    "muryFD4sL4XsVanqsHwX": "GS_SHOP_001",  # Default shop ID for this client
    # Add more client_id -> shop_id mappings here as needed
}


class GasAdapter(RobotAPIInterface):
    """GS robot API adapter"""

    # Gas-specific mappings (may differ from Pudu)
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

        # Get shop_id from config or use mapping based on client_id
        self.shop_id = self.config.get('shop_id') or SHOP_ID_MAPPING.get(client_id, 'GS_SHOP_001')
        self.shop_name = self.config.get('shop_name', f'Shop_{self.shop_id}')

    # ==================== Basic API Methods ====================

    def get_robot_details(self, sn: str) -> Dict[str, Any]:
        """获取机器人详细信息 - 匹配pudu格式"""
        try:
            gas_status = self.client.get_robot_status(sn)

            if not gas_status or 'error' in gas_status:
                print(f"Error getting gas robot status: {gas_status}")
                return {}

            # Extract battery info
            battery_info = gas_status.get('battery', {})
            battery_percentage = int(battery_info.get('powerPercentage', 0))

            # Extract localization info
            localization_info = gas_status.get('localizationInfo', {})
            map_info = localization_info.get('map', {})
            map_position = localization_info.get('mapPosition', {})

            # Transform to pudu format
            return {
                'mac': '',
                'nickname': gas_status.get('displayName', sn),
                'online': gas_status.get('online', False),
                'battery': battery_percentage,
                'map': {
                    'name': map_info.get('name', ''),
                    'lv': 1,
                    'floor': ''
                },
                'cleanbot': {
                    'rising': 0,
                    'sewage': 0,
                    'task': 0,
                    'clean': None,
                    'last_mode': 1,
                    'detail': '',
                    'last_task': ''
                },
                'shop': {
                    'id': self.shop_id,
                    'name': self.shop_name
                },
                'position': {
                    'x': map_position.get('x', 0),
                    'y': map_position.get('y', 0),
                    'z': map_position.get('angle', 0)
                },
                'sn': sn
            }
        except Exception as e:
            print(f"Error getting robot details for {sn}: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_robot_status(self, sn: str) -> Dict[str, Any]:
        """获取机器人状态 - 直接返回gas格式"""
        return self.client.get_robot_status(sn)

    def get_list_stores(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取门店列表"""
        stores = [{
            'company_id': '',
            'company_name': '',
            'shop_id': self.shop_id,
            'shop_name': self.shop_name
        }]

        if offset:
            stores = stores[offset:]
        if limit:
            stores = stores[:limit]

        return {
            'total': 1,
            'list': stores
        }

    def get_list_robots(self, shop_id: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """获取机器人列表"""
        try:
            page = (offset // (limit or 10)) + 1 if offset else 1
            page_size = limit or 200

            response = self.client.list_robots(page=page, page_size=page_size)

            if not response or 'error' in response:
                print(f"Error listing robots: {response}")
                return {'total': 0, 'list': []}

            # Gas API returns {'robots': [...], 'total': '2'} NOT {'data': {'list': [...]}}
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
                    'mac': '',
                    'shop_id': self.shop_id,
                    'shop_name': self.shop_name,
                    'sn': robot.get('serialNumber', '')
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

    # ==================== Enhanced Methods with Data Processing ====================

    def get_schedule_table(self, start_time: str, end_time: str, location_id: Optional[str] = None,
                          robot_sn: Optional[str] = None, timezone_offset: int = 0) -> pd.DataFrame:
        """
        Get the schedule table for Gas robots
        包含完整的Gas数据处理逻辑
        """
        # Initialize empty DataFrame with same columns as Pudu
        schedule_df = pd.DataFrame(columns=[
            'Location ID', 'Task Name', 'Task ID', 'Robot SN', 'Map Name', 'Is Report', 'Map URL',
            'Actual Area', 'Plan Area', 'Start Time', 'End Time', 'Duration',
            'Efficiency', 'Remaining Time', 'Consumption', 'Battery Usage', 'Water Consumption', 'Progress', 'Status',
            'Mode', 'Sub Mode', 'Type', 'Vacuum Speed', 'Vacuum Suction',
            'Wash Speed', 'Wash Suction', 'Wash Water'
        ])

        # Filter by location_id if specified
        if location_id is not None and location_id != self.shop_id:
            return schedule_df

        # Get robots
        robots_response = self.get_list_robots(shop_id=self.shop_id)
        robots = robots_response.get('list', [])

        # Filter by robot_sn if specified
        if robot_sn is not None:
            robots = [r for r in robots if r.get('sn') == robot_sn]

        # Process each robot
        for robot in robots:
            sn = robot.get('sn')
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
                    print(f"No task reports for robot {sn}: {response}")
                    continue

                # Gas API might return {'data': {'robotTaskReports': [...]}} or directly {'robotTaskReports': [...]}
                # Check both structures
                if 'data' in response:
                    reports = response.get('data', {}).get('robotTaskReports', [])
                else:
                    reports = response.get('robotTaskReports', [])

                print(f"Found {len(reports)} reports for robot {sn}")

                # Process each report
                for report in reports:
                    try:
                        # Parse timestamps
                        start_timestamp = self._parse_timestamp(report.get('startTime', ''))
                        end_timestamp = self._parse_timestamp(report.get('endTime', ''))
                        start_dt = pd.to_datetime(start_timestamp, unit='s') if start_timestamp else None
                        end_dt = pd.to_datetime(end_timestamp, unit='s') if end_timestamp else None

                        # Calculate areas and completion
                        plan_area = report.get('plannedCleaningAreaSquareMeter', 0)
                        actual_area = report.get('actualCleaningAreaSquareMeter', 0)
                        completion_percentage = report.get('completionPercentage', 0)
                        progress = int(completion_percentage * 100) if completion_percentage else 0

                        # Determine status based on completion
                        if completion_percentage >= 1.0:
                            status = "Task Ended"
                        elif completion_percentage > 0:
                            status = "In Progress"
                        else:
                            status = "Not Started"

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
                        # Assuming similar battery capacity as Pudu (1.2288 kWh)
                        consumption = round((battery_usage / 100) * 1.2288, 5)

                        # Water consumption
                        water_consumption = int(report.get('waterConsumptionLiter', 0) * 1000)  # Convert L to mL

                        # Get map name from report (if available)
                        map_name = report.get('map', '')

                        # Create entry
                        new_entry = pd.DataFrame({
                            'Location ID': [self.shop_id],
                            'Task Name': [report.get('displayName', '')],
                            'Task ID': [report.get('id', '')],
                            'Robot SN': [sn],
                            'Map Name': [map_name],
                            'Is Report': [1],
                            'Map URL': [''],  # Gas API doesn't provide map URL directly
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
                            'Mode': ['Scrubbing'],  # Default
                            'Sub Mode': ['Custom'],  # Gas doesn't provide sub mode
                            'Type': ['Custom'],
                            'Vacuum Speed': ['Standard'],
                            'Vacuum Suction': ['Standard'],
                            'Wash Speed': ['Standard'],
                            'Wash Suction': ['Standard'],
                            'Wash Water': ['Standard']
                        })

                        schedule_df = pd.concat([schedule_df, new_entry], ignore_index=True)

                    except Exception as e:
                        print(f"Error processing report for robot {sn}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue

            except Exception as e:
                print(f"Error getting task reports for robot {sn}: {e}")
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
            'Initial Power', 'Final Power', 'Power Gain', 'Status'
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
        robot_df = pd.DataFrame(columns=['Location ID', 'Robot SN', 'Robot Name', 'Robot Type',
                                        'Water Level', 'Sewage Level', 'Battery Level',
                                        'x', 'y', 'z', 'Status'])

        # Filter by location_id if specified
        if location_id is not None and location_id != self.shop_id:
            return robot_df

        # Get all robots
        robots_response = self.get_list_robots(shop_id=self.shop_id)
        robots = robots_response.get('list', [])

        # Filter by robot_sn if specified
        if robot_sn is not None:
            robots = [r for r in robots if r.get('sn') == robot_sn]

        # Process each robot
        for robot in robots:
            sn = robot.get('sn')
            if not sn:
                continue

            try:
                # Get robot details
                robot_details = self.get_robot_details(sn)

                if not robot_details:
                    continue

                # Get status
                is_online = robot_details.get('online', False)
                status = 'Online' if is_online else 'Offline'

                # Get battery percentage
                battery_percentage = robot_details.get('battery', None)

                # Gas doesn't provide water and sewage levels
                water_percentage = None
                sewage_percentage = None

                # Get robot name
                robot_name = robot_details.get('nickname', sn)

                # Get position
                position = robot_details.get('position', {})

                # Create row
                robot_row = pd.DataFrame({
                    'Location ID': [self.shop_id],
                    'Robot SN': [sn],
                    'Robot Name': [robot_name],
                    'Robot Type': ['GS-S'],  # Gas robot type
                    'Water Level': [water_percentage],
                    'Sewage Level': [sewage_percentage],
                    'Battery Level': [battery_percentage],
                    'x': [position.get('x', None)],
                    'y': [position.get('y', None)],
                    'z': [position.get('z', None)],
                    'Status': [status]
                })

                robot_df = pd.concat([robot_df, robot_row], ignore_index=True)

            except Exception as e:
                print(f"Error processing robot {sn}: {e}")
                continue

        return robot_df

    def get_ongoing_tasks_table(self, location_id: Optional[str] = None, robot_sn: Optional[str] = None) -> pd.DataFrame:
        """
        Get ongoing tasks for Gas robots
        """
        ongoing_tasks_df = pd.DataFrame(columns=[
            'location_id', 'task_name', 'task_id', 'robot_sn', 'map_name', 'is_report', 'map_url',
            'actual_area', 'plan_area', 'start_time', 'end_time', 'duration',
            'efficiency', 'remaining_time', 'battery_usage', 'consumption', 'water_consumption', 'progress', 'status',
            'mode', 'sub_mode', 'type', 'vacuum_speed', 'vacuum_suction',
            'wash_speed', 'wash_suction', 'wash_water'
        ])

        # Filter by location_id if specified
        if location_id is not None and location_id != self.shop_id:
            return ongoing_tasks_df

        # Get robots
        robots_response = self.get_list_robots(shop_id=self.shop_id)
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

                    # Estimate progress and other metrics from current status
                    # Gas API doesn't provide detailed ongoing task metrics

                    ongoing_task_row = pd.DataFrame({
                        'location_id': [self.shop_id],
                        'task_name': [task_name],
                        'task_id': [''],  # Not available for ongoing tasks
                        'robot_sn': [sn],
                        'map_name': [gas_status.get('localizationInfo', {}).get('map', {}).get('name', '')],
                        'is_report': [0],  # Mark as ongoing task
                        'map_url': [''],
                        'actual_area': [0],
                        'plan_area': [0],
                        'start_time': [pd.Timestamp.now()],  # Approximation
                        'end_time': [pd.Timestamp.now()],
                        'duration': [0],
                        'efficiency': [0],
                        'remaining_time': [0],
                        'battery_usage': [0],
                        'consumption': [0],
                        'water_consumption': [0],
                        'progress': [0],
                        'status': ['In Progress'],
                        'mode': ['Scrubbing'],
                        'sub_mode': ['Custom'],
                        'type': ['Custom'],
                        'vacuum_speed': ['Standard'],
                        'vacuum_suction': ['Standard'],
                        'wash_speed': ['Standard'],
                        'wash_suction': ['Standard'],
                        'wash_water': ['Standard']
                    })

                    ongoing_tasks_df = pd.concat([ongoing_tasks_df, ongoing_task_row], ignore_index=True)

            except Exception as e:
                print(f"Error checking ongoing tasks for robot {sn}: {e}")
                continue

        return ongoing_tasks_df

    def get_robot_work_location_and_mapping_data(self) -> tuple:
        """
        Get robot work location data and map floor mapping data in a single pass
        包含完整的Gas数据处理逻辑

        Returns:
            tuple: (work_location_df, mapping_df)
        """
        work_location_rows = []
        map_floor_data = {}
        current_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

        # Get all robots
        robots_response = self.get_list_robots(shop_id=self.shop_id)
        robots = robots_response.get('list', [])

        for robot in robots:
            sn = robot.get('sn')
            if not sn:
                continue

            try:
                # Get robot status
                gas_status = self.client.get_robot_status(sn)

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
                executing_task = gas_status.get('executingTask')
                is_in_task = executing_task and executing_task.get('name')

                if is_in_task:
                    # Get localization info
                    localization_info = gas_status.get('localizationInfo', {})
                    map_info = localization_info.get('map', {})
                    map_position = localization_info.get('mapPosition', {})

                    map_name = map_info.get('name')
                    # Gas API doesn't provide floor number directly, use map name as approximation
                    floor_number = map_info.get('id', '')  # or could parse from name
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