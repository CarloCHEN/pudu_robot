"""
Robot Package
"""

from .foxx_api import *

__all__ = [
    # from foxx_api
    "get_location_table",
    "get_robot_status_table",
    "get_robot_table", # deprecated
    "get_schedule_table",
    "get_charging_table",
    "get_data",
    "get_task_overview_data",
    "get_events_table",
    "get_ongoing_tasks_table",
    "get_robot_work_location_and_mapping_data"
]