import logging
from typing import Dict
from pudu.rds.rdsTable import RDSTable
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logger = logging.getLogger(__name__)

# Define decimal precision for common fields that use decimal(10, 2) in database
DECIMAL_FIELDS_PRECISION = {
    # Fields that should be rounded to 2 decimal places to match database schema
    'actual_area': 2,
    'plan_area': 2,
    'duration': 2,
    'efficiency': 2,
    'remaining_time': 2,
    'consumption': 2,
    'water_consumption': 2,
    'progress': 2,
    'battery_level': 2,
    'water_level': 2,
    'sewage_level': 2,
    'cost_water': 2,
    'cost_battery': 2,
    'clean_area': 2,
    'task_area': 2,
    'average_area': 2,
    'percentage': 2
}

def normalize_decimal_value(value, field_name: str):
    """
    Normalize a value to match database decimal precision

    Args:
        value: The value to normalize
        field_name: The field name to determine precision

    Returns:
        Normalized value with appropriate decimal precision
    """
    if value is None:
        return None

    # Get the expected decimal places for this field
    decimal_places = DECIMAL_FIELDS_PRECISION.get(field_name.lower())

    if decimal_places is not None:
        try:
            # Convert to Decimal for precise rounding
            if isinstance(value, str):
                # Handle percentage strings like "100%"
                if '%' in value:
                    value = value.replace('%', '')
                decimal_value = Decimal(str(value))
            else:
                decimal_value = Decimal(str(value))

            # Round to the specified decimal places
            quantizer = Decimal('0.1') ** decimal_places
            rounded_value = decimal_value.quantize(quantizer, rounding=ROUND_HALF_UP)

            # Return as float for consistency (pandas DataFrames typically use float)
            return float(rounded_value)

        except (ValueError, TypeError, Exception) as e:
            logger.debug(f"Could not normalize decimal for field {field_name}, value {value}: {e}")
            return value

    return value

def normalize_record_for_comparison(record: dict) -> dict:
    """
    Normalize all decimal fields in a record for database comparison

    Args:
        record: Dictionary containing field values

    Returns:
        Dictionary with normalized decimal values
    """
    normalized = {}
    for field_name, value in record.items():
        normalized[field_name] = normalize_decimal_value(value, field_name)
    return normalized

