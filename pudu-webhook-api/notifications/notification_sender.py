import logging
from typing import Dict, Tuple

from .notification_service import NotificationService
from .icon_manager import get_icon_manager

logger = logging.getLogger(__name__)

# Severity and status mappings
SEVERITY_LEVELS = {
    'fatal': 'fatal',
    'error': 'error',
    'warning': 'warning',
    'event': 'event',
    'success': 'success',
    'neutral': 'neutral'
}

STATUS_TAGS = {
    'completed': 'completed',
    'failed': 'failed',
    'warning': 'warning',
    'charging': 'charging',
    'offline': 'offline',
    'online': 'online',
    'normal': 'normal',
    'abnormal': 'abnormal',
    'active': 'active',
}

def send_change_based_notifications(notification_service: NotificationService, database_name: str,
                                   table_name: str, changes_dict: Dict[str, Dict], callback_type: str) -> Tuple[int, int]:
    """Send notifications for detected changes"""
    if not changes_dict:
        logger.info(f"No changes detected for {callback_type}, no notifications sent")
        return 0, 0

    successful_notifications = 0
    failed_notifications = 0

    # Determine notification type based on callback
    if callback_type in ['robotStatus', 'notifyRobotPower']:
        notification_type = 'robot_status'
    elif callback_type == 'robotErrorWarning':
        notification_type = 'robot_status'  # Events go to robot_status type
    elif callback_type == 'notifyRobotPose':
        # Skip pose notifications as they're too frequent
        return len(changes_dict), 0
    else:
        notification_type = 'robot_status'

    # Send notification for each change
    for unique_id, change_info in changes_dict.items():
        try:
            robot_sn = change_info.get('robot_sn', 'unknown')
            database_key = change_info.get('database_key', None)

            # Build payload with database location info
            payload = {
                "database_name": database_name,
                "table_name": table_name,
                "related_biz_id": database_key,
                "related_biz_type": callback_type
            }

            # Generate notification content
            title, content = generate_notification_content(callback_type, change_info)

            # Skip notifications for certain types of changes
            if should_skip_notification(callback_type, change_info):
                continue

            # Get severity and status
            severity, status = get_severity_and_status(callback_type, change_info)

            # Format title with icons
            icon_manager = get_icon_manager()
            formatted_title = icon_manager.format_title_with_icons(title, severity, status)

            # Send notification
            if notification_service.send_notification(
                robot_sn=robot_sn,
                notification_type=notification_type,
                title=formatted_title,
                content=content,
                severity=severity,
                status=status,
                payload=payload
            ):
                successful_notifications += 1
                logger.info(f"✅ Sent notification for {unique_id}: {formatted_title}")
            else:
                failed_notifications += 1
                logger.error(f"❌ Failed to send notification for {unique_id}")

        except Exception as e:
            logger.error(f"Error sending notification for {unique_id}: {e}")
            failed_notifications += 1

    logger.info(f"📧 {callback_type} notifications: {successful_notifications}/{len(changes_dict)} sent")
    return successful_notifications, failed_notifications

def should_skip_notification(callback_type: str, change_info: Dict) -> bool:
    """Determine if notification should be skipped"""
    change_type = change_info.get('change_type', 'unknown')
    changed_fields = change_info.get('changed_fields', [])
    new_values = change_info.get('new_values', {})

    # Skip pose updates (too frequent)
    if callback_type == 'notifyRobotPose':
        return True

    # Skip power updates unless battery is low
    if callback_type == 'notifyRobotPower':
        if change_type == 'update':
            return True  # Skip power update notifications
        # For new records, check if battery is low
        power_level = new_values.get('power', 100)
        if isinstance(power_level, (int, float)) and power_level >= 20:
            return True  # Skip if battery >= 20%

    # Skip status updates that are just position changes
    if callback_type == 'robotStatus':
        if change_type == 'update' and 'status' not in changed_fields:
            # Check if only position fields changed
            position_fields = {'x', 'y', 'z', 'timestamp'}
            if set(changed_fields).issubset(position_fields):
                return True

    return False

