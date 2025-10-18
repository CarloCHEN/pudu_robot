from typing import List, Dict
from services.robot_database_resolver import RobotDatabaseResolver
import logging

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Enhanced database configuration that supports dynamic project database resolution"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.main_database_name = self.config.get('main_database', 'ry-vue')
        self.resolver = RobotDatabaseResolver(self.main_database_name)

    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        import yaml
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            raise FileNotFoundError(f"Configuration file {self.config_path} not found")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise ValueError(f"Error parsing YAML configuration: {e}")

    def get_table_configs_for_robots(self, table_type: str, robot_sns: List[str]) -> List[Dict]:
        """
        Get table configurations for specific robots, resolving project databases dynamically

        Args:
            table_type: Type of table (e.g., 'robot_status', 'robot_events')
            robot_sns: List of robot serial numbers

        Returns:
            List of table configurations with resolved database names
        """
        base_configs = self.config.get('tables', {}).get(table_type, [])
        resolved_configs = []

        # Group robots by their target database
        db_to_robots = self.resolver.group_robots_by_database(robot_sns)

        for base_config in base_configs:
            database_type = base_config['database']
            # does not trigger this main database in webhook callback
            if database_type == 'main':
                # Main database - use as is
                config = base_config.copy()
                config['database'] = self.main_database_name
                config['robot_sns'] = robot_sns  # All robots can access main DB
                resolved_configs.append(config)

            elif database_type == 'project':
                # Project databases - create one config per database
                for database_name, robots_in_db in db_to_robots.items():
                    config = base_config.copy()
                    config['database'] = database_name
                    config['robot_sns'] = robots_in_db
                    resolved_configs.append(config)

        return resolved_configs

    def get_transform_supported_databases(self) -> List[str]:
        """
        Get list of databases that support transformations (have floor plan mapping data).

        Returns:
            List[str]: Database names that support transformations
        """
        return self.config.get('transform_supported_databases', [])

    def filter_robots_for_transform_support(self, robot_sns: List[str]) -> tuple:
        """
        Filter robots based on whether their database supports transformations.

        Args:
            robot_sns: List of robot serial numbers

        Returns:
            tuple: (robots_with_transform_support, robots_without_transform_support)
        """
        # Get robot to database mapping
        robot_to_db = self.resolver.get_robot_database_mapping(robot_sns)

        # Get databases that support transformations
        supported_databases = self.get_transform_supported_databases()

        robots_with_support = []
        robots_without_support = []

        for robot_sn in robot_sns:
            database_name = robot_to_db.get(robot_sn)
            if database_name and database_name in supported_databases:
                robots_with_support.append(robot_sn)
            else:
                robots_without_support.append(robot_sn)
                if database_name:
                    logger.debug(f"Robot {robot_sn} in database {database_name} - transformations not supported")
                else:
                    logger.debug(f"Robot {robot_sn} - no database mapping found")

        logger.info(f"Transform filtering: {len(robots_with_support)} robots with support, {len(robots_without_support)} without support")
        return robots_with_support, robots_without_support

    def get_robots_in_transform_supported_databases(self) -> List[str]:
        """
        Get all robots that are in databases supporting transformations.

        Returns:
            List[str]: Robot serial numbers in transform-supported databases
        """
        # Get all robots
        all_robots = list(self.resolver.get_robot_database_mapping().keys())

        # Filter for transform support
        supported_robots, _ = self.filter_robots_for_transform_support(all_robots)

        return supported_robots

    def get_notification_databases(self) -> List[str]:
        """Get list of databases that need notifications"""
        notification_needed = self.config.get('notification_needed', [])
        resolved_databases = []

        for db_identifier in notification_needed:
            if db_identifier == 'main':
                resolved_databases.append(self.main_database_name)
            elif db_identifier == 'project':
                resolved_databases.extend(self.resolver.get_all_project_databases())
            else:
                resolved_databases.append(db_identifier)

        return resolved_databases

    def close(self):
        """Close resolver connection"""
        if self.resolver.main_db:
            self.resolver.close()