def detect_data_changes(table, data_list: list, primary_keys: list) -> Dict[str, Dict]:
    """
    Detect what data has actually changed compared to existing database records
    Returns a dictionary with unique record identifier as key and change details as value
    """
    if not data_list or not primary_keys:
        return {}

    changes_detected = {}

    try:
        # Get actual table columns to avoid checking non-existent fields
        table_columns = set()
        try:
            column_query = f"DESCRIBE {table.table_name}"
            columns_result = table.query_data(column_query)
            if columns_result:
                table_columns = {col[0] for col in columns_result}
        except Exception as e:
            logger.debug(f"Could not get table columns for {table.table_name}: {e}")
            # Fallback: assume all fields in data are valid
            table_columns = set()
            for record in data_list:
                table_columns.update(record.keys())

        # Normalize all new records for comparison
        normalized_data_list = [normalize_record_for_comparison(record) for record in data_list]

        # Build WHERE clause for primary keys to fetch existing records
        primary_key_conditions = []
        for record in normalized_data_list:
            pk_condition = " AND ".join([f"{pk} = '{record[pk]}'" for pk in primary_keys if pk in record])
            if pk_condition:
                primary_key_conditions.append(f"({pk_condition})")

        if not primary_key_conditions:
            # No primary keys found, treat all as new records
            for i, (original_record, normalized_record) in enumerate(zip(data_list, normalized_data_list)):
                robot_sn = normalized_record.get('robot_sn', normalized_record.get('sn', f'unknown_{i}'))
                unique_id = f"{robot_sn}_{i}"
                changes_detected[unique_id] = {
                    'robot_sn': robot_sn,
                    'primary_key_values': {pk: normalized_record.get(pk) for pk in primary_keys},
                    'change_type': 'new_record',
                    'changed_fields': list(normalized_record.keys()),
                    'old_values': {},
                    'new_values': original_record
                }
            return changes_detected

        # Query existing records
        where_clause = " OR ".join(primary_key_conditions)
        query = f"SELECT * FROM {table.table_name} WHERE {where_clause}"
        logger.debug(f"Query for existing records: {query}")

        existing_records_result = table.query_data(query)
        logger.debug(f"Found {len(existing_records_result) if existing_records_result else 0} existing records")

        # Handle different return types from query_data
        existing_records = []
        if existing_records_result:
            first_record = existing_records_result[0]

            if isinstance(first_record, tuple):
                # Get column names by querying table structure
                column_query = f"DESCRIBE {table.table_name}"
                try:
                    columns_result = table.query_data(column_query)
                    column_names = [col[0] for col in columns_result]
                except:
                    column_names = list(normalized_data_list[0].keys()) if normalized_data_list else []

                # Convert tuples to dictionaries
                for record_tuple in existing_records_result:
                    record_dict = {}
                    for i, value in enumerate(record_tuple):
                        if i < len(column_names):
                            record_dict[column_names[i]] = value
                    existing_records.append(record_dict)
            else:
                existing_records = existing_records_result

        # Normalize existing records for comparison
        normalized_existing_records = [normalize_record_for_comparison(record) for record in existing_records]

        # Convert existing records to dictionary keyed by primary key combination
        existing_dict = {}
        for original_record, normalized_record in zip(existing_records, normalized_existing_records):
            try:
                pk_values = []
                for pk in primary_keys:
                    value = normalized_record.get(pk)
                    pk_values.append(str(value) if value is not None else '')
                pk_key = tuple(pk_values)
                existing_dict[pk_key] = {
                    'original': original_record,
                    'normalized': normalized_record
                }
            except AttributeError as e:
                logger.warning(f"Error processing existing record: {normalized_record}, error: {e}")
                continue

        # Compare new data with existing data
        for i, (original_new_record, normalized_new_record) in enumerate(zip(data_list, normalized_data_list)):
            # Create primary key for new record
            pk_values = []
            for pk in primary_keys:
                value = normalized_new_record.get(pk)
                pk_values.append(str(value) if value is not None else '')
            pk_key = tuple(pk_values)

            # Get robot_sn for notification purposes
            robot_sn = normalized_new_record.get('robot_sn', normalized_new_record.get('sn', 'unknown'))

            # Create unique identifier using primary key values
            unique_id = "_".join(pk_values) if pk_values else f"record_{i}"

            # Extract primary key values for notification use
            primary_key_values = {pk: normalized_new_record.get(pk) for pk in primary_keys}

            if pk_key in existing_dict:
                # Record exists, check for changes
                existing_data = existing_dict[pk_key]
                existing_normalized = existing_data['normalized']
                existing_original = existing_data['original']

                changed_fields = []
                old_values = {}
                new_values = {}

                # Compare normalized values for change detection
                # SIMPLE FIX: Only check fields that exist in the table
                for field, new_value in normalized_new_record.items():
                    # Skip fields that don't exist in the database table
                    if table_columns and field not in table_columns:
                        continue
                    # skip robot_name comparison since it is designed to be changable in the database by user
                    if field == 'robot_name':
                        continue

                    old_value = existing_normalized.get(field)

                    if not values_are_equivalent(old_value, new_value, field):
                        if field not in primary_keys:
                            changed_fields.append(field)
                            old_values[field] = existing_original.get(field)
                            new_values[field] = original_new_record.get(field)

                if changed_fields:
                    full_new_values = {field: original_new_record.get(field) for field in original_new_record.keys() if field in table_columns}

                    changes_detected[unique_id] = {
                        'robot_sn': robot_sn,
                        'primary_key_values': primary_key_values,
                        'change_type': 'update',
                        'changed_fields': changed_fields,
                        'old_values': existing_original,
                        'new_values': full_new_values
                    }
                    logger.info(f"Detected update for record {unique_id} (robot {robot_sn}): {len(changed_fields)} fields changed")
            else:
                # New record
                # Only check fields that exist in the table
                new_values = {field: original_new_record.get(field) for field in original_new_record.keys() if field in table_columns}
                logger.info(f"Detected new record {unique_id} (robot {robot_sn})")
                changes_detected[unique_id] = {
                    'robot_sn': robot_sn,
                    'primary_key_values': primary_key_values,
                    'change_type': 'new_record',
                    'changed_fields': list(original_new_record.keys()),
                    'old_values': {},
                    'new_values': new_values
                }

    except Exception as e:
        logger.warning(f"Error detecting changes for {table.database_name}.{table.table_name}: {e}")
        # Fallback: treat all records as potentially changed
        for i, record in enumerate(data_list):
            robot_sn = record.get('robot_sn', record.get('sn', 'unknown'))
            unique_id = f"{robot_sn}_{i}"
            primary_key_values = {pk: record.get(pk) for pk in primary_keys}
            changes_detected[unique_id] = {
                'robot_sn': robot_sn,
                'primary_key_values': primary_key_values,
                'change_type': 'unknown',
                'changed_fields': list(record.keys()),
                'old_values': {},
                'new_values': record
            }

    return changes_detected

