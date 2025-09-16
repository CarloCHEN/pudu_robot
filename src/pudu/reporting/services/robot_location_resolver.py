# src/pudu/reporting/services/robot_location_resolver.py
import logging
from typing import Dict, List, Optional, Any
from pudu.rds.rdsTable import RDSTable
from pudu.configs.database_config_loader import DynamicDatabaseConfig

logger = logging.getLogger(__name__)

class RobotLocationResolver:
    """Service to resolve robots based on location criteria (building, city, state, country)"""

    def __init__(self, config: DynamicDatabaseConfig):
        self.config = config
        self.connection_config = "credentials.yaml"

    def resolve_robots_by_location(self, location_criteria: Dict[str, str]) -> List[str]:
        """
        Resolve robot serial numbers based on location criteria

        Args:
            location_criteria: Dict with keys: country, state, city, building

        Returns:
            List of robot serial numbers matching criteria
        """
        logger.info(f"Resolving robots by location: {location_criteria}")

        try:
            # If no location criteria specified, return all robots
            if not any(location_criteria.values()):
                return self._get_all_robots()

            # Get matching building IDs based on location criteria
            matching_buildings = self._get_buildings_by_location(location_criteria)

            if not matching_buildings:
                logger.warning(f"No buildings found matching criteria: {location_criteria}")
                return []

            # Get robots in those buildings
            robots = self._get_robots_by_buildings(matching_buildings)

            logger.info(f"Found {len(robots)} robots matching location criteria")
            return robots

        except Exception as e:
            logger.error(f"Error resolving robots by location: {e}")
            return []

    def resolve_robots_by_name_or_sn(self, robot_name: str = None, robot_sn: str = None) -> List[str]:
        """
        Resolve robots by specific name or serial number

        Args:
            robot_name: Specific robot name
            robot_sn: Specific robot serial number

        Returns:
            List of robot serial numbers (usually just one)
        """
        logger.info(f"Resolving robots by name='{robot_name}' or sn='{robot_sn}'")

        try:
            # If serial number provided, return it directly (after validation)
            if robot_sn:
                if self._validate_robot_exists(robot_sn):
                    return [robot_sn]
                else:
                    logger.warning(f"Robot with SN '{robot_sn}' not found")
                    return []

            # If robot name provided, find by name
            if robot_name:
                robots = self._get_robots_by_name(robot_name)
                logger.info(f"Found {len(robots)} robots with name '{robot_name}'")
                return robots

            return []

        except Exception as e:
            logger.error(f"Error resolving robots by name/SN: {e}")
            return []

    def _get_buildings_by_location(self, location_criteria: Dict[str, str]) -> List[str]:
        """Get building IDs that match location criteria"""
        try:
            # Get building info table configurations
            building_configs = self.config.get_all_table_configs('location')  # This queries pro_building_info

            all_buildings = []
            for config in building_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys'],
                        reuse_connection=True
                    )

                    # Build WHERE clause based on provided criteria
                    where_conditions = []

                    if location_criteria.get('country'):
                        where_conditions.append(f"country = '{location_criteria['country'].upper()}'")
                    if location_criteria.get('state'):
                        where_conditions.append(f"state = '{location_criteria['state'].upper()}'")
                    if location_criteria.get('city'):
                        where_conditions.append(f"city = '{location_criteria['city'].upper()}'")
                    if location_criteria.get('building'):
                        building_val = location_criteria['building']
                        where_conditions.append(f"(building_name LIKE '%{building_val}%' OR building_name = '{building_val}')")

                    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                    query = f"""
                        SELECT building_id, building_name, city, state, country
                        FROM {table.table_name}
                        WHERE {where_clause}
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        building_ids = result_df['building_id'].tolist()
                        all_buildings.extend(building_ids)
                        logger.info(f"Found {len(building_ids)} buildings in {config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error querying buildings from {config['database']}: {e}")
                    continue

            # Remove duplicates
            unique_buildings = list(set(all_buildings))
            logger.info(f"Total unique buildings found: {len(unique_buildings)}")
            return unique_buildings

        except Exception as e:
            logger.error(f"Error getting buildings by location: {e}")
            return []

    def _get_robots_by_buildings(self, building_ids: List[str]) -> List[str]:
        """Get robots located in specific buildings"""
        try:
            # Get robot management table configurations
            robot_configs = self.config.get_all_table_configs('robot_status')  # This queries mnt_robots_management

            all_robots = []
            for config in robot_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys'],
                        reuse_connection=True
                    )

                    # Query robots by location_id (which matches building_id)
                    building_list = "', '".join(building_ids)
                    query = f"""
                        SELECT robot_sn, robot_name, location_id
                        FROM {table.table_name}
                        WHERE location_id IN ('{building_list}')
                        AND robot_sn IS NOT NULL
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        robot_sns = result_df['robot_sn'].tolist()
                        all_robots.extend(robot_sns)
                        logger.info(f"Found {len(robot_sns)} robots in buildings from {config['database']}")

                    table.close()

                except Exception as e:
                    logger.error(f"Error querying robots from {config['database']}: {e}")
                    continue

            # Remove duplicates
            unique_robots = list(set(all_robots))
            logger.info(f"Total unique robots found: {len(unique_robots)}")
            return unique_robots

        except Exception as e:
            logger.error(f"Error getting robots by buildings: {e}")
            return []

    def _get_robots_by_name(self, robot_name: str) -> List[str]:
        """Get robots by name"""
        try:
            robot_configs = self.config.get_all_table_configs('robot_status')

            all_robots = []
            for config in robot_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys'],
                        reuse_connection=True
                    )

                    query = f"""
                        SELECT robot_sn, robot_name
                        FROM {table.table_name}
                        WHERE robot_name LIKE '%{robot_name}%'
                        AND robot_sn IS NOT NULL
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        robot_sns = result_df['robot_sn'].tolist()
                        all_robots.extend(robot_sns)

                    table.close()

                except Exception as e:
                    logger.error(f"Error querying robots by name from {config['database']}: {e}")
                    continue

            return list(set(all_robots))

        except Exception as e:
            logger.error(f"Error getting robots by name: {e}")
            return []

    def _validate_robot_exists(self, robot_sn: str) -> bool:
        """Validate that a robot with given SN exists"""
        try:
            robot_configs = self.config.get_all_table_configs('robot_status')

            for config in robot_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys'],
                        reuse_connection=True
                    )

                    query = f"""
                        SELECT robot_sn
                        FROM {table.table_name}
                        WHERE robot_sn = '{robot_sn}'
                        LIMIT 1
                    """

                    result_df = table.execute_query(query)
                    table.close()

                    if not result_df.empty:
                        return True

                except Exception as e:
                    logger.error(f"Error validating robot from {config['database']}: {e}")
                    continue

            return False

        except Exception as e:
            logger.error(f"Error validating robot existence: {e}")
            return False

    def _get_all_robots(self) -> List[str]:
        """Get all robots across all databases"""
        try:
            # Use the existing resolver to get all robots
            all_robot_mapping = self.config.resolver.get_robot_database_mapping()
            return list(all_robot_mapping.keys())

        except Exception as e:
            logger.error(f"Error getting all robots: {e}")
            return []

    def get_location_options(self) -> Dict[str, Any]:
        """Get available location options for form dropdowns"""
        try:
            building_configs = self.config.get_all_table_configs('location')

            options = {
                'countries': set(),
                'states': set(),
                'cities': set(),
                'buildings': []
            }

            for config in building_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys'],
                        reuse_connection=True
                    )

                    query = f"""
                        SELECT DISTINCT country, state, city, building_name, building_id
                        FROM {table.table_name}
                        WHERE country IS NOT NULL
                        ORDER BY country, state, city, building_name
                    """

                    result_df = table.execute_query(query)
                    if not result_df.empty:
                        options['countries'].update(result_df['country'].dropna().tolist())
                        options['states'].update(result_df['state'].dropna().tolist())
                        options['cities'].update(result_df['city'].dropna().tolist())

                        buildings = result_df[['building_id', 'building_name']].dropna().to_dict('records')
                        options['buildings'].extend(buildings)

                    table.close()

                except Exception as e:
                    logger.error(f"Error getting location options from {config['database']}: {e}")
                    continue

            # Convert sets to sorted lists
            options['countries'] = sorted(list(options['countries']))
            options['states'] = sorted(list(options['states']))
            options['cities'] = sorted(list(options['cities']))

            logger.info(f"Location options: {len(options['countries'])} countries, {len(options['buildings'])} buildings")
            return options

        except Exception as e:
            logger.error(f"Error getting location options: {e}")
            return {'countries': [], 'states': [], 'cities': [], 'buildings': []}