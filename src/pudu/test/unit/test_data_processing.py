"""
Test actual data processing functions - NO MOCKING OF WHAT WE'RE TESTING
"""
import sys
# Add src to Python path
sys.path.append('../../')

import pandas as pd
from pudu.app.main import prepare_df_for_database

class TestDataProcessing:
    """Test real data processing functions"""

    def test_prepare_df_for_database_column_formatting(self):
        """Test that column names are formatted correctly"""
        # Create test DataFrame with various column names
        test_df = pd.DataFrame({
            'Robot SN': ['TEST001', 'TEST002'],
            'Battery Level': [95, 20],
            'Water Level': [80, 30],
            'Location ID': ['LOC001', 'LOC002']
        })

        # Call the REAL function
        result = prepare_df_for_database(test_df)

        # Test the actual processing logic
        expected_columns = ['robot_sn', 'battery_level', 'water_level', 'location_id']
        assert list(result.columns) == expected_columns

        # Test data preservation
        assert len(result) == 2
        assert result.iloc[0]['robot_sn'] == 'TEST001'
        assert result.iloc[0]['battery_level'] == 95

    def test_prepare_df_for_database_removes_specified_columns(self):
        """Test that specified columns are removed"""
        test_df = pd.DataFrame({
            'Robot SN': ['TEST001'],
            'ID': [1],  # Should be removed
            'Location ID': ['LOC001']  # Should be removed if specified
        })

        # Test column removal
        result = prepare_df_for_database(test_df, columns_to_remove=['id', 'location_id'])

        assert 'id' not in result.columns
        assert 'location_id' not in result.columns
        assert 'robot_sn' in result.columns

    def test_prepare_df_for_database_with_empty_dataframe(self):
        """Test handling of empty DataFrame"""
        empty_df = pd.DataFrame()

        result = prepare_df_for_database(empty_df)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

def run_data_processing_tests():
    """Run all data processing tests"""
    print("=" * 60)
    print("🧪 TESTING REAL DATA PROCESSING FUNCTIONS")
    print("=" * 60)

    test_instance = TestDataProcessing()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
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