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
