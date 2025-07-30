"""
Integration tests for complete pipeline flow using test data
"""

import pytest
from unittest.mock import patch, MagicMock
from pudu.test.mocks.mock_rds import MockRDSTable
from pudu.test.utils.test_helpers import TestDataLoader
import pandas as pd

class TestPipelineFlow:
    """Test complete data pipeline flow using test data"""

    def setup_method(self):
        """Setup for each test"""
        self.test_data = TestDataLoader()
        self.mock_tables = {}
        self.start_time = "2024-09-01 00:00:00"
        self.end_time = "2024-09-01 23:59:59"

    def test_robot_status_pipeline_with_test_data(self):
        """Test robot status data pipeline using test data"""
        # Load test data
        status_data = self.test_data.get_robot_status_data()
        valid_robots = status_data.get("valid_robots", [])

        # Create mock table
        mock_table = MockRDSTable("test", "test_db", "mnt_robots_management",
                                 primary_keys=["robot_sn"])

        # Simulate the pipeline process
        with patch('pudu.apis.get_robot_status_table') as mock_api:
            mock_api.return_value = pd.DataFrame(valid_robots)

            # Get data through API
            from pudu.apis import get_robot_status_table
            api_result = get_robot_status_table()

            # Convert to database format
            db_data = api_result.to_dict(orient='records')

            # Insert to mock database
            mock_table.batch_insert(db_data)

            # Verify data was stored correctly
            stored_data = mock_table.get_inserted_data()
            assert len(stored_data) == len(valid_robots)

            # Check specific robot data
            test_robot = next((r for r in valid_robots if r["robot_sn"] == "811064412050012"), None)
            if test_robot:
                stored_robot = next((r for r in stored_data if r["robot_sn"] == "811064412050012"), None)
                assert stored_robot is not None
                assert stored_robot["status"] == test_robot["status"]
                assert stored_robot["battery_level"] == test_robot["battery_level"]

    def test_task_data_pipeline_with_test_data(self):
        """Test task data pipeline using test data"""
        # Load test data
        task_data = self.test_data.get_robot_task_data()
        valid_tasks = task_data.get("valid_tasks", [])

        # Create mock table
        mock_table = MockRDSTable("test", "test_db", "mnt_robots_task",
                                 primary_keys=["robot_sn", "task_name", "start_time"])

        with patch('pudu.apis.get_schedule_table') as mock_api:
            mock_api.return_value = pd.DataFrame(valid_tasks)

            # Simulate pipeline
            from pudu.apis import get_schedule_table
            api_result = get_schedule_table(self.start_time, self.end_time)

            # Process and store
            db_data = api_result.to_dict(orient='records')
            mock_table.batch_insert(db_data)

            # Verify results
            stored_data = mock_table.get_inserted_data()
            assert len(stored_data) == len(valid_tasks)

            # Check for completed task
            completed_task = next((t for t in valid_tasks if t.get("status") == "Task Ended"), None)
            if completed_task:
                stored_completed = next((t for t in stored_data if t.get("status") == "Task Ended"), None)
                assert stored_completed is not None
                assert stored_completed["progress"] == 100.0

    def test_change_detection_with_test_data(self):
        """Test change detection using test data"""
        # Load test data
        status_data = self.test_data.get_robot_status_data()
        valid_robots = status_data.get("valid_robots", [])

        if not valid_robots:
            pytest.skip("No valid robot data for change detection test")

        # Create mock table with existing data
        mock_table = MockRDSTable("test", "test_db", "mnt_robots_management",
                                 primary_keys=["robot_sn"])

        # Insert initial data
        initial_robot = valid_robots[0].copy()
        mock_table.batch_insert([initial_robot])

        # Simulate a change (battery level decrease)
        changed_robot = initial_robot.copy()
        changed_robot["battery_level"] = 15  # Low battery

        # Test change detection logic
        from pudu.notifications import detect_data_changes
        changes = detect_data_changes(mock_table, [changed_robot], ["robot_sn"])

        # Verify changes were detected
        assert len(changes) > 0

        robot_sn = initial_robot["robot_sn"]
        change_key = next((k for k in changes.keys() if robot_sn in k), None)
        assert change_key is not None

        change_info = changes[change_key]
        assert change_info["change_type"] == "update"
        assert "battery_level" in change_info["changed_fields"]
        assert change_info["new_values"]["battery_level"] == 15

    def test_notification_trigger_with_test_data(self):
        """Test notification triggering with test data"""
        # Load test data
        status_data = self.test_data.get_robot_status_data()
        valid_robots = status_data.get("valid_robots", [])

        # Find low battery robot from test data
        low_battery_robot = next((r for r in valid_robots if r.get("battery_level", 100) < 20), None)

        if low_battery_robot:
            # Mock notification service
            from pudu.test.mocks.mock_notifications import MockNotificationService
            mock_notif_service = MockNotificationService()

            # Create change info
            change_info = {
                "robot_id": low_battery_robot["robot_sn"],
                "change_type": "update",
                "changed_fields": ["battery_level"],
                "old_values": {"battery_level": 80},
                "new_values": low_battery_robot
            }

            # Test notification logic
            from pudu.notifications import send_change_based_notifications
            success, failed = send_change_based_notifications(
                mock_notif_service,
                {"test_change": change_info},
                "robot_status"
            )

            # Verify notification was sent
            notifications = mock_notif_service.get_sent_notifications()
            assert len(notifications) > 0

            # Check notification content
            notification = notifications[0]
            assert "battery" in notification["title"].lower() or "battery" in notification["content"].lower()
            assert notification["severity"] in ["warning", "error", "fatal"]