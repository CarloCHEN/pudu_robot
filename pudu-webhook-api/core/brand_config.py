# core/brand_config.py
import json
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

    def _convert_value(self, value: Any, conversion_rules: Dict[str, Any]) -> Any:
        """
        Apply conversion rules to a value

        Conversions are applied in order:
        1. Type conversion (lowercase, int, etc.)
        2. Value mapping (H2 -> error, etc.)
        """
        if value is None:
            return None

        # Step 1: Apply type conversion first (but don't return yet!)
        value_type = conversion_rules.get('type')
        if value_type == 'lowercase':
            value = str(value).lower()
        elif value_type == 'uppercase':
            value = str(value).upper()
        elif value_type == 'int':
            try:
                value = int(value)
            except (ValueError, TypeError):
                return None
        elif value_type == 'float':
            try:
                value = float(value)
            except (ValueError, TypeError):
                return None
        elif value_type == 'timestamp_ms_to_s':
            try:
                value = int(value) // 1000
            except (ValueError, TypeError):
                return None
        elif value_type == 'multiply_by_1000':
            try:
                value = float(value) * 1000
            except (ValueError, TypeError):
                return None
        elif value_type == 'divide_by_1000':
            try:
                value = float(value) / 1000
            except (ValueError, TypeError):
                return None

        # Step 2: Apply value mapping (after type conversion)
        mapping = conversion_rules.get('mapping')
        if mapping and isinstance(mapping, dict):
            # Support both string and integer keys
            mapped_value = mapping.get(str(value)) or mapping.get(value)
            if mapped_value is not None:
                value = mapped_value

        return value

    def _calculate_field(self, source_data: Dict[str, Any], calculation: Dict[str, Any]) -> Any:
        """
        Calculate field value using formula

        Supported calculations:
        - operation: 'subtract', 'add', 'multiply', 'divide'
        - fields: [field1, field2] (supports nested paths)

        Example:
        {
            'operation': 'subtract',
            'fields': ['payload.taskReport.endBatteryPercentage', 'payload.taskReport.startBatteryPercentage']
        }
        """
        operation = calculation.get('operation')
        fields = calculation.get('fields', [])

        if not operation or len(fields) < 2:
            logger.warning(f"Invalid calculation config: {calculation}")
            return None

        # Get values for all fields
        values = []
        for field_path in fields:
            value = self._get_nested_value(source_data, field_path)
            if value is None:
                logger.debug(f"Missing value for calculation field: {field_path}")
                return None
            try:
                values.append(float(value))
            except (ValueError, TypeError):
                logger.warning(f"Cannot convert to float for calculation: {field_path} = {value}")
                return None

        # Perform calculation
        try:
            if operation == 'subtract':
                result = values[0] - values[1]
            elif operation == 'add':
                result = sum(values)
            elif operation == 'multiply':
                result = values[0]
                for v in values[1:]:
                    result *= v
            elif operation == 'divide':
                result = values[0] / values[1] if values[1] != 0 else None
            else:
                logger.warning(f"Unknown calculation operation: {operation}")
                return None

            return result
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return None

    def _collect_extra_fields(
        self,
        source_data: Dict[str, Any],
        extra_fields_config: List[str]
    ) -> Dict[str, Any]:
        """
        Collect extra brand-specific fields into a JSON object

        Args:
            source_data: Raw callback data
            extra_fields_config: List of field paths to collect

        Returns:
            Dictionary with collected fields
        """
        extra_data = {}

        for field_path in extra_fields_config:
            value = self._get_nested_value(source_data, field_path)
            if value is not None:
                # Use the last part of the path as the key
                key = field_path.split('.')[-1]
                extra_data[key] = value

        return extra_data

    def map_fields(self, abstract_type: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map source data fields to database schema fields

        Args:
            abstract_type: Abstract type (e.g., 'error_event', 'report_event')
            source_data: Raw callback data from brand

        Returns:
            Mapped data ready for database insertion
        """
        field_mapping = self.config.get_field_mapping(abstract_type)
        source_to_db = field_mapping.get('source_to_db', {})
        conversions = field_mapping.get('conversions', {})
        calculations = field_mapping.get('calculations', {})
        extra_fields = field_mapping.get('extra_fields', [])

        mapped_data = {}

        # 1. Map direct fields
        for source_path, db_field in source_to_db.items():
            # Get value from source (supports nested paths)
            value = self._get_nested_value(source_data, source_path)

            # Apply conversions if defined
            if db_field in conversions:
                value = self._convert_value(value, conversions[db_field])

            # Set in mapped data
            if value is not None:
                mapped_data[db_field] = value

        # 2. Calculate computed fields
        for db_field, calculation in calculations.items():
            calculated_value = self._calculate_field(source_data, calculation)
            if calculated_value is not None:
                mapped_data[db_field] = calculated_value

        # 3. Collect extra brand-specific fields as JSON
        if extra_fields:
            extra_data = self._collect_extra_fields(source_data, extra_fields)
            if extra_data:
                mapped_data['extra_data'] = json.dumps(extra_data)  # Store as JSON string

        logger.debug(f"Mapped {len(mapped_data)} fields for {abstract_type}")
        return mapped_data