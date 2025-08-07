import pymysql
import yaml
import os
import pandas as pd
import boto3
from botocore.exceptions import ClientError
import json


def connect_rds_instance(config_file="credentials.yaml"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(base_dir, "credentials.yaml")
    # Load the YAML configuration file
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        # Extract the database connection parameters
        db_config = config['database']
    username, password = get_secret(db_config['secret_name'], db_config['region_name'])
    return pymysql.connect(
        host=db_config['host'],
        user=username,
        password=password)

def get_secret(secret_name, region_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    # Parse the JSON string
    secret = json.loads(secret)

    # Access the username and password
    username = secret.get("username")
    password = secret.get("password")
    return username, password

def show_databases(cursor):
    cursor.execute("SHOW DATABASES")
    return cursor.fetchall()

def use_database(cursor, db_name: str):
    if '-' in db_name:
        cursor.execute("USE `{}`;".format(db_name))
    else:
        cursor.execute("USE {};".format(db_name))

def show_tables(cursor):
    cursor.execute("SHOW TABLES")
    return cursor.fetchall()

def check_if_db_exists(cursor, db_name: str):
    cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
    return cursor.fetchone() is not None

def check_if_table_exists(cursor, table_name: str):
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    return cursor.fetchone() is not None

def insert_data(cursor, table_name: str, data: dict, primary_keys: list = []):
    # Prepare the column names and values
    columns = ', '.join(data.keys())
    values = ', '.join([f"'{value}'" if value is not None else "NULL" for value in data.values()])

    # Prepare ON DUPLICATE KEY UPDATE clause if primary keys are provided
    if primary_keys:
        # Use all columns except primary keys for updating
        update_clause = ', '.join([f"{key}=VALUES({key})" for key in data.keys() if key not in primary_keys])
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values}) ON DUPLICATE KEY UPDATE {update_clause}"
    else:
        # No duplicate handling needed if no primary keys provided
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"

    # Execute the SQL statement
    cursor.execute(sql)
    cursor.connection.commit()

def batch_insert(cursor, table_name: str, data_list: list, primary_keys: list):
    # Prepare the column names
    columns = ', '.join(data_list[0].keys())

    # Prepare values as a bulk insert
    values = ", ".join([
        "(" + ", ".join([f"'{value}'" if value is not None else "NULL" for value in row.values()]) + ")"
        for row in data_list
    ])

    # Add ON DUPLICATE KEY UPDATE if primary keys are present
    if primary_keys:
        update_clause = ', '.join(
            [f"{key}=VALUES({key})" for key in data_list[0].keys() if key not in primary_keys]
        )
        sql = f"INSERT INTO {table_name} ({columns}) VALUES {values} ON DUPLICATE KEY UPDATE {update_clause}"
    else:
        sql = f"INSERT INTO {table_name} ({columns}) VALUES {values}"
    # Execute the SQL statement
    cursor.execute(sql)
    cursor.connection.commit()

def get_primary_key_column(cursor, table_name: str):
    """
    Automatically detect the primary key column name for a MySQL table.

    Returns:
        str: Primary key column name, or None if not found
    """
    try:
        cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = '{table_name}'
            AND CONSTRAINT_NAME = 'PRIMARY'
            AND TABLE_SCHEMA = DATABASE()
        """)
        result = cursor.fetchone()
        if result:
            return result[0]
    except:
        pass

    # Fallback: try common primary key names
    common_pk_names = ['id', 'ID', f'{table_name}_id']
    for pk_name in common_pk_names:
        try:
            cursor.execute(f"SELECT {pk_name} FROM {table_name} LIMIT 1")
            return pk_name
        except:
            continue

    return None

def batch_insert_with_ids(cursor, table_name: str, data_list: list, primary_keys: list = None):
    """
    Batch insert data and return primary keys matched to original data.
    The batch_insert_with_ids function will return IDs for ALL data passed to it, regardless of whether they were actually inserted, updated, or unchanged.

    Args:
        cursor: Database cursor
        table_name: Name of the table to insert into
        data_list: List of dictionaries containing data to insert
        primary_keys: List of column names that form unique constraints (for ON DUPLICATE KEY UPDATE)

    Returns:
        list of tuples: [(original_data_dict, unique_key_in_db), ...]
    """
    if not data_list:
        return []

    # Step 1: Get primary key column name
    pk_column = get_primary_key_column(cursor, table_name)
    if not pk_column:
        raise ValueError(f"Could not detect primary key column for table '{table_name}'")

    # Step 2: Perform batch insert using existing function
    batch_insert(cursor, table_name, data_list, primary_keys or [])

    # Step 3: Query back the primary keys
    if primary_keys:
        # Use unique constraints to find the records
        return _query_ids_by_unique_keys(cursor, table_name, data_list, primary_keys, pk_column)
    else:
        # For pure inserts, use lastrowid
        first_id = cursor.lastrowid
        results = []
        for i, data in enumerate(data_list):
            results.append((data, first_id + i))
        return results

def _query_ids_by_unique_keys(cursor, table_name: str, data_list: list, unique_keys: list, pk_column: str):
    """
    Query primary keys for records using their unique key constraints.
    """
    results = []

    # Build batch query to get all primary keys at once
    where_conditions = []

    def escape_value(value):
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            return f"'{value.replace(chr(39), chr(39)+chr(39))}'" # chr(39) == "'"
        else:
            return f"'{value}'"

    for data in data_list:
        record_conditions = []
        for key in unique_keys:
            if key in data:
                value = data[key]
                if value is None:
                    record_conditions.append(f"{key} IS NULL")
                else:
                    record_conditions.append(f"{key} = {escape_value(value)}")

        if record_conditions:
            where_conditions.append("(" + " AND ".join(record_conditions) + ")")

    if where_conditions:
        where_clause = " OR ".join(where_conditions)
        select_columns = [pk_column] + unique_keys
        query = f"SELECT {', '.join(select_columns)} FROM {table_name} WHERE {where_clause}"

        cursor.execute(query)
        db_results = cursor.fetchall()

        # Create mapping from unique key values to primary key
        pk_map = {}
        for row in db_results:
            pk_value = row[0]
            unique_values = row[1:]
            unique_tuple = tuple(unique_values)
            pk_map[unique_tuple] = pk_value

        # Match each original data record to its primary key
        for data in data_list:
            unique_tuple = tuple(data.get(key) for key in unique_keys)
            pk_value = pk_map.get(unique_tuple)
            results.append((data, pk_value))

    return results

def update_field_by_filters(cursor, table_name: str, field_name: str, new_value: str, filter_clause: str):
    """
    Update a specific field in a row, based on a unique identifier.

    :param cursor: Database cursor object
    :param table_name: The name of the table to update
    :param field_name: The name of the field to update
    :param new_value: The new value for the field
    :param filter_clause: The WHERE clause to identify the row to update
    """
    # Prepare the SQL query
    sql_query = f"UPDATE {table_name} SET {field_name} = %s WHERE {filter_clause}"

    # Execute the SQL command
    cursor.execute(sql_query, (new_value,))
    cursor.connection.commit()

def query_data(cursor, table_name: str):
    cursor.execute(f"SELECT * FROM {table_name}")
    return cursor.fetchall()

def query_with_script(cursor, query: str):
    cursor.execute(query)
    cursor.connection.commit()
    return cursor.fetchall()

def query_data_as_df(connection, table_name: str):
    return pd.read_sql_query(f"SELECT * FROM {table_name}", connection)

def query_with_script_as_df(connection, query: str):
    return pd.read_sql_query(query, connection)