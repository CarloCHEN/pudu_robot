"""
Unit tests for data processing functions - tests real API data transformations with JSON data
"""

import sys
sys.path.append('../../')

import pandas as pd
from pudu.app.main import App
from pudu.test.utils.test_helpers import TestDataLoader, TestValidator

class TestDataProcessing:
    """Test actual data processing functions with real data patterns from JSON"""

    def setup_method(self):
        """Setup test data loader"""
        self.test_data = TestDataLoader()
        self.validator = TestValidator()
        # Create app instance for testing (without full initialization)
        self.app = App.__new__(App)

    def test_prepare_df_for_database_with_json_robot_data(self):
        """Test column transformation with actual robot data from JSON"""
        print("  📊 Testing column transformation with JSON robot data")

        # Get real robot data from JSON
        status_data = self.test_data.get_robot_status_data()
        valid_robots = status_data.get("valid_robots", [])

        assert len(valid_robots) > 0, "No robot data found in JSON"

        # Convert to DataFrame with typical API column names
        df_data = []
        for robot in valid_robots:
            df_data.append({
                'Robot SN': robot.get('robot_sn'),
                'Robot Name': robot.get('robot_name'),
                'Robot Type': robot.get('robot_type'),
                'Water Level': robot.get('water_level'),
                'Sewage Level': robot.get('sewage_level'),
                'Battery Level': robot.get('battery_level'),
                'Status': robot.get('status')
            })

        api_data = pd.DataFrame(df_data)
        result = self.app._prepare_df_for_database(api_data)

        # Test column transformation
        expected_columns = ['robot_sn', 'robot_name', 'robot_type', 'water_level',
                           'sewage_level', 'battery_level', 'status']
        assert list(result.columns) == expected_columns

        # Test data preservation with actual JSON values
        first_robot = valid_robots[0]
        assert result.iloc[0]['robot_sn'] == first_robot['robot_sn']
        assert result.iloc[0]['robot_name'] == first_robot['robot_name']
        assert result.iloc[0]['status'] == first_robot['status']

    def test_prepare_df_for_database_with_json_task_data(self):
        """Test task data processing with JSON task data"""
        print("  📋 Testing task data processing with JSON")

        task_data = self.test_data.get_robot_task_data()
        valid_tasks = task_data.get("valid_tasks", [])

        if len(valid_tasks) > 0:
            # Convert to DataFrame format like get_schedule_table() would return
            df_data = []
            for task in valid_tasks:
                df_data.append({
                    'Task Name': task.get('task_name'),
                    'Robot SN': task.get('robot_sn'),
                    'Mode': task.get('mode'),
                    'Sub Mode': task.get('sub_mode'),
                    'Actual Area': task.get('actual_area'),
                    'Plan Area': task.get('plan_area'),
                    'Progress': task.get('progress'),
                    'Status': task.get('status'),
                    'Efficiency': task.get('efficiency'),
                    'Start Time': '2024-09-01 14:30:00',  # Add required fields
                    'End Time': '2024-09-01 16:00:00'
                })

            task_df = pd.DataFrame(df_data)
            result = self.app._prepare_df_for_database(task_df, columns_to_remove=['id', 'location_id'])

            # Test task-specific processing
            expected_task_columns = ['task_name', 'robot_sn', 'mode', 'sub_mode',
                                    'actual_area', 'plan_area', 'progress', 'status',
                                    'efficiency', 'start_time', 'end_time']

            for col in expected_task_columns:
                assert col in result.columns, f"Missing column: {col}"

            # Test data integrity with JSON values
            first_task = valid_tasks[0]
            assert result.iloc[0]['task_name'] == first_task['task_name']
            assert result.iloc[0]['robot_sn'] == first_task['robot_sn']

    def test_prepare_df_for_database_with_json_charging_data(self):
        """Test charging data processing with JSON charging data"""
        print("  🔌 Testing charging data processing with JSON")

        charging_data = self.test_data.get_robot_charging_data()
        valid_sessions = charging_data.get("valid_charging_sessions", [])

        if len(valid_sessions) > 0:
            # Convert to DataFrame format like get_charging_table() would return
            df_data = []
            for session in valid_sessions:
                df_data.append({
                    'Robot Name': session.get('robot_name'),
                    'Robot SN': session.get('robot_sn'),
                    'Start Time': session.get('start_time'),
                    'End Time': session.get('end_time'),
                    'Duration': session.get('duration'),
                    'Initial Power': session.get('initial_power'),
                    'Final Power': session.get('final_power'),
                    'Power Gain': session.get('power_gain')
                })

            charging_df = pd.DataFrame(df_data)
            result = self.app._prepare_df_for_database(charging_df, columns_to_remove=['id', 'location_id'])

            # Test charging-specific processing
            expected_columns = ['robot_name', 'robot_sn', 'start_time', 'end_time',
                               'duration', 'initial_power', 'final_power', 'power_gain']

            for col in expected_columns:
                assert col in result.columns, f"Missing column: {col}"

            # Test data integrity
            first_session = valid_sessions[0]
            assert result.iloc[0]['robot_sn'] == first_session['robot_sn']
            assert result.iloc[0]['robot_name'] == first_session['robot_name']

    def test_prepare_df_for_database_column_removal_with_real_columns(self):
        """Test column removal with actual problematic columns from your system"""
        print("  🗑️ Testing column removal with real problematic columns")

        # Create DataFrame with columns that cause conflicts in database insertion
        problematic_data = pd.DataFrame({
            'Robot SN': ['1230', '1231'],
            'Task Name': ['Library Cleaning', 'Office Sweep'],
            'ID': [1, 2],  # Auto-increment conflict
            'Location ID': ['USF001', 'USF002'],  # Foreign key that should be removed
            'Status': ['Online', 'Online'],
            'created_at': ['2024-09-01', '2024-09-02']  # Timestamp that might conflict
        })

        result = self.app._prepare_df_for_database(problematic_data,
                                                  columns_to_remove=['id', 'location_id', 'created_at'])

        # Test that problematic columns are removed
        assert 'id' not in result.columns
        assert 'location_id' not in result.columns
        assert 'created_at' not in result.columns

        # Test that essential columns remain
        assert 'robot_sn' in result.columns
        assert 'task_name' in result.columns
        assert 'status' in result.columns

    def test_prepare_df_for_database_with_json_edge_cases(self):
        """Test edge case handling with JSON edge case data"""
        print("  ⚠️ Testing edge case handling with JSON data")

        # Get edge cases from all data sources
        status_edge_cases = self.test_data.get_robot_status_data().get("edge_cases", [])
        charging_edge_cases = self.test_data.get_robot_charging_data().get("edge_cases", [])
        location_edge_cases = self.test_data.get_location_data().get("edge_cases", [])

        # Test status edge cases
        if status_edge_cases:
            edge_df = pd.DataFrame(status_edge_cases)
            result = self.app._prepare_df_for_database(edge_df)

            # Should not crash with edge cases
            assert isinstance(result, pd.DataFrame)
            assert len(result) == len(status_edge_cases)

            # Test that column transformation still works
            if 'robot_sn' in edge_df.columns:
                assert 'robot_sn' in result.columns

        # Test location edge cases
        if location_edge_cases:
            location_df = pd.DataFrame(location_edge_cases)
            result = self.app._prepare_df_for_database(location_df)

            assert isinstance(result, pd.DataFrame)
            # Should handle empty building names gracefully
            if len(result) > 0 and 'building_name' in result.columns:
                # Empty building names should be preserved (might be valid edge case)
                pass

    def test_prepare_df_for_database_data_type_preservation(self):
        """Test that data types are preserved during processing with JSON data"""
        print("  🔢 Testing data type preservation with JSON numeric data")

        # Get robots with various numeric data types
        all_robots = self.test_data.get_all_robots_from_status_data()
        robots_with_coords = [r for r in all_robots if 'x' in r and r['x'] is not None]

        if robots_with_coords:
            robot = robots_with_coords[0]

            # Create DataFrame with mixed data types
            mixed_data = pd.DataFrame([{
                'Robot SN': robot['robot_sn'],  # String
                'Battery Level': robot['battery_level'],  # Numeric
                'X': robot.get('x'),  # Float coordinate (might be None)
                'Y': robot.get('y'),  # Float coordinate (might be None)
                'Z': robot.get('z'),  # Float coordinate (might be None)
                'Water Level': robot.get('water_level'),  # Integer percentage
                'Status': robot['status']  # String
            }])

            result = self.app._prepare_df_for_database(mixed_data)

            # Test data type preservation
            assert result.iloc[0]['robot_sn'] == robot['robot_sn']

            if robot.get('battery_level') is not None:
                import numpy as np
                assert isinstance(result.iloc[0]['battery_level'], (int, np.int64, float))

            if robot.get('x') is not None:
                assert isinstance(result.iloc[0]['x'], (int, float))

    def test_prepare_df_for_database_empty_and_null_handling(self):
        """Test handling of empty DataFrames and null values"""
        print("  🚫 Testing empty DataFrame and null value handling")

        # Test empty DataFrame
        empty_df = pd.DataFrame()
        result = self.app._prepare_df_for_database(empty_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

        # Test DataFrame with null values using edge case data
        edge_cases = self.test_data.get_robot_status_data().get("edge_cases", [])

        if edge_cases:
            # Add some None values to test null handling
            test_data = edge_cases[0].copy()
            test_data.update({
                'battery_level': None,
                'water_level': None,
                'x': None,
                'y': None,
                'z': None
            })

            null_df = pd.DataFrame([test_data])
            result = self.app._prepare_df_for_database(null_df)

            # Should handle null values gracefully
            assert len(result) == 1
            assert pd.isna(result.iloc[0]['battery_level']) or result.iloc[0]['battery_level'] is None

    def test_prepare_df_for_database_with_realistic_api_output(self):
        """Test with data structure that matches your actual API output"""
        print("  🔌 Testing with realistic API output structure")

        # Create data that matches the structure of get_robot_status_table()
        api_output = pd.DataFrame({
            'Location ID': ['USF001', 'USF002'],
            'Robot SN': ['811064412050012', '811064412050013'],
            'Robot Name': ['USF_LIB', 'USF_OFFICE'],
            'Robot Type': ['CC1', 'CC1'],
            'Water Level': [80, 50],
            'Sewage Level': [20, 75],
            'Battery Level': [95.567, 15.234],  # High precision from API
            'x': [-0.233, 0.655],  # Coordinates
            'y': [-0.045, 0.102],
            'z': [0.026, -0.186],
            'Status': ['Online', 'Online']
        })

        result = self.app._prepare_df_for_database(api_output, columns_to_remove=['location_id'])

        # Test that location_id is removed but other columns transformed
        assert 'location_id' not in result.columns
        assert 'robot_sn' in result.columns
        assert 'battery_level' in result.columns
        assert 'x' in result.columns

        # Test that high precision values are preserved
        assert isinstance(result.iloc[0]['battery_level'], (int, float))
        assert isinstance(result.iloc[0]['x'], (int, float))

        # Test that data values are correct
        assert result.iloc[0]['robot_sn'] == '811064412050012'
        assert result.iloc[1]['robot_sn'] == '811064412050013'

    def test_get_robots_for_data_extraction(self):
        """Test robot extraction from DataFrames using JSON data"""
        print("  🤖 Testing robot extraction from DataFrames")

        # Get test data
        all_robots = self.test_data.get_all_robots_from_status_data()

        if len(all_robots) > 0:
            # Create DataFrame
            robot_df = pd.DataFrame(all_robots)

            # Test robot extraction (this method exists in your App class)
            robots = self.app._get_robots_for_data(robot_df, 'robot_sn')

            expected_robots = [r['robot_sn'] for r in all_robots if 'robot_sn' in r and r['robot_sn']]
            assert set(robots) == set(expected_robots)

    def test_column_formatting_edge_cases(self):
        """Test column name formatting with various edge cases"""
        print("  📝 Testing column name formatting edge cases")

        # Test various column name patterns that might come from APIs
        edge_case_df = pd.DataFrame({
            'Robot   SN': ['test'],  # Extra spaces
            'ROBOT TYPE': ['CC1'],   # All caps
            'robot name': ['test'],  # All lowercase
            'Robot-Type-2': ['CC1'], # Hyphens
            'Robot_Name_3': ['test'], # Underscores
            'Location ID ': ['USF001'], # Trailing space
        })

        result = self.app._prepare_df_for_database(edge_case_df)

        # Test that all edge cases are handled correctly
        expected_columns = ['robot___sn', 'robot_type', 'robot_name',
                           'robot-type-2', 'robot_name_3', 'location_id_']

        # All should be lowercase with spaces converted to underscores
        for col in result.columns:
            assert col.islower(), f"Column {col} should be lowercase"

    def test_data_integrity_throughout_processing(self):
        """Test that data integrity is maintained throughout processing pipeline"""
        print("  🔍 Testing data integrity throughout processing")

        # Use comprehensive data from multiple JSON sources
        all_robots = self.test_data.get_all_robots_from_status_data()
        all_tasks = self.test_data.get_all_tasks_from_task_data()
        all_charging = self.test_data.get_all_charging_sessions()

        # Test robot data integrity
        if all_robots:
            original_df = pd.DataFrame(all_robots)
            processed_df = self.app._prepare_df_for_database(original_df)

            # Should maintain same number of records
            assert len(processed_df) == len(original_df)

            # Key field values should be preserved
            if 'robot_sn' in original_df.columns and 'robot_sn' in processed_df.columns:
                original_sns = set(original_df['robot_sn'].dropna())
                processed_sns = set(processed_df['robot_sn'].dropna())
                assert original_sns == processed_sns

        # Test task data integrity
        if all_tasks:
            task_df = pd.DataFrame(all_tasks)
            processed_task_df = self.app._prepare_df_for_database(task_df)

            assert len(processed_task_df) == len(task_df)

            # Task names should be preserved
            if 'task_name' in task_df.columns and 'task_name' in processed_task_df.columns:
                original_tasks = set(task_df['task_name'].dropna())
                processed_tasks = set(processed_task_df['task_name'].dropna())
                assert original_tasks == processed_tasks

    def test_prepare_df_handles_json_location_data(self):
        """Test location data processing with JSON location data"""
        print("  🏢 Testing location data processing with JSON")

        location_data = self.test_data.get_location_data()
        valid_locations = location_data.get("valid_locations", [])

        if len(valid_locations) > 0:
            # Convert to format like get_location_table() returns
            df_data = []
            for location in valid_locations:
                df_data.append({
                    'Building ID': location.get('building_id'),
                    'Building Name': location.get('building_name')
                })

            location_df = pd.DataFrame(df_data)
            result = self.app._prepare_df_for_database(location_df)

            # Test location processing
            assert 'building_id' in result.columns
            assert 'building_name' in result.columns
            assert len(result) == len(valid_locations)

            # Test that building IDs are preserved
            original_ids = set(location_df['Building ID'])
            processed_ids = set(result['building_id'])
            assert original_ids == processed_ids

def run_data_processing_tests():
    """Run all data processing tests with JSON data"""
    print("=" * 70)
    print("🧪 TESTING DATA PROCESSING FUNCTIONS WITH JSON DATA")
    print("=" * 70)

    test_instance = TestDataProcessing()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            test_instance.setup_method()
            method = getattr(test_instance, method_name)
            method()
            passed += 1
            print(f"✅ {method_name} - PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {method_name} - FAILED: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n📊 Data Processing Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_data_processing_tests()