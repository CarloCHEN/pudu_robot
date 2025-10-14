import base64
import datetime
import hashlib
import hmac
import json
from urllib.parse import urlparse
from urllib.parse import unquote

import requests
import pandas as pd

# 应用 ApiAppKey
ApiAppKey = 'APID18lGz1qBaBF9XWuttd5YszenrpsodKgt20i9'
# 应用 ApiAppSecret
ApiAppSecret = 'k2fmGdhz6mhqcl79eWot9f2kqoqosC2q0cm6csM1'

def run_url(url):
    # Parse URL
    url_info = urlparse(url)
    host = url_info.hostname
    path = url_info.path

    # Adjust path for signature calculation
    if path.startswith(("/release", "/test", "/prepub")):
        path = "/" + path[1:].split("/", 1)[1]
    path = path if path else "/"

    # Handle query parameters
    if url_info.query:
        query_str = url_info.query
        split_str = query_str.split("&")
        sorted_query = "&".join(sorted(split_str))
        path += "?" + unquote(sorted_query)

    # Generate headers
    gmt_format = "%a, %d %b %Y %H:%M:%S GMT"
    x_date = datetime.datetime.utcnow().strftime(gmt_format)
    content_md5 = ""
    signing_str = f"x-date: {x_date}\nGET\napplication/json\napplication/json\n{content_md5}\n{path}"

    # Sign the request
    sign = hmac.new(ApiAppSecret.encode(), msg=signing_str.encode(), digestmod=hashlib.sha1).digest()
    signature = base64.b64encode(sign).decode()
    authorization = f'hmac id="{ApiAppKey}", algorithm="hmac-sha1", headers="x-date", signature="{signature}"'

    headers = {
        "Host": host,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-date": x_date,
        "Authorization": authorization
    }

    # Send GET request
    response = requests.get(url, headers=headers)
    return response.text

def get_list_stores(limit=None, offset=None):
    """Accepts limit and offset as parameters and returns a list of stores
    @param limit: The number of stores to return
    @param offset: The offset to start from
    @return: Count and a list of store dictionaries - {company_id, company_name, shop_id, shop_name}
    {}
    """
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-open-platform-service/v1/api/shop?"
    if limit and offset:
        url += f"limit={limit}&offset={offset}"
    elif limit:
        url += f"limit={limit}"
    elif offset:
        url += f"offset={offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_list_robots(shop_id=None, limit=None, offset=None):
    """Accepts limit and offset as parameters and returns a list of robots
    @param shop_id: The ID of the shop to filter robots by
    @param limit: The number of robots to return
    @param offset: The offset to start from
    @return: Count and a list of robot dictionaries - {mac, shop_id, shop_name, sn}
    """
    url = "https://csu-open-platform.pudutech.com/pudu-entry/data-open-platform-service/v1/api/robot?"

    # Add parameters to the URL if they are provided
    params = []
    if shop_id is not None:
        params.append(f"shop_id={shop_id}")
    if limit is not None:
        params.append(f"limit={limit}")
    if offset is not None:
        params.append(f"offset={offset}")

    # Append parameters to the base URL
    if params:
        url += "&".join(params)

    response = run_url(url)  # Assuming run_url is a function that handles API requests
    response = json.loads(response)

    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_list_maps(shop_id):
    """ Accepts a shop ID and returns a list of maps for that shop
    @param shop_id: The shop ID to get maps for
    @return: Count and a list of map dictionaries - {map_name}
    """
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-open-platform-service/v1/api/maps?shop_id={shop_id}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_map_details(shop_id, map_name, device_width, device_height):
    """ Accepts a shop ID, map name, device width, and device height and returns map details
    @param shop_id: The shop ID
    @param map_name: The map name
    @param device_width: The device width
    @param device_height: The device height
    @return: The map details dictionary - {"canvas_translate_x": 2.4473324,
                                           "canvas_translate_y": 402.68384,
                                           "element_list": [
                                           {
                                           "clean_path_list": [],
                                           "id": "7##return_point0EC1D9EA2821F1691742592683",
                                           "mode": "return_point",
                                           "name": "返航点2",
                                           "type": "source",
                                           "vector_list": [
                                           ]
                                           }]}
    """
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-open-platform-service/v1/api/maps?shop_id={shop_id}&map_name={map_name}&device_width={device_width}&device_height={device_height}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_robot_current_position(shop_id, sn):
    """ Accepts a shop ID and serial number and returns the current position of the robot. Only support PUDU CC1
    @param shop_id: The shop ID
    @param sn: The serial number of the robot
    @return: The current position dictionary - {}
    """
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-open-platform-service/v1/api/map/robotCurrentPosition?shop_id={shop_id}&sn={sn}"
    response = run_url(url)
    response = json.loads(response)
    if response["message"] != "Robot is offline":
        return response["data"]
    else:
        return response

