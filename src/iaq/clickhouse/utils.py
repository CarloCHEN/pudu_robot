import yaml
import os
import clickhouse_connect

def connect_ch_instance(config_file="credentials.yaml"):
    """
    Connects to the ClickHouse database instance.

    :param config_file: Path to the YAML configuration file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(base_dir, "credentials.yaml")
    # Load the YAML configuration file
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        # Extract the database connection parameters
        db_config = config['database']
    client = clickhouse_connect.get_client(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        secure=True
    )
    return client


def query_data_as_df(client, query):
    """
    Queries the ClickHouse database and returns the result as a Pandas DataFrame.

    :param client: ClickHouse client object.
    :param query: Query string.
    """
    return client.query_df(query)