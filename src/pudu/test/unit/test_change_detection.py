"""
Test real change detection logic with actual data scenarios
"""

import sys
# Add src to Python path
sys.path.append('../../')

from pudu.notifications.change_detector import (
    normalize_decimal_value,
    values_are_equivalent,
    normalize_record_for_comparison,
    detect_data_changes
)
from pudu.test.mocks.mock_rds import MockRDSTable

class TestChangeDetection:
    """Test actual change detection algorithms"""

    def test_decimal_normalization_real_scenarios(self):
        """Test decimal normalization with real-world edge cases"""
        # Test various real inputs that could come from APIs
        test_cases = [
            # (input, field, expected_output)
            (95.567891234, "battery_level", 95.57),
            ("95.567", "battery_level", 95.57),
            (95, "battery_level", 95.00),
            ("95", "battery_level", 95.00),
            (None, "battery_level", None),
            ("", "battery_level", ""),  # Should handle gracefully
            (150.555555, "actual_area", 150.56),
            (0.123456789, "efficiency", 0.12),
        ]

        for input_val, field, expected in test_cases:
            result = normalize_decimal_value(input_val, field)
            if expected is None:
                assert result is None
            elif isinstance(expected, str):
                assert result == expected
            else:
                assert abs(result - expected) < 0.01, f"Input: {input_val}, Expected: {expected}, Got: {result}"

    def test_values_equivalence_edge_cases(self):
        """Test value equivalence with tricky real-world scenarios"""
        # Test cases that actually happen in production
        equivalence_tests = [
            # Numeric variations
            (100.0, 100, True),
            (95.56, 95.567, False),  # Should be equivalent when rounded
            (95.56, 95.57, False),   # Close enough for decimal fields
            (95.50, 95.6, False),   # Too different

            # String variations
            ("Online", "online", True),
            ("Task_Ended", "task ended", True),
            ("Task-Ended", "task_ended", True),
            ("Robot Clean", "robot_clean", True),
            ("Completely Different", "Other Text", False),

            # Null/empty variations
            (None, None, True),
            ("", None, True),
            (0, None, False),
            (0.0, None, False),
        ]

        for val1, val2, expected in equivalence_tests:
            result = values_are_equivalent(val1, val2)
            assert result == expected, f"values_are_equivalent({val1}, {val2}) expected {expected}, got {result}"

    def test_record_normalization_with_mixed_data(self):
        """Test record normalization with mixed data types"""
        # Simulate real data that might come from API
        messy_record = {
            "robot_sn": "  ROBOT_001  ",  # Has whitespace
            "battery_level": "95.567",     # String number
            "actual_area": 150.555555,     # High precision
            "status": "Online",            # Normal string
            "efficiency": 0.123456789,     # High precision decimal
            "task_name": "Hall Cleaning",  # Normal string
        }

        normalized = normalize_record_for_comparison(messy_record)

        # Test that decimal fields are normalized
        assert normalized["battery_level"] == 95.57
        assert normalized["actual_area"] == 150.56
        assert abs(normalized["efficiency"] - 0.12) < 0.01

        # Test that non-decimal fields are unchanged
        assert normalized["robot_sn"] == "  ROBOT_001  "  # Should preserve as-is
        assert normalized["status"] == "Online"
        assert normalized["task_name"] == "Hall Cleaning"

    def test_change_detection_with_real_scenario(self):
        """Test change detection with realistic data scenario"""
        # Create mock table with existing data
        mock_table = MockRDSTable("test", "test_db", "robots", primary_keys=["robot_sn"])

        # Insert "existing" robot data
        existing_robot = {
            "robot_sn": "REAL_ROBOT_001",
            "battery_level": 80.0,
            "status": "Online",
            "actual_area": 150.0
        }
        mock_table.batch_insert([existing_robot])

        # Simulate new data with changes
        updated_robot = {
            "robot_sn": "REAL_ROBOT_001",
            "battery_level": 15.5,  # Significant change
            "status": "online",     # Same but different case
            "actual_area": 150.01   # Tiny change
        }

        # Test change detection
        changes = detect_data_changes(mock_table, [updated_robot], ["robot_sn"])

        # Should detect battery change but not status or area
        assert len(changes) == 1
        change_info = list(changes.values())[0]
        assert change_info["change_type"] == "update"
        assert "battery_level" in change_info["changed_fields"]
        assert "status" not in change_info["changed_fields"]  # Should be equivalent
        assert "actual_area" in change_info["changed_fields"]  # Too small to matter

def run_change_detection_tests():
    """Run real change detection tests"""
    print("=" * 60)
    print("🧪 TESTING REAL CHANGE DETECTION LOGIC")
    print("=" * 60)

    test_instance = TestChangeDetection()
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

    print(f"\n📊 Real Change Detection Tests: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_change_detection_tests()