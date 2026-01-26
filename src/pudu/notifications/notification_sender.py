import logging
from typing import Dict, Tuple
from .notification_service import NotificationService
from .icon_manager import get_icon_manager

# Configure logging
logger = logging.getLogger(__name__)

# Task status mapping as provided
TASK_STATUS_MAPPING = {
    0: "Not Started",
    1: "In Progress",
    2: "Task Suspended",
    3: "Task Interrupted",
    4: "Task Ended",
    5: "Task Abnormal",
    6: "Task Cancelled"
}

# Severity and status tag mappings based on template document
SEVERITY_LEVELS = {
    'fatal': 'fatal',    # Red - Immediate attention required
    'error': 'error',    # Orange - Task failed or serious problem
    'warning': 'warning', # Yellow - Moderate issue or degraded state
    'event': 'event',      # Blue - Informational or neutral event
    'success': 'success', # Green - Positive/normal outcome
    'neutral': 'neutral'  # Gray - Scheduled or inactive items
}

STATUS_TAGS = {
    # Task-specific tags
    'done': 'done',
    'uncompleted': 'uncompleted',
    'in_progress': 'in_progress',
    'scheduled': 'scheduled',

    # Event tags
    'critical': 'critical',
    'error': 'error',

    # Robot state tags
    'warning': 'warning',
    'charging': 'charging',
    'offline': 'offline',
    'online': 'online'
}

def should_skip_notification(data_type: str, change_info: Dict) -> bool:
    """Determine if notification should be skipped for this change"""
    change_type = change_info.get('change_type', 'unknown')
    changed_fields = change_info.get('changed_fields', [])
    old_values = change_info.get('old_values', {})
    new_values = change_info.get('new_values', {})

    # new task or task status update
    if data_type == 'robot_task':
        # skip all in progress tasks
        current_status = new_values.get('status', 0)
        if isinstance(current_status, int):
            status_name = TASK_STATUS_MAPPING.get(current_status, 'Unknown')
        else:
            status_name = current_status
        status_name = status_name.lower()
        if status_name == "in progress":
            return True
        # Skip non-status updates
        if change_type == 'update':
            if 'status' not in changed_fields:
                return True
        # if database_key is None, skip the notification
        # if change_info.get('database_key', None) is None:
        #     return True
        return False

    # new charging record or charging status update
    elif data_type == 'robot_charging':
        # Skip all charging updates
        if change_type == 'update':
            return True
        return True  # Skip new charging records

    # low battery level
    elif data_type == 'robot_status':
        # TIME-SERIES DATA: Every record is 'new_record' since id is auto-increment
        status = new_values.get('status', 'Unknown').lower()
        battery_level = new_values.get('battery_level')

        # NOTIFY if battery is critically low (< 5%)
        # if battery_level is not None:
        #     try:
        #         battery_level = float(battery_level)
        #         if battery_level < 5:
        #             return False  # Don't skip - send notification
        #     except (ValueError, TypeError):
        #         pass

        # # NOTIFY if robot goes offline
        # if status == 'offline':
        #     return False  # Don't skip - send notification

        # SKIP all other routine status records
        return True

    elif data_type == 'location':
        # Skip all location notifications for now
        return True

    elif data_type == 'robot_events':
        # skip all robot events now
        return True
        # # Do not skip all fatal and error events
        # if change_type == 'new_record':
        #     try:
        #         event_level = new_values.get('event_level', 'info').lower()
        #         if event_level in ['fatal', 'error']:
        #             return False
        #     except:
        #         pass
        # return True

    # Skip other data types by default
    return True

