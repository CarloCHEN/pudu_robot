import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
import time
from models import (
    CallbackResponse, CallbackStatus, RobotStatus,
    RobotInfo, ErrorInfo, RobotPose, PowerInfo
)

logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """Base class for all callback processors"""

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> CallbackResponse:
        """Process the callback data"""
        pass

    def extract_robot_info(self, data: Dict[str, Any]) -> RobotInfo:
        """Extract robot information from callback data"""
        return RobotInfo(
            robot_sn=data.get('sn', ''),
            timestamp=data.get('timestamp', int(time.time()))
        )

class RobotStatusProcessor(BaseProcessor):
    """Processor for robot status callbacks"""

    def process(self, data: Dict[str, Any]) -> CallbackResponse:
        if data is None or data == {}:
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Invalid data"
            )
        try:
            robot_info = self.extract_robot_info(data)
            status = data.get('run_status', '').lower()

            logger.info(f"Robot {robot_info.robot_sn} status: {status}")

            # Map status to our enum based on common Pudu robot states
            status_mapping = {
                'online': RobotStatus.ONLINE,
                'offline': RobotStatus.OFFLINE,
                'working': RobotStatus.WORKING,
                'cleaning': RobotStatus.WORKING,
                'idle': RobotStatus.IDLE,
                'charging': RobotStatus.CHARGING,
                'error': RobotStatus.ERROR,
                'maintenance': RobotStatus.MAINTENANCE,
                'standby': RobotStatus.IDLE,
                'paused': RobotStatus.IDLE,
                'moving': RobotStatus.WORKING
            }

            robot_status = status_mapping.get(status, RobotStatus.OFFLINE)

            # Handle specific status changes
            if robot_status == RobotStatus.OFFLINE:
                self._handle_robot_offline(robot_info)
            elif robot_status == RobotStatus.ERROR:
                self._handle_robot_error_status(robot_info, data)
            elif robot_status == RobotStatus.WORKING:
                self._handle_robot_working(robot_info, data)

            return CallbackResponse(
                status=CallbackStatus.SUCCESS,
                message=f"Robot status processed: {status}",
                timestamp=robot_info.timestamp,
                data={
                    "robot_sn": robot_info.robot_sn,
                    "status": robot_status.value,
                    "timestamp": robot_info.timestamp
                }
            )

        except Exception as e:
            logger.error(f"Error processing robot status: {str(e)}")
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message=f"Failed to process robot status: {str(e)}"
            )

    def _handle_robot_offline(self, robot_info: RobotInfo):
        """Handle robot going offline"""
        logger.warning(f"Robot {robot_info.robot_sn} went offline")
        # Add offline handling logic here
        # e.g., send alerts, update database, etc.

    def _handle_robot_error_status(self, robot_info: RobotInfo, data: Dict[str, Any]):
        """Handle robot error status"""
        logger.error(f"Robot {robot_info.robot_sn} is in error state")
        # Add error handling logic here

    def _handle_robot_working(self, robot_info: RobotInfo, data: Dict[str, Any]):
        """Handle robot working status"""
        logger.info(f"Robot {robot_info.robot_sn} started working")
        # Add working status logic here

class RobotErrorProcessor(BaseProcessor):
    """Processor for robot error and warning callbacks"""

    def process(self, data: Dict[str, Any]) -> CallbackResponse:
        try:
            robot_info = self.extract_robot_info(data)

            error_info = ErrorInfo(
                robot_sn=data.get('sn', ''),
                timestamp=data.get('timestamp', int(time.time())),
                error_type=data.get('error_type', ''),
                error_level=data.get('error_level', ''),
                error_detail=data.get('error_detail', ''),
                error_id=data.get('error_id', '')
            )

            logger.error(f"Robot {robot_info.robot_sn} error: {error_info.error_type} - {error_info.error_detail}")

            # Handle different error severities
            if error_info.error_level.lower() == 'fatal':
                self._handle_fatal(robot_info, error_info)
            elif error_info.error_level.lower() == 'error':
                self._handle_error(robot_info, error_info)
            elif error_info.error_level.lower() == 'warning':
                self._handle_warning(robot_info, error_info)
            else:
                self._handle_event(robot_info, error_info)

            return CallbackResponse(
                status=CallbackStatus.SUCCESS,
                message=f"Error processed: {error_info.error_type}",
                timestamp=error_info.timestamp,
                data={
                    "robot_sn": robot_info.robot_sn,
                    "error_type": error_info.error_type,
                    "error_level": error_info.error_level,
                    "error_detail": error_info.error_detail,
                    "error_id": error_info.error_id,
                    "timestamp": error_info.timestamp
                }
            )

        except Exception as e:
            logger.error(f"Error processing robot error: {str(e)}")
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message=f"Failed to process robot error: {str(e)}"
            )

    def _handle_fatal(self, robot_info: RobotInfo, error_info: ErrorInfo):
        """Handle fatal events requiring immediate attention"""
        logger.critical(f"FATAL EVENT on robot {robot_info.robot_sn}: {error_info.error_detail}")
        # Add fatal event handling: immediate alerts, emergency stop, etc.

    def _handle_error(self, robot_info: RobotInfo, error_info: ErrorInfo):
        """Handle errors"""
        logger.error(f"ERROR on robot {robot_info.robot_sn}: {error_info.error_detail}")
        # Add error handling

    def _handle_warning(self, robot_info: RobotInfo, error_info: ErrorInfo):
        """Handle warnings"""
        logger.warning(f"WARNING on robot {robot_info.robot_sn}: {error_info.error_detail}")
        # Add warning handling

    def _handle_event(self, robot_info: RobotInfo, error_info: ErrorInfo):
        """Handle other events"""
        logger.warning(f"Event on robot {robot_info.robot_sn}: {error_info.error_detail}")
        # Add event handling

