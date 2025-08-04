import logging
from typing import Dict, Optional, Tuple

from .icon_manager import get_icon_manager
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

# Severity and status mappings
SEVERITY_LEVELS = {
    "fatal": "fatal",  # Purple - Immediate attention required
    "error": "error",  # Red - Task failed or serious problem
    "warning": "warning",  # Yellow - Moderate issue or degraded state
    "event": "event",  # Blue - Informational or neutral event
    "success": "success",  # Green - Positive/normal outcome
    "neutral": "neutral",  # Gray - Scheduled or inactive items
}

STATUS_TAGS = {
    "completed": "completed",  # ✅ Green - Task completed
    "failed": "failed",  # ❌ Red - Task failed
    "warning": "warning",  # ⚠️ Yellow - Battery low, performance warning
    "charging": "charging",  # 🔌 Purple - Robot in charging state
    "offline": "offline",  # 📴 Red - Robot went offline
    "online": "online",  # 📶 Green - Robot came online
    "normal": "normal",  # ✅ Green - Event resolved or status normal
    "abnormal": "abnormal",  # ❌ Red - Error occurred or abnormal status
    "active": "active",  # ⏳ Blue - Process active or ongoing
}


def send_webhook_notification(callback_type: str, callback_data: dict, payload: dict, notification_service: NotificationService) -> bool:
    """
    Send notification for webhook callbacks

    Args:
        callback_type: Type of callback (robotStatus, robotErrorWarning, notifyRobotPower)
        callback_data: Callback data from Pudu
        notification_service: Notification service instance

    Returns:
        bool: True if notification sent successfully
    """
    try:
        robot_sn = callback_data.get("sn", "unknown")

        # Skip position notifications as requested
        if callback_type == "notifyRobotPose":
            logger.debug(f"Skipping position notification for robot {robot_sn}")
            return True

        # Generate notification content based on callback type
        title, content, severity, status = generate_webhook_notification_content(callback_type, callback_data)

        if not title:  # Skip if no notification should be sent
            return True

        # Format title with appropriate icons
        icon_manager = get_icon_manager()
        formatted_title = icon_manager.format_title_with_icons(title, severity, status)

        # Determine notification type
        if callback_type in ["robotStatus", "notifyRobotPower"]:
            notification_type = "robot_status"
        elif callback_type == "robotErrorWarning":
            notification_type = "robot_status"  # Events go to robot_status type
        else:
            notification_type = "robot_status"

        # Send notification
        success = notification_service.send_notification(
            robot_id=robot_sn,
            notification_type=notification_type,
            title=formatted_title,
            content=content,
            severity=severity,
            status=status,
            payload=payload
        )

        if success:
            logger.info(f"✅ Webhook notification sent for robot {robot_sn}: {formatted_title}")
        else:
            logger.error(f"❌ Failed to send webhook notification for robot {robot_sn}")

        return success

    except Exception as e:
        logger.error(f"Error sending webhook notification: {e}", exc_info=True)
        return False


def generate_webhook_notification_content(callback_type: str, callback_data: dict) -> Tuple[str, str, str, str]:
    """
    Generate notification content for webhook callbacks

    Returns:
        tuple: (title, content, severity, status)
    """
    robot_sn = callback_data.get("sn", "unknown")

    try:
        if callback_type == "robotStatus":
            return handle_robot_status_notification(robot_sn, callback_data)

        elif callback_type == "robotErrorWarning":
            return handle_robot_error_notification(robot_sn, callback_data)

        elif callback_type == "notifyRobotPower":
            return handle_robot_power_notification(robot_sn, callback_data)

        elif callback_type == "notifyRobotPose":
            # Skip position notifications
            return None, None, None, None

        else:
            # Unknown callback type
            title = f"Unknown Event"
            content = f"Robot: {robot_sn}; Unknown callback type: {callback_type}"
            return title, content, SEVERITY_LEVELS["event"], STATUS_TAGS["normal"]

    except Exception as e:
        logger.warning(f"Error generating notification content for {callback_type}: {e}")
        title = f"Callback Processing"
        content = f"Robot: {robot_sn}; Received {callback_type} callback"
        return title, content, SEVERITY_LEVELS["event"], STATUS_TAGS["normal"]


