import json
import requests
from typing import Dict, List, Optional, Any
import time
from datetime import datetime
from typing import Dict, Union

class GaussianRobotAPI:
    """Gaussian Robot API Client

    Implementation based on Gaussian Open Platform API documentation, supporting OAuth authentication and all robot management features
    Reference documentation: https://developer.dev.gs-robot.com/en_US/GeneralIntroduction
    """

    def __init__(self, base_url: str = "https://openapi.gs-robot.com", client_id: str = "muryFD4sL4XsVanqsHwX",
                 client_secret: str = "sWYjrp0D9X7gnkHLP727SeR5lJ1MFbUpOIumN6rt6tHwExvOOJk", open_access_key: str = "5d810a147b55ca9978afa82819b9625d"):
        """Initialize API client

        Args:
            base_url: API base URL, defaults to staging environment
            client_id: Client ID (needs to be replaced with actual value)
            client_secret: Client secret (needs to be replaced with actual value)
            open_access_key: Open access key (needs to be replaced with actual value)
        """
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.open_access_key = open_access_key
        self.access_token = None
        self.refresh_token = None

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                     params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """Generic method for sending HTTP requests

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: URL parameters
            headers: Additional request headers

        Returns:
            API response data
        """
        url = f"{self.base_url}{endpoint}"

        # Set default request headers
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Add Authorization header if access_token exists
        if self.access_token:
            default_headers["Authorization"] = f"Bearer {self.access_token}"

        # Merge custom request headers
        if headers:
            default_headers.update(headers)

        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=default_headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}

    def get_oauth_token(self) -> Dict:
        """Get OAuth access token

        Use client_id, client_secret and open_access_key to get access token

        Returns:
            Dictionary containing access_token and refresh_token
        """
        endpoint = "/gas/api/v1alpha1/oauth/token"
        data = {
            "grant_type": "urn:gaussian:params:oauth:grant-type:open-access-token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "open_access_key": self.open_access_key
        }

        response = self._make_request("POST", endpoint, data=data)

        # If token is successfully obtained, save to instance variables
        if "access_token" in response:
            self.access_token = response["access_token"]
        if "refresh_token" in response:
            self.refresh_token = response["refresh_token"]

        return response

    def list_robots(self, page: int = 1, page_size: int = 200,
                   filter_params: Optional[str] = None, relation: str = "bound") -> Dict:
        """List robots belonging to the tenant
        Link: https://developer.gs-robot.com/zh_CN/Robot%20Information%20Service/List%20Robots

        Args:
            page: Page number
            page_size: Page size
            filter_params: Filter parameters, format "key=value", e.g. "online=true&serialNumber=TEST00-0000-000-B024"
            relation: Relation type, "bound" lists robots of binded robots, other values list all accessible robots

        Returns:
            {'serialNumber': 'GS438-6030-74Q-Q100',
             'name': 'robots/GS438-6030-74Q-Q100',
             'displayName': 'Baton.phantas',
             'modelFamilyCode': 'S',
             'modelTypeCode': 'Scrubber S1',
             'online': True,
             'softwareVersion': 'GS-S-OS1804-OTA_S1-60-0p-20240104',
             'hardwareVersion': 'V1.0'
            }
        """
        endpoint = "/v1alpha1/robots"
        params = {
            "page": page,
            "pageSize": page_size,
            "relation": relation
        }

        if filter_params:
            params["filter"] = filter_params

        return self._make_request("GET", endpoint, params=params)

    def get_robot_status(self, serial_number: str) -> Dict:
        """Query real-time status of a single robot. Link: https://developer.gs-robot.com/zh_CN/Robot%20Information%20Service/V1%20Get%20Robot%20Status

        Args:
            serial_number: Robot serial number

        Returns:
             Data Structure:
             {
                 'serialNumber': str,
                 'name': str,
                 'position': {
                     'latitude': float,
                     'longitude': float,
                     'angle': float
                 },
                 'taskState': str,
                 'online': bool,
                 'speedKilometerPerHour': float,
                 'battery': {
                     'charging': bool,
                     'powerPercentage': float,
                     'totalVoltage': float,
                     'current': float,
                     'fullCapacity': float,
                     'soc': float,
                     'soh': str,
                     'cycleTimes': int,
                     'protectorStatus': list,
                     'temperature1': float,
                     'temperature2': float,
                     'temperature3': float,
                     'temperature4': float,
                     'temperature5': float,
                     'temperature6': float,
                     'temperature7': float,
                     'cellVoltage1': float,
                     'cellVoltage2': float,
                     'cellVoltage3': float,
                     'cellVoltage4': float,
                     'cellVoltage5': float,
                     'cellVoltage6': float,
                     'cellVoltage7': float
                 },
                 'emergencyStop': {
                     'enabled': bool
                 },
                 'localizationInfo': {
                     'localizationState': str,
                     'map': {
                         'id': str,
                         'name': str
                     },
                     'mapPosition': {
                         'x': float,
                         'y': float,
                         'angle': float
                     }
                 },
                 'navStatus': str,
                 'currentElevatorStatus': str,
                 'executableTasks': list[dict],
                 'executingTask': dict,
                 'cleanModes': list[dict],
                 'device': dict,
                 'workModes': list[dict]
             }
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/status"
        return self._make_request("GET", endpoint)

    def get_status_reports(self, serial_number: str,
                          start_time: Union[int, str, datetime],
                          end_time: Union[int, str, datetime],
                          utc_offset_seconds: int = 0) -> Dict:
        """Get robot online/offline status reports. Link: https://developer.gs-robot.com/zh_CN/Robot%20Information%20Service/List%20Robot%20Status%20Reports

        Args:
            serial_number: Robot serial number
            start_time: Start time (Unix timestamp seconds, or ISO format string, or datetime object)
            end_time: End time (Unix timestamp seconds, or ISO format string, or datetime object)
            utc_offset_seconds: UTC offset (seconds), multiples of 3600 represent different timezones

        Returns:
            Status report data

            {'reports': [{'date': '2025-08-31',
                          'onlineDuration': 28801,
                          'offlineDuration': 0},
                         {'date': '2025-09-01', 'onlineDuration': 64463, 'offlineDuration': 21906},
                         {'date': '2025-09-02', 'onlineDuration': 0, 'offlineDuration': 32376}]}
        """

        def _convert_to_timestamp(time_value: Union[int, str, datetime]) -> int:
            """Convert various time formats to Unix timestamp seconds"""
            if isinstance(time_value, int):
                return time_value
            elif isinstance(time_value, str):
                # Try to parse ISO format string
                try:
                    dt = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                    return int(dt.timestamp())
                except ValueError:
                    raise ValueError(f"Invalid time string format: {time_value}. Use ISO format (e.g., '2023-10-01T12:00:00')")
            elif isinstance(time_value, datetime):
                return int(time_value.timestamp())
            else:
                raise TypeError(f"Unsupported time type: {type(time_value)}")

        # Convert times to timestamp seconds
        start_time_seconds = _convert_to_timestamp(start_time)
        end_time_seconds = _convert_to_timestamp(end_time)

        endpoint = f"/v1alpha1/robots/{serial_number}/statusReports"
        params = {
            "timeSpan.startTime.seconds": start_time_seconds,
            "timeSpan.endTime.seconds": end_time_seconds,
            "utcOffset.seconds": utc_offset_seconds
        }

        return self._make_request("GET", endpoint, params=params)

    def batch_get_robot_statuses(self, serial_numbers: List[str]) -> Dict:
        """Batch query real-time status of multiple robots

        Args:
            serial_numbers: List of robot serial numbers

        Returns:
            Batch robot status data
        {'robotStatuses': [result of get_robot_status()]}

        """
        endpoint = "/v1alpha1/robots/-/status:batchGet"
        params = {}

        # Add multiple names parameters
        for sn in serial_numbers:
            if "names" not in params:
                params["names"] = []
            params["names"].append(sn)

        return self._make_request("GET", endpoint, params=params)

    def get_cleaning_reports(self, serial_number: str, start_time_seconds: int,
                           end_time_seconds: int, utc_offset_seconds: int = 3600) -> Dict:
        """Get robot cleaning reports

        Args:
            serial_number: Robot serial number
            start_time_seconds: Start time (Unix timestamp seconds)
            end_time_seconds: End time (Unix timestamp seconds)
            utc_offset_seconds: UTC offset (seconds), multiples of 3600 represent different timezones

        Returns:
            Cleaning report data
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/cleaningReports"
        params = {
            "timeSpan.startTime.seconds": start_time_seconds,
            "timeSpan.endTime.seconds": end_time_seconds,
            "utcOffset.seconds": utc_offset_seconds
        }

        return self._make_request("GET", endpoint, params=params)

    def get_map_download_uri(self, serial_number: str, map_id: str) -> Dict:
        """Get map download URI (when map is in cloud). Link: https://developer.gs-robot.com/zh_CN/Robot%20Map%20Service/V1%20Get%20Robot%20Map

        Args:
            serial_number: Robot serial number
            map_id: Map ID

        Returns:
            Map download URI data
        {
            "downloadUri": str
        }
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/maps/{map_id}"
        return self._make_request("GET", endpoint)

    def upload_robot_map(self, serial_number: str, map_file: str) -> Dict:
        """Upload map from robot to cloud (when cloud map is deleted)

        Args:
            serial_number: Robot serial number
            map_file: Map file parameter, can be found in GetRobotStatus or BatchGetRobotStatuses interface

        Returns:
            Upload result data

        {
            "recordId": "7f49a7f9-153c-49ad-8531-07450ee7ad54"
        }
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/maps/-:uploadRobotMap"
        data = {
            "mapFile": map_file
        }

        return self._make_request("POST", endpoint, data=data)

    def get_upload_status(self, serial_number: str, record_id: str) -> Dict:
        """Query upload file status

        Args:
            serial_number: Robot serial number
            record_id: Record ID

        Returns:
            Upload status data
        {
            "id": "3f69c2b9-415d-4623-9299-389ecc147f3c",
            "recordStatus": "AVAILABLE"
        }
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/records/{record_id}"
        return self._make_request("GET", endpoint)

    def get_task_reports(self, serial_number: str,
                        startTimeUtcFloor: Union[str, datetime],
                        startTimeUtcUpper: Union[str, datetime],
                        page: int = 1, page_size: int = 200) -> Dict:
        """Get robot task reports list. Link: https://developer.gs-robot.com/zh_CN/Robot%20Cleaning%20Data%20Service/V1%20List%20Robot%20Task%20Reports

        Args:
            serial_number: Robot serial number
            startTimeUtcFloor: Start time floor (ISO format string, datetime object, or string like "2025-09-01 09:00:01")
            startTimeUtcUpper: Start time upper bound (ISO format string, datetime object, or string like "2025-09-01 09:00:01")
            page: Page number
            page_size: Page size

        Returns:
            Task reports list data
            {
                "robotTaskReports": list[{
                    "id": str,
                    "name": str,
                    "areaNameList": str,
                    "map": str,
                    "displayName": str,
                    "robot": str,
                    "robotSerialNumber": str,
                    "operator": str,
                    "completionPercentage": float,
                    "durationSeconds": int,
                    "plannedCleaningAreaSquareMeter": float,
                    "actualCleaningAreaSquareMeter": float,
                    "efficiencySquareMeterPerHour": float,
                    "plannedPolishingAreaSquareMeter": float,
                    "actualPolishingAreaSquareMeter": float,
                    "waterConsumptionLiter": float,
                    "startBatteryPercentage": int,
                    "endBatteryPercentage": int,
                    "consumablesResidualPercentage": {
                        "brush": int,
                        "filter": int,
                        "suctionBlade": int
                    },
                    "startTime": str,
                    "endTime": str
                }],
                "page": int,
                "pageSize": int,
                "total": str
            }
        """

        def _convert_to_iso_format(time_value: Union[str, datetime]) -> str:
            """Convert various time formats to ISO format string with Z timezone"""
            if isinstance(time_value, datetime):
                # Convert datetime to UTC ISO format with Z timezone
                return time_value.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Handle string inputs
            time_str = str(time_value).strip()

            # If it's already in ISO format with Z timezone
            if time_str.endswith('Z') and 'T' in time_str:
                return time_str

            try:
                # Try common datetime formats
                formats = [
                    '%Y-%m-%dT%H:%M:%S',      # ISO without timezone
                    '%Y-%m-%d %H:%M:%S',      # Space separated
                    '%Y-%m-%dT%H:%M:%S.%f',   # ISO with microseconds
                    '%Y-%m-%d %H:%M:%S.%f',   # Space separated with microseconds
                    '%Y-%m-%dT%H:%M',         # ISO without seconds
                    '%Y-%m-%d %H:%M',         # Space separated without seconds
                ]

                for fmt in formats:
                    try:
                        dt = datetime.strptime(time_str, fmt)
                        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                    except ValueError:
                        continue

                # If none of the formats work, try fromisoformat as fallback
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

            except ValueError:
                raise ValueError(f"Invalid time string format: {time_value}. Use formats like '2024-01-12T08:00:00Z', '2024-01-12 08:00:00', or datetime object")

        # Convert times to ISO format strings
        start_time_floor_iso = _convert_to_iso_format(startTimeUtcFloor)
        start_time_upper_iso = _convert_to_iso_format(startTimeUtcUpper)

        endpoint = f"/v1alpha1/robots/{serial_number}/taskReports"
        params = {
            "page": page,
            "pageSize": page_size,
            "startTimeUtcFloor": start_time_floor_iso,
            "startTimeUtcUpper": start_time_upper_iso
        }

        return self._make_request("GET", endpoint, params=params)

    def generate_robot_task_report_png(self, serial_number: str, task_report_id: str,
                                     language_code: str = "zh") -> Dict:
        """Generate robot task report PNG image

        Args:
            serial_number: Robot serial number
            task_report_id: Task report ID
            language_code: Language code, defaults to "zh"

        Returns:
            Generated PNG image data
        {
           "uri": str
        }
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/taskReports/{task_report_id}:generateRobotTaskReportPng"
        data = {
            "languageCode": language_code
        }

        return self._make_request("POST", endpoint, data=data)

    def list_robot_commands(self, serial_number: str, page: int = 1, page_size: int = 5,
                           order_by: str = "create_time desc") -> Dict:
        """List commands created for specified robot

        Args:
            serial_number: Robot serial number
            page: Page number
            page_size: Page size
            order_by: Sort order, options: create_time asc, create_time desc, update_time asc, update_time desc

        Returns:
            Command list data
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/commands"
        params = {
            "page": page,
            "pageSize": page_size,
            "order_by": order_by
        }

        return self._make_request("GET", endpoint, params=params)

    def get_robot_command(self, serial_number: str, command_id: str) -> Dict:
        """Get specified command and its status for specified robot

        Args:
            serial_number: Robot serial number
            command_id: Command ID

        Returns:
            Command details and status data
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/commands/{command_id}"
        return self._make_request("GET", endpoint)

    def create_remote_task_command(self, serial_number: str, command_type: str,
                                 start_time_seconds: int, start_delay: int = 180000,
                                 user: str = "Gaussian", cleaning_mode: str = "middle_cleaning",
                                 map_name: str = "", task_name: str = "execute_task_fg1",
                                 loop: bool = False, loop_count: int = 1) -> Dict:
        """Create remote task command

        Args:
            serial_number: Robot serial number
            command_type: Remote task command type, options: START_TASK, PAUSE_TASK, RESUME_TASK, STOP_TASK
            start_time_seconds: Start time (Unix timestamp seconds)
            start_delay: Start delay (milliseconds)
            user: User name
            cleaning_mode: Cleaning mode, can be obtained from GetRobotStatus interface
            map_name: Map name, can be obtained from GetRobotStatus interface
            task_name: Task name
            loop: Whether to loop
            loop_count: Loop count

        Returns:
            Created command data
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/commands"
        data = {
            "user": user,
            "startTime": {
                "seconds": start_time_seconds,
                "nanos": 1000
            },
            "startDelay": start_delay,
            "serialNumber": serial_number,
            "remoteTaskCommandType": command_type,
            "commandParameter": {
                "startTaskParameter": {
                    "cleaningMode": cleaning_mode,
                    "task": {
                        "loop": loop,
                        "loopCount": loop_count,
                        "map": map_name,
                        "name": task_name
                    }
                }
            }
        }

        return self._make_request("POST", endpoint, data=data)

    def create_remote_navigation_command(self, serial_number: str, command_type: str,
                                       start_time_seconds: int, start_delay: int = 180000,
                                       user: str = "Gaussian", map_name: str = "",
                                       position: str = "") -> Dict:
        """Create remote navigation command

        Args:
            serial_number: Robot serial number
            command_type: Remote navigation command type, options: CROSS_NAVIGATE, PAUSE_NAVIGATE, RESUME_NAVIGATE, STOP_NAVIGATE
            start_time_seconds: Start time (Unix timestamp seconds)
            start_delay: Start delay (milliseconds)
            user: User name
            map_name: Map name, can be obtained from GetRobotStatus interface
            position: Position information, can be obtained from GetRobotStatus interface

        Returns:
            Created command data
        """
        endpoint = f"/v1alpha1/robots/{serial_number}/commands"
        data = {
            "user": user,
            "startTime": {
                "seconds": start_time_seconds,
                "nanos": 1000
            },
            "startDelay": start_delay,
            "serialNumber": serial_number,
            "remoteNavigationCommandType": command_type,
            "commandParameter": {
                "startNavigationParameter": {
                    "map": map_name,
                    "position": position
                }
            }
        }

        return self._make_request("POST", endpoint, data=data)


# Convenience function for quickly creating API client instance
def create_gaussian_api_client(base_url: str = "https://openapi.gs-robot.com",
                              client_id: str = "muryFD4sL4XsVanqsHwX",
                              client_secret: str = "sWYjrp0D9X7gnkHLP727SeR5lJ1MFbUpOIumN6rt6tHwExvOOJk",
                              open_access_key: str = "5d810a147b55ca9978afa82819b9625d") -> GaussianRobotAPI:
    """Create Gaussian Robot API client instance

    Args:
        base_url: API base URL
        client_id: Client ID
        client_secret: Client secret
        open_access_key: Open access key

    Returns:
        GaussianRobotAPI instance
    """
    return GaussianRobotAPI(base_url, client_id, client_secret, open_access_key)


# Usage example
if __name__ == "__main__":
    # Create API client
    api = create_gaussian_api_client()

    # Get OAuth token
    token_response = api.get_oauth_token()
    print("Token response:", token_response)

    # List robots
    # robots = api.list_robots()
    # print("Robots:", robots)

    # Get robot status
    robots_list = ["GS438-6030-74Q-Q100","GS442-6130-82R-6000"]
    status = api.batch_get_robot_statuses(robots_list)
    print("Robot status:", status)
