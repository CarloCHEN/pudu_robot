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
    'fatal': 'fatal',    # Purple - Immediate attention required
    'error': 'error',    # Red - Task failed or serious problem
    'warning': 'warning', # Yellow - Moderate issue or degraded state
    'event': 'event',      # Blue - Informational or neutral event
    'success': 'success', # Green - Positive/normal outcome
    'neutral': 'neutral'  # Gray - Scheduled or inactive items
}

STATUS_TAGS = {
    # Task-specific tags
    'completed': 'completed',      # ✅ Green - Task completed
    'failed': 'failed',           # ❌ Red - Task failed
    'uncompleted': 'uncompleted', # 🚫 Orange - Task not completed as planned
    'in_progress': 'in_progress', # ⏳ Blue - Task currently running
    'scheduled': 'scheduled',     # 💤 Gray - Upcoming task

    # Event/Status tags (same icons, different semantics)
    'normal': 'normal',       # ✅ Green - Event resolved or status normal
    'abnormal': 'abnormal',            # ❌ Red - Error occurred or abnormal status
    'active': 'active',          # ⏳ Blue - Process active or ongoing
    'inactive': 'inactive',      # 🚫 Orange - Process inactive or stopped
    'pending': 'pending',        # 💤 Gray - Pending or waiting

    # Robot state tags
    'warning': 'warning',         # ⚠️ Yellow - Battery low, performance warning
    'charging': 'charging',       # 🔌 Purple - Robot in charging state
    'offline': 'offline',         # 📴 Red - Robot went offline
    'online': 'online'           # 📶 Green - Robot came online
}

def should_skip_notification(data_type: str, change_info: Dict) -> bool:
    """Determine if notification should be skipped for this change"""
    change_type = change_info.get('change_type', 'unknown')
    changed_fields = change_info.get('changed_fields', [])
    old_values = change_info.get('old_values', {})
    new_values = change_info.get('new_values', {})

    if data_type == 'robot_task':
        # Skip non-status updates
        if change_type == 'update':
            if 'status' not in changed_fields:
                return True
        return False

    elif data_type == 'robot_charging':
        # Skip all charging updates
        if change_type == 'update':
            return True
        return False  # Don't skip new charging records

    elif data_type == 'robot_status':
        # Skip battery updates unless battery is low (< 20%)
        if change_type == 'update' and 'battery_level' in changed_fields and 'status' not in changed_fields:
            try:
                new_battery = new_values.get('battery_level', 100)
                if isinstance(new_battery, (int, float)):
                    return new_battery >= 20  # Skip if battery is >= 20%
            except:
                pass
        elif change_type == 'update' and 'status' not in changed_fields:
            return True # skip other status updates
        return False  # Don't skip other status updates

    elif data_type == 'location':
        # Skip all location notifications for now
        return True

    # Skip other data types by default
    return True

def get_severity_and_status_for_robot_status(old_values: dict, new_values: dict, changed_fields: list) -> Tuple[str, str]:
    """Determine severity and status for robot status changes"""
    if 'status' in changed_fields:
        new_status = new_values.get('status', '').lower()
        if 'online' in new_status:
            return SEVERITY_LEVELS['success'], STATUS_TAGS['online']
        elif 'offline' in new_status:
            return SEVERITY_LEVELS['error'], STATUS_TAGS['offline']
        else:
            return SEVERITY_LEVELS['event'], STATUS_TAGS['active']

    elif 'battery_level' in changed_fields:
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
                    return SEVERITY_LEVELS['success'], STATUS_TAGS['normal']
        except:
            pass
        return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

    else:
        # Other status updates (position, tank levels, etc.)
        return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

