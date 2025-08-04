"""
Unit tests for data validation and sanitization
"""

import sys
# Add src to Python path
sys.path.append('../../')

from pudu.notifications.change_detector import normalize_decimal_value, normalize_record_for_comparison
from pudu.test.utils.test_helpers import TestDataLoader, TestValidator

class TestDataValidation:
    """Test data validation and sanitization"""

    def setup_method(self):
        """Setup for each test"""
        self.test_data = TestDataLoader()
        self.validator = TestValidator()

    def test_decimal_precision_handling(self):
        """Test decimal precision normalization"""
        # Test various decimal fields
        test_cases = [
            ("battery_level", 95.567, 95.57),
            ("actual_area", 150.555, 150.56),
            ("efficiency", 0.123456, 0.12),
            ("progress", 75.999, 76.00)
        ]

        for field_name, input_value, expected in test_cases:
            result = normalize_decimal_value(input_value, field_name)
            assert abs(result - expected) < 0.01, f"Field {field_name}: expected {expected}, got {result}"

    def test_robot_data_validation(self):
        """Test robot data structure validation"""
        status_data = self.test_data.get_robot_status_data()
        valid_robots = status_data.get("valid_robots", [])

        required_fields = ["robot_sn", "status", "battery_level"]

        for robot in valid_robots:
            assert self.validator.validate_robot_data(robot, required_fields)

def run_data_validation_tests():
    """Run all data validation tests"""
    print("=" * 60)
    print("🧪 RUNNING DATA VALIDATION TESTS")
    print("=" * 60)

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

    print(f"\n📊 Data Validation Tests Summary: {passed} passed, {failed} failed")
    return passed, failed

if __name__ == "__main__":
    run_data_validation_tests()