def get_severity_and_status_for_robot_status(old_values: dict, new_values: dict, changed_fields: list) -> Tuple[str, str]:
    """Determine severity and status for robot status changes"""
    # low battery level
    if 'battery_level' in changed_fields:
        try:
            new_battery = new_values.get('battery_level', 100)
            if isinstance(new_battery, (int, float)):
                if new_battery < 5:
                    return SEVERITY_LEVELS['fatal'], STATUS_TAGS['warning']
                elif new_battery < 10:
                    return SEVERITY_LEVELS['error'], STATUS_TAGS['warning']
                elif new_battery < 20:
                    return SEVERITY_LEVELS['warning'], STATUS_TAGS['warning']
                else:
                    return None, None
        except:
            pass
        return None, None
    # if 'status' in changed_fields:
    #     new_status = new_values.get('status', '').lower()
    #     if 'online' in new_status:
    #         return SEVERITY_LEVELS['success'], STATUS_TAGS['online']
    #     elif 'offline' in new_status:
    #         return SEVERITY_LEVELS['error'], STATUS_TAGS['offline']
    #     else:
    #         return None, None
    else:
        # Other status updates (position, tank levels, etc.)
        return None, None

def get_severity_and_status_for_task(change_type: str, old_values: dict, new_values: dict, changed_fields: list) -> Tuple[str, str]:
    """Determine severity and status for task changes"""
    # Get current status regardless of whether it's new or updated
    current_status = new_values.get('status', 0)
    if isinstance(current_status, int):
        status_name = TASK_STATUS_MAPPING.get(current_status, 'Unknown')
    else:
        status_name = current_status
    status_name = status_name.lower()

    # Determine severity and status based on current task status
    if status_name == "task ended":
        return SEVERITY_LEVELS['success'], STATUS_TAGS['done']
    elif status_name in ["task abnormal", "task interrupted", "task cancelled", "task suspended"]:
        return SEVERITY_LEVELS['fatal'], STATUS_TAGS['uncompleted']
    elif status_name == "in progress":
        return SEVERITY_LEVELS['event'], STATUS_TAGS['in_progress']
    elif status_name == "not started":
        return SEVERITY_LEVELS['event'], STATUS_TAGS['scheduled']
    else:
        return None, None

def get_severity_and_status_for_charging(change_type: str, old_values: dict, new_values: dict, changed_fields: list) -> Tuple[str, str]:
    """Determine severity and status for charging changes"""
    if change_type == 'new_record':
        return SEVERITY_LEVELS['event'], STATUS_TAGS['charging']
    else:
        return None, None

def get_severity_and_status_for_events(change_type: str, new_values: dict) -> Tuple[str, str]:
    """Determine severity and status for robot events"""
    event_level = new_values.get('event_level', 'event').lower()
    if event_level == 'fatal':
        return SEVERITY_LEVELS['fatal'], STATUS_TAGS['critical']
    elif event_level == 'error':
        return SEVERITY_LEVELS['error'], STATUS_TAGS['error']
    else:  # event or other
        return None, None

def get_severity_and_status_for_location(change_type: str, changed_fields: list) -> Tuple[str, str]:
    """Determine severity and status for location changes"""
    if change_type == 'new_record':
        return SEVERITY_LEVELS['success'], STATUS_TAGS['normal']
    else:
        return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

def send_change_based_notifications(notification_service: NotificationService, database_name: str, table_name: str,
                                    changes_dict: Dict[str, Dict], data_type: str, time_range: str = ""):
    """Send individual notifications for each record that has actual data changes"""
    if not changes_dict:
        logger.info(f"No changes detected for {data_type}, no notifications sent")
        return 0, 0

    successful_notifications = 0
    failed_notifications = 0
    if data_type == 'location':
        notification_type = 'robot_location'
    elif data_type in ['robot_status', 'robot_charging', 'robot_events']:
        notification_type = "robot_status"
    elif data_type in ['robot_task']:
        notification_type = "robot_task"

    # Send individual notification for each changed record
    for unique_id, change_info in changes_dict.items():
        try:
            robot_sn = change_info.get('robot_sn', 'unknown')
            # primary_key_values = change_info.get('primary_key_values', {})
            database_key = change_info.get('database_key', None)
            payload = {
                "database_name": database_name,
                "table_name": table_name,
                "related_biz_id": database_key,
                "related_biz_type": data_type
            }

            if should_skip_notification(data_type, change_info):
                logger.info(f"Skipping notification for {unique_id} (payload: {payload}) because it should be skipped")
                continue

            # Generate notification content for this specific record
            title, content = generate_individual_notification_content(data_type, change_info, time_range)
            if title is None or content is None:
                logger.info(f"Title or content is None for {unique_id}, skipping notification")
                continue

            # Get severity and status based on data type and change details
            severity, status = get_severity_and_status_for_change(data_type, change_info)
            if severity is None or status is None:
                logger.error(f"Severity or status is None for {unique_id}, skipping notification")
                continue

            # Format title with appropriate icons
            # icon_manager = get_icon_manager()
            # formatted_title = icon_manager.format_title_with_icons(title, severity, status)

            # Send notification with severity and status
            if notification_service.send_notification(
                robot_sn=robot_sn,
                notification_type=notification_type,
                title=title,
                content=content,
                severity=severity,
                status=status,
                payload=payload # for identifying the record in the database
            ):
                successful_notifications += 1
                logger.debug(f"✅ Sent notification for {unique_id}: {title} (severity: {severity}, status: {status})")
            else:
                failed_notifications += 1
                logger.debug(f"❌ Failed to send notification for {unique_id}")
        except Exception as e:
            logger.error(f"Error sending notification for record {unique_id}: {e}")
            failed_notifications += 1

    total_records = len(changes_dict)
    logger.info(f"📧 {data_type} individual notifications: {successful_notifications}/{total_records} records notified")
    return successful_notifications, failed_notifications

