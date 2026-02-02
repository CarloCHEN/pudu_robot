import logging
import sys
import traceback
from typing import Dict, List, Optional
from rds.rdsTable import RDSDatabase

logger = logging.getLogger(__name__)

import time
from functools import wraps

def retry_db_operation(max_retries=3, base_delay=1, exponential_backoff=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                        raise e

                    delay = base_delay * (2 ** attempt if exponential_backoff else 1)
                    logger.warning(f"Database operation failed (attempt {attempt + 1}), retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class RobotDatabaseResolver:
    def __init__(self, main_database_name: str):
        self.main_database_name = main_database_name
        self.main_db = None
        self._connection_pool = {}
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes

    def _initialize_connection(self):
        """Initialize database connection with retry logic"""
        try:
            self.main_db = RDSDatabase(connection_config="credentials.yaml", database_name=self.main_database_name)
            logger.info(f"Database connection initialized: {self.main_database_name}")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            self.main_db = None

    def _ensure_connection(self):
        """Ensure database connection is healthy"""
        current_time = time.time()

        # Check health periodically
        if current_time - self._last_health_check > self._health_check_interval:
            if not self._check_connection_health():
                logger.warning("Database connection unhealthy, reinitializing...")
                self._initialize_connection()
            self._last_health_check = current_time

    def _check_connection_health(self) -> bool:
        """Check if database connection is healthy"""
        if not self.main_db:
            return False

        try:
            # Simple ping query
            self.main_db.query_data("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False

    @retry_db_operation(max_retries=3, base_delay=2)
    def get_robot_database_mapping(self, robot_sns: List[str] = None) -> Dict[str, str]:
        """
        Get mapping of robot_sn to database name with detailed logging.
        Uses sys_tenant.database_name joined by tenant_id.

        Args:
            robot_sns: List of robot serial numbers to resolve. If None, resolves all robots.

        Returns:
            Dict mapping robot_sn -> database_name
        """
        step = "init"

        if not self.main_db:
            logger.info("Initializing database connection...")
            self._initialize_connection()

        self._ensure_connection()

        if not self.main_db:
            logger.error("No database connection available")
            return {}

        # Cache tenant->db to avoid repeated lookups
        if not hasattr(self, "_tenant_db_cache") or not isinstance(getattr(self, "_tenant_db_cache"), dict):
            self._tenant_db_cache = {}

        try:
            # Step 1: Validate inputs
            step = "input_validation"
            if robot_sns is not None:
                if not isinstance(robot_sns, list):
                    logger.error(f"[ERROR] robot_sns is not a list: {type(robot_sns)}")
                    return {}

                for i, sn in enumerate(robot_sns):
                    if not isinstance(sn, str) or not sn.strip():
                        logger.error(f"[ERROR] Invalid robot_sn at index {i}: {sn} (type: {type(sn)})")
                        return {}
            else:
                logger.info("robot_sns is None, will fetch all robots")

            # Step 2: Test database connection
            step = "database_connection_test"
            try:
                test_result = self.main_db.query_data("SELECT 1 as test_value")
                logger.debug(f"DB test result: {test_result[:1] if test_result else test_result}")
            except Exception as conn_error:
                logger.error(f"Database connection failed: {conn_error}")
                logger.error(f"Connection error type: {type(conn_error)}")
                logger.error(f"Connection error traceback: {traceback.format_exc()}")
                return {}

            # Step 3: Check if tables exist (simple smoke queries)
            step = "table_existence_check"
            try:
                self.main_db.query_data("SELECT 1 FROM mnt_robots_management LIMIT 1")
                self.main_db.query_data("SELECT 1 FROM sys_tenant LIMIT 1")
            except Exception as table_error:
                logger.error(f"Table existence check failed: {table_error}")
                logger.error(f"Table error type: {type(table_error)}")
                logger.error(f"Table error traceback: {traceback.format_exc()}")
                return {}

            # Step 4: Build and validate query
            step = "query_building"
            base_query = """
                SELECT
                    mrm.robot_sn,
                    mrm.tenant_id,
                    st.database_name
                FROM mnt_robots_management mrm
                LEFT JOIN sys_tenant st
                    ON mrm.tenant_id = st.tenant_id
                WHERE mrm.tenant_id IS NOT NULL
                  AND st.database_name IS NOT NULL
                  AND st.database_name <> ''
            """

            if robot_sns:
                # Sanitize robot_sns to prevent SQL injection (escape single quotes)
                sanitized_sns = [sn.strip().replace("'", "''") for sn in robot_sns if sn and sn.strip()]
                if not sanitized_sns:
                    logger.warning("robot_sns provided but all values were empty after sanitization")
                    query = base_query
                else:
                    robot_list = "', '".join(sanitized_sns)
                    query = f"{base_query} AND mrm.robot_sn IN ('{robot_list}')"
            else:
                query = base_query

            # Step 5: Execute main query
            step = "main_query_execution"
            try:
                results = self.main_db.query_data(query)

                if results:
                    logger.info(f"First result sample: {results[0]}")
                    logger.info(f"First result type: {type(results[0])}")
                    logger.info(f"Query returned {len(results)} rows")
                else:
                    logger.warning("Query returned no results")

            except Exception as query_error:
                logger.error(f"Main query execution failed: {query_error}")
                logger.error(f"Query error type: {type(query_error)}")
                logger.error(f"Query error args: {query_error.args if hasattr(query_error, 'args') else 'No args'}")
                logger.error(f"Query error traceback: {traceback.format_exc()}")

                if hasattr(query_error, "errno"):
                    logger.error(f"MySQL errno: {query_error.errno}")
                if hasattr(query_error, "msg"):
                    logger.error(f"MySQL msg: {query_error.msg}")
                if hasattr(query_error, "sqlstate"):
                    logger.error(f"MySQL sqlstate: {query_error.sqlstate}")

                return {}

            # Step 6: Process results
            step = "result_processing"
            if not results:
                logger.warning("No results to process, returning empty dict")
                return {}

            robot_to_database: Dict[str, str] = {}
            processed_count = 0
            error_count = 0

            for i, result in enumerate(results):
                try:
                    logger.debug(f"Processing result {i}: {result} (type: {type(result)})")

                    robot_sn = None
                    tenant_id = None
                    database_name = None

                    if isinstance(result, tuple) and len(result) >= 3:
                        robot_sn, tenant_id, database_name = result[0], result[1], result[2]
                    elif isinstance(result, dict):
                        robot_sn = result.get("robot_sn")
                        tenant_id = result.get("tenant_id")
                        database_name = result.get("database_name")
                    else:
                        logger.warning(f"Unexpected result format at index {i}: {result} (type: {type(result)})")
                        error_count += 1
                        continue

                    if robot_sn and database_name and str(database_name).strip():
                        robot_sn_str = str(robot_sn).strip()
                        db_name_str = str(database_name).strip()

                        robot_to_database[robot_sn_str] = db_name_str
                        processed_count += 1
                        logger.debug(f"✓ Added mapping: {robot_sn_str} -> {db_name_str}")

                        # Cache tenant info
                        if tenant_id is not None:
                            self._tenant_db_cache[tenant_id] = db_name_str
                            logger.debug(f"✓ Cached tenant db: {tenant_id} -> {db_name_str}")
                    else:
                        logger.warning(
                            f"⚠ Missing required data in result {i}: "
                            f"robot_sn='{robot_sn}', tenant_id='{tenant_id}', database_name='{database_name}'"
                        )
                        error_count += 1

                except Exception as row_error:
                    logger.error(f"✗ Error processing result row {i}: {row_error}")
                    logger.error(f"Row error type: {type(row_error)}")
                    logger.error(f"Row error traceback: {traceback.format_exc()}")
                    error_count += 1
                    continue

            logger.info(
                f"Processed {processed_count} rows; {error_count} rows had issues. "
                f"Returning {len(robot_to_database)} robot database mappings."
            )
            if robot_to_database:
                logger.info(f"Sample mappings: {dict(list(robot_to_database.items())[:3])}")

            return robot_to_database

        except Exception as e:
            logger.error(f"[CRITICAL ERROR] Exception in step '{step}': {e}")
            logger.error(f"[CRITICAL ERROR] Error type: {type(e)}")
            logger.error(f"[CRITICAL ERROR] Error args: {e.args if hasattr(e, 'args') else 'No args'}")

            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            for line_num, line in enumerate(tb_lines):
                logger.error(f"[TRACEBACK {line_num}] {line.strip()}")

            frame = sys._getframe()
            logger.error(f"[FRAME INFO] Function: {frame.f_code.co_name}")
            logger.error(f"[FRAME INFO] File: {frame.f_code.co_filename}")
            logger.error(f"[FRAME INFO] Line: {frame.f_lineno}")

            try:
                local_vars = {
                    k: str(v)[:100] for k, v in frame.f_locals.items()
                    if not k.startswith("self") and not callable(v)
                }
                logger.error(f"[FRAME LOCALS] {local_vars}")
            except Exception as local_error:
                logger.error(f"[FRAME LOCALS] Could not log locals: {local_error}")

            return {}

    def get_database_for_robot(self, robot_sn: str) -> Optional[str]:
        """Get database name for a specific robot"""
        mapping = self.get_robot_database_mapping([robot_sn])
        return mapping.get(robot_sn)

    def group_robots_by_database(self, robot_sns: List[str]) -> Dict[str, List[str]]:
        """
        Group robots by their target database

        Returns:
            Dict mapping database_name to list of robot_sns
        """
        robot_to_db = self.get_robot_database_mapping(robot_sns)

        db_to_robots = {}
        for robot_sn, database_name in robot_to_db.items():
            if database_name not in db_to_robots:
                db_to_robots[database_name] = []
            db_to_robots[database_name].append(robot_sn)

        return db_to_robots

    @retry_db_operation(max_retries=3, base_delay=2)
    def get_all_project_databases(self) -> List[str]:
        """Get list of all project database names"""
        if not self.main_db:
            logger.info("Initializing database connection...")
            self._initialize_connection()

        self._ensure_connection()

        try:
            query = "SELECT DISTINCT database_name FROM sys_tenant"
            results = self.main_db.query_data(query)

            databases = []
            for result in results:
                if isinstance(result, tuple):
                    database_name = result[0]
                elif isinstance(result, dict):
                    database_name = result.get('database_name')
                else:
                    continue

                if database_name:
                    databases.append(database_name)

            return databases

        except Exception as e:
            logger.error(f"Error getting project databases: {e}")
            return []

    def close(self):
        """Close database connection"""
        try:
            self.main_db.close()
        except Exception as e:
            logger.warning(f"Error closing main database connection: {e}")