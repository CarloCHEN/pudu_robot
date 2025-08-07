import logging
from typing import Any, Dict, Tuple
import time

from models import CallbackResponse, CallbackStatus
from processors import RobotErrorProcessor, RobotPoseProcessor, RobotPowerProcessor, RobotStatusProcessor
from database_writer import DatabaseWriter

logger = logging.getLogger(__name__)


class CallbackHandler:
    """
    Callback handler with dynamic database routing and change detection
    """

    def __init__(self, config_path: str = "database_config.yaml"):
        self.processors = {
            "robotStatus": RobotStatusProcessor(),
            "robotErrorWarning": RobotErrorProcessor(),
            "notifyRobotPose": RobotPoseProcessor(),
            "notifyRobotPower": RobotPowerProcessor(),
        }

        # Delivery-related callbacks to ignore (as requested)
        self.ignored_callbacks = {
            "deliveryStatus",
            "deliveryComplete",
            "deliveryError",
            "orderStatus",
            "orderComplete",
            "orderError",
            "orderReceived",
            "deliveryStart",
            "deliveryCancel",
        }

        # Initialize enhanced database writer
        self.database_writer = DatabaseWriter(config_path)

    def process_callback(self, data: Dict[str, Any]) -> CallbackResponse:
        """
        Process incoming callback based on callback type
        """
        try:
            callback_type = data.get("callback_type")

            if not callback_type:
                logger.error("No callback type specified")
                return CallbackResponse(status=CallbackStatus.ERROR, message="No callback type specified")

            # Check if this is a delivery-related callback to ignore
            if callback_type in self.ignored_callbacks:
                logger.info(f"Ignoring delivery-related callback: {callback_type}")
                return CallbackResponse(status=CallbackStatus.SUCCESS, message=f"Delivery callback ignored: {callback_type}")

            # Get appropriate processor
            processor = self.processors.get(callback_type)

            if not processor:
                logger.warning(f"No processor found for callback type: {callback_type}")
                return CallbackResponse(
                    status=CallbackStatus.WARNING,
                    message=f"Unknown callback type: {callback_type}",
                    data={"callback_type": callback_type},
                )

            # Process the callback
            return processor.process(data.get("data"))

        except Exception as e:
            logger.error(f"Error in callback processing: {str(e)}", exc_info=True)
            return CallbackResponse(status=CallbackStatus.ERROR, message=f"Processing error: {str(e)}")

    def write_to_database_with_change_detection(self, data: Dict[str, Any]) -> Tuple[list, list, dict]:
        """
        Write callback data to database with dynamic routing and change detection

        Returns:
            tuple: (database_names, table_names, changes_detected)
        """
        try:
            callback_type = data.get("callback_type")
            callback_data = data.get("data", {})
            robot_sn = callback_data.get("sn", "")

            if not robot_sn:
                logger.warning("No robot SN found in callback data")
                return [], [], {}

            if callback_type == "robotStatus":
                status_data = {
                    "robot_sn": robot_sn,
                    "status": callback_data.get("run_status", "").lower(),
                    "timestamp": callback_data.get("timestamp"),
                }
                return self.database_writer.write_robot_status(robot_sn, status_data)

            elif callback_type == "notifyRobotPose":
                pose_data = {
                    "robot_sn": robot_sn,
                    "x": callback_data.get("x"),
                    "y": callback_data.get("y"),
                    "z": callback_data.get("yaw"),  # Note: API uses 'yaw' for z-coordinate
                    "timestamp": callback_data.get("timestamp"),
                }
                return self.database_writer.write_robot_pose(robot_sn, pose_data)

            elif callback_type == "notifyRobotPower":
                power_data = {
                    "robot_sn": robot_sn,
                    "battery_level": callback_data.get("power"),
                    "charge_state": callback_data.get("charge_state"),
                    "timestamp": callback_data.get("timestamp"),
                }
                return self.database_writer.write_robot_power(robot_sn, power_data)

            elif callback_type == "robotErrorWarning":
                event_data = {
                    "robot_sn": robot_sn,
                    "event_id": callback_data.get("error_id", ""),
                    "error_id": callback_data.get("error_id", ""),
                    "event_level": callback_data.get("error_level", "").lower(),
                    "event_type": callback_data.get("error_type", ""),
                    "event_detail": callback_data.get("error_detail", ""),
                    "task_time": callback_data.get("timestamp", int(time.time())),
                    "upload_time": int(time.time()),
                }
                return self.database_writer.write_robot_event(robot_sn, event_data)

            return [], [], {}

        except Exception as e:
            logger.error(f"Error writing callback to database: {str(e)}")
            return [], [], {}

    def close(self):
        """Close database connections"""
        try:
            self.database_writer.close_all_connections()
        except Exception as e:
            logger.warning(f"Error closing database writer: {e}")
