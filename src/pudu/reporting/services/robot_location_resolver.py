import logging
from typing import Dict, List, Optional, Any, Union
from pudu.rds.rdsTable import RDSTable
from pudu.configs.database_config_loader import DynamicDatabaseConfig

logger = logging.getLogger(__name__)

reuse_connection = False

class RobotLocationResolver:
    """Service to resolve robots based on location criteria (building, city, state, country) and robot names/SNs"""

    def __init__(self, config: DynamicDatabaseConfig):
        self.config = config
        self.connection_config = "credentials.yaml"

    def resolve_robots_by_location(self, location_criteria: Dict[str, Union[str, List[str]]]) -> List[str]:
        """
        Resolve robot serial numbers based on location criteria - Enhanced for multiple selections

        Args:
            location_criteria: Dict with keys: countries, states, cities, buildings (each can be string or list)

        Returns:
            List of robot serial numbers matching criteria
        """
        logger.info(f"Resolving robots by location: {location_criteria}")

        try:
            # Convert old format to new format for backward compatibility
            location_criteria = self._normalize_location_criteria(location_criteria)

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

    def resolve_robots_by_name_or_sn(self, robot_names: Union[str, List[str]] = None,
                                   robot_sns: Union[str, List[str]] = None) -> List[str]:
        """
        Resolve robots by specific names or serial numbers - Enhanced for multiple selections

        Args:
            robot_names: Single robot name or list of robot names
            robot_sns: Single robot serial number or list of serial numbers

        Returns:
            List of robot serial numbers
        """
        logger.info(f"Resolving robots by names={robot_names} or sns={robot_sns}")

        try:
            all_robots = []

            # Handle serial numbers
            if robot_sns:
                sns_list = robot_sns if isinstance(robot_sns, list) else [robot_sns]
                for sn in sns_list:
                    if sn and self._validate_robot_exists(sn):
                        all_robots.append(sn)
                    elif sn:
                        logger.warning(f"Robot with SN '{sn}' not found")

            # Handle robot names
            if robot_names:
                names_list = robot_names if isinstance(robot_names, list) else [robot_names]
                for name in names_list:
                    if name:
                        robots = self._get_robots_by_name(name)
                        all_robots.extend(robots)
                        logger.info(f"Found {len(robots)} robots with name '{name}'")

            # Remove duplicates while preserving order
            unique_robots = list(dict.fromkeys(all_robots))
            logger.info(f"Total unique robots found: {len(unique_robots)}")
            return unique_robots

        except Exception as e:
            logger.error(f"Error resolving robots by name/SN: {e}")
            return []

    def resolve_robots_combined(self, location_criteria: Dict[str, Union[str, List[str]]] = None,
                              robot_names: Union[str, List[str]] = None,
                              robot_sns: Union[str, List[str]] = None) -> List[str]:
        """
        Resolve robots using both location and robot criteria - NEW METHOD

        Args:
            location_criteria: Location criteria (countries, states, cities, buildings)
            robot_names: Robot names
            robot_sns: Robot serial numbers

        Returns:
            List of robot serial numbers matching ALL criteria (intersection)
        """
        logger.info("Resolving robots using combined criteria")

        try:
            result_sets = []

            # Get robots by location if specified
            if location_criteria and any(location_criteria.values()):
                location_robots = self.resolve_robots_by_location(location_criteria)
                if location_robots:
                    result_sets.append(set(location_robots))
                    logger.info(f"Found {len(location_robots)} robots by location")
                else:
                    logger.info("No robots found by location criteria")
                    return []  # If location specified but no robots found, return empty

            # Get robots by names/SNs if specified
            if robot_names or robot_sns:
                name_sn_robots = self.resolve_robots_by_name_or_sn(robot_names, robot_sns)
                if name_sn_robots:
                    result_sets.append(set(name_sn_robots))
                    logger.info(f"Found {len(name_sn_robots)} robots by name/SN")
                else:
                    logger.info("No robots found by name/SN criteria")
                    return []  # If names/SNs specified but no robots found, return empty

            # If no criteria specified, return all robots
            if not result_sets:
                all_robots = self._get_all_robots()
                logger.info(f"No criteria specified, returning all {len(all_robots)} robots")
                return all_robots

            # Find intersection of all criteria
            final_robots = list(result_sets[0])
            for robot_set in result_sets[1:]:
                final_robots = [r for r in final_robots if r in robot_set]

            logger.info(f"Final result after combining criteria: {len(final_robots)} robots")
            return final_robots

        except Exception as e:
            logger.error(f"Error resolving robots with combined criteria: {e}")
            return []

    def _normalize_location_criteria(self, location_criteria: Dict[str, Union[str, List[str]]]) -> Dict[str, List[str]]:
        """Normalize location criteria to support both old and new formats"""
        normalized = {
            'countries': [],
            'states': [],
            'cities': [],
            'buildings': []
        }

        # Handle old format (singular keys)
        for old_key, new_key in [('country', 'countries'), ('state', 'states'),
                                ('city', 'cities'), ('building', 'buildings')]:
            if old_key in location_criteria:
                value = location_criteria[old_key]
                if isinstance(value, str) and value.strip():
                    normalized[new_key] = [value.strip()]
                elif isinstance(value, list):
                    normalized[new_key] = [v.strip() for v in value if v and v.strip()]

        # Handle new format (plural keys)
        for key in ['countries', 'states', 'cities', 'buildings']:
            if key in location_criteria:
                value = location_criteria[key]
                if isinstance(value, str) and value.strip():
                    normalized[key] = [value.strip()]
                elif isinstance(value, list):
                    normalized[key] = [v.strip() for v in value if v and v.strip()]

        return normalized

    def _get_buildings_by_location(self, location_criteria: Dict[str, List[str]]) -> List[str]:
        """Get building IDs that match location criteria - for multiple selections and case-insensitive matching"""
        try:
            # Get building info table configurations
            building_configs = self.config.get_all_table_configs('location')

            all_buildings = []
            for config in building_configs:
                try:
                    table = RDSTable(
                        connection_config=self.connection_config,
                        database_name=config['database'],
                        table_name=config['table_name'],
                        fields=config.get('fields'),
                        primary_keys=config['primary_keys'],
                        reuse_connection=reuse_connection
                    )

                    # Build WHERE clause based on provided criteria
                    where_conditions = []

                    # Handle multiple countries (case-insensitive)
                    if location_criteria.get('countries'):
                        countries = location_criteria['countries']
                        if len(countries) == 1:
                            where_conditions.append(f"UPPER(country) = UPPER('{countries[0]}')")
                        else:
                            # Escape single quotes and build case-insensitive IN clause
                            country_list = "', '".join([c.replace("'", "''") for c in countries])
                            where_conditions.append(f"UPPER(country) IN (UPPER('{country_list}'))")

                    # Handle multiple states (case-insensitive)
                    if location_criteria.get('states'):
                        states = location_criteria['states']
                        if len(states) == 1:
                            where_conditions.append(f"UPPER(state) = UPPER('{states[0]}')")
                        else:
                            # Escape single quotes and build case-insensitive IN clause
                            state_list = "', '".join([s.replace("'", "''") for s in states])
                            where_conditions.append(f"UPPER(state) IN (UPPER('{state_list}'))")

                    # Handle multiple cities (case-insensitive)
                    if location_criteria.get('cities'):
                        cities = location_criteria['cities']
                        if len(cities) == 1:
                            where_conditions.append(f"UPPER(city) = UPPER('{cities[0]}')")
                        else:
                            # Escape single quotes and build case-insensitive IN clause
                            city_list = "', '".join([c.replace("'", "''") for c in cities])
                            where_conditions.append(f"UPPER(city) IN (UPPER('{city_list}'))")

                    # Handle multiple buildings (case-insensitive partial matching)
                    if location_criteria.get('buildings'):
                        buildings = location_criteria['buildings']
                        building_conditions = []
                        for building in buildings:
                            # Escape single quotes for SQL safety
                            escaped_building = building.replace("'", "''")
                            building_conditions.append(
                                f"(UPPER(building_name) LIKE UPPER('%{escaped_building}%') OR UPPER(building_name) = UPPER('{escaped_building}'))"
                            )
                        where_conditions.append(f"({' OR '.join(building_conditions)})")

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
            if not building_ids:
                return []

            # Get robot management table configurations
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
                        reuse_connection=reuse_connection
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
        """Get robots by name - supports partial matching"""
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
                        reuse_connection=reuse_connection
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
                        reuse_connection=reuse_connection
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
                        reuse_connection=reuse_connection
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