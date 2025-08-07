"""
Unit tests for data processing functions - tests real API data transformations
"""

import sys
sys.path.append('../../')

import pandas as pd
from pudu.app.main import App

class TestDataProcessing:
    """Test actual data processing functions with real data patterns"""

    def setup_method(self):
        """Setup test instance"""
        # Don't initialize full app, just use the processing methods
        pass

    def test_prepare_df_for_database_column_transformation(self):
        """Test column name transformation matches your actual needs"""
        # Use actual column names from your API functions
        api_data = pd.DataFrame({
            'Robot SN': ['1230', '1231'],
            'Robot Name': ['demo_UF_demo', 'LDS-test'],
            'Robot Type': ['CC1', 'CC1'],
            'Water Level': [25, 0],
            'Sewage Level': [0, 0],
            'Battery Level': [100, 100],
            'Status': ['Online', 'Online'],
            'Location ID': ['523670000', '450270000']
        })

        # Use actual App method
        app = App.__new__(App)  # Create instance without __init__
        result = app._prepare_df_for_database(api_data)

        # Test column transformation
        expected_columns = ['robot_sn', 'robot_name', 'robot_type', 'water_level',
                           'sewage_level', 'battery_level', 'status', 'location_id']
        assert list(result.columns) == expected_columns

        # Test data preservation
        assert len(result) == 2
        assert result.iloc[0]['robot_sn'] == '1230'
        assert result.iloc[0]['robot_name'] == 'demo_UF_demo'
        assert result.iloc[1]['robot_sn'] == '1231'

    def test_prepare_df_for_database_column_removal(self):
        """Test column removal functionality with actual use cases"""
        # Data with columns that should be removed for database insertion
        api_data = pd.DataFrame({
            'Robot SN': ['1230'],
            'Task Name': ['Library Cleaning'],
            'ID': [1],  # Should be removed - conflicts with auto-increment
            'Location ID': ['523670000'],  # Should be removed if specified
            'Status': ['Online']
        })

        app = App.__new__(App)
        result = app._prepare_df_for_database(api_data, columns_to_remove=['id', 'location_id'])

        # Test removal
        assert 'id' not in result.columns
        assert 'location_id' not in result.columns
        # Test preservation
        assert 'robot_sn' in result.columns
        assert 'task_name' in result.columns
        assert 'status' in result.columns

    def test_prepare_df_for_database_with_real_api_patterns(self):
        """Test with actual patterns from your API responses"""
        # Simulate get_robot_status_table() output
        robot_status_data = pd.DataFrame({
            'Location ID': ['523670000', '450270000'],
            'Robot SN': ['1230', '1231'],
            'Robot Name': ['demo_UF_demo', 'LDS-test'],
            'Robot Type': ['CC1', 'CC1'],
            'Water Level': [25, 0],
            'Sewage Level': [0, 0],
            'Battery Level': [100.567, 100.123],  # High precision from API
            'x': [-0.23293037200521216, 0.6546468716153662],
            'y': [-0.044921584455721364, 0.10216624231873786],
            'z': [0.026269476759686716, -0.1855085439150417],
            'Status': ['Online', 'Online']
        })

        app = App.__new__(App)
        result = app._prepare_df_for_database(robot_status_data, columns_to_remove=['location_id'])

        # Test transformation with real data
        assert 'location_id' not in result.columns
        assert 'robot_sn' in result.columns
        assert 'battery_level' in result.columns

        # Test data types preserved
        assert result.iloc[0]['robot_sn'] == '1230'
        assert isinstance(result.iloc[0]['battery_level'], (int, float))
        assert isinstance(result.iloc[0]['x'], (int, float))

    def test_prepare_df_for_database_task_data(self):
        """Test processing of task data from get_schedule_table()"""
        # Simulate get_schedule_table() output
        task_data = pd.DataFrame({
            'Task Name': ['Library Cleaning', 'Office Sweep'],
            'Robot SN': ['1230', '1231'],
            'Map Name': ['1#6#USF-LIB-basement', '1#3#USF-Office-1st'],
            'Actual Area': [150.56, 89.23],
            'Plan Area': [200.0, 120.0],
            'Start Time': ['2024-09-01 14:30:00', '2024-09-01 15:00:00'],
            'End Time': ['2024-09-01 16:00:00', '2024-09-01 16:30:00'],
            'Duration': [5400, 3600],  # seconds
            'Efficiency': [45.26, 32.15],
            'Progress': [75.28, 74.36],
            'Status': ['Task Ended', 'In Progress']
        })

        app = App.__new__(App)
        result = app._prepare_df_for_database(task_data, columns_to_remove=['id'])

        # Test task-specific processing
        expected_task_columns = ['task_name', 'robot_sn', 'map_name', 'actual_area',
                                'plan_area', 'start_time', 'end_time', 'duration',
                                'efficiency', 'progress', 'status']

        for col in expected_task_columns:
            assert col in result.columns, f"Missing column: {col}"

        # Test data integrity
        assert len(result) == 2
        assert result.iloc[0]['task_name'] == 'Library Cleaning'
        assert result.iloc[0]['robot_sn'] == '1230'

    def test_prepare_df_for_database_empty_and_edge_cases(self):
        """Test edge cases and empty data handling"""
        app = App.__new__(App)

        # Test empty DataFrame
        empty_df = pd.DataFrame()
        result = app._prepare_df_for_database(empty_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

        # Test DataFrame with only one row
        single_row = pd.DataFrame({
            'Robot SN': ['TEST001'],
            'Status': ['Online']
        })
        result = app._prepare_df_for_database(single_row)
        assert len(result) == 1
        assert 'robot_sn' in result.columns
        assert 'status' in result.columns

        # Test with None values
        data_with_nulls = pd.DataFrame({
            'Robot SN': ['1230', None],
            'Battery Level': [95.5, None],
            'Status': ['Online', 'Unknown']
        })
        result = app._prepare_df_for_database(data_with_nulls)
        assert len(result) == 2
        assert pd.isna(result.iloc[1]['robot_sn'])
        assert pd.isna(result.iloc[1]['battery_level'])

def run_data_processing_tests():
    """Run all data processing tests"""
    print("=" * 60)
    print("🧪 TESTING DATA PROCESSING FUNCTIONS")
    print("=" * 60)

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