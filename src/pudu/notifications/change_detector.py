import logging
from typing import Dict
from pudu.rds.rdsTable import RDSTable

# Configure logging
logger = logging.getLogger(__name__)

def detect_data_changes(table: RDSTable, data_list: list, primary_keys: list) -> Dict[str, Dict]:
    """
    Detect what data has actually changed compared to existing database records
    Returns a dictionary with unique record identifier as key and change details as value
    """
    if not data_list or not primary_keys:
        return {}

    changes_detected = {}

    try:
        # Build WHERE clause for primary keys to fetch existing records
        primary_key_conditions = []
        for record in data_list:
            pk_condition = " AND ".join([f"{pk} = '{record[pk]}'" for pk in primary_keys if pk in record])
            if pk_condition:
                primary_key_conditions.append(f"({pk_condition})")

        if not primary_key_conditions:
            # No primary keys found, treat all as new records
            logger.warning(f"No primary key conditions found. Primary keys: {primary_keys}")
            for i, record in enumerate(data_list):
                robot_id = record.get('robot_sn', record.get('sn', f'unknown_{i}'))
                unique_id = f"{robot_id}_{i}"  # Use index to ensure uniqueness
                changes_detected[unique_id] = {
                    'robot_id': robot_id,
                    'primary_key_values': {pk: record.get(pk) for pk in primary_keys},
                    'change_type': 'new_record',
                    'changed_fields': list(record.keys()),
                    'old_values': {},
                    'new_values': record
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
            # Check if first element is a tuple or dict
            first_record = existing_records_result[0]

            if isinstance(first_record, tuple):
                # Get column names by querying table structure
                column_query = f"DESCRIBE {table.table_name}"
                try:
                    columns_result = table.query_data(column_query)
                    column_names = [col[0] for col in columns_result]  # First element of each tuple is column name
                except:
                    # Fallback: use data_list keys as column names
                    column_names = list(data_list[0].keys()) if data_list else []

                # Convert tuples to dictionaries
                for record_tuple in existing_records_result:
                    record_dict = {}
                    for i, value in enumerate(record_tuple):
                        if i < len(column_names):
                            record_dict[column_names[i]] = value
                    existing_records.append(record_dict)
            else:
                # Already dictionaries
                existing_records = existing_records_result

        # Convert existing records to dictionary keyed by primary key combination
        existing_dict = {}
        for record in existing_records:
            try:
                # Create primary key tuple - handle both string and numeric values properly
                pk_values = []
                for pk in primary_keys:
                    value = record.get(pk)
                    # Convert to string but preserve the original type for comparison
                    pk_values.append(str(value) if value is not None else '')
                pk_key = tuple(pk_values)
                existing_dict[pk_key] = record
                logger.debug(f"Added existing record with PK: {pk_key}")
            except AttributeError as e:
                logger.warning(f"Error processing existing record: {record}, error: {e}")
                continue

        # Compare new data with existing data
        for i, new_record in enumerate(data_list):
            # Create primary key for new record
            pk_values = []
            for pk in primary_keys:
                value = new_record.get(pk)
                pk_values.append(str(value) if value is not None else '')
            pk_key = tuple(pk_values)

            # Get robot_id for notification purposes
            robot_id = new_record.get('robot_sn', new_record.get('sn', 'unknown'))

            # Create unique identifier using primary key values
            unique_id = "_".join(pk_values) if pk_values else f"record_{i}"

            # Extract primary key values for notification use
            primary_key_values = {pk: new_record.get(pk) for pk in primary_keys}

            logger.debug(f"Looking for new record PK: {pk_key} in existing records")
            logger.debug(f"Existing PKs: {list(existing_dict.keys())}")

            if pk_key in existing_dict:
                # Record exists, check for changes
                existing_record = existing_dict[pk_key]
                changed_fields = []
                old_values = {}
                new_values = {}

                # Compare ALL fields, including primary keys for notification purposes
                for field, new_value in new_record.items():
                    old_value = existing_record.get(field)

                    # Smart comparison that handles Decimal vs float/int equivalence
                    if not values_are_equivalent(old_value, new_value):
                        # Only add to changed_fields if it's NOT a primary key (for update logic)
                        if field not in primary_keys:
                            changed_fields.append(field)
                            old_values[field] = old_value
                            new_values[field] = new_value
                        logger.debug(f"Field '{field}' changed: {old_value} -> {new_value}")

                if changed_fields:
                    # Include primary key values AND all new values for notification context
                    full_new_values = new_record.copy()  # Include ALL fields including primary keys
                    full_old_values = {field: existing_record.get(field) for field in new_record.keys()}

                    changes_detected[unique_id] = {
                        'robot_id': robot_id,
                        'primary_key_values': primary_key_values,
                        'change_type': 'update',
                        'changed_fields': changed_fields,
                        'old_values': full_old_values,  # All fields for context
                        'new_values': full_new_values   # All fields including primary keys
                    }
                    logger.info(f"Detected update for record {unique_id} (robot {robot_id}): {len(changed_fields)} fields changed")
                else:
                    logger.info(f"No changes detected for record {unique_id} (robot {robot_id})")
            else:
                # New record - include all values including primary keys
                logger.info(f"Detected new record {unique_id} (robot {robot_id})")
                changes_detected[unique_id] = {
                    'robot_id': robot_id,
                    'primary_key_values': primary_key_values,
                    'change_type': 'new_record',
                    'changed_fields': list(new_record.keys()),
                    'old_values': {},
                    'new_values': new_record  # All fields including primary keys
                }

    except Exception as e:
        logger.warning(f"Error detecting changes for {table.database_name}.{table.table_name}: {e}")
        # Fallback: treat all records as potentially changed
        for i, record in enumerate(data_list):
            robot_id = record.get('robot_sn', record.get('sn', 'unknown'))
            unique_id = f"{robot_id}_{i}"
            primary_key_values = {pk: record.get(pk) for pk in primary_keys}
            changes_detected[unique_id] = {
                'robot_id': robot_id,
                'primary_key_values': primary_key_values,
                'change_type': 'unknown',
                'changed_fields': list(record.keys()),
                'old_values': {},
                'new_values': record
            }

    return changes_detected

def values_are_equivalent(old_value, new_value) -> bool:
    """
    Compare two values for equivalence, handling Decimal vs float/int, None vs NULL vs NaN cases, and case-insensitive strings
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
        null_equivalents = ['NULL', 'None', 'nan', '0', '0.0', '0.00', 'null']
        return any(old_str.lower() in null_equivalents and new_str.lower() in null_equivalents for _ in [1])

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