class RobotPoseProcessor(BaseProcessor):
    """Processor for robot pose/position callbacks"""

    def process(self, data: Dict[str, Any]) -> CallbackResponse:
        if data is None or data == {}:
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Invalid data"
            )
        try:
            robot_info = self.extract_robot_info(data)

            # Extract pose information
            pose_info = RobotPose(
                x=data.get('x'),
                y=data.get('y'),
                yaw=data.get('yaw'),
                robot_sn=data.get('sn', ''),
                robot_mac=data.get('mac', ''),
                timestamp=data.get('timestamp', int(time.time()))
            )

            logger.info(f"Robot {robot_info.robot_sn} pose update: x={pose_info.x}, y={pose_info.y}, yaw={pose_info.yaw}")

            # Handle pose updates
            self._handle_pose_update(robot_info, pose_info, data)

            return CallbackResponse(
                status=CallbackStatus.SUCCESS,
                message=f"Robot {robot_info.robot_sn} pose processed",
                timestamp=pose_info.timestamp,
                data={
                    "robot_sn": robot_info.robot_sn,
                    "position": {
                        "x": pose_info.x,
                        "y": pose_info.y,
                        "yaw": pose_info.yaw
                    },
                    "robot_mac": pose_info.robot_mac,
                    "timestamp": pose_info.timestamp
                }
            )

        except Exception as e:
            logger.error(f"Error processing robot pose: {str(e)}")
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message=f"Failed to process robot pose: {str(e)}"
            )

    def _handle_pose_update(self, robot_info: RobotInfo, pose_info: RobotPose, data: Dict[str, Any]):
        """Handle robot pose updates"""
        logger.debug(f"Robot {robot_info.robot_sn} moved to position ({pose_info.x}, {pose_info.y})")
        # Add pose handling logic here
        # e.g., update robot tracking system, check boundaries, etc.

class RobotPowerProcessor(BaseProcessor):
    """Processor for robot power/battery callbacks"""

    def process(self, data: Dict[str, Any]) -> CallbackResponse:
        if data is None or data == {}:
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message="Invalid data"
            )
        try:
            robot_info = self.extract_robot_info(data)
            # Extract power information
            power_value = data.get('power', 0)
            try:
                power_value = int(power_value)
            except (ValueError, TypeError):
                power_value = 0  # Fallback if conversion fails

            # Extract power information
            power_info = PowerInfo(
                robot_sn=data.get('sn', ''),
                robot_mac=data.get('mac', ''),
                charge_state=data.get('charge_state', '').lower().strip(),
                power=power_value,
                timestamp=data.get('timestamp', int(time.time()))
            )

            logger.info(f"Robot {robot_info.robot_sn} power: {power_info.power}% (charging: {power_info.charge_state})")

            # Handle different power conditions
            if power_info.power is not None:
                if power_info.power <= 10 and power_info.charge_state != 'charging':
                    self._handle_critical_battery(robot_info, power_info)
                elif power_info.power <= 20 and power_info.charge_state != 'charging':
                    self._handle_low_battery(robot_info, power_info)
                elif power_info.power >= 95 and power_info.charge_state == 'charging':
                    self._handle_battery_full(robot_info, power_info)

            return CallbackResponse(
                status=CallbackStatus.SUCCESS,
                message=f"Robot {robot_info.robot_sn} power processed: {power_info.power}%",
                timestamp=power_info.timestamp,
                data={
                    "robot_sn": robot_info.robot_sn,
                    "power": power_info.power,
                    "charge_state": power_info.charge_state,
                    "timestamp": power_info.timestamp
                }
            )

        except Exception as e:
            logger.error(f"Error processing robot power: {str(e)}")
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message=f"Failed to process robot power: {str(e)}"
            )

    def _handle_critical_battery(self, robot_info: RobotInfo, power_info: PowerInfo):
        """Handle critical battery level"""
        logger.critical(f"CRITICAL BATTERY on robot {robot_info.robot_sn}: {power_info.power}%")
        # Add critical battery handling: force return to dock, emergency alerts, etc.

    def _handle_low_battery(self, robot_info: RobotInfo, power_info: PowerInfo):
        """Handle low battery level"""
        logger.warning(f"Low battery on robot {robot_info.robot_sn}: {power_info.power}%")
        # Add low battery handling: suggest charging, send notifications, etc.

    def _handle_battery_full(self, robot_info: RobotInfo, power_info: PowerInfo):
        """Handle battery fully charged"""
        logger.info(f"Robot {robot_info.robot_sn} battery full: {power_info.power}%")
        # Add full battery handling: ready for tasks, disconnect charging, etc.