def get_severity_and_status_for_task(change_type: str, old_values: dict, new_values: dict, changed_fields: list) -> Tuple[str, str]:
    """Determine severity and status for task changes"""
    # Get current status regardless of whether it's new or updated
    current_status = new_values.get('status', 0)
    if isinstance(current_status, int):
        status_name = TASK_STATUS_MAPPING.get(current_status, 'Unknown')
    else:
        status_name = current_status

    # Determine severity and status based on current task status
    if status_name == "Task Ended":
        return SEVERITY_LEVELS['success'], STATUS_TAGS['completed']
    elif status_name in ["Task Abnormal", "Task Interrupted"]:
        return SEVERITY_LEVELS['error'], STATUS_TAGS['failed']
    elif status_name == "Task Cancelled":
        return SEVERITY_LEVELS['warning'], STATUS_TAGS['uncompleted']
    elif status_name == "Task Suspended":
        return SEVERITY_LEVELS['warning'], STATUS_TAGS['warning']
    elif status_name == "In Progress":
        return SEVERITY_LEVELS['event'], STATUS_TAGS['in_progress']
    elif status_name == "Not Started":
        return SEVERITY_LEVELS['event'], STATUS_TAGS['scheduled']
    else:
        return SEVERITY_LEVELS['event'], STATUS_TAGS['active']

def get_severity_and_status_for_charging(change_type: str, old_values: dict, new_values: dict, changed_fields: list) -> Tuple[str, str]:
    """Determine severity and status for charging changes"""
    if change_type == 'new_record':
        return SEVERITY_LEVELS['event'], STATUS_TAGS['charging']

    elif 'final_power' in changed_fields or 'power_gain' in changed_fields:
        try:
            final_power = new_values.get('final_power', 0)
            if isinstance(final_power, (int, float)) and final_power >= 90:
                return SEVERITY_LEVELS['success'], STATUS_TAGS['normal']
            else:
                return SEVERITY_LEVELS['event'], STATUS_TAGS['charging']
        except:
            return SEVERITY_LEVELS['event'], STATUS_TAGS['charging']

    else:
        return SEVERITY_LEVELS['event'], STATUS_TAGS['active']

