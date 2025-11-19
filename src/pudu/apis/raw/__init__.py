# Raw API

from .gas_api import create_gaussian_api_client, GaussianRobotAPI
from .pudu_api import *

__all__ = [
    'create_gaussian_api_client',
    'GaussianRobotAPI',
    'get_list_stores',
    'get_list_robots',
    'get_list_maps',
    'get_map_details',
    'get_robot_current_position',
    'get_robot_overview_data',
    'get_robot_overview_operation_data',
    'get_store_overview_data',
    'get_store_analytics',
    'get_store_analytics_list',
    'get_machine_run_analytics',
    'get_machine_run_analytics_list',
    'get_log_list',
    'get_event_list',
    'get_charging_record_list',
    'get_battery_health_list',
    'get_task_list',
    'get_scheduled_task_list',
    'get_robot_details',
    'send_command_to_robot',
    'get_task_schema_analytics',
    'get_task_schema_analytics_list',
    'get_task_distribution_schema_analytics',
    'get_cleaning_report_list',
    'get_cleaning_report_detail',
]