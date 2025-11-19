"""
Mock Pudu API functions for testing
"""

import logging
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

# Mock data for different API calls
MOCK_LOCATION_DATA = [
    {"Building ID": "USF001", "Building Name": "USF Library"},
    {"Building ID": "USF002", "Building Name": "USF Office"}
]

MOCK_ROBOT_STATUS_DATA = [
    {
        "Location ID": "USF001",
        "Robot SN": "811064412050012",
        "Robot Name": "USF_LIB",
        "Robot Type": "CC1",
        "Water Level": 80,
        "Sewage Level": 20,
        "Battery Level": 95,
        "Status": "Online"
    }
]

def mock_get_location_table():
    """Mock location table API"""
    logger.info("Mock API: Getting location table")
    return pd.DataFrame(MOCK_LOCATION_DATA)

def mock_get_robot_status_table(location_id=None, robot_sn=None):
    """Mock robot status table API"""
    logger.info(f"Mock API: Getting robot status (location={location_id}, robot={robot_sn})")
    data = MOCK_ROBOT_STATUS_DATA.copy()

    if location_id:
        data = [r for r in data if r.get("Location ID") == location_id]
    if robot_sn:
        data = [r for r in data if r.get("Robot SN") == robot_sn]

    return pd.DataFrame(data)

def mock_get_schedule_table(start_time: str, end_time: str, location_id=None,
                           robot_sn=None, timezone_offset=0):
    """Mock schedule table API"""
    logger.info(f"Mock API: Getting schedule ({start_time} to {end_time})")
    mock_data = [
        {
            "Task Name": "Test Task",
            "Robot SN": "811064412050012",
            "Actual Area": 150.5,
            "Plan Area": 200.0,
            "Status": "Task Ended"
        }
    ]
    return pd.DataFrame(mock_data)

def mock_get_charging_table(start_time: str, end_time: str, location_id=None,
                           robot_sn=None, timezone_offset=0):
    """Mock charging table API"""
    logger.info(f"Mock API: Getting charging data ({start_time} to {end_time})")
    return pd.DataFrame([
        {
            "Robot Name": "USF_LIB",
            "Robot SN": "811064412050012",
            "Duration": "2h 30min",
            "Initial Power": "20%",
            "Final Power": "95%"
        }
    ])

def mock_get_events_table(start_time: str, end_time: str, location_id=None,
                         robot_sn=None, error_levels=None, error_types=None,
                         timezone_offset=0):
    """Mock events table API"""
    logger.info(f"Mock API: Getting events ({start_time} to {end_time})")
    return pd.DataFrame([
        {
            "Robot SN": "811064412050012",
            "Event Level": "warning",
            "Event Type": "Lost Localization",
            "Event Detail": "Odom Slip"
        }
    ])

def mock_get_task_overview_data(start_time: str, end_time: str, location_id=None,
                               robot_sn=None, timezone_offset=0):
    """Mock task overview data API"""
    logger.info(f"Mock API: Getting task overview ({start_time} to {end_time})")
    mock_data = [
        {
            "Robot Name": "USF_LIB",
            "Robot SN": "811064412050012",
            "Actual Area": 150.5,
            "Plan Area": 200.0,
            "Percentage": 75.25,
            "Duration": 3600,
            "Task Count": 3,
            "Efficiency": 0.042,
            "Day": "2024-09-01",
            "Hour": 14
        }
    ]

    if robot_sn:
        mock_data = [r for r in mock_data if r.get("Robot SN") == robot_sn]

    return pd.DataFrame(mock_data)

def mock_get_data(start_time: str, end_time: str, location_id=None,
                  robot_sn=None, timezone_offset=0):
    """Mock data API for cleaning percentage"""
    logger.info(f"Mock API: Getting cleaning data ({start_time} to {end_time})")
    return pd.DataFrame([
        {
            "Task Name": "Library Cleaning",
            "End Time": pd.Timestamp("2024-09-01 15:30:00"),
            "Robot Name": "USF_LIB",
            "Robot SN": "811064412050012",
            "Actual Area": 150.5,
            "Plan Area": 200.0,
            "Cost Water": 2.5,
            "Cost Battery": 0.15,
            "Duration": 3600,
            "Efficiency": 0.042
        }
    ])