def get_severity_and_status_for_change(data_type: str, change_info: Dict) -> Tuple[str, str]:
    """Get severity and status for a specific change based on data type"""
    change_type = change_info.get('change_type', 'unknown')
    changed_fields = change_info.get('changed_fields', [])
    old_values = change_info.get('old_values', {})
    new_values = change_info.get('new_values', {})

    if data_type == 'robot_status':
        return get_severity_and_status_for_robot_status(old_values, new_values, changed_fields)
    elif data_type == 'robot_task':
        return get_severity_and_status_for_task(change_type, old_values, new_values, changed_fields)
    elif data_type == 'robot_charging':
        return get_severity_and_status_for_charging(change_type, old_values, new_values, changed_fields)
    elif data_type == 'robot_events':
        return get_severity_and_status_for_events(change_type, new_values)
    elif data_type == 'location':
        return get_severity_and_status_for_location(change_type, changed_fields)
    else:
        # Default for unknown data types
        return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

def generate_individual_notification_content(data_type: str, change_info: Dict, time_range: str = "") -> tuple:
    """Generate notification content for a single record change"""
    robot_sn = change_info.get('robot_sn', 'unknown')
    change_type = change_info.get('change_type', 'unknown')
    changed_fields = change_info.get('changed_fields', [])
    old_values = change_info.get('old_values', {})
    new_values = change_info.get('new_values', {})
    primary_key_values = change_info.get('primary_key_values', {})
    time_info = f" from {time_range}" if time_range else ""

    try:
        if data_type == 'robot_status':
            # Primary keys: ["robot_sn"]
            if change_type == 'new_record':
                status = new_values.get('status', 'Unknown').lower()
                battery = new_values.get('battery_level', 'N/A')
                robot_name = new_values.get('robot_name', f'SN: {robot_sn}')
                # title = f"Robot {status}"
                # content = f"Robot {robot_name} is now {status} with {battery}% battery."
                status_changed_fields = ['battery_level']
                title, content = generate_status_change_content(robot_sn, status_changed_fields, old_values, new_values)
            else:  # update
                title, content = None, None
            return title, content

        elif data_type == 'robot_task':
            # Primary keys: ["robot_sn", "task_name", "start_time"]
            task_name = new_values.get('task_name', 'Unknown Task')
            start_time = new_values.get('start_time', 'Unknown Time')

            if change_type == 'new_record':
                status = new_values.get('status', 'Unknown')
                if isinstance(status, int):
                    status_name = TASK_STATUS_MAPPING.get(status, 'Unknown')
                else:
                    status_name = status

                robot_name = new_values.get('robot_name', f'SN: {robot_sn}')
                title = f"New Task: {task_name}"
                content = f"Robot {robot_name} has a new task: {task_name} (status: {status_name})."

            else:  # update
                robot_name = new_values.get('robot_name', f'SN: {robot_sn}')

                if 'status' in changed_fields:
                    old_status = old_values.get('status', 'Unknown')
                    new_status = new_values.get('status', 'Unknown')

                    # Convert status codes to names if needed
                    if isinstance(old_status, int):
                        old_status_name = TASK_STATUS_MAPPING.get(old_status, 'Unknown')
                    else:
                        old_status_name = old_status

                    if isinstance(new_status, int):
                        new_status_name = TASK_STATUS_MAPPING.get(new_status, 'Unknown')
                    else:
                        new_status_name = new_status
                    title = f"Task ({task_name}) Status Updated "
                    content = f"Robot {robot_name}'s task - {task_name} has changed to a new status - {new_status_name} now."

                elif 'progress' in changed_fields:
                    # do not send notification now
                    new_progress = new_values.get('progress', 0)
                    title = f"Task ({task_name}) Progress Updated"
                    content = f"Robot {robot_name}'s task - {task_name} has updated its progress to {new_progress}%."

                else:
                    # Generic task update - do not send notification now
                    title = f"Task ({task_name}) Updated"
                    content = f"Robot {robot_name}'s task - {task_name} has been updated."

            return title, content

        elif data_type == 'robot_charging':
            # Primary keys: ["robot_sn", "start_time", "end_time"]
            robot_name = new_values.get('robot_name', f'SN: {robot_sn}')
            final_power = new_values.get('final_power', 'N/A')

            if change_type == 'new_record':
                title = f"Robot Charging"
                content = f"Robot {robot_name} has been charged with {final_power} power."
            else:  # update - do not send notification now
                title, content = None, None

            return title, content

        elif data_type == 'robot_events':
            # Primary keys: ["robot_sn", "event_id"]
            event_type = new_values.get('event_type', 'Unknown Event')
            event_level = new_values.get('event_level', 'info').lower()
            robot_name = new_values.get('robot_name', f'SN: {robot_sn}')
            time_info = f"{new_values.get('upload_time', 'Unknown Time')}"

            title = f"Robot Incident: {event_type}"

            if event_level == 'fatal':
                content = f"Robot {robot_name} has a new critical event - {event_type} at {time_info}."
            elif event_level == 'error':
                content = f"Robot {robot_name} has a new error - {event_type} at {time_info}."
            else:
                title, content = None, None

            return title, content

        elif data_type == 'location':
            title, content = None, None
            return title, content
        else:
            title, content = None, None
            return title, content

    except Exception as e:
        logger.warning(f"Error generating notification content for {data_type}: {e}")
        # Fallback
        title, content = None, None

    return title, content