def handle_robot_status_notification(robot_sn: str, data: dict) -> Tuple[str, str, str, str]:
    """Handle robot status change notifications"""
    run_status = data.get("run_status", "").upper()

    if run_status == "ONLINE":
        title = "Robot Online"
        content = f"Robot SN: {robot_sn} is now online."
        severity = SEVERITY_LEVELS["success"]
        status = STATUS_TAGS["online"]

    elif run_status == "OFFLINE":
        title = "Robot Offline"
        content = f"Robot SN: {robot_sn} has gone offline."
        severity = SEVERITY_LEVELS["error"]
        status = STATUS_TAGS["offline"]

    elif run_status in ["WORKING", "CLEANING"]:
        title = "Robot Working"
        content = f"Robot SN: {robot_sn} has started working."
        severity = SEVERITY_LEVELS["success"]
        status = STATUS_TAGS["active"]

    elif run_status == "IDLE":
        title = "Robot Idle"
        content = f"Robot SN: {robot_sn} is now idle."
        severity = SEVERITY_LEVELS["event"]
        status = STATUS_TAGS["normal"]

    elif run_status == "CHARGING":
        title = "Robot Charging"
        content = f"Robot SN: {robot_sn} is now charging."
        severity = SEVERITY_LEVELS["event"]
        status = STATUS_TAGS["charging"]

    elif run_status == "ERROR":
        title = "Robot Error"
        content = f"Robot SN: {robot_sn} is in error state."
        severity = SEVERITY_LEVELS["error"]
        status = STATUS_TAGS["failed"]

    else:
        title = "Robot Status Update"
        content = f"Robot SN: {robot_sn} status changed to {run_status}."
        severity = SEVERITY_LEVELS["event"]
        status = STATUS_TAGS["normal"]

    return title, content, severity, status


def handle_robot_error_notification(robot_sn: str, data: dict) -> Tuple[str, str, str, str]:
    """Handle robot error/warning notifications"""
    error_level = data.get("error_level", "EVENT").upper()
    error_type = data.get("error_type", "Unknown Error")
    error_detail = data.get("error_detail", "")
    timestamp = data.get("timestamp", "Unknown Time")

    # Convert technical strings to readable format
    readable_error_type = convert_technical_string(error_type)
    readable_error_detail = convert_technical_string(error_detail)

    title = f"Robot Incident: {readable_error_type}"

    if "FATAL" in error_level:
        content = f"Robot SN: {robot_sn} has a new fatal event - {error_type} at {timestamp}."
        severity = SEVERITY_LEVELS["fatal"]
        status = STATUS_TAGS["failed"]

    elif "ERROR" in error_level:
        content = f"Robot SN: {robot_sn} has a new error - {error_type} at {timestamp}."
        severity = SEVERITY_LEVELS["error"]
        status = STATUS_TAGS["abnormal"]

    elif "WARNING" in error_level:
        content = f"Robot SN: {robot_sn} has a new warning - {error_type} at {timestamp}."
        severity = SEVERITY_LEVELS["warning"]
        status = STATUS_TAGS["warning"]

    else:  # EVENT or other
        content = f"Robot SN: {robot_sn} has a new event - {error_type} at {timestamp}."
        severity = SEVERITY_LEVELS["event"]
        status = STATUS_TAGS["normal"]

    return title, content, severity, status


def handle_robot_power_notification(robot_sn: str, data: dict) -> Tuple[str, str, str, str]:
    """Handle robot power/battery notifications"""
    power_level = data.get("power", 0)
    charge_state = data.get("charge_state", "").lower()

    # Only send notifications for low battery or charging state changes
    if isinstance(power_level, (int, float)):
        if power_level < 5:
            title = "Critical Battery Alert"
            content = f"Robot SN: {robot_sn} Critical battery level at {power_level}%!"
            severity = SEVERITY_LEVELS["fatal"]
            status = STATUS_TAGS["warning"]

        elif power_level < 10:
            title = "Low Battery Alert"
            content = f"Robot SN: {robot_sn} Low battery level at {power_level}%"
            severity = SEVERITY_LEVELS["error"]
            status = STATUS_TAGS["warning"]

        elif power_level < 20:
            title = "Battery Warning"
            content = f"Robot SN: {robot_sn} Battery level at {power_level}%"
            severity = SEVERITY_LEVELS["warning"]
            status = STATUS_TAGS["warning"]

        elif power_level >= 95 and "charg" in charge_state:
            title = "Battery Fully Charged"
            content = f"Robot SN: {robot_sn} Battery fully charged at {power_level}%"
            severity = SEVERITY_LEVELS["success"]
            status = STATUS_TAGS["completed"]

        else:
            # Skip normal battery level notifications
            return None, None, None, None
    else:
        # Skip if power level is not numeric
        return None, None, None, None

    return title, content, severity, status


def convert_technical_string(text: str) -> str:
    """Convert technical strings to human-readable format"""
    if not text:
        return text

    # Handle underscore-separated strings
    if "_" in text:
        words = text.split("_")
        formatted_words = [word.capitalize() for word in words]
        return " ".join(formatted_words)

    # Handle camelCase strings
    else:
        import re

        spaced = re.sub("([a-z])([A-Z])", r"\1 \2", text)
        return spaced.title()
