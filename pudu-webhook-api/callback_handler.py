# callback_handler.py
import logging
from typing import Any, Dict, Tuple
import time

from models import CallbackResponse, CallbackStatus
from database_writer import DatabaseWriter
from core.brand_config import BrandConfig, FieldMapper
from core.services.verification_service import VerificationService

logger = logging.getLogger(__name__)


class CallbackHandler:
    """
    Enhanced callback handler with brand support
    Handles verification, type mapping, field mapping, and database writing
    """

    def __init__(self, database_config_path: str = "configs/database_config.yaml", brand: str = "pudu"):
        """
        Initialize callback handler with brand configuration

        Args:
            database_config_path: Path to database configuration YAML
            brand: Brand name (e.g., 'pudu', 'gas')
        """
        self.brand = brand

        # Load brand-specific configuration
        self.brand_config = BrandConfig(brand)
        self.field_mapper = FieldMapper(self.brand_config)
        self.verification_service = VerificationService(self.brand_config)

        # Initialize enhanced database writer
        self.database_writer = DatabaseWriter(database_config_path)

        logger.info(f"CallbackHandler initialized for brand: {brand}")

    def verify_request(self, data: Dict[str, Any], headers: Dict[str, str]) -> Tuple[bool, str]:
        """
        Verify incoming request using brand-specific verification

        Args:
            data: Request body
            headers: Request headers

        Returns:
            tuple: (is_valid, error_message)
        """
        return self.verification_service.verify(data, headers)

    def process_callback(self, data: Dict[str, Any]) -> CallbackResponse:
        # Just validate and map
        abstract_type = self.brand_config.map_callback_type(data)

        if not abstract_type:
            return CallbackResponse(status=CallbackStatus.WARNING, message="Unknown type")

        if self.brand_config.is_ignored_type(data):
            return CallbackResponse(status=CallbackStatus.SUCCESS, message="Type ignored")

        # Just return success - all real work happens in write_to_database
        return CallbackResponse(
            status=CallbackStatus.SUCCESS,
            message=f"Callback received: {abstract_type}"
        )

    def _extract_callback_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract callback data payload based on brand format

        Args:
            data: Raw callback data

        Returns:
            Extracted data payload
        """
        # Pudu format: {'callback_type': 'xxx', 'data': {...}}
        if 'callback_type' in data and 'data' in data:
            return data.get('data', {})

        # Gas format: {'messageTypeId': 1, 'payload': {...}}
        # For Gas, we'll return the entire data since field mapper handles nested paths
        if 'messageTypeId' in data:
            return data

        # Fallback: return as-is
        return data

    def write_to_database_with_change_detection(
        self,
        raw_data: Dict[str, Any]
    ) -> Tuple[list, list, dict]:
        """
        Write callback data to database with brand-aware field mapping and change detection

        Args:
            raw_data: Raw callback data from brand

        Returns:
            tuple: (database_names, table_names, changes_detected)
        """
        try:
            # Map to abstract type
            abstract_type = self.brand_config.map_callback_type(raw_data)

            if not abstract_type:
                logger.warning("Cannot write to database: unknown callback type")
                return [], [], {}

            # Extract callback data
            callback_data = self._extract_callback_data(raw_data)

            # Map fields using brand-specific field mapper
            mapped_data = self.field_mapper.map_fields(abstract_type, callback_data)

            if not mapped_data:
                logger.warning(f"No data after field mapping for {abstract_type}")
                return [], [], {}

            # Drop brand-specific fields
            cleaned_data = self.field_mapper.drop_fields(abstract_type, mapped_data)

            logger.info(f"Cleaned data: {cleaned_data}")

            # Extract robot_sn for database routing
            robot_sn = cleaned_data.get("robot_sn", "")

            if not robot_sn:
                logger.warning("No robot_sn found after field mapping")
                return [], [], {}

            # Route to appropriate database writer method based on abstract type
            if abstract_type == "status_event":
                return self.database_writer.write_robot_status(robot_sn, cleaned_data)

            elif abstract_type == "pose_event":
                return self.database_writer.write_robot_pose(robot_sn, cleaned_data)

            elif abstract_type == "power_event":
                return self.database_writer.write_robot_power(robot_sn, cleaned_data)

            elif abstract_type == "error_event":
                # Ensure required fields for error events
                error_data = {
                    "robot_sn": cleaned_data.get("robot_sn", robot_sn),
                    "event_id": cleaned_data.get("event_id", ""),
                    "error_id": cleaned_data.get("error_id", cleaned_data.get("event_id", "")),
                    "event_level": cleaned_data.get("event_level", ""),
                    "event_type": cleaned_data.get("event_type", ""),
                    "event_detail": cleaned_data.get("event_detail", ""),
                    "task_time": cleaned_data.get("task_time", int(time.time())),
                    "upload_time": int(time.time()),
                    "extra_fields": cleaned_data.get("extra_fields"),  # JSON string
                }
                return self.database_writer.write_robot_event(robot_sn, error_data)

            elif abstract_type == "report_event":
                task_data = {
                    "robot_sn": cleaned_data.get("robot_sn", robot_sn),
                    "robot_type": cleaned_data.get("robot_type", ""),
                    "task_id": cleaned_data.get("task_id", ""),
                    "task_name": cleaned_data.get("task_name", ""),
                    "map_name": cleaned_data.get("map_name", ""),
                    "start_time": cleaned_data.get("start_time"),
                    "end_time": cleaned_data.get("end_time"),
                    "progress": cleaned_data.get("progress"),
                    "duration": cleaned_data.get("duration"),
                    "actual_area": cleaned_data.get("actual_area"),
                    "plan_area": cleaned_data.get("plan_area"),
                    "efficiency": cleaned_data.get("efficiency"),
                    "water_consumption": cleaned_data.get("water_consumption"),
                    "mode": cleaned_data.get("mode", ""),
                    "status": cleaned_data.get("status"),
                    "map_url": cleaned_data.get("map_url", ""),
                    "battery_usage": cleaned_data.get("battery_usage"),
                    "extra_fields": cleaned_data.get("extra_fields"),  # JSON string
                }
                return self.database_writer.write_robot_task(robot_sn, task_data)
            return [], [], {}

        except Exception as e:
            logger.error(f"Error writing callback to database: {str(e)}", exc_info=True)
            return [], [], {}

    def get_handler_info(self) -> Dict[str, Any]:
        """
        Get handler configuration info (for debugging/health checks)

        Returns:
            Dictionary with handler configuration details
        """
        return {
            "brand": self.brand,
            "verification": self.verification_service.get_verification_info(),
            "supported_types": list(self.brand_config.type_mappings.values()),
            "ignored_types": list(self.brand_config.ignored_types),
            "transform_enabled": self.brand_config.transform_enabled
        }

    def close(self):
        """Close database connections"""
        try:
            self.database_writer.close_all_connections()
        except Exception as e:
            logger.warning(f"Error closing database writer: {e}")