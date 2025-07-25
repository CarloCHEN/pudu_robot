import logging
from typing import Dict
from .notification_service import NotificationService
# Configure logging
logger = logging.getLogger(__name__)


def send_change_based_notifications(notification_service: NotificationService, changes_dict: Dict[str, Dict],
                                 data_type: str, time_range: str = ""):
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

            # Generate notification content for this specific record
            title, content = generate_individual_notification_content(data_type, change_info, time_range)

            # Send notification
            if notification_service.send_notification(
                robot_id=robot_id,
                notification_type=notification_type,
                title=title,
                content=content
            ):
                successful_notifications += 1
                logger.debug(f"✅ Sent notification for {unique_id}: {title}")
            else:
                failed_notifications += 1
                logger.debug(f"❌ Failed to send notification for {unique_id}")
        except Exception as e:
            logger.error(f"Error sending notification for record {unique_id}: {e}")
            failed_notifications += 1

    total_records = len(changes_dict)
    logger.info(f"📧 {data_type} individual notifications: {successful_notifications}/{total_records} records notified")
    return successful_notifications, failed_notifications

def generate_individual_notification_content(data_type: str, change_info: Dict, time_range: str = "") -> tuple:
    """Generate notification content for a single record change"""
    robot_id = change_info.get('robot_id', 'unknown')
    change_type = change_info.get('change_type', 'unknown')
    changed_fields = change_info.get('changed_fields', [])
    old_values = change_info.get('old_values', {})
    new_values = change_info.get('new_values', {})
    primary_key_values = change_info.get('primary_key_values', {})
    time_info = f" for {time_range}" if time_range else ""

    try:
        if data_type == 'robot_status':
            # Primary keys: ["robot_sn"]
            if change_type == 'new_record':
                status = new_values.get('status', 'Unknown')
                battery = new_values.get('battery_level', 'N/A')
                robot_name = new_values.get('robot_name', f'Robot {robot_id}')
                title = f"New Robot Detected - {robot_name}"
                content = f"Robot {robot_id} ({robot_name}) is now {status.lower()} with {battery}% battery"
                severity_level = 'success' if 'online' in status.lower() else 'error'
                status_tag = status.lower()
            else:  # update
                return generate_status_change_content(robot_id, changed_fields, old_values, new_values)

        elif data_type == 'robot_task':
            # Primary keys: ["robot_sn", "task_name", "start_time"]
            task_name = new_values.get('task_name', 'Unknown Task')
            start_time = new_values.get('start_time', 'Unknown Time')

            if change_type == 'new_record':
                status = new_values.get('status', 'Unknown')
                progress = new_values.get('progress', 0)
                title = f"New Task Started - {task_name}"
                content = f"Robot {robot_id} started new task '{task_name}' at {start_time}. Status: {status}, Progress: {progress}%"

                # Add additional details if available
                plan_area = new_values.get('plan_area')
                if plan_area:
                    content += f", Planned area: {plan_area}m²"

            else:  # update
                if 'progress' in changed_fields:
                    old_progress = old_values.get('progress', 0)
                    new_progress = new_values.get('progress', 0)
                    title = f"Task Progress Update - {task_name}"
                    content = f"Robot {robot_id} task '{task_name}' (started {start_time}) progress: {old_progress}% → {new_progress}%"

                elif 'status' in changed_fields:
                    old_status = old_values.get('status', 'Unknown')
                    new_status = new_values.get('status', 'Unknown')
                    title = f"Task Status Change - {task_name}"
                    content = f"Robot {robot_id} task '{task_name}' (started {start_time}) status: {old_status} → {new_status}"

                    # Add progress if task completed
                    if new_status in ['Task Ended', 'Task Completed']:
                        progress = new_values.get('progress', 0)
                        content += f", Final progress: {progress}%"

                elif 'actual_area' in changed_fields:
                    old_area = old_values.get('actual_area', 0)
                    new_area = new_values.get('actual_area', 0)
                    title = f"Task Area Update - {task_name}"
                    content = f"Robot {robot_id} task '{task_name}' (started {start_time}) cleaned area: {old_area}m² → {new_area}m²"

                elif 'efficiency' in changed_fields:
                    old_efficiency = old_values.get('efficiency', 0)
                    new_efficiency = new_values.get('efficiency', 0)
                    title = f"Task Efficiency Update - {task_name}"
                    content = f"Robot {robot_id} task '{task_name}' (started {start_time}) efficiency: {old_efficiency} → {new_efficiency} m²/h"

                else:
                    # Generic update
                    field_names = ', '.join(changed_fields[:3])
                    title = f"Task Update - {task_name}"
                    content = f"Robot {robot_id} task '{task_name}' (started {start_time}) updated: {field_names}"
                    if len(changed_fields) > 3:
                        content += f" and {len(changed_fields) - 3} more fields"

        elif data_type == 'robot_charging':
            # Primary keys: ["robot_sn", "start_time", "end_time"]
            start_time = new_values.get('start_time', 'Unknown Time')
            end_time = new_values.get('end_time', 'Unknown Time')

            if change_type == 'new_record':
                initial_power = new_values.get('initial_power', 'N/A')
                final_power = new_values.get('final_power', 'N/A')
                duration = new_values.get('duration', 'N/A')
                title = f"New Charging Session Started"
                content = f"Robot {robot_id} started charging at {start_time}. Initial power: {initial_power}, Duration: {duration}"

                if final_power != 'N/A':
                    content += f", Final power: {final_power}"

            else:  # update
                if 'final_power' in changed_fields or 'power_gain' in changed_fields:
                    old_power = old_values.get('final_power', 'N/A')
                    new_power = new_values.get('final_power', 'N/A')
                    power_gain = new_values.get('power_gain', 'N/A')
                    title = f"Charging Progress Update"
                    content = f"Robot {robot_id} charging session (started {start_time}) power: {old_power} → {new_power}"
                    if power_gain != 'N/A':
                        content += f", Total gain: {power_gain}"

                elif 'duration' in changed_fields:
                    old_duration = old_values.get('duration', 'N/A')
                    new_duration = new_values.get('duration', 'N/A')
                    title = f"Charging Duration Update"
                    content = f"Robot {robot_id} charging session (started {start_time}) duration: {old_duration} → {new_duration}"

                else:
                    # Generic charging update
                    field_names = ', '.join(changed_fields[:3])
                    title = f"Charging Session Updated"
                    content = f"Robot {robot_id} charging session (started {start_time}) updated: {field_names}"

        elif data_type == 'robot_events':
            # Primary keys: ["robot_sn", "event_id"]
            event_id = new_values.get('event_id', 'Unknown ID')
            event_type = new_values.get('event_type', 'Unknown Event')
            event_level = new_values.get('event_level', 'info').lower()
            upload_time = new_values.get('upload_time', 'Unknown Time')

            # Use appropriate emoji based on event level
            level_emoji = {'error': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}.get(event_level, '📋')

            if change_type == 'new_record':
                title = f"{level_emoji} Robot {robot_id} Had A New {event_level.title()} Event - {event_type}"
                content = f"Robot {robot_id} had a new {event_type} (ID: {event_id}) at {upload_time}"

                # Add event detail if available and short
                event_detail = new_values.get('event_detail', '')
                if event_detail and len(event_detail) < 100:
                    content += f" - {event_detail}"

            else:  # update (rare for events, but possible)
                title = f"Robot {robot_id}: Event Updated"
                field_names = ', '.join(changed_fields[:3])
                content = f"Robot {robot_id} event {event_type} (ID: {event_id}) updated: {field_names}"

        elif data_type == 'location':
            # Primary keys: ["location_id"]
            location_id = new_values.get('location_id', 'Unknown ID')
            location_name = new_values.get('location_name', 'Unknown Location')

            if change_type == 'new_record':
                title = f"New Location Added - {location_name}"
                content = f"Location '{location_name}' (ID: {location_id}) has been added to the system"

                # Add description if available
                description = new_values.get('description')
                if description:
                    content += f". Description: {description}"

            else:  # update
                if 'location_name' in changed_fields:
                    old_name = old_values.get('location_name', 'Unknown')
                    title = f"Location Renamed - {location_name}"
                    content = f"Location (ID: {location_id}) renamed from '{old_name}' to '{location_name}'"
                else:
                    field_names = ', '.join(changed_fields[:3])
                    title = f"Location Updated - {location_name}"
                    content = f"Location '{location_name}' (ID: {location_id}) updated: {field_names}"

        else:
            # Generic handling for other data types
            if change_type == 'new_record':
                title = f"New {data_type.replace('_', ' ').title()} Record"
                content = f"Robot {robot_id}: new {data_type} record created{time_info}"
            else:
                field_names = ', '.join(changed_fields[:3])
                title = f"{data_type.replace('_', ' ').title()} Updated"
                content = f"Robot {robot_id}: {data_type} record updated: {field_names}{time_info}"
                if len(changed_fields) > 3:
                    content += f" and {len(changed_fields) - 3} more fields"

    except Exception as e:
        logger.warning(f"Error generating notification content for {data_type}: {e}")
        # Fallback
        title = f"{data_type.replace('_', ' ').title()} Updated"
        content = f"Robot {robot_id}: {data_type} record updated{time_info}"

    return title, content

