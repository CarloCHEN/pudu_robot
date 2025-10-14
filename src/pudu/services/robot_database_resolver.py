import logging
from typing import Dict, List, Optional
from pudu.rds.rdsTable import RDSDatabase

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
    """Service to resolve which database each robot belongs to based on tenant/project hierarchy"""

    def __init__(self, main_database_name: str):
        self.main_database_name = main_database_name
        self.main_db = None
        self._project_info_cache = {}
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
    def get_active_robot_types(self) -> set:
        """
        Get set of active robot types in current region's database

        Returns:
            Set of robot types (e.g., {'PUDU CC1', 'GAUSIUM'})
        """
        if not self.main_db:
            logger.info("Initializing database connection...")
            self._initialize_connection()

        self._ensure_connection()

        if not self.main_db:
            logger.error("No database connection available")
            return set()

        try:
            query = """
                SELECT DISTINCT robot_type
                FROM mnt_robots_management
                WHERE robot_type IS NOT NULL
            """

            results = self.main_db.query_data(query)

            robot_types = set()
            for result in results:
                if isinstance(result, tuple):
                    robot_type = result[0]
                elif isinstance(result, dict):
                    robot_type = result.get('robot_type')
                else:
                    continue

                if robot_type:
                    robot_types.add(robot_type)

            logger.info(f"Active robot types in database: {robot_types}")
            return robot_types

        except Exception as e:
            logger.error(f"Error getting active robot types: {e}")
            return set()

    @retry_db_operation(max_retries=3, base_delay=2)
    def get_robot_database_mapping(self, robot_sns: List[str] = None) -> Dict[str, str]:
        """
        Get mapping of robot_sn to database name

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

        try:
            # Build query to get robot to project mapping from ry-vue's mnt_robots_management
            base_query = """
                SELECT mrm.robot_sn, mrm.project_id, ppi.project_name
                FROM mnt_robots_management mrm
                JOIN pro_project_info ppi ON mrm.project_id = ppi.project_id
                WHERE mrm.project_id IS NOT NULL
                AND ppi.project_name IS NOT NULL
            """

            if robot_sns:
                # Filter for specific robots
                robot_list = "', '".join(robot_sns)
                query = f"{base_query} AND mrm.robot_sn IN ('{robot_list}')"
            else:
                query = base_query

            #logger.info(f"Resolving robot database mappings with query: {query}")
            results = self.main_db.query_data(query)

            robot_to_database = {}
            for result in results:
                if isinstance(result, tuple) and len(result) >= 3:
                    robot_sn, project_id, project_name = result[0], result[1], result[2]
                elif isinstance(result, dict):
                    robot_sn = result.get('robot_sn')
                    project_id = result.get('project_id')
                    project_name = result.get('project_name')
                else:
                    continue

                if robot_sn and project_name:
                    robot_to_database[robot_sn] = project_name
                    # Cache project info
                    if project_id:
                        self._project_info_cache[project_id] = project_name

            #logger.info(f"Resolved {len(robot_to_database)} robot database mappings")
            return robot_to_database

        except Exception as e:
            logger.error(f"Error resolving robot database mappings: {e}")
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
            if self.main_db:
                self.main_db.close()
        except Exception as e:
            logger.warning(f"Error closing main database connection: {e}")