def get_robot_overview_data(start_time, end_time, shop_id=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns an overview of robot data
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @return: The overview data dictionary - {'summary': {'boot_count': 1,
                                            'total_count': 1,
                                            'bind_count': 0,
                                            'active_count': 0,
                                            'lively_rate': 100},
                                            'qoq': {'boot_count': 1,
                                            'total_count': 1,
                                            'bind_count': 1,
                                            'active_count': 1,
                                            'lively_rate': 0},
                                            'chart': {}}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/brief/robot?timezone_offset={timezone_offset}&start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_robot_overview_operation_data(start_time, end_time, shop_id=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns an overview of robot operation data

    returns the operation data of a shop for all robots?
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @return: The overview operation data dictionary - {'summary': {'duration': 81.45,
                                                        'mileage': 0,
                                                        'task_count': 91,
                                                        'area': 56430.62},
                                                       'qoq': {'duration': 37.83, 'mileage': 0, 'task_count': 78, 'area': 24498.51}}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/brief/run?timezone_offset={timezone_offset}&start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_store_overview_data(start_time, end_time, shop_id=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns an overview of store data
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @return: The overview data dictionary - {'summary': {'lively_count': 1,
                                              'total_count': 1,
                                              'new_count': 0,
                                              'lively_rate': 100},
                                             'qoq': {'lively_count': 1,
                                              'total_count': 1,
                                              'new_count': 1,
                                              'lively_rate': 0},
                                             'lively_top10': [{'shop_id': 434300005,
                                               'shop_name': 'USF',
                                               'run_count': 1,
                                               'bind_count': 1,
                                               'duration': 81.45,
                                               'stop_duration': 635.88}],
                                             'silent_top10': []}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/brief/shop?timezone_offset={timezone_offset}&start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_store_analytics(start_time, end_time, shop_id=None, time_unit=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns store analytics data
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param time_unit: The time unit to aggregate data by day or hour
    @param timezone_offset: The timezone offset

    @return: The store analytics data dictionary - {'summary': {'lively_count': 1,
                                                     'silent_count': 0,
                                                     'new_count': 0,
                                                     'total_count': 1},
                                                    'qoq': {'lively_count': 1,
                                                     'silent_count': 0,
                                                     'new_count': 1,
                                                     'total_count': 1},
                                                    'chart': [{'task_time': '2024-09-01',
                                                      'lively_count': 0,
                                                      'silent_count': 1,
                                                      'new_count': 0,
                                                      'total_count': 1}]}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/analysis/shop?timezone_offset={timezone_offset}&start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if time_unit:
        url += f"&time_unit={time_unit}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_store_analytics_list(start_time, end_time, shop_id=None, time_unit=None, offset=None, limit=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns store analytics data with paging
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param time_unit: The time unit to aggregate data by day or hour
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param timezone_offset: The timezone offset

    @return: The store analytics data dictionary - {'total': 1,
                                                    'offset': 0,
                                                    'limit': 20,
                                                    'list': [{'rank': 1,
                                                      'shop_id': 434300005,
                                                      'shop_name': 'USF',
                                                      'run_count': 1,
                                                      'bind_count': 1,
                                                      'duration': 81.45,
                                                      'mileage': 0,
                                                      'task_count': 91,
                                                      'create_time': '2024-08-21 06:04:31'}]}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/analysis/shop/paging?timezone_offset={timezone_offset}&start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if time_unit:
        url += f"&time_unit={time_unit}"
    if offset:
        url += f"&offset={offset}"
    if limit:
        url += f"&limit={limit}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_machine_run_analytics(start_time, end_time, shop_id=None, time_unit=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns machine run analytics data

    returns the number of tasks run by each robot in a shop?
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param time_unit: The time unit to aggregate data by day or hour
    @param timezone_offset: The timezone offset

    @return: The machine run analytics data dictionary - {'chart': [{'task_time': '2024-09-01', 'run_count': 0, 'list': []},
                                                                    {'task_time': '2024-09-02', 'run_count': 0, 'list': []},
                                                                    {'task_time': '2024-09-03',
                                                                     'run_count': 1,
                                                                     'list': [{'task_time': '2024-09-03',
                                                                       'product_code': 'CC1',
                                                                       'run_count': 1}]}]}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/analysis/run?timezone_offset={timezone_offset}&start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if time_unit:
        url += f"&time_unit={time_unit}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_machine_run_analytics_list(start_time, end_time, shop_id=None, time_unit=None, offset=None, limit=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns machine run analytics data with paging

    returns the number of tasks, duration run by each robot in a shop, on each day? difference vs get_machine_run_analytics?

    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param time_unit: The time unit to aggregate data by day or hour
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param timezone_offset: The timezone offset

    @return: The machine run analytics data dictionary - {'total': 16,
                                                          'offset': 0,
                                                          'limit': 20,
                                                          'list': [{'task_time': '2024-09-20',
                                                            'product_code': 'CC1',
                                                            'mac': 'B0:0C:9D:59:16:E8',
                                                            'shop_id': 434300005,
                                                            'shop_name': 'USF',
                                                            'first_run_time': '2024-09-20 05:26:43',
                                                            'duration': 0.05,
                                                            'mileage': 0,
                                                            'task_count': 3,
                                                            'sn': '811064412050012'}]}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/analysis/run/paging?timezone_offset={timezone_offset}&start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if time_unit:
        url += f"&time_unit={time_unit}"
    if offset:
        url += f"&offset={offset}"
    if limit:
        url += f"&limit={limit}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_log_list(start_time, end_time, shop_id=None, offset=None, limit=None, check_step=None, is_success=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns a list of logs
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param check_step: Self-test items, e.g. CheckCAN
    @param is_success: All items are self-tested successfully: 0 failed (with exception) 1 succeeded (no abnormal) -1 did not filter
    @param timezone_offset: The timezone offset

    @return: The log list dictionary - {'total': 0, 'offset': 0, 'limit': 100, 'list': []}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/log/boot/query_list?start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if offset:
        url += f"&offset={offset}"
    if limit:
        url += f"&limit={limit}"
    if check_step:
        url += f"&check_step={check_step}"
    if is_success:
        url += f"&is_success={is_success}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_event_list(start_time, end_time, shop_id=None, offset=None, limit=None, error_levels=None, error_types=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns a list of events
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param error_levels: The event level
    @param error_types: The event type
    @param timezone_offset: The timezone offset

    @return: The event list dictionary - {'total': 402,
                                          'offset': 0,
                                          'limit': 100,
                                          'list': [{'id': 'd8670a3f-a6ab-4ef6-8155-ef71aa5d9cd0',
                                            'sn': '811064412050012',
                                            'mac': 'B0:0C:9D:59:16:E8',
                                            'product_code': 'CC1',
                                            'upload_time': '2024-09-20 09:13:26',
                                            'task_time': '2024-09-20 09:13:16',
                                            'soft_version': '2.0.5.216_P01C0000B2409140902CNU',
                                            'hard_version': '',
                                            'os_version': '27',
                                            'error_level': 'WARNING',
                                            'error_type': 'LostLocalization',
                                            'error_detail': 'OdomSlip',
                                            'error_id': 'vir_1726794796'}]}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/log/error/query_list?start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if offset:
        url += f"&offset={offset}"
    if limit:
        url += f"&limit={limit}"
    if error_levels:
        url += f"&error_levels={error_levels}"
    if error_types:
        url += f"&error_types={error_types}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_charging_record_list(start_time, end_time, shop_id=None, offset=None, limit=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns a list of charging records
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param timezone_offset: The timezone offset

    @return: The charging record list dictionary - {'total': 78,
                                                    'offset': 0,
                                                    'limit': 100,
                                                    'list':
                                                    [{'id': 'e45bc3fc-7a90-4ab1-a9e7-403df889056a',
                                                      'sn': '811064412050012',
                                                      'mac': 'B0:0C:9D:59:16:E8',
                                                      'product_code': 'CC1',
                                                      'upload_time': '2024-09-20 07:04:34',
                                                      'task_time': '2024-09-20 06:43:53',
                                                      'soft_version': '2.0.5.216_P01C0000B2409140902CNU',
                                                      'hard_version': '',
                                                      'os_version': '27',
                                                      'charge_power_percent': 0,
                                                      'charge_duration': 10,
                                                      'min_power_percent': 100,
                                                      'max_power_percent': 100}]
                                                    }
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/log/charge/query_list?start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if offset:
        url += f"&offset={offset}"
    if limit:
        url += f"&limit={limit}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_battery_health_list(start_time, end_time, shop_id=None, sn=None, offset=None, limit=None, timezone_offset=0):
    """ Accepts a shop ID, start time, and end time and returns a list of battery health records
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param sn: The serial number of the robot
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param timezone_offset: The timezone offset

    @return: The battery health list dictionary with cycle, soc, and soh data

    {
        "code": int,  # 200
        "message": str,  # "ok"
        "data": {
            "total": int,  # 12
            "page": int,  # 0
            "limit": int,  # 1
            "list": [
                {
                    "id": str,  # "a70ee902-6f7a-4a32-8765-917f58ca1a11"
                    "sn": str,  # "PDY202503051721"
                    "mac": str,  # "14:80:CC:89:26:6D"
                    "product_code": str,  # "81"
                    "upload_time": str,  # "2025-07-01 00:00:03"
                    "task_time": str,  # "2025-06-30 23:59:51"
                    "soft_version": str,  # "SD1.0.10.2025062917@master"
                    "hard_version": str,  # "0.4.27"
                    "os_version": str,  # "32"
                    "battery_sn": str,  # "F7S4PNH2412280039"
                    "battery_model": int,  # 41
                    "cycle": int,  # 50
                    "design_capacity": int,  # 10000
                    "pack_voltage": int,  # 24851
                    "soc": int,  # 28
                    "soh": int,  # 100
                    "battery_model_name": str,  # "赣锋 7串4并"
                    "shop_id": str,  # "450300000"
                    "shop_name": str,  # "闪电匣机型系列测试门店（国内）"
                    "full_capacity": int,  # 10160
                    "work_status": int,  # 2
                    "current": int,  # -838
                    "cell_temperature": list,  # []
                    "cell_voltage": list  # []
                }
            ],
            "offset": int  # 0
        }
    }
    """
    try:
        # convert str to seconds
        start_time_ts = int(pd.to_datetime(start_time).timestamp())
        end_time_ts = int(pd.to_datetime(end_time).timestamp())

        url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/log/battery/query_list?start_time={start_time_ts}&end_time={end_time_ts}"

        if shop_id:
            url += f"&shop_id={shop_id}"
        if sn:
            url += f"&sn={sn}"
        if offset:
            url += f"&offset={offset}"
        if limit:
            url += f"&limit={limit}"
        if timezone_offset:
            url += f"&timezone_offset={timezone_offset}"

        response = run_url(url)

        # 解析JSON响应
        response_data = json.loads(response)

        # 检查响应状态 - 根据实际的响应消息
        message = response_data.get("message", "").upper()
        if message in ["SUCCESS", "OK"]:
            return response_data.get("data", {})
        else:
            # 返回整个响应以便查看错误信息
            print(f"API returned non-success status: {message}")
            return response_data

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return {"error": "Invalid JSON response", "raw_response": response}
    except Exception as e:
        print(f"Request failed: {e}")
        return {"error": f"Request failed: {str(e)}"}

def get_task_list(shop_id=None, sn=None):
    """ Accepts a shop ID and serial number and returns a list of tasks
    @param shop_id: The shop ID
    @param sn: The serial number of the robot
    @return: The task list dictionary - {'count': 10,
                                         'item': [{'task_id': '1023883777229209600',
                                           'version': 1726093945251,
                                           'name': 'Basement Dry',
                                           'desc': '',
                                           'config': {
                                            'mode': 2,
                                            'vacuum_speed': 2,
                                            'vacuum_suction': 2,
                                            'wash_speed': 0,
                                            'wash_suction': 0,
                                            'wash_water': 0,
                                            'type': 1,
                                            'left_brush': 0,
                                            'right_brush': 0
                                            },
                                           'floor_list': [{'map': {'name': '1#6#USF-LIB-basement',
                                              'lv': 10,
                                              'floor': '1'},
                                             'area_list': [],
                                             'area_array': [
                                                {'area_id': '11724279170981B00C9D5916E81724279170982',
                                                'clean_count': 1,
                                                'type': 0,
                                                'area': 166.59},
                                                {'area_id': '27B00C9D5916E81724279171241',
                                                'clean_count': 1,
                                                'type': 1,
                                                'area': 46.564785},
                                                {'area_id': '11724279170980B00C9D5916E81724279170981',
                                                'clean_count': 1,
                                                'type': 0,
                                                'area': 487.01},
                                                {'area_id': '23B00C9D5916E81724279171114',
                                                'clean_count': 1,
                                                'type': 2,
                                                'area': 34.892174}
                                               ],
                                             'elv_array': []}],
                                           'status': 1,
                                           'is_single_task': True,
                                           'task_count': 1,
                                           'task_mode': -1,
                                           'back_point': {'floor': '1',
                                            'map_name': '1#6#USF-LIB-basement',
                                            'point_name': 'basement home',
                                            'point_id': '7##return_point0B00C9D5916E81724279170766'},
                                           'pre_clean_time': 3307,
                                           'is_area_connect': False,
                                           'station_config': None,
                                           'cleanagent_config': {'isopen': False, 'scale': 0},
                                           'is_hand_sort': True,
                                           'mode': 2,
                                           'temporary_point': None,
                                           'product': 'cleanbot',
                                           'move_speed': 0,
                                           'cleaning_speed': 0}]}
    """
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/cleanbot-service/v1/api/open/task/list"
    if shop_id:
        url += f"?shop_id={shop_id}"
    if sn:
        url += f"&sn={sn}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_scheduled_task_list(sn=None):
    """ Accepts a serial number and returns a list of scheduled tasks
    @param sn: The serial number of the robot
    @return: The task list dictionary -
    """
    if not sn:
        raise ValueError("Serial number is required")
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/cleanbot-service/v1/api/open/cron/list?sn={sn}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_robot_details(sn):
    """ Accepts a serial number and returns the details of the robot updated every 30s
    @param sn: The serial number of the robot
    @return: The robot details dictionary - {'mac': 'B0:0C:9D:59:16:E8',
                                             'nickname': 'USF_LIB',
                                             'online': False,
                                             'battery': 92,
                                             'map': {'name': '1#11#USF-ISA-1ST-FLOORV2', 'lv': 1, 'floor': ''},
                                             'cleanbot': {'rising': 0, # clean water percentage
                                              'sewage': 0, # sewage water percentage
                                              'task': 0, # task percentage
                                              'clean': None, # clean task json details
                                              'last_mode': 1,
                                              'detail': '',
                                              'last_task': '1034371902204297216'},
                                             'shop': {'id': 434300005, 'name': 'USF'},
                                             'position': {'x': 0.5876039557511565,
                                                          'y': -43.2574551034073,
                                                          'z': -1.7211329927921517},
                                             'sn': '811064412050012'}
    """
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/cleanbot-service/v1/api/open/robot/detail?sn={sn}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def send_command_to_robot():
    pass

def get_task_schema_analytics(start_time, end_time, shop_id=None, time_unit=None, clean_mode=None, sub_mode=None, timezone_offset=None):
    """ Accepts a shop ID, start time, and end time and returns a list of task schema analytics
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param time_unit: The time unit to aggregate data by day or hour
    @param clean_mode: The clean mode
    @param sub_mode: The sub mode
    @param timezone_offset: The timezone offset

    @return: The task schema analytics dictionary - {'summary': {'area': 277.94,
                                                                 'duration': 0.57,
                                                                 'power_consumption': 0.16,
                                                                 'water_consumption': 0,
                                                                 'task_count': 6,
                                                                 'plan_area': 1087.83},
                                                     'qoq': {'area': 0,
                                                             'duration': 0,
                                                             'power_consumption': 0,
                                                             'water_consumption': 0,
                                                             'task_count': 0,
                                                             'plan_area': 0},
                                                     'chart':
                                                     [
                                                        {'task_time': '2024-09-01',
                                                         'area': 0,
                                                         'duration': 0,
                                                         'power_consumption': 0,
                                                         'water_consumption': 0,
                                                         'task_count': 0,
                                                         'plan_area': 0
                                                        }
                                                     ]
                                                    }
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/analysis/clean/mode?start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if time_unit:
        url += f"&time_unit={time_unit}"
    if clean_mode:
        url += f"&clean_mode={clean_mode}"
    if sub_mode:
        url += f"&sub_mode={sub_mode}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_task_schema_analytics_list(start_time, end_time, shop_id=None, offset=None, limit=None, time_unit=None, group_by=None, clean_mode=None, sub_mode=None, timezone_offset=None):
    """ Accepts a shop ID, start time, and end time and returns a list of task schema analytics with paging

    Returns a list in which each contains running statistics of each robot of a shop.

    @param start_time: The start time
    @param end_time: The end time
    @param shop_id: The shop ID
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param time_unit: The time unit to aggregate data by day or hour
    @param group_by: The group by field - robot or shop
    @param clean_mode: The clean mode
    @param sub_mode: The sub mode
    @param timezone_offset: The timezone offset

    @return: The task schema analytics dictionary - {'total': 2,
                                                     'offset': 0,
                                                     'limit': 100,
                                                     'list': [{'task_time': '2024-09-19',
                                                               'mac': 'B0:0C:9D:59:16:E8',
                                                               'shop_id': 434300005,
                                                               'shop_name': 'USF',
                                                               'product_code': 'CC1',
                                                               'area': 18.25,
                                                               'duration': 0.05,
                                                               'sn': '811064412050012',
                                                               'run_count': 0,
                                                               'bind_count': 1,
                                                               'power_consumption': 0,
                                                               'water_consumption': 0,
                                                               'task_count': 3,
                                                               'robot_name': 'USF_LIB',
                                                               'plan_area': 689.25,
                                                               'work_days': 0}]}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/analysis/clean/paging?start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if time_unit:
        url += f"&time_unit={time_unit}"
    if clean_mode:
        url += f"&clean_mode={clean_mode}"
    if sub_mode:
        url += f"&sub_mode={sub_mode}"
    if offset:
        url += f"&offset={offset}"
    if limit:
        url += f"&limit={limit}"
    if group_by:
        url += f"&group_by={group_by}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_task_distribution_schema_analytics(start_time, end_time, shop_id=None, clean_mode=None, sub_mode=None, timezone_offset=None):
    """ Accepts a shop ID, start time, and end time and returns a list of task distribution schema analytics
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param clean_mode: The clean mode
    @param sub_mode: The sub mode
    @param timezone_offset: The timezone offset

    @return: The task distribution schema analytics dictionary - [{'task_time': '00:00:00', 'running_task_count': 0},
                                                                  {'task_time': '00:10:00', 'running_task_count': 0}]
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/analysis/clean/detail?start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if clean_mode:
        url += f"&clean_mode={clean_mode}"
    if sub_mode:
        url += f"&sub_mode={sub_mode}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["chart"]
    else:
        return response

def get_cleaning_report_list(start_time, end_time, shop_id=None, sn=None, offset=None, limit=None, timezone_offset=None):
    """ Accepts a shop ID, start time, and end time and returns a list of cleaning reports
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param sn: The serial number of the robot
    @param offset: The offset to start from
    @param limit: The number of records to return
    @param timezone_offset: The timezone offset

    @return: The cleaning report list dictionary - {'total': 82,
                                                    'offset': 0,
                                                    'limit': 100,
                                                    'list': [{'task_name': 'ISA 1st floor wet',
                                                              'report_id': '1034379657271316480',
                                                              'mode': 1,
                                                              'start_time': 1726781793,
                                                              'end_time': 1726781989,
                                                              'clean_time': 93,
                                                              'clean_area': 9.256633758544922,
                                                              'create_time': '2024-09-19 23:04:25',
                                                              'mac': 'B0:0C:9D:59:16:E8',
                                                              'sn': '811064412050012',
                                                              'status': 6,
                                                              'sub_mode': 0,
                                                              'task_area': 229.7475}]}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/log/clean_task/query_list?start_time={start_time}&end_time={end_time}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if sn:
        url += f"&sn={sn}"
    if offset:
        url += f"&offset={offset}"
    if limit:
        url += f"&limit={limit}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response

def get_cleaning_report_detail(start_time, end_time, sn, report_id, shop_id=None, timezone_offset=None):
    """ Accepts a shop ID, start time, and end time and returns a cleaning report detail updated in real time
    @param shop_id: The shop ID
    @param start_time: The start time
    @param end_time: The end time
    @param sn: The serial number of the robot
    @param report_id: The report ID
    @param timezone_offset: The timezone offset

    @return: The cleaning report detail dictionary - {'task_name': '5th floor dry',
                                                      'report_id': '1034159705138401280',
                                                      'mode': 2,
                                                      'start_time': 1726729353,
                                                      'end_time': 1726749361,
                                                      'clean_time': 8001,
                                                      'clean_area': 1565.227783203125,
                                                      'create_time': '2024-09-19 12:36:04',
                                                      'mac': 'B0:0C:9D:59:16:E8',
                                                      'sn': '811064412050012',
                                                      'task_id': '1023176310191046656',
                                                      'task_version': '1724889770596',
                                                      'battery': 97,
                                                      'elevator_count': 0,
                                                      'status': 6,
                                                      'config': '{"mode":2,"type":1,"vacuum_speed":2,"vacuum_suction":2,"wash_speed":0,"wash_suction":0,"wash_wash":0}',
                                                      'floor_list': '[{"map_floor":"1","map_name":"1#3#USF-Lib-5th-floor","map_version":20,"result":{"area":1565.2278111575692,"break_point":{"clean_type":2,"index":23329,"start":{},
                                                                       "vector":{"x":-8.643852775128627,"y":-14.019915767333533,"z":0.9385061952372705}},"status":6,"time":8001},"task_local_url":"/sdcard/pudu/report/1034159705138401280MSMzI1VTRi1MaWItNXRoLWZsb29y1726749361991.png","task_result_url":"https://fr-tech-cloud-open.s3.eu-central-1.amazonaws.com/pudu_cloud_platform/map/B00C9D5916E8/ff39361d283ef924d968042d2d4d5bdd.png"}]',
                                                      'floor_count': 1,
                                                      'break_count': 0,
                                                      'task_area': 1954.4976,
                                                      'average_area': 0,
                                                      'percentage': 82,
                                                      'remaining_time': 1705,
                                                      'cost_water': 0,
                                                      'cost_battery': 88,
                                                      'charge_count': 0,
                                                      'sub_mode': 1}
    """
    # convert str to seconds
    start_time = int(pd.to_datetime(start_time).timestamp())
    end_time = int(pd.to_datetime(end_time).timestamp())
    url = f"https://csu-open-platform.pudutech.com/pudu-entry/data-board/v1/log/clean_task/query?start_time={start_time}&end_time={end_time}&sn={sn}&report_id={report_id}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    if timezone_offset:
        url += f"&timezone_offset={timezone_offset}"
    response = run_url(url)
    response = json.loads(response)
    if any(status in response["message"].lower() for status in ["success", "ok"]):
        return response["data"]
    else:
        return response