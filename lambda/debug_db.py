# Create a debug script to test database access
# Save this as debug_db.py and run it locally

import sys
import os

# Add path for local testing
sys.path.insert(0, '../src')

from pudu.rds.rdsTable import RDSDatabase
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_database_access():
    """Test database access and permissions"""

    databases_to_test = ["ry-vue", "foxx_irvine_office_test"]

    for db_name in databases_to_test:
        print(f"\n{'='*50}")
        print(f"Testing database: {db_name}")
        print(f"{'='*50}")

        try:
            # Initialize database connection
            database = RDSDatabase(connection_config="credentials.yaml", database_name=db_name)
            print(f"✅ Successfully connected to {db_name}")

            # Test 1: Show databases
            try:
                databases = database.show_databases()
                print(f"✅ Can list databases: {len(databases)} found")
            except Exception as e:
                print(f"❌ Cannot list databases: {e}")


            # Test 3: Check specific table
            table_name = "mnt_robots_locations"
            try:
                query = f"SHOW TABLES LIKE '{table_name}'"
                result = database.query_data(query)
                if result:
                    print(f"✅ Table {table_name} exists")
                else:
                    print(f"❌ Table {table_name} does NOT exist")
            except Exception as e:
                print(f"❌ Error checking table {table_name}: {e}")

            # Test 4: Try to select from table
            try:
                query = f"SELECT 1 FROM {table_name} LIMIT 1"
                result = database.query_data(query)
                print(f"✅ Can query {table_name}: {result}")
            except Exception as e:
                print(f"❌ Cannot query {table_name}: {e}")

            # Test 5: Check user permissions
            try:
                query = "SELECT USER(), CURRENT_USER()"
                result = database.query_data(query)
                print(f"✅ Current user: {result}")
            except Exception as e:
                print(f"❌ Cannot get user info: {e}")

            # Test 6: Check grants
            try:
                query = "SHOW GRANTS"
                result = database.query_data(query)
                print(f"✅ User permissions:")
                for grant in result:
                    print(f"   - {grant[0]}")
            except Exception as e:
                print(f"❌ Cannot show grants: {e}")

            database.close()

        except Exception as e:
            print(f"❌ Failed to connect to {db_name}: {e}")

if __name__ == "__main__":
    test_database_access()# Create a debug script to test database access
# Save this as debug_db.py and run it locally

import sys
import os

# Add path for local testing
sys.path.insert(0, '../src')

from pudu.rds.rdsTable import RDSDatabase
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_database_access():
    """Test database access and permissions"""

    databases_to_test = ["ry-vue", "foxx_irvine_office_test"]

    for db_name in databases_to_test:
        print(f"\n{'='*50}")
        print(f"Testing database: {db_name}")
        print(f"{'='*50}")

        try:
            # Initialize database connection
            database = RDSDatabase(connection_config="credentials.yaml", database_name=db_name)
            print(f"✅ Successfully connected to {db_name}")

            # Test 1: Show databases
            try:
                databases = database.show_databases()
                print(f"✅ Can list databases: {len(databases)} found")
            except Exception as e:
                print(f"❌ Cannot list databases: {e}")

            # Test 2: Show tables
            try:
                tables = database.show_tables()
                print(f"✅ Can list tables in {db_name}: {len(tables)} found")
                for table in tables[:5]:  # Show first 5 tables
                    print(f"   - {table[0]}")
            except Exception as e:
                print(f"❌ Cannot list tables: {e}")

            # Test 3: Check specific table
            table_name = "mnt_robots_locations"
            try:
                query = f"SHOW TABLES LIKE '{table_name}'"
                result = database.query_data(query)
                if result:
                    print(f"✅ Table {table_name} exists")
                else:
                    print(f"❌ Table {table_name} does NOT exist")
            except Exception as e:
                print(f"❌ Error checking table {table_name}: {e}")

            # Test 4: Try to select from table
            try:
                query = f"SELECT 1 FROM {table_name} LIMIT 1"
                result = database.query_data(query)
                print(f"✅ Can query {table_name}: {result}")
            except Exception as e:
                print(f"❌ Cannot query {table_name}: {e}")

            # Test 5: Check user permissions
            try:
                query = "SELECT USER(), CURRENT_USER()"
                result = database.query_data(query)
                print(f"✅ Current user: {result}")
            except Exception as e:
                print(f"❌ Cannot get user info: {e}")

            # Test 6: Check grants
            try:
                query = "SHOW GRANTS"
                result = database.query_data(query)
                print(f"✅ User permissions:")
                for grant in result:
                    print(f"   - {grant[0]}")
            except Exception as e:
                print(f"❌ Cannot show grants: {e}")

            database.close()

        except Exception as e:
            print(f"❌ Failed to connect to {db_name}: {e}")

if __name__ == "__main__":
    test_database_access()