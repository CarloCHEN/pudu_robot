# core/brand_config.py
import json
import yaml
import logging
import re
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

        # Chinese to English cleaning mode mapping
        self.CLEANING_MODE_TRANSLATION = {
            # Common cleaning modes
            '清洗': 'Cleaning',
            '清洁': 'Cleaning',
            '清扫': 'Sweeping',
            '扫洗': 'Sweep and Wash',
            '尘推': 'Dust Push',
            '吸尘': 'Vacuuming',
            '拖地': 'Mopping',
            '抛光': 'Polishing',

            # Strength/Intensity modes
            '强劲清洗': 'Strong Cleaning',
            '强力清洗': 'Powerful Cleaning',
            '标准清洗': 'Standard Cleaning',
            '轻柔清洗': 'Gentle Cleaning',
            '静音清洗': 'Quiet Cleaning',

            # Special modes
            '长续航清洗': 'Long Endurance Cleaning',
            '节能清洗': 'Energy Saving Cleaning',
            '快速清洗': 'Quick Cleaning',
            '深度清洗': 'Deep Cleaning',
            '日常清洗': 'Daily Cleaning',

            # Custom modes
            '自定义清洗': 'Custom Cleaning',
            '定制清洗': 'Customized Cleaning',

            # Area-specific modes
            '边缘清洗': 'Edge Cleaning',
            '定点清洗': 'Spot Cleaning',
            '区域清洗': 'Zone Cleaning',

            # Brush/Rolling modes
            '滚刷': 'Rolling Brush',
            '边刷': 'Side Brush',

            # Combined modes
            '扫洗一体': 'Integrated Sweep and Wash',
            '吸拖一体': 'Integrated Vacuum and Mop',

            # Cleaning type
            '地毯清洁': 'Carpet Cleaning',
            '木地板清洁': 'Wood Floor Cleaning',
            '瓷砖清洁': 'Tile Cleaning',
            '大理石清洁': 'Marble Cleaning'
        }

    def _translate_cleaning_mode(self, chinese_mode: str) -> str:
        """Translate Chinese cleaning mode to English and clean the text"""
        if not chinese_mode or not isinstance(chinese_mode, str):
            return ''

        # Remove underscores, dashes, and other symbols
        cleaned_mode = chinese_mode.replace('_', ' ').replace('-', ' ').replace('__', ' ')

        # Remove any remaining non-alphanumeric characters except spaces
        cleaned_mode = re.sub(r'[^\w\s]', '', cleaned_mode)

        # Remove extra spaces
        cleaned_mode = ' '.join(cleaned_mode.split())

        # Try exact match first
        if cleaned_mode in self.CLEANING_MODE_TRANSLATION:
            return self.CLEANING_MODE_TRANSLATION[cleaned_mode]

        # Try partial matches for combined modes
        for chinese, english in self.CLEANING_MODE_TRANSLATION.items():
            if chinese in cleaned_mode:
                # Replace the Chinese part with English
                result = cleaned_mode.replace(chinese, english)
                # Clean up any double spaces that might have been created
                return ' '.join(result.split())

        # If no translation found, return the cleaned Chinese text
        return cleaned_mode

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
        3. Special conversions (cleaning mode translation)
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
        elif value_type == 'translate_cleaning_mode':
            # Special conversion for cleaning mode translation
            value = self._translate_cleaning_mode(str(value))

        # Step 2: Apply value mapping (after type conversion)
        mapping = conversion_rules.get('mapping')
        if mapping and isinstance(mapping, dict):
            # Support both string and integer keys
            mapped_value = (
                mapping.get(value)
                or mapping.get(value.lower())
                or mapping.get(value.upper())
            )
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
        field_processors = field_mapping.get('field_processors', {})
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

        # 3. Process complex field transformations
        for db_field, processor_config in field_processors.items():
            processed_value = self._process_field(source_data, processor_config)
            if processed_value is not None:
                mapped_data[db_field] = processed_value

        # 4. Collect extra brand-specific fields as JSON
        if extra_fields:
            extra_data = self._collect_extra_fields(source_data, extra_fields)
            if extra_data:
                mapped_data['extra_fields'] = json.dumps(extra_data)  # Store as JSON string

        logger.debug(f"Mapped {len(mapped_data)} fields for {abstract_type}")
        return mapped_data

    def _process_field(self, source_data: Dict[str, Any], processor_config: Dict[str, Any]) -> Any:
        """
        Process fields using configured processors for complex transformations
        """
        processor_type = processor_config.get('processor')
        source_path = processor_config.get('source')
        config = processor_config.get('config', {})

        # Get source value
        source_value = self._get_nested_value(source_data, source_path)

        if processor_type == 'extract_map_names':
            return self._extract_map_names(source_value, config) # source_value is subtasks
        elif processor_type == 'join_strings':
            return self._join_strings(source_value, config)
        elif processor_type == 'extract_unique_values':
            return self._extract_unique_values(source_value, config)
        return None

    def _extract_map_names(self, dataList: List[Dict], config: Dict[str, Any]) -> str:
        """
        Generic map name extraction that can be configured
        """
        if not dataList:
            return ''

        map_name_field = config.get('map_name_field', 'mapName')
        delimiter = config.get('delimiter', ', ')
        max_items = config.get('max_items')

        map_names = [
            data.get(map_name_field, '')
            for data in dataList
            if data.get(map_name_field)
        ]

        if max_items and len(map_names) > max_items:
            map_names = map_names[:max_items]
            map_names.append('...')

        if len(map_names) == 1:
            return map_names[0]
        elif len(map_names) > 1:
            return delimiter.join(map_names)
        else:
            return ''

    def _join_strings(self, items: List, config: Dict[str, Any]) -> str:
        """Join list of strings with configurable delimiter"""
        delimiter = config.get('delimiter', ', ')
        return delimiter.join(str(item) for item in items if item)

    def _extract_unique_values(self, items: List[Dict], config: Dict[str, Any]) -> List:
        """Extract unique values from a specific field in dictionaries"""
        field_name = config.get('field_name')
        if not field_name or not items:
            return []

        unique_values = set()
        for item in items:
            if field_name in item:
                unique_values.add(item[field_name])

        return list(unique_values)