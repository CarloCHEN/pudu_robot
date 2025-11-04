"""
Unit tests for data validation and sanitization using JSON test data
"""

import sys
sys.path.append('../../')

import pandas as pd
from pudu.notifications.change_detector import (
    normalize_decimal_value,
    normalize_record_for_comparison,
    DECIMAL_FIELDS_PRECISION
)
from pudu.apis.utils import convert_technical_string
from pudu.test.utils.test_helpers import TestDataLoader, TestValidator

class TestDataValidation:
    """Test data validation and sanitization with actual JSON data"""

    def setup_method(self):
        """Setup for each test"""
        self.test_data = TestDataLoader()
        self.validator = TestValidator()

    def test_decimal_precision_with_all_json_fields(self):
        """Test decimal precision normalization with all numeric fields from JSON"""
        print("  📐 Testing decimal precision with all JSON numeric fields")

        # Get all decimal test cases from JSON data
        decimal_cases = self.test_data.get_decimal_precision_test_cases()

        assert len(decimal_cases) > 0, "No decimal test cases found in JSON data"
        print(f"    📊 Testing {len(decimal_cases)} decimal cases from JSON")

        for case in decimal_cases:
            value = case['value']
            field = case['field']
            source = case['source']

            result = normalize_decimal_value(value, field)

            # Test that decimal fields are normalized correctly
            if field.lower() in DECIMAL_FIELDS_PRECISION:
                expected_precision = DECIMAL_FIELDS_PRECISION[field.lower()]
                if isinstance(result, (int, float)) and not pd.isna(result):
                    # Check precision is correct
                    decimal_places = len(str(result).split('.')[-1]) if '.' in str(result) else 0
                    assert decimal_places <= expected_precision + 1, f"Field {field}: too many decimal places"

            print(f"      ✅ {source}.{field}: {value} → {result}")

    def test_robot_data_structure_validation_with_json(self):
        """Test robot data structure validation using JSON robot data"""
        print("  🤖 Testing robot data structure validation with JSON")

        all_robots = self.test_data.get_all_robots_from_status_data()

        # Define required fields based on your actual API structure
        required_fields = ["robot_sn", "status"]
        optional_fields = ["robot_name", "robot_type", "battery_level", "water_level", "sewage_level"]

        for robot in all_robots:
            # Test required fields
            assert self.validator.validate_robot_data(robot, required_fields), f"Robot {robot.get('robot_sn')} missing required fields"

            # Test data type validation for numeric fields
            for field in ["battery_level", "water_level", "sewage_level"]:
                if field in robot and robot[field] is not None:
                    assert isinstance(robot[field], (int, float)), f"Field {field} should be numeric"

                    # Test reasonable ranges
                    if field.endswith('_level'):
                        assert 0 <= robot[field] <= 100, f"Field {field} should be 0-100 percentage"

    def test_coordinate_data_validation_with_json(self):
        """Test coordinate data validation using JSON robot data"""
        print("  📍 Testing coordinate data validation with JSON")

        robots_with_coords = [r for r in self.test_data.get_all_robots_from_status_data()
                             if 'x' in r and r['x'] is not None]

        for robot in robots_with_coords:
            # Test coordinate validation
            for coord in ['x', 'y', 'z']:
                if coord in robot and robot[coord] is not None:
                    assert isinstance(robot[coord], (int, float)), f"Coordinate {coord} should be numeric"

                    # Test that coordinates are reasonable (not extremely large)
                    assert abs(robot[coord]) < 1000, f"Coordinate {coord} seems unreasonably large: {robot[coord]}"

            # Test coordinate normalization (should preserve precision)
            normalized = normalize_record_for_comparison(robot)

            # Coordinates should NOT be in decimal precision list (preserve full precision)
            for coord in ['x', 'y', 'z']:
                if coord in robot:
                    assert normalized[coord] == robot[coord], f"Coordinate {coord} should preserve precision"

    def test_task_data_validation_with_json(self):
        """Test task data validation using JSON task data"""
        print("  📋 Testing task data validation with JSON")

        all_tasks = self.test_data.get_all_tasks_from_task_data()

        for task in all_tasks:
            # Test required task fields
            required_task_fields = ["robot_sn", "task_name"]
            assert self.validator.validate_robot_data(task, required_task_fields), f"Task missing required fields"

            # Test area fields
            for area_field in ["actual_area", "plan_area"]:
                if area_field in task and task[area_field] is not None:
                    assert isinstance(task[area_field], (int, float)), f"Area field {area_field} should be numeric"
                    assert task[area_field] >= 0, f"Area field {area_field} should be non-negative"

            # Test progress field
            if "progress" in task and task["progress"] is not None:
                assert isinstance(task["progress"], (int, float)), "Progress should be numeric"
                assert 0 <= task["progress"] <= 100, f"Progress should be 0-100, got {task['progress']}"

            # Test efficiency field
            if "efficiency" in task and task["efficiency"] is not None:
                assert isinstance(task["efficiency"], (int, float)), "Efficiency should be numeric"
                assert task["efficiency"] >= 0, "Efficiency should be non-negative"

    def test_event_data_validation_with_json(self):
        """Test event data validation using JSON event data"""
        print("  ⚠️ Testing event data validation with JSON")

        all_events = self.test_data.get_all_events()

        valid_event_levels = ["error", "warning", "fatal", "info", "debug"]

        for event in all_events:
            # Test required event fields
            required_event_fields = ["robot_sn", "event_type"]
            assert self.validator.validate_robot_data(event, required_event_fields), f"Event missing required fields"

            # Test event level validation
            if "event_level" in event:
                event_level = event["event_level"].lower()
                assert event_level in valid_event_levels, f"Invalid event level: {event_level}"

            # Test timestamp fields if present
            for time_field in ["task_time", "upload_time"]:
                if time_field in event and event[time_field] is not None:
                    # Should be either timestamp integer or string
                    assert isinstance(event[time_field], (int, str)), f"Time field {time_field} should be int or string"

    def test_charging_data_validation_with_json(self):
        """Test charging data validation using JSON charging data"""
        print("  🔋 Testing charging data validation with JSON")

        all_charging = self.test_data.get_all_charging_sessions()

        for session in all_charging:
            # Test required charging fields
            required_charging_fields = ["robot_sn"]
            assert self.validator.validate_robot_data(session, required_charging_fields), f"Charging session missing required fields"

            # Test power level fields
            for power_field in ["initial_power", "final_power"]:
                if power_field in session and session[power_field] is not None:
                    power_value = session[power_field]

                    # Handle percentage strings
                    if isinstance(power_value, str) and power_value.endswith('%'):
                        numeric_value = int(power_value[:-1])
                        assert 0 <= numeric_value <= 100, f"Power percentage should be 0-100: {power_value}"
                    elif isinstance(power_value, (int, float)):
                        assert 0 <= power_value <= 100, f"Power value should be 0-100: {power_value}"

    def test_technical_string_conversion_validation(self):
        """Test technical string conversion using real patterns from your codebase"""
        print("  🔧 Testing technical string conversion validation")

        # Test actual technical strings that appear in your event data
        technical_strings = [
            ("OdomSlip", "Odom Slip"),
            ("LostLocalization", "Lost Localization"),
            ("U_PHASE_HARDWARE_OVER_CURRENT", "U Phase Hardware Over Current"),
            ("LaserLocateLose", "Laser Locate Lose"),
            ("", ""),  # Empty string
            (None, None)  # None value
        ]

        for input_str, expected_output in technical_strings:
            result = convert_technical_string(input_str)
            assert result == expected_output, f"convert_technical_string({input_str}) expected '{expected_output}', got '{result}'"

    def test_data_sanitization_with_json_edge_cases(self):
        """Test data sanitization with edge cases from JSON"""
        print("  🧹 Testing data sanitization with JSON edge cases")

        # Get edge cases from all JSON files
        status_edge_cases = self.test_data.get_robot_status_data().get("edge_cases", [])
        charging_edge_cases = self.test_data.get_robot_charging_data().get("edge_cases", [])
        location_edge_cases = self.test_data.get_location_data().get("edge_cases", [])

        all_edge_cases = status_edge_cases + charging_edge_cases + location_edge_cases

        for edge_case in all_edge_cases:
            try:
                # Test that normalization doesn't crash on edge cases
                normalized = normalize_record_for_comparison(edge_case)
                assert isinstance(normalized, dict), "Normalization should return a dictionary"

                # Test that all original fields are present in normalized result
                for field in edge_case.keys():
                    assert field in normalized, f"Field {field} missing after normalization"

            except Exception as e:
                print(f"    ❌ Edge case failed: {edge_case} - {e}")
                raise

    def test_numeric_field_validation_with_json_ranges(self):
        """Test numeric field validation with actual value ranges from JSON"""
        print("  📊 Testing numeric field validation with JSON value ranges")

        # Get all numeric values from JSON data to understand actual ranges
        all_robots = self.test_data.get_all_robots_from_status_data()
        all_tasks = self.test_data.get_all_tasks_from_task_data()

        # Test battery level ranges from actual data
        battery_levels = [r.get('battery_level') for r in all_robots if r.get('battery_level') is not None]
        if battery_levels:
            for battery in battery_levels:
                assert 0 <= battery <= 100, f"Battery level out of range: {battery}"

                # Test normalization preserves valid range
                normalized = normalize_decimal_value(battery, 'battery_level')
                assert 0 <= normalized <= 100, f"Normalized battery out of range: {normalized}"

        # Test area values from task data
        area_fields = ['actual_area', 'plan_area']
        for task in all_tasks:
            for field in area_fields:
                if field in task and task[field] is not None:
                    area_value = task[field]
                    assert area_value >= 0, f"Area {field} should be non-negative: {area_value}"

                    # Test normalization
                    normalized = normalize_decimal_value(area_value, field)
                    assert normalized >= 0, f"Normalized area should be non-negative: {normalized}"

    def test_field_presence_validation_across_json_data(self):
        """Test field presence validation across all JSON data types"""
        print("  📋 Testing field presence validation across JSON data")

        # Define expected field patterns for each data type
        field_requirements = {
            "robot_status": {
                "required": ["robot_sn", "status"],
                "optional": ["robot_name", "robot_type", "battery_level", "water_level", "sewage_level", "x", "y", "z"]
            },
            "robot_task": {
                "required": ["robot_sn", "task_name"],
                "optional": ["mode", "sub_mode", "actual_area", "plan_area", "progress", "status", "efficiency"]
            },
            "robot_events": {
                "required": ["robot_sn", "event_type"],
                "optional": ["event_level", "event_detail", "error_id", "task_time", "upload_time"]
            },
            "robot_charging": {
                "required": ["robot_sn"],
                "optional": ["robot_name", "start_time", "end_time", "duration", "initial_power", "final_power", "power_gain"]
            }
        }

        # Validate each data type
        data_sources = {
            "robot_status": self.test_data.get_all_robots_from_status_data(),
            "robot_task": self.test_data.get_all_tasks_from_task_data(),
            "robot_events": self.test_data.get_all_events(),
            "robot_charging": self.test_data.get_all_charging_sessions()
        }

        for data_type, records in data_sources.items():
            requirements = field_requirements[data_type]

            for record in records:
                # Check required fields
                for req_field in requirements["required"]:
                    assert req_field in record, f"{data_type} record missing required field: {req_field}"
                    assert record[req_field] is not None, f"{data_type} required field {req_field} is None"

                # Optional fields can be missing or None, but if present should be valid
                for opt_field in requirements["optional"]:
                    if opt_field in record and record[opt_field] is not None:
                        # Field is present and not None, validate it
                        if opt_field in ["battery_level", "water_level", "sewage_level", "progress"]:
                            assert isinstance(record[opt_field], (int, float)), f"Percentage field {opt_field} should be numeric"
                            assert 0 <= record[opt_field] <= 100, f"Percentage field {opt_field} should be 0-100"

def run_data_validation_tests():
    """Run all data validation tests with JSON data"""
    print("=" * 70)
    print("🧪 TESTING DATA VALIDATION WITH JSON DATA")
    print("=" * 70)

    test_instance = TestDataValidation()
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

    print(f"\n📊 Data Validation Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_data_validation_tests()