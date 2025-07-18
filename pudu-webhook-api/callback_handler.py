import logging
from typing import Dict, Any
from models import CallbackResponse, CallbackStatus
from processors import (
    RobotStatusProcessor,
    RobotErrorProcessor,
    RobotPoseProcessor,
    RobotPowerProcessor
)

logger = logging.getLogger(__name__)

class CallbackHandler:
    """
    Main handler for processing Pudu robot callbacks
    """

    def __init__(self):
        self.processors = {
            'robotStatus': RobotStatusProcessor(),
            'robotErrorWarning': RobotErrorProcessor(),
            'notifyRobotPose': RobotPoseProcessor(),
            'notifyRobotPower': RobotPowerProcessor(),
        }

        # Delivery-related callbacks to ignore (as requested)
        self.ignored_callbacks = {
            'deliveryStatus', 'deliveryComplete', 'deliveryError',
            'orderStatus', 'orderComplete', 'orderError',
            'orderReceived', 'deliveryStart', 'deliveryCancel'
        }

    def process_callback(self, data: Dict[str, Any]) -> CallbackResponse:
        """
        Process incoming callback based on callback type
        """
        try:
            callback_type = data.get('callback_type')

            if not callback_type:
                logger.error("No callback type specified")
                return CallbackResponse(
                    status=CallbackStatus.ERROR,
                    message="No callback type specified"
                )

            # Check if this is a delivery-related callback to ignore
            if callback_type in self.ignored_callbacks:
                logger.info(f"Ignoring delivery-related callback: {callback_type}")
                return CallbackResponse(
                    status=CallbackStatus.SUCCESS,
                    message=f"Delivery callback ignored: {callback_type}"
                )

            # Get appropriate processor
            processor = self.processors.get(callback_type)

            if not processor:
                logger.warning(f"No processor found for callback type: {callback_type}")
                return CallbackResponse(
                    status=CallbackStatus.WARNING,
                    message=f"Unknown callback type: {callback_type}",
                    data={"callback_type": callback_type}
                )

            # Process the callback
            return processor.process(data.get('data'))

        except Exception as e:
            logger.error(f"Error in callback processing: {str(e)}", exc_info=True)
            return CallbackResponse(
                status=CallbackStatus.ERROR,
                message=f"Processing error: {str(e)}"
            )

    def write_to_database(self, data: Dict[str, Any], database_writer):
        """Write callback data to database"""
        try:
            callback_type = data.get('callback_type')
            callback_data = data.get('data', {})
            robot_sn = callback_data.get('sn', '')

            if not robot_sn:
                logger.warning("No robot SN found in callback data")
                return

            if callback_type == 'robotStatus':
                status_data = {
                    'status': callback_data.get('run_status', '').lower(),
                    'timestamp': callback_data.get('timestamp')
                }
                database_writer.write_robot_status(robot_sn, status_data)

            elif callback_type == 'notifyRobotPose':
                pose_data = {
                    'x': callback_data.get('x'),
                    'y': callback_data.get('y'),
                    'yaw': callback_data.get('yaw'),
                    'timestamp': callback_data.get('timestamp')
                }
                database_writer.write_robot_pose(robot_sn, pose_data)

            elif callback_type == 'notifyRobotPower':
                power_data = {
                    'power': callback_data.get('power'),
                    'charge_state': callback_data.get('charge_state'),
                    'timestamp': callback_data.get('timestamp')
                }
                database_writer.write_robot_power(robot_sn, power_data)

            elif callback_type == 'robotErrorWarning':
                event_data = {
                    'error_level': callback_data.get('error_level'),
                    'error_type': callback_data.get('error_type'),
                    'error_detail': callback_data.get('error_detail'),
                    'error_id': callback_data.get('error_id'),
                    'timestamp': callback_data.get('timestamp')
                }
                database_writer.write_robot_event(robot_sn, event_data)

        except Exception as e:
            logger.error(f"Error writing callback to database: {str(e)}")