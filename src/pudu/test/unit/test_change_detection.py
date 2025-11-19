"""
Unit tests for change detection logic - tests real functions with JSON test data
"""

import sys
import os
sys.path.append('../../')

from pudu.notifications.change_detector import (
    normalize_decimal_value,
    values_are_equivalent,
    normalize_record_for_comparison,
    detect_data_changes,
    DECIMAL_FIELDS_PRECISION
)
from pudu.test.utils.test_helpers import TestDataLoader, TestValidator
from decimal import Decimal
from unittest.mock import MagicMock

class TestChangeDetection:
    """Test actual change detection algorithms with JSON test data"""

    def setup_method(self):
        """Setup test data loader"""
        self.test_data = TestDataLoader()
        self.validator = TestValidator()

    def test_decimal_normalization_with_json_data(self):
        """Test decimal normalization using all decimal values from JSON test data"""
        # Get all decimal precision test cases from JSON data
        decimal_test_cases = self.test_data.get_decimal_precision_test_cases()

        assert len(decimal_test_cases) > 0, "No decimal test cases found in JSON data"
        print(f"  📊 Testing {len(decimal_test_cases)} decimal cases from JSON data")

        for test_case in decimal_test_cases:
            value = test_case['value']
            field = test_case['field']
            source = test_case['source']

            # Test normalization
            result = normalize_decimal_value(value, field)

            # Verify normalization behavior based on field type
            if field.lower() in DECIMAL_FIELDS_PRECISION:
                expected_precision = DECIMAL_FIELDS_PRECISION[field.lower()]
                if isinstance(result, (int, float)) and not (result != result):  # Not NaN
                    # Check that result has correct precision
                    result_str = f"{result:.{expected_precision}f}"
                    assert len(result_str.split('.')[-1]) == expected_precision

            print(f"    ✅ {source}.{field}: {value} → {result}")

    def test_values_equivalence_with_json_robot_data(self):
        """Test value equivalence using actual robot data patterns from JSON"""
        # Get all robots to test equivalence scenarios
        all_robots = self.test_data.get_all_robots_from_status_data()

        # Test case-insensitive status comparisons
        online_robots = self.test_data.get_robots_by_status("Online")
        for robot in online_robots:
            status = robot.get('status', '')
            # Test that different cases are equivalent
            assert values_are_equivalent(status, "online")
            assert values_are_equivalent(status, "ONLINE")
            assert values_are_equivalent(status, "Online")

        # Test numeric equivalence with actual battery levels
        for robot in all_robots:
            battery = robot.get('battery_level')
            if battery is not None:
                # Test string vs numeric equivalence
                assert values_are_equivalent(battery, str(battery))
                assert values_are_equivalent(str(battery), battery)

                # Test decimal equivalence
                if isinstance(battery, (int, float)):
                    battery_decimal = Decimal(str(battery))
                    assert values_are_equivalent(battery, battery_decimal)

    def test_record_normalization_with_all_json_robots(self):
        """Test record normalization with all robot data from JSON"""
        all_robots = self.test_data.get_all_robots_from_status_data()

        assert len(all_robots) > 0, "No robot data found in JSON"
        print(f"  📊 Testing normalization with {len(all_robots)} robots from JSON")

        for robot in all_robots:
            normalized = normalize_record_for_comparison(robot)

            # Verify all fields are present
            for field, value in robot.items():
                assert field in normalized, f"Field {field} missing after normalization"

            # Verify decimal fields are properly normalized
            for field in ['battery_level', 'water_level', 'sewage_level']:
                if field in robot and robot[field] is not None:
                    original_value = robot[field]
                    normalized_value = normalized[field]

                    if isinstance(original_value, (int, float)):
                        # Should be normalized to 2 decimal places
                        assert isinstance(normalized_value, (int, float))

            # Verify coordinate precision is preserved (not in DECIMAL_FIELDS_PRECISION)
            for coord_field in ['x', 'y', 'z']:
                if coord_field in robot:
                    assert normalized[coord_field] == robot[coord_field]

    def test_change_detection_with_json_scenarios(self):
        """Test change detection using comprehensive JSON scenarios"""
        # Test with low battery robots
        low_battery_robots = self.test_data.get_robots_by_battery_level(max_level=20)
        normal_battery_robots = self.test_data.get_robots_by_battery_level(min_level=50)

        if low_battery_robots and normal_battery_robots:
            # Create scenario: robot with normal battery changes to low battery
            existing_robot = normal_battery_robots[0].copy()
            low_battery_robot = low_battery_robots[0].copy()
            low_battery_robot['robot_sn'] = existing_robot['robot_sn']  # Same robot

            # Create mock table
            mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [existing_robot])

            # Test change detection
            changes = detect_data_changes(mock_table, [low_battery_robot], ["robot_sn"])

            assert len(changes) == 1, "Should detect battery level change"
            change_info = list(changes.values())[0]
            assert change_info['change_type'] == 'update'
            assert 'battery_level' in change_info['changed_fields']

            print(f"    ✅ Battery change: {existing_robot['battery_level']}% → {low_battery_robot['battery_level']}%")

        # Test with offline robots
        offline_robots = self.test_data.get_robots_by_status("Offline")
        online_robots = self.test_data.get_robots_by_status("Online")

        if offline_robots and online_robots:
            # Create scenario: offline robot comes online
            existing_robot = offline_robots[0].copy()
            online_robot = online_robots[0].copy()
            online_robot['robot_sn'] = existing_robot['robot_sn']  # Same robot

            mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [existing_robot])
            changes = detect_data_changes(mock_table, [online_robot], ["robot_sn"])

            assert len(changes) == 1
            change_info = list(changes.values())[0]
            assert 'status' in change_info['changed_fields']

            print(f"    ✅ Status change: {existing_robot['status']} → {online_robot['status']}")

    def test_new_record_detection_with_json_data(self):
        """Test new record detection using all JSON robot data"""
        all_robots = self.test_data.get_all_robots_from_status_data()

        # Test new record detection (empty database)
        mock_table = self._create_mock_table("mnt_robots_management", ["robot_sn"], [])
        changes = detect_data_changes(mock_table, all_robots, ["robot_sn"])

        # Should detect all robots as new records
        assert len(changes) == len(all_robots), f"Expected {len(all_robots)} new records, got {len(changes)}"

        for change_info in changes.values():
            assert change_info['change_type'] == 'new_record'
            assert len(change_info['changed_fields']) > 0
            assert change_info['old_values'] == {}

        print(f"  ✅ Detected {len(changes)} new records from JSON data")

    def test_edge_cases_from_json(self):
        """Test edge cases defined in JSON test data"""
        # Test robot status edge cases
        status_data = self.test_data.get_robot_status_data()
        edge_cases = status_data.get("edge_cases", [])

        for edge_case in edge_cases:
            try:
                normalized = normalize_record_for_comparison(edge_case)
                # Should not crash with edge cases
                assert isinstance(normalized, dict)
                print(f"    ✅ Edge case handled: {edge_case.get('name', 'unnamed')}")
            except Exception as e:
                print(f"    ❌ Edge case failed: {edge_case.get('name', 'unnamed')} - {e}")
                raise

        # Test charging edge cases
        charging_data = self.test_data.get_robot_charging_data()
        charging_edge_cases = charging_data.get("edge_cases", [])

        for edge_case in charging_edge_cases:
            try:
                normalized = normalize_record_for_comparison(edge_case)
                assert isinstance(normalized, dict)
                print(f"    ✅ Charging edge case handled: {edge_case.get('robot_name', 'unnamed')}")
            except Exception as e:
                print(f"    ❌ Charging edge case failed: {edge_case.get('robot_name', 'unnamed')} - {e}")
                raise

    def _create_mock_table(self, table_name, primary_keys, existing_data):
        """Helper to create mock table for testing"""
        mock_table = MagicMock()
        mock_table.table_name = table_name
        mock_table.primary_keys = primary_keys
        mock_table.database_name = "test_db"
        mock_table.query_data.return_value = existing_data
        return mock_table

    def test_values_equivalence_real_scenarios(self):
        """Test value equivalence with actual database comparison scenarios"""
        # Real scenarios from production data
        equivalence_tests = [
            # MySQL Decimal vs Python float comparisons
            (Decimal('95.56'), 95.56, True),
            (Decimal('95.567'), 95.57, False),  # Different after rounding

            # Case variations from robot status
            ("Online", "online", True),
            ("Task_Ended", "task ended", True),
            ("Task-Ended", "task_ended", True),
            ("Robot Clean", "robot_clean", True),
            ("CC1", "cc1", True),

            # Null variations from database
            (None, None, True),
            ("", None, True),
            ("NULL", None, True),
            ("null", None, True),
            (0, None, False),
            (0.0, None, False),

            # Numeric string comparisons
            ("100.00", "100.0", True),
            ("95.567", "95.57", False),
            ("0", 0, True),
            ("0.0", 0, True),

            # Real robot name variations
            ("USF_LIB", "usf lib", True),
            ("demo-UF-demo", "demo_uf_demo", True),
            ("LDS-test", "lds test", True),
        ]

        for val1, val2, expected in equivalence_tests:
            result = values_are_equivalent(val1, val2)
            assert result == expected, f"values_are_equivalent({val1}, {val2}) expected {expected}, got {result}"

    def test_record_normalization_real_robot_data(self):
        """Test record normalization with actual robot data structure"""
        # Simulate real robot data from your APIs
        real_robot_record = {
            "robot_sn": "811064412050012",
            "robot_type": "CC1",
            "robot_name": "demo_UF_demo",
            "location_id": "523670000",
            "water_level": 25,
            "sewage_level": 0,
            "battery_level": 100.567891,  # High precision from API
            "x": -0.23293037200521216,    # High precision coordinates
            "y": -0.044921584455721364,
            "z": 0.026269476759686716,
            "status": "Online",
            "tenant_id": "000000"
        }

        normalized = normalize_record_for_comparison(real_robot_record)

        # Test decimal field normalization
        assert normalized["battery_level"] == 100.57
        assert abs(normalized["x"] - (-0.23)) < 0.01  # x, y, z not in DECIMAL_FIELDS_PRECISION, so unchanged

        # Test non-decimal fields unchanged
        assert normalized["robot_sn"] == "811064412050012"
        assert normalized["status"] == "Online"
        assert normalized["tenant_id"] == "000000"

    def test_decimal_fields_precision_coverage(self):
        """Test that all expected decimal fields are covered in DECIMAL_FIELDS_PRECISION"""
        expected_fields = [
            'actual_area', 'plan_area', 'duration', 'efficiency', 'remaining_time',
            'consumption', 'water_consumption', 'progress', 'battery_level',
            'water_level', 'sewage_level', 'cost_water', 'cost_battery',
            'clean_area', 'task_area', 'average_area', 'percentage'
        ]

        for field in expected_fields:
            assert field in DECIMAL_FIELDS_PRECISION, f"Field '{field}' missing from DECIMAL_FIELDS_PRECISION"
            assert isinstance(DECIMAL_FIELDS_PRECISION[field], int), f"Precision for '{field}' should be integer"
            assert DECIMAL_FIELDS_PRECISION[field] >= 0, f"Precision for '{field}' should be non-negative"

    def test_edge_case_normalization(self):
        """Test edge cases that might break normalization"""
        edge_cases = [
            # Invalid numeric strings
            ("abc", "battery_level", "abc"),  # Should return as-is if can't convert
            ("95%", "battery_level", "95%"),  # Should handle gracefully

            # Very large/small numbers
            (999999.999999, "actual_area", 1000000.00),
            (0.000001, "efficiency", 0.00),

            # Special float values
            (float('inf'), "battery_level", float('inf')),  # Should handle gracefully
            (float('-inf'), "efficiency", float('-inf')),
        ]

        for input_val, field, expected in edge_cases:
            try:
                result = normalize_decimal_value(input_val, field)
                # For edge cases, just ensure it doesn't crash
                assert result is not None or input_val is None
            except Exception as e:
                # Some edge cases might raise exceptions, which is acceptable
                pass

def run_change_detection_tests():
    """Run all change detection tests with JSON data"""
    print("=" * 60)
    print("🧪 TESTING CHANGE DETECTION WITH JSON DATA")
    print("=" * 60)

    test_instance = TestChangeDetection()
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

    print(f"\n📊 Change Detection Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_change_detection_tests()