def generate_status_change_content(robot_sn: str, changed_fields: list, old_values: dict, new_values: dict) -> tuple:
    """Generate specific content for robot status changes"""
    robot_name = new_values.get('robot_name', f'SN: {robot_sn}')
    icon_manager = get_icon_manager()

    # Prioritize important status changes
    if 'battery_level' in changed_fields:
        new_battery = new_values.get('battery_level', 'N/A')
        # Only send notification if battery level is below 20%
        if new_battery < 5:
            return "Critical Battery Alert", f"Robot {robot_name} critical battery level at {new_battery}%!"
        elif new_battery < 10:
            return "Low Battery Alert", f"Robot {robot_name} low battery level at {new_battery}%"
        elif new_battery < 20:
            return "Battery Warning", f"Robot {robot_name} battery level at {new_battery}%"
        else:
            return "Battery Update", f"Robot {robot_name} battery at {new_battery}%"

    elif 'status' in changed_fields:
        new_status = new_values.get('status', 'Unknown')

        if 'online' in str(new_status).lower():
            title = "Robot Online"
            content = f"Robot {robot_name} is now online."
        elif 'offline' in str(new_status).lower():
            title = "Robot Offline"
            content = f"Robot {robot_name} is offline."
        else:
            title = "Robot Status Update"
            content = f"Robot {robot_name} status changed to {new_status}."
    else:
        # Generic status update - do not send notification now
        title = "Robot Status Update"
        content = f"Robot {robot_name} status has been updated."

    return title, content