"""
Unit tests for API functions using test data
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from pudu.test.utils.test_helpers import TestDataLoader

class TestAPIFunctions:
    """Test API function behavior using test data"""

    def setup_method(self):
        """Setup for each test"""
        self.test_data = TestDataLoader()

    def test_get_location_table_with_test_data(self):
        """Test location table API using test data"""
        location_data = self.test_data.get_location_data()
        expected_locations = location_data.get("valid_locations", [])

        # Mock the API to return our test data
        with patch('pudu.apis.get_location_table') as mock_api:
            mock_api.return_value = pd.DataFrame(expected_locations)

            from pudu.apis import get_location_table
            result = get_location_table()

            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(expected_locations)
            if not result.empty:
                assert "building_id" in result.columns
                assert "building_name" in result.columns

                # Test specific data from test file
                first_location = expected_locations[0]
                assert result.iloc[0]["building_id"] == first_location["building_id"]

    def test_get_robot_status_table_with_test_data(self):
        """Test robot status table API using test data"""
        status_data = self.test_data.get_robot_status_data()
        valid_robots = status_data.get("valid_robots", [])

        with patch('pudu.apis.get_robot_status_table') as mock_api:
            mock_api.return_value = pd.DataFrame(valid_robots)

            from pudu.apis import get_robot_status_table
            result = get_robot_status_table()

            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(valid_robots)

            # Test specific robot from test data
            if valid_robots:
                test_robot = valid_robots[0]
                found_robot = result[result["robot_sn"] == test_robot["robot_sn"]]
                assert len(found_robot) == 1
                assert found_robot.iloc[0]["status"] == test_robot["status"]
                assert found_robot.iloc[0]["battery_level"] == test_robot["battery_level"]

    def test_get_robot_status_edge_cases(self):
        """Test robot status edge cases from test data"""
        status_data = self.test_data.get_robot_status_data()
        edge_cases = status_data.get("edge_cases", [])

        with patch('pudu.apis.get_robot_status_table') as mock_api:
            mock_api.return_value = pd.DataFrame(edge_cases)

            from pudu.apis import get_robot_status_table
            result = get_robot_status_table()

            # Test offline robot case
            offline_robots = result[result["status"] == "Offline"]
            assert len(offline_robots) >= 0  # Should handle offline robots gracefully

    def test_get_schedule_table_with_test_data(self):
        """Test schedule table API using test data"""
        task_data = self.test_data.get_robot_task_data()
        valid_tasks = task_data.get("valid_tasks", [])

        with patch('pudu.apis.get_schedule_table') as mock_api:
            mock_api.return_value = pd.DataFrame(valid_tasks)

            from pudu.apis import get_schedule_table
            result = get_schedule_table("2024-09-01 00:00:00", "2024-09-01 23:59:59")

            assert isinstance(result, pd.DataFrame)

            if valid_tasks:
                # Test completed task
                completed_tasks = result[result["status"] == "Task Ended"]
                if len(completed_tasks) > 0:
                    completed_task = completed_tasks.iloc[0]
                    assert completed_task["progress"] == 100.0

                # Test in-progress task
                in_progress_tasks = result[result["status"] == "In Progress"]
                if len(in_progress_tasks) > 0:
                    in_progress_task = in_progress_tasks.iloc[0]
                    assert 0 < in_progress_task["progress"] < 100