import logging
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
        Get mapping of robot_sn to database name with detailed logging

        Args:
            robot_sns: List of robot serial numbers to resolve. If None, resolves all robots.

        Returns:
            Dict mapping robot_sn to database_name
        """
        if not self.main_db:
            logger.info("Initializing database connection...")
            self._initialize_connection()

        self._ensure_connection()

        if not self.main_db:
            logger.error("No database connection available")
            return {}

        self._project_info_cache = {}  # Cache for project info to avoid repeated queries

        try:
            logger.info(f"[STEP 1] Starting get_robot_database_mapping with robot_sns: {robot_sns}")

            # Step 1: Validate inputs
            step = "input_validation"
            if robot_sns is not None:
                logger.info(f"[STEP 2] Validating robot_sns list with {len(robot_sns)} items")
                if not isinstance(robot_sns, list):
                    logger.error(f"[ERROR] robot_sns is not a list: {type(robot_sns)}")
                    return {}

                for i, sn in enumerate(robot_sns):
                    if not isinstance(sn, str) or not sn.strip():
                        logger.error(f"[ERROR] Invalid robot_sn at index {i}: {sn} (type: {type(sn)})")
                        return {}
                logger.info(f"[STEP 2] ✓ Input validation passed")
            else:
                logger.info(f"[STEP 2] ✓ robot_sns is None, will fetch all robots")

            # Step 2: Test database connection
            step = "database_connection_test"
            logger.info(f"[STEP 3] Testing database connection...")
            try:
                connection_test = "SELECT 1 as test_value"
                logger.info(f"[STEP 3] Executing connection test query: {connection_test}")
                test_result = self.main_db.query_data(connection_test)
                logger.info(f"[STEP 3] ✓ Connection test result: {test_result}")
            except Exception as conn_error:
                logger.error(f"[STEP 3] ✗ Database connection failed: {conn_error}")
                logger.error(f"[STEP 3] Connection error type: {type(conn_error)}")
                logger.error(f"[STEP 3] Connection error traceback: {traceback.format_exc()}")
                return {}

            # Step 3: Check if tables exist
            step = "table_existence_check"
            logger.info(f"[STEP 4] Checking if required tables exist...")
            try:
                # Check mnt_robots_management table
                check_mrm = "SELECT COUNT(*) as count FROM mnt_robots_management LIMIT 1"
                logger.info(f"[STEP 4] Checking mnt_robots_management table: {check_mrm}")
                mrm_result = self.main_db.query_data(check_mrm)
                logger.info(f"[STEP 4] mnt_robots_management check result: {mrm_result}")

                # Check pro_project_info table
                check_ppi = "SELECT COUNT(*) as count FROM pro_project_info LIMIT 1"
                logger.info(f"[STEP 4] Checking pro_project_info table: {check_ppi}")
                ppi_result = self.main_db.query_data(check_ppi)
                logger.info(f"[STEP 4] pro_project_info check result: {ppi_result}")
                logger.info(f"[STEP 4] ✓ Both tables exist and are accessible")

            except Exception as table_error:
                logger.error(f"[STEP 4] ✗ Table existence check failed: {table_error}")
                logger.error(f"[STEP 4] Table error type: {type(table_error)}")
                logger.error(f"[STEP 4] Table error traceback: {traceback.format_exc()}")
                return {}

            # Step 4: Build and validate query
            step = "query_building"
            logger.info(f"[STEP 5] Building main query...")

            base_query = """
                SELECT mrm.robot_sn, mrm.project_id, ppi.project_name
                FROM mnt_robots_management mrm
                JOIN pro_project_info ppi ON mrm.project_id = ppi.project_id
                WHERE mrm.project_id IS NOT NULL
                AND ppi.project_name IS NOT NULL
            """
            logger.info(f"[STEP 5] Base query built: {base_query.strip()}")

            if robot_sns:
                logger.info(f"[STEP 5] Adding robot_sn filter for {len(robot_sns)} robots")
                # Sanitize robot_sns to prevent SQL injection
                sanitized_sns = []
                for sn in robot_sns:
                    sanitized_sn = sn.replace("'", "''")  # Escape single quotes
                    sanitized_sns.append(sanitized_sn)
                    logger.debug(f"[STEP 5] Sanitized '{sn}' -> '{sanitized_sn}'")

                robot_list = "', '".join(sanitized_sns)
                query = f"{base_query} AND mrm.robot_sn IN ('{robot_list}')"
                logger.info(f"[STEP 5] Robot filter added. Robot list: [{robot_list}]")
            else:
                query = base_query
                logger.info(f"[STEP 5] No robot filter applied")

            logger.info(f"[STEP 5] ✓ Final query: {query}")

            # Step 5: Execute main query
            step = "main_query_execution"
            logger.info(f"[STEP 6] Executing main query...")
            try:
                logger.info(f"[STEP 6] About to call self.main_db.query_data() with query")
                results = self.main_db.query_data(query)
                logger.info(f"[STEP 6] ✓ Query executed successfully")
                logger.info(f"[STEP 6] Raw results type: {type(results)}")
                logger.info(f"[STEP 6] Raw results length: {len(results) if results else 0}")

                if results:
                    logger.info(f"[STEP 6] First result sample: {results[0] if len(results) > 0 else 'None'}")
                    logger.info(f"[STEP 6] First result type: {type(results[0]) if len(results) > 0 else 'None'}")
                else:
                    logger.warning(f"[STEP 6] ⚠ Query returned no results")

            except Exception as query_error:
                logger.error(f"[STEP 6] ✗ Main query execution failed: {query_error}")
                logger.error(f"[STEP 6] Query error type: {type(query_error)}")
                logger.error(f"[STEP 6] Query error args: {query_error.args if hasattr(query_error, 'args') else 'No args'}")
                logger.error(f"[STEP 6] Query error traceback: {traceback.format_exc()}")

                # Try to get more specific error info
                if hasattr(query_error, 'errno'):
                    logger.error(f"[STEP 6] MySQL errno: {query_error.errno}")
                if hasattr(query_error, 'msg'):
                    logger.error(f"[STEP 6] MySQL msg: {query_error.msg}")
                if hasattr(query_error, 'sqlstate'):
                    logger.error(f"[STEP 6] MySQL sqlstate: {query_error.sqlstate}")

                return {}

            # Step 6: Process results
            step = "result_processing"
            logger.info(f"[STEP 7] Processing query results...")

            if not results:
                logger.warning(f"[STEP 7] No results to process, returning empty dict")
                return {}

            robot_to_database = {}
            processed_count = 0
            error_count = 0

            for i, result in enumerate(results):
                try:
                    logger.debug(f"[STEP 7] Processing result {i}: {result} (type: {type(result)})")

                    robot_sn = None
                    project_id = None
                    project_name = None

                    if isinstance(result, tuple) and len(result) >= 3:
                        robot_sn, project_id, project_name = result[0], result[1], result[2]
                        logger.debug(f"[STEP 7] Extracted from tuple - robot_sn: {robot_sn}, project_id: {project_id}, project_name: {project_name}")
                    elif isinstance(result, dict):
                        robot_sn = result.get('robot_sn')
                        project_id = result.get('project_id')
                        project_name = result.get('project_name')
                        logger.debug(f"[STEP 7] Extracted from dict - robot_sn: {robot_sn}, project_id: {project_id}, project_name: {project_name}")
                    else:
                        logger.warning(f"[STEP 7] Unexpected result format at index {i}: {result} (type: {type(result)})")
                        error_count += 1
                        continue

                    if robot_sn and project_name:
                        robot_to_database[robot_sn] = project_name
                        processed_count += 1
                        logger.debug(f"[STEP 7] ✓ Added mapping: {robot_sn} -> {project_name}")

                        # Cache project info
                        if project_id:
                            self._project_info_cache[project_id] = project_name
                            logger.debug(f"[STEP 7] ✓ Cached project info: {project_id} -> {project_name}")
                    else:
                        logger.warning(f"[STEP 7] ⚠ Missing required data in result {i}: robot_sn='{robot_sn}', project_name='{project_name}'")
                        error_count += 1

                except Exception as row_error:
                    logger.error(f"[STEP 7] ✗ Error processing result row {i}: {row_error}")
                    logger.error(f"[STEP 7] Row error type: {type(row_error)}")
                    logger.error(f"[STEP 7] Row error traceback: {traceback.format_exc()}")
                    error_count += 1
                    continue

            logger.info(f"[STEP 7] ✓ Result processing completed:")
            logger.info(f"[STEP 7]   - Total results: {len(results)}")
            logger.info(f"[STEP 7]   - Successfully processed: {processed_count}")
            logger.info(f"[STEP 7]   - Errors encountered: {error_count}")
            logger.info(f"[STEP 7]   - Final mapping count: {len(robot_to_database)}")

            # Step 7: Return results
            step = "return_results"
            logger.info(f"[STEP 8] Returning {len(robot_to_database)} robot database mappings")
            if robot_to_database:
                logger.info(f"[STEP 8] Sample mappings: {dict(list(robot_to_database.items())[:3])}")

            return robot_to_database

        except Exception as e:
            # Enhanced error logging
            logger.error(f"[CRITICAL ERROR] Exception in step '{step}': {e}")
            logger.error(f"[CRITICAL ERROR] Error type: {type(e)}")
            logger.error(f"[CRITICAL ERROR] Error args: {e.args if hasattr(e, 'args') else 'No args'}")

            # Get detailed traceback info
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(f"[CRITICAL ERROR] Exception type: {exc_type}")
            logger.error(f"[CRITICAL ERROR] Exception value: {exc_value}")

            # Log full traceback with line numbers
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            for line_num, line in enumerate(tb_lines):
                logger.error(f"[TRACEBACK {line_num}] {line.strip()}")

            # Log current frame info
            frame = sys._getframe()
            logger.error(f"[FRAME INFO] Function: {frame.f_code.co_name}")
            logger.error(f"[FRAME INFO] File: {frame.f_code.co_filename}")
            logger.error(f"[FRAME INFO] Line: {frame.f_lineno}")

            # Log local variables in current frame (be careful with sensitive data)
            try:
                local_vars = {k: str(v)[:100] for k, v in frame.f_locals.items()
                             if not k.startswith('self') and not callable(v)}
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
            query = "SELECT DISTINCT project_name FROM pro_project_info"
            results = self.main_db.query_data(query)

            databases = []
            for result in results:
                if isinstance(result, tuple):
                    project_name = result[0]
                elif isinstance(result, dict):
                    project_name = result.get('project_name')
                else:
                    continue

                if project_name:
                    databases.append(project_name)

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