def generate_status_change_content(robot_id: str, changed_fields: list, old_values: dict, new_values: dict) -> tuple:
    """Generate specific content for robot status changes"""
    robot_name = new_values.get('robot_name', f'Robot {robot_id}')

    # Prioritize important status changes
    if 'status' in changed_fields:
        old_status = old_values.get('status', 'Unknown')
        new_status = new_values.get('status', 'Unknown')
        title = f"Status Change - {robot_name}"
        content = f"Robot {robot_id} ({robot_name}) changed from {old_status} to {new_status}"

        # Add battery info if it also changed
        if 'battery_level' in changed_fields:
            old_battery = old_values.get('battery_level', 'N/A')
            new_battery = new_values.get('battery_level', 'N/A')
            content += f". Battery: {old_battery}% → {new_battery}%"
        severity_level = 'success' if 'online' in new_status.lower() else 'error'
        status_tag = new_status.lower()

    elif 'battery_level' in changed_fields:
        old_battery = old_values.get('battery_level', 'N/A')
        new_battery = new_values.get('battery_level', 'N/A')
        title = f"Battery Update - {robot_name}"
        content = f"Robot {robot_id} ({robot_name}) battery: {old_battery}% → {new_battery}%"

        # Add warning for low battery
        try:
            if isinstance(new_battery, (int, float)) and new_battery < 20:
                content += " ⚠️ Low battery!"
                status_tag = 'warning'
        except:
            pass
        if
        # battery<20% wa

    elif any(field in changed_fields for field in ['water_level', 'sewage_level']):
        title = f"Tank Levels Updated - {robot_name}"
        changes = []
        if 'water_level' in changed_fields:
            changes.append(f"Water: {old_values.get('water_level', 'N/A')}% → {new_values.get('water_level', 'N/A')}%")
        if 'sewage_level' in changed_fields:
            changes.append(f"Sewage: {old_values.get('sewage_level', 'N/A')}% → {new_values.get('sewage_level', 'N/A')}%")
        content = f"Robot {robot_id} ({robot_name}) {', '.join(changes)}"

    elif any(field in changed_fields for field in ['x', 'y', 'z']):
        title = f"Position Updated - {robot_name}"
        old_pos = f"({old_values.get('x', 'N/A')}, {old_values.get('y', 'N/A')})"
        new_pos = f"({new_values.get('x', 'N/A')}, {new_values.get('y', 'N/A')})"
        content = f"Robot {robot_id} ({robot_name}) moved from {old_pos} to {new_pos}"

    else:
        # Generic status update
        field_list = ', '.join(changed_fields[:3])
        title = f"Status Updated - {robot_name}"
        content = f"Robot {robot_id} ({robot_name}) updated: {field_list}"

    return title, content

def generate_charging_change_content(robot_id: str, changed_fields: list, old_values: dict, new_values: dict, time_info: str) -> tuple:
    """Generate specific content for charging changes"""
    if any(field in changed_fields for field in ['initial_power', 'final_power', 'power_gain']):
        title = f"Charging Session Update"
        power_info = []
        if 'power_gain' in changed_fields:
            power_gain = new_values.get('power_gain', '+0%')
            power_info.append(f"Power gain: {power_gain}")
        if 'final_power' in changed_fields:
            final_power = new_values.get('final_power', 'N/A')
            power_info.append(f"Final: {final_power}")

        content = f"Robot {robot_id} charging session {', '.join(power_info)}{time_info}"
    else:
        # Generic charging update
        title = f"Charging Data Updated"
        field_list = ', '.join(changed_fields[:3])
        content = f"Robot {robot_id} charging information updated: {field_list}{time_info}"

    return title, content
