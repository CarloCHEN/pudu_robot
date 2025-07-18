import pymysql
import yaml
import os
import boto3
from botocore.exceptions import ClientError
import json
import logging

logger = logging.getLogger(__name__)

def get_secret(secret_name, region_name):
    """Get database credentials from AWS Secrets Manager"""
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
        raise e

    secret = get_secret_value_response['SecretString']
    secret = json.loads(secret)
    username = secret.get("username")
    password = secret.get("password")
    return username, password

def connect_rds_instance(config_file="credentials.yaml"):
    """Connect to RDS instance using credentials from config file"""
    # Load the YAML configuration file
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        db_config = config['database']

    username, password = get_secret(db_config['secret_name'], db_config['region_name'])
    return pymysql.connect(
        host=db_config['host'],
        user=username,
        password=password
    )

def use_database(cursor, db_name: str):
    """Switch to specified database"""
    if '-' in db_name:
        cursor.execute("USE `{}`;".format(db_name))
    else:
        cursor.execute("USE {};".format(db_name))

def batch_insert(cursor, table_name: str, data_list: list, primary_keys: list):
    """Insert or update multiple records"""
    if not data_list:
        return

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