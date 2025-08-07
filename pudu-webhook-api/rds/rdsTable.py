from .utils import *
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import warnings


class RDSDatabase:
    def __init__(self, connection_config, database_name):
        self.connection_config = connection_config
        self.db = connect_rds_instance(config_file=self.connection_config)
        self.cursor = self.db.cursor()
        self.database_name = database_name
        self.use_db(self.database_name)

    def use_db(self, db_name: str):
        if not check_if_db_exists(self.cursor, db_name):
            raise ValueError(f"Database {db_name} does not exist.")
        use_database(self.cursor, db_name)

    def show_databases(self):
        return show_databases(self.cursor)

    def show_tables(self):
        return show_tables(self.cursor)

    def query_data(self, query: str):
        return query_with_script(self.cursor, query)

    def query_data_as_df(self, query: str): #deprecated - will cause pandas warnings
        return query_with_script_as_df(self.db, query)

    def execute_query(self, query: str):
        """
        Execute query using SQLAlchemy engine to avoid pandas warnings
        """
        # Create SQLAlchemy engine on-demand
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(base_dir, "credentials.yaml")

        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
            db_config = config['database']

        from .utils import get_secret
        username, password = get_secret(db_config['secret_name'], db_config['region_name'])

        # Use the clean database name (without backticks) for connection string
        clean_db_name = self.database_name.strip('`')

        # Create connection string with database
        connection_string = f"mysql+pymysql://{username}:{password}@{db_config['host']}/{clean_db_name}"

        # Suppress pandas warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

            try:
                # Create engine with proper configuration
                engine = create_engine(
                    connection_string,
                    poolclass=NullPool,
                    echo=False,
                    future=True  # Use SQLAlchemy 2.0 style
                )

                # Execute query using pandas with the engine
                result = pd.read_sql_query(text(query), engine)
                return result

            except Exception as e:
                # If SQLAlchemy approach fails, fall back to original method
                return self.query_data_as_df(query)

            finally:
                if 'engine' in locals():
                    engine.dispose()

    def close(self):
        self.cursor.close()
        self.db.close()


class RDSTable(RDSDatabase):
    def __init__(self, connection_config, database_name, table_name, fields, primary_keys=None):
        self.connection_config = connection_config
        self.database_name = database_name
        self.db = connect_rds_instance(config_file=self.connection_config)
        self.cursor = self.db.cursor()
        self.table_name = table_name
        self.fields = fields
        self.primary_keys = primary_keys
        self.use_db(self.database_name)
        if not check_if_table_exists(self.cursor, self.table_name):
            raise ValueError(f"Table {self.table_name} does not exist.")

    def insert_data(self, data: dict):
        insert_data(self.cursor, self.table_name, data, primary_keys=self.primary_keys)

    def batch_insert(self, data_list: list):
        batch_insert(self.cursor, self.table_name, data_list, primary_keys=self.primary_keys)

    def batch_insert_with_ids(self, data_list: list):
        """
        Batch insert data and return primary keys matched to original data.

        Returns:
            list of tuples: [(original_data_dict, auto_generated_primary_key), ...]
        """
        return batch_insert_with_ids(self.cursor, self.table_name, data_list, self.primary_keys)

    def query_data(self, query: str = None):
        if query:
            data_tuples = query_with_script(self.cursor, query)
        else:
            data_tuples = query_data(self.cursor, self.table_name)
        if self.fields:
            # according to the schema, the order of the fields is the same as the order of the values in the tuple
            return [dict(zip(self.fields.keys(), data)) for data in data_tuples]
        return data_tuples

    def query_data_as_df(self, query: str = None):
        if query:
            return query_with_script_as_df(self.db, query)
        return query_data_as_df(self.db, self.table_name)

    def close(self):
        self.cursor.close()
        self.db.close()

    def update_field_by_filters(self, field_name: str, new_value: str, filters: dict):
        """
        Update a specific field in a row, based on a unique identifier.

        :param field_name: The field to update
        :param new_value: The new value for the field
        :param filters: A dictionary of column-value pairs to filter the rows
        """
        filter_clause = ' AND '.join([f"{key} = '{value}'" for key, value in filters.items()])
        update_field_by_filters(self.cursor, self.table_name, field_name, new_value, filter_clause)