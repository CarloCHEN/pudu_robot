# core/brand_config.py
import os
import yaml
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class BrandConfig:
    """Brand-specific configuration for callback handling"""

    def __init__(self, brand: str):
        self.brand = brand
        self._config = self._load_brand_config()

        # Core config sections
        self.verification = self._config.get('verification', {})
        self.type_mappings = self._config.get('type_mappings', {})
        self.field_mappings = self._config.get('field_mappings', {})
        self.ignored_types = set(self._config.get('ignored_types', []))
        self.transform_enabled = self._config.get('transform_enabled', False)

    def _load_brand_config(self) -> Dict[str, Any]:
        """Load brand-specific configuration from YAML"""
        config_path = Path(f'configs/{self.brand}/config.yaml')

        if not config_path.exists():
            logger.error(f"Brand config not found: {config_path}")
            return {}

        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}

        logger.info(f"Loaded brand config from {config_path}")
        return config_data

    def get_verification_method(self) -> str:
        """Get verification method: 'header' or 'body'"""
        return self.verification.get('method', 'header')

    def get_verification_key(self) -> str:
        """Get verification key name (e.g., 'callbackcode' or 'appId')"""
        return self.verification.get('key', '')

    def map_callback_type(self, callback_data: Dict[str, Any]) -> Optional[str]:
        """
        Map brand-specific callback type to abstract type

        Args:
            callback_data: Raw callback data from brand

        Returns:
            Abstract type (e.g., 'error_event', 'pose_event') or None
        """
        # For Pudu: use callback_type field
        if 'callback_type' in callback_data:
            callback_type = callback_data['callback_type']
            abstract_type = self.type_mappings.get(callback_type)
            if abstract_type:
                logger.debug(f"Mapped {self.brand} type '{callback_type}' -> '{abstract_type}'")
                return abstract_type

        # For Gas: use messageTypeId field
        if 'messageTypeId' in callback_data:
            message_type_id = str(callback_data['messageTypeId'])
            abstract_type = self.type_mappings.get(message_type_id)
            if abstract_type:
                logger.debug(f"Mapped {self.brand} type '{message_type_id}' -> '{abstract_type}'")
                return abstract_type

        logger.warning(f"No type mapping found for {self.brand} callback")
        return None

    def is_ignored_type(self, callback_data: Dict[str, Any]) -> bool:
        """Check if callback type should be ignored"""
        callback_type = callback_data.get('callback_type', '')
        message_type_id = str(callback_data.get('messageTypeId', ''))

        return callback_type in self.ignored_types or message_type_id in self.ignored_types

    def get_field_mapping(self, abstract_type: str) -> Dict[str, Any]:
        """Get field mapping configuration for abstract type"""
        return self.field_mappings.get(abstract_type, {})

    def supports_reports(self) -> bool:
        """Check if brand supports task reports"""
        return 'report_event' in self.type_mappings.values()


class FieldMapper:
    """Handles field mapping and transformation between brand data and DB schema"""

    def __init__(self, brand_config: BrandConfig):
        self.config = brand_config

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get value from nested dictionary using dot notation

        Example: 'payload.content.incidentId' -> data['payload']['content']['incidentId']
        """
        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None

        return value

    def _convert_value(self, value: Any, conversion_rules: Dict[str, Any]) -> Any:
        """
        Apply conversion rules to a value

        Supported conversions:
        - type: 'lowercase', 'uppercase', 'int', 'float', 'timestamp_ms_to_s'
        - mapping: dict for value mapping (e.g., 'H2' -> 'fatal')
        """
        if value is None:
            return None

        # Apply type conversion
        value_type = conversion_rules.get('type')
        if value_type == 'lowercase':
            return str(value).lower()
        elif value_type == 'uppercase':
            return str(value).upper()
        elif value_type == 'int':
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        elif value_type == 'float':
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        elif value_type == 'timestamp_ms_to_s':
            try:
                # Convert millisecond timestamp to seconds
                return int(value) // 1000
            except (ValueError, TypeError):
                return None
        elif value_type == 'div_by_1000':
            try:
                return int(value) / 1000
            except (ValueError, TypeError):
                return None

        # Apply value mapping
        mapping = conversion_rules.get('mapping')
        if mapping and isinstance(mapping, dict):
            return mapping.get(str(value), value)

        return value

    def map_fields(self, abstract_type: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map source data fields to database schema fields

        Args:
            abstract_type: Abstract type (e.g., 'error_event')
            source_data: Raw callback data from brand

        Returns:
            Mapped data ready for database insertion
        """
        field_mapping = self.config.get_field_mapping(abstract_type)
        source_to_db = field_mapping.get('source_to_db', {})
        conversions = field_mapping.get('conversions', {})

        mapped_data = {}

        for source_path, db_field in source_to_db.items():
            # Get value from source (supports nested paths)
            value = self._get_nested_value(source_data, source_path)

            # Apply conversions if defined
            if db_field in conversions:
                value = self._convert_value(value, conversions[db_field])

            # Set in mapped data
            if value is not None:
                mapped_data[db_field] = value

        logger.debug(f"Mapped {len(mapped_data)} fields for {abstract_type}")
        return mapped_data

    def drop_fields(self, abstract_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Drop brand-specific fields that don't belong in unified schema

        Args:
            abstract_type: Abstract type (e.g., 'error_event')
            data: Data to clean

        Returns:
            Cleaned data without dropped fields
        """
        field_mapping = self.config.get_field_mapping(abstract_type)
        drop_fields = set(field_mapping.get('drop_fields', []))

        if not drop_fields:
            return data

        cleaned_data = {k: v for k, v in data.items() if k not in drop_fields}

        if len(cleaned_data) < len(data):
            logger.debug(f"Dropped {len(data) - len(cleaned_data)} fields for {abstract_type}")

        return cleaned_data