def get_severity_and_status_for_events(change_type: str, new_values: dict) -> Tuple[str, str]:
    """Determine severity and status for robot events"""
    event_level = new_values.get('event_level', 'event').lower()

    if event_level == 'error':
        return SEVERITY_LEVELS['error'], STATUS_TAGS['abnormal']
    elif event_level == 'warning':
        return SEVERITY_LEVELS['warning'], STATUS_TAGS['warning']
    elif event_level == 'fatal':
        return SEVERITY_LEVELS['fatal'], STATUS_TAGS['abnormal']
    else:  # event or other
        return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

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
            robot_id = change_info.get('robot_id', 'unknown')
            # primary_key_values = change_info.get('primary_key_values', {})
            database_key = change_info.get('database_key', None)
            payload = {
                "database_name": database_name,
                "table_name": table_name,
                "related_biz_id": database_key,
                "related_biz_type": data_type
            }

            if should_skip_notification(data_type, change_info):
                logger.info(f"Skipping notification for {unique_id} because it should be skipped")
                continue

            # Generate notification content for this specific record
            title, content = generate_individual_notification_content(data_type, change_info, time_range)

            # Get severity and status based on data type and change details
            severity, status = get_severity_and_status_for_change(data_type, change_info)

            # Format title with appropriate icons
            icon_manager = get_icon_manager()
            formatted_title = icon_manager.format_title_with_icons(title, severity, status)

            # Send notification with severity and status
            if notification_service.send_notification(
                robot_id=robot_id,
                notification_type=notification_type,
                title=formatted_title,
                content=content,
                severity=severity,
                status=status,
                payload=payload # for identifying the record in the database
            ):
                successful_notifications += 1
                logger.debug(f"✅ Sent notification for {unique_id}: {formatted_title} (severity: {severity}, status: {status})")
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
    robot_id = change_info.get('robot_id', 'unknown')
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
                status = new_values.get('status', 'Unknown')
                battery = new_values.get('battery_level', 'N/A')
                robot_name = new_values.get('robot_name', f'SN: {robot_id}')
                title = f"Robot Online"
                content = f"Robot {robot_name} is now online."
            else:  # update
                return generate_status_change_content(robot_id, changed_fields, old_values, new_values)

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

                robot_name = new_values.get('robot_name', f'SN: {robot_id}')
                title = f"New Task: {task_name}"
                content = f"Robot {robot_name} has a new task: {task_name} (status: {status_name})."

            else:  # update
                robot_name = new_values.get('robot_name', f'SN: {robot_id}')

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

        elif data_type == 'robot_charging':
            # Primary keys: ["robot_sn", "start_time", "end_time"]
            robot_name = new_values.get('robot_name', f'SN: {robot_id}')
            final_power = new_values.get('final_power', 'N/A')

            if change_type == 'new_record':
                title = f"Robot Charging"
                content = f"Robot {robot_name} has been charged with {final_power} power."
            else:  # update - do not send notification now
                if 'final_power' in changed_fields or 'power_gain' in changed_fields:
                    final_power = new_values.get('final_power', 'N/A')
                    title = f"Robot Charging"
                    if not isinstance(final_power, (int, float)):
                        final_power_value = int(final_power.replace('%', ''))
                    if final_power_value >= 90:
                        content = f"Robot {robot_name} has completed charging with {final_power} power."
                    else:
                        content = f"Robot {robot_name} is charging with {final_power} power."
                else:
                    title = f"Robot Charging"
                    content = f"Robot {robot_name} charging status updated."

        elif data_type == 'robot_events':
            # Primary keys: ["robot_sn", "event_id"]
            event_type = new_values.get('event_type', 'Unknown Event')
            event_level = new_values.get('event_level', 'info').lower()
            robot_name = new_values.get('robot_name', f'SN: {robot_id}')
            time_info = f"{new_values.get('upload_time', 'Unknown Time')}"

            title = f"Robot Incident: {event_type}"
            if event_level == 'error':
                content = f"Robot {robot_name} has a new error - {event_type} at {time_info}."
            elif event_level == 'warning':
                content = f"Robot {robot_name} has a new warning - {event_type} at {time_info}."
            elif event_level == 'fatal':
                content = f"Robot {robot_name} has a new fatal event - {event_type} at {time_info}."
            else:
                content = f"Robot {robot_name} has a new event - {event_type} at {time_info}."

        elif data_type == 'location':
            # do not send notification now
            # Primary keys: ["location_id"]
            location_name = new_values.get('location_name', 'Unknown Location')

            if change_type == 'new_record':
                title = f"New Location Added"
                content = f"A new location - {location_name} has been added to the system."
            else:  # update
                title = f"Location Updated"
                content = f"Location - {location_name} has been updated."

        else:
            # Generic handling for other data types - do not send notification now
            robot_name = new_values.get('robot_name', f'SN: {robot_id}')
            if change_type == 'new_record':
                title = f"New {data_type.replace('_', ' ').title()}"
                content = f"Robot {robot_name} has a new {data_type} record created."
            else:
                title = f"{data_type.replace('_', ' ').title()} Updated"
                content = f"Robot: {robot_name}; {data_type} record updated."

    except Exception as e:
        logger.warning(f"Error generating notification content for {data_type}: {e}")
        # Fallback
        robot_name = new_values.get('robot_name', f'Robot SN: {robot_id}')
        title = f"{data_type.replace('_', ' ').title()}"
        content = f"Robot: {robot_name}; {data_type} updated."

    return title, content

def generate_status_change_content(robot_id: str, changed_fields: list, old_values: dict, new_values: dict) -> tuple:
    """Generate specific content for robot status changes"""
    robot_name = new_values.get('robot_name', f'SN: {robot_id}')
    icon_manager = get_icon_manager()

    # Prioritize important status changes
    if 'status' in changed_fields:
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

    elif 'battery_level' in changed_fields:
        new_battery = new_values.get('battery_level', 'N/A')
        # Only send notification if battery level is below 20%
        title = "Low Battery Alert"
        content = f"Robot {robot_name} battery level is at {new_battery}%."

    else:
        # Generic status update - do not send notification now
        title = "Robot Status Update"
        content = f"Robot {robot_name} status has been updated."

    return title, content