def values_are_equivalent(old_value, new_value, field_name: str = None) -> bool:
    """
    Compare two values for equivalence, handling Decimal vs float/int, None vs NULL vs NaN cases,
    and case-insensitive strings, with special handling for decimal fields
    """
    import math

    # Handle None/NULL/NaN cases
    old_is_null = old_value is None or (isinstance(old_value, float) and math.isnan(old_value))
    new_is_null = new_value is None or (isinstance(new_value, float) and math.isnan(new_value))

    if old_is_null and new_is_null:
        return True
    if old_is_null or new_is_null:
        # One is null/nan, the other should also be considered null-equivalent
        old_str = str(old_value) if old_value is not None else 'NULL'
        new_str = str(new_value) if new_value is not None else 'NULL'
        null_equivalents = ['NULL', 'None', 'nan', '', 'null']
        return any(old_str.lower() in null_equivalents and new_str.lower() in null_equivalents for _ in [1])

    # Special handling for decimal fields - normalize both values to same precision
    if field_name and field_name.lower() in DECIMAL_FIELDS_PRECISION:
        try:
            # Both values should already be normalized, but double-check
            normalized_old = normalize_decimal_value(old_value, field_name)
            normalized_new = normalize_decimal_value(new_value, field_name)

            # Compare the normalized values
            if isinstance(normalized_old, (int, float)) and isinstance(normalized_new, (int, float)):
                # Use a small epsilon for floating point comparison
                epsilon = 10 ** -(DECIMAL_FIELDS_PRECISION[field_name.lower()] + 1)
                return abs(normalized_old - normalized_new) < epsilon

        except (ValueError, TypeError) as e:
            logger.debug(f"Error in decimal comparison for field {field_name}: {e}")
            # Fall through to general comparison

    # Try numeric comparison first (handles Decimal vs float/int)
    try:
        from decimal import Decimal
        # Convert both to float for comparison if they're numeric
        if isinstance(old_value, (int, float, Decimal)) and isinstance(new_value, (int, float, Decimal)):
            # Check for NaN in numeric values
            old_float = float(old_value)
            new_float = float(new_value)
            if math.isnan(old_float) and math.isnan(new_float):
                return True
            if math.isnan(old_float) or math.isnan(new_float):
                return False
            return old_float == new_float
    except (ValueError, TypeError, ImportError):
        pass

    # String comparison with case-insensitive handling
    old_str = str(old_value).strip()
    new_str = str(new_value).strip()

    # Case-insensitive comparison
    if old_str.lower() == new_str.lower():
        return True

    # Handle nan string representations (case-insensitive)
    if old_str.lower() == 'nan' and new_str.lower() in ['none', 'null']:
        return True
    if new_str.lower() == 'nan' and old_str.lower() in ['none', 'null']:
        return True

    # Check for equivalent numeric strings (e.g., "100.00" vs "100.0")
    try:
        old_float = float(old_str)
        new_float = float(new_str)
        if math.isnan(old_float) and math.isnan(new_float):
            return True
        return old_float == new_float
    except (ValueError, TypeError):
        pass

    # Handle common string variations with case-insensitive and formatting differences
    # Remove common separators and compare
    old_clean = old_str.lower().replace('_', ' ').replace('-', ' ').strip()
    new_clean = new_str.lower().replace('_', ' ').replace('-', ' ').strip()

    if old_clean == new_clean:
        return True

    # Handle space variations (e.g., "Robot Clean" vs "robot_clean" vs "robot-clean")
    old_normalized = ''.join(old_clean.split())
    new_normalized = ''.join(new_clean.split())

    return old_normalized == new_normalized