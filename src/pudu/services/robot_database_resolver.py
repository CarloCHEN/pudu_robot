import logging
from typing import Dict, List, Optional
from pudu.rds.rdsTable import RDSDatabase

logger = logging.getLogger(__name__)

class RobotDatabaseResolver:
    """Service to resolve which database each robot belongs to based on tenant/project hierarchy"""

    def __init__(self, main_database_name: str):
        self.main_database_name = main_database_name
        self.main_db = RDSDatabase(connection_config="credentials.yaml", database_name=main_database_name)
        self._robot_to_database_cache = {}
        self._project_info_cache = {}

    def get_robot_database_mapping(self, robot_sns: List[str] = None) -> Dict[str, str]:
        """
        Get mapping of robot_sn to database name

        Args:
            robot_sns: List of robot serial numbers to resolve. If None, resolves all robots.

        Returns:
            Dict mapping robot_sn to database_name
        """
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

    def get_all_project_databases(self) -> List[str]:
        """Get list of all project database names"""
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