def generate_notification_content(callback_type: str, change_info: Dict) -> Tuple[str, str]:
    """Generate notification title and content"""
    robot_sn = change_info.get('robot_sn', 'unknown')
    change_type = change_info.get('change_type', 'unknown')
    new_values = change_info.get('new_values', {})
    changed_fields = change_info.get('changed_fields', [])

    try:
        if callback_type == 'robotStatus':
            if 'status' in changed_fields or change_type == 'new_record':
                status = new_values.get('status', 'unknown')
                if 'online' in status.lower():
                    return "Robot Online", f"Robot {robot_sn} is now online."
                elif 'offline' in status.lower():
                    return "Robot Offline", f"Robot {robot_sn} has gone offline."
                else:
                    return "Robot Status Update", f"Robot {robot_sn} status changed to {status}."
            else:
                return "Robot Update", f"Robot {robot_sn} information updated."

        elif callback_type == 'robotErrorWarning':
            error_type = new_values.get('error_type', 'Unknown Error')
            error_level = new_values.get('error_level', 'info')
            upload_time = new_values.get('upload_time', 'Unknown Time')

            title = f"Robot Incident: {convert_technical_string(error_type)}"

            if error_level == 'error':
                content = f"Robot {robot_sn} has a new error - {error_type} at {upload_time}."
            elif error_level == 'warning':
                content = f"Robot {robot_sn} has a new warning - {error_type} at {upload_time}."
            elif error_level == 'fatal':
                content = f"Robot {robot_sn} has a new fatal event - {error_type} at {upload_time}."
            else:
                content = f"Robot {robot_sn} has a new event - {error_type} at {upload_time}."

            return title, content

        elif callback_type == 'notifyRobotPower':
            power_level = new_values.get('power', 0)

            if isinstance(power_level, (int, float)):
                if power_level < 5:
                    return "Critical Battery Alert", f"Robot {robot_sn} critical battery level at {power_level}%!"
                elif power_level < 10:
                    return "Low Battery Alert", f"Robot {robot_sn} low battery level at {power_level}%"
                elif power_level < 20:
                    return "Battery Warning", f"Robot {robot_sn} battery level at {power_level}%"
                else:
                    return "Battery Update", f"Robot {robot_sn} battery at {power_level}%"
            else:
                return "Power Update", f"Robot {robot_sn} power status updated."

        else:
            return f"{callback_type} Update", f"Robot {robot_sn} {callback_type} updated."

    except Exception as e:
        logger.warning(f"Error generating notification content: {e}")
        return f"{callback_type} Update", f"Robot {robot_sn} {callback_type} updated."

def get_severity_and_status(callback_type: str, change_info: Dict) -> Tuple[str, str]:
    """Get severity and status for notification"""
    new_values = change_info.get('new_values', {})
    changed_fields = change_info.get('changed_fields', [])

    if callback_type == 'robotStatus':
        if 'status' in changed_fields:
            status = new_values.get('status', '').lower()
            if 'online' in status:
                return SEVERITY_LEVELS['success'], STATUS_TAGS['online']
            elif 'offline' in status:
                return SEVERITY_LEVELS['error'], STATUS_TAGS['offline']
            else:
                return SEVERITY_LEVELS['event'], STATUS_TAGS['active']
        else:
            return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

    elif callback_type == 'robotErrorWarning':
        error_level = new_values.get('event_level', 'info').lower()
        if error_level == 'fatal':
            return SEVERITY_LEVELS['fatal'], STATUS_TAGS['abnormal']
        elif error_level == 'error':
            return SEVERITY_LEVELS['error'], STATUS_TAGS['abnormal']
        elif error_level == 'warning':
            return SEVERITY_LEVELS['warning'], STATUS_TAGS['warning']
        else:
            return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

    elif callback_type == 'notifyRobotPower':
        power_level = new_values.get('power', 100)
        if isinstance(power_level, (int, float)):
            if power_level < 5:
                return SEVERITY_LEVELS['fatal'], STATUS_TAGS['warning']
            elif power_level < 10:
                return SEVERITY_LEVELS['error'], STATUS_TAGS['warning']
            elif power_level < 20:
                return SEVERITY_LEVELS['warning'], STATUS_TAGS['warning']
            else:
                return SEVERITY_LEVELS['success'], STATUS_TAGS['normal']
        else:
            return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

    else:
        return SEVERITY_LEVELS['event'], STATUS_TAGS['normal']

def convert_technical_string(text: str) -> str:
    """Convert technical strings to human-readable format"""
    if not text:
        return text

    # Handle underscore-separated strings
    if '_' in text:
        words = text.split('_')
        formatted_words = [word.capitalize() for word in words]
        return ' '.join(formatted_words)

    # Handle camelCase strings
    else:
        import re
        spaced = re.sub('([a-z])([A-Z])', r'\1 \2', text)
        return spaced.title()
