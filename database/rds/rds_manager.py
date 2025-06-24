import pymysql
import yaml
import os
import pandas as pd
import boto3
from botocore.exceptions import ClientError
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class RDSManager:
    """Manages all interactions with the RDS database."""

    def __init__(self, config_dir: str):
        """
        Initializes the RDSManager.

        Args:
            config_dir: The path to the directory containing 'credentials.yaml'.
        """
        self.config_path = os.path.join(config_dir, "credentials.yaml")
        self.conn = self._connect()
        self.cursor = self.conn.cursor()

    def _get_secret(self, secret_name: str, region_name: str) -> Dict[str, str]:
        """Retrieves database credentials from AWS Secrets Manager."""
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager', region_name=region_name)
        try:
            get_secret_value_response = client.get_secret_value(SecretId=secret_name)
            secret = get_secret_value_response['SecretString']
            return json.loads(secret)
        except ClientError as e:
            logger.error(f"Could not retrieve secret from AWS Secrets Manager: {e}")
            raise

    def _connect(self) -> pymysql.connections.Connection:
        """Establishes a connection to the RDS instance."""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)['database']

            credentials = self._get_secret(config['secret_name'], config['region_name'])

            return pymysql.connect(
                host=config['host'],
                user=credentials.get("username"),
                password=credentials.get("password"),
                database=config.get('db_name'),
                cursorclass=pymysql.cursors.DictCursor  # Return rows as dictionaries
            )
        except FileNotFoundError:
            logger.error(f"RDS credentials file not found at: {self.config_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to RDS: {e}")
            raise

    def get_alert_targets(self) -> List[Dict]:
        """
        Get sensors/scores with alert functionality enabled.

        Returns:
            List of dictionaries containing alert target configurations
        """
        try:
            query = """
            SELECT
                mnt_sensor_alarm_setting.*,
                pro_sensor_info.sensor_type,
                'sensor' as source_type
            FROM mnt_sensor_alarm_setting
            JOIN pro_sensor_info
                ON pro_sensor_info.sensor_id = mnt_sensor_alarm_setting.sensor_id
            JOIN mnt_sensor_function_setting
                ON mnt_sensor_alarm_setting.sensor_id = mnt_sensor_function_setting.sensor_id
                AND mnt_sensor_alarm_setting.data_type = mnt_sensor_function_setting.data_type
            WHERE mnt_sensor_function_setting.open_alarm = 1
            ORDER BY mnt_sensor_alarm_setting.sensor_id, mnt_sensor_alarm_setting.data_type
            """

            result = self.query_data_as_df(query)
            return result.to_dict('records')

        except Exception as e:
            logger.error(f"Error getting alert targets: {e}")
            raise

    def query_data_as_df(self, query: str) -> pd.DataFrame:
        """
        Executes a query and returns the result as a pandas DataFrame.
        """
        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()

            if not results:
                return pd.DataFrame()

            # Create DataFrame from the results
            # Since we're using DictCursor, results is already a list of dictionaries
            return pd.DataFrame(results)

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def batch_insert(self, table_name: str, data_list: List[Dict[str, Any]], primary_keys: List[str]):
        """
        Inserts a batch of data into the specified table.
        """
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
        try:
            self.cursor.execute(sql)
            self.conn.commit()
            logger.info(f"Successfully saved {len(data_list)} alert results.")
        except Exception as e:
            logger.error(f"Failed to batch insert data: {e}")
            self.conn.rollback()

    def save_alert_results(self, table_name: str, alert_results: List[Dict],
                          primary_keys: List[str]):
        """
        Save alert results to the database.

        Args:
            table_name: Name of the alert table
            alert_results: List of alert dictionaries
            primary_keys: List of primary key column names
        """
        try:
            if not alert_results:
                return

            # Convert to DataFrame for easier processing
            df = pd.DataFrame(alert_results)

            # Handle timestamp formatting
            timestamp_columns = ['start_timestamp', 'end_timestamp']
            for col in timestamp_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])

            # Prepare data for insertion
            records = df.to_dict('records')

            self.batch_insert(table_name, records, primary_keys)

            logger.info(f"Successfully saved {len(alert_results)} alerts to {table_name}")

        except Exception as e:
            logger.error(f"Error saving alert results: {e}")
            raise

    def update_alert_start_timestamp(self, table_name: str, sensor_id: str,
                                    data_type: str, next_timestamp: datetime):
        """
        Update the next monitoring timestamp for a sensor/data_type combination.

        Args:
            table_name: Name of the alert setting table
            sensor_id: Sensor identifier
            data_type: Data type (e.g., 'temperature', 'humidity')
            next_timestamp: Next timestamp to start monitoring from
        """
        try:
            # Format timestamp for database
            if isinstance(next_timestamp, pd.Timestamp):
                next_timestamp = next_timestamp.to_pydatetime()

            formatted_timestamp = next_timestamp.strftime('%Y-%m-%d %H:%M:%S')

            # Update query
            query = f"""
            UPDATE {table_name}
            SET alarm_start_timestamp = '{formatted_timestamp}'
            WHERE sensor_id = '{sensor_id}' AND data_type = '{data_type}'
            """

            self.execute_query(query)
            logger.debug(f"Updated next timestamp for {sensor_id}_{data_type}: {formatted_timestamp}")

        except Exception as e:
            logger.error(f"Error updating alert start timestamp: {e}")
            raise

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("RDS connection closed.")