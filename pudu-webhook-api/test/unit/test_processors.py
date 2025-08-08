"""
Unit tests for individual processors
"""

import os
import sys
from pathlib import Path

# Fix path resolution when running from test directory
# Current file: test/unit/test_processors.py
current_file = Path(__file__).resolve()
unit_dir = current_file.parent      # test/unit/
test_dir = unit_dir.parent          # test/
root_dir = test_dir.parent          # pudu-webhook-api/

# Add the root directory to Python path
sys.path.insert(0, str(root_dir))

# Change working directory to root so relative imports work
os.chdir(root_dir)

# Import test utilities
from test.utils.test_helpers import TestDataLoader, TestValidator, setup_test_logging

# Import main modules
try:
    from models import CallbackStatus
    from processors import RobotErrorProcessor, RobotPoseProcessor, RobotPowerProcessor, RobotStatusProcessor
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"📍 Current working directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path[:3]}...")
    print("\n💡 Debug info:")
    print(f"   Root dir: {root_dir}")
    print(f"   Root dir exists: {root_dir.exists()}")
    print(f"   models.py exists: {(root_dir / 'models.py').exists()}")
    print(f"   processors.py exists: {(root_dir / 'processors.py').exists()}")
    sys.exit(1)

class TestRobotStatusProcessor:
    """Test RobotStatusProcessor"""

    def setup_method(self):
        """Setup for each test"""
        self.processor = RobotStatusProcessor()
        self.test_data = TestDataLoader().get_robot_status_data()

    def test_valid_status_changes(self):
        """Test all valid status changes"""
        valid_cases = self.test_data.get("valid_status_changes", [])

        for case in valid_cases:
            print(f"\n🧪 Testing: {case['name']}")

            response = self.processor.process(case["data"])

            # Validate response structure
            assert TestValidator.validate_callback_response(response.to_dict())

            # Validate specific expectations
            assert response.status == CallbackStatus.SUCCESS
            assert case["data"]["sn"] == response.data["robot_sn"]

            # Check data content
            if "data" in response.to_dict():
                assert response.data["robot_sn"] == case["data"]["sn"]
                assert response.data["status"] == case["expected_status"]

            print(f"✅ Passed: {case['name']}")

    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        edge_cases = self.test_data.get("edge_cases", [])

        for case in edge_cases:
            print(f"\n🧪 Testing edge case: {case['name']}")

            response = self.processor.process(case["data"])

            # Should still succeed for edge cases
            assert response.status == CallbackStatus.SUCCESS
            assert case["data"]["sn"] == response.data["robot_sn"]
            print(f"✅ Passed: {case['name']}")

    def test_invalid_cases(self):
        """Test invalid input handling"""
        # Test with None input
        response = self.processor.process(None)
        assert response.status == CallbackStatus.ERROR

        # Test with empty dict
        response = self.processor.process({})
        assert response.status == CallbackStatus.ERROR

        print("✅ Invalid cases handled correctly")


class TestRobotErrorProcessor:
    """Test RobotErrorProcessor"""

    def setup_method(self):
        """Setup for each test"""
        self.processor = RobotErrorProcessor()
        self.test_data = TestDataLoader().get_robot_error_data()

    def test_all_error_types(self):
        """Test all error types and severity levels"""
        for category_name, cases in self.test_data.items():
            # if category_name == 'edge_cases':
            #     continue

            print(f"\n🧪 Testing error category: {category_name}")

            for case in cases:
                print(f"  Testing: {case['name']}")

                response = self.processor.process(case["data"])

                # Validate response
                assert TestValidator.validate_callback_response(response.to_dict())
                assert response.status == CallbackStatus.SUCCESS

                # Check error details are captured
                if "data" in response.to_dict():
                    assert response.data["robot_sn"] == case["data"]["sn"]
                    assert response.data["error_type"] == case["data"]["error_type"]
                    assert (
                        response.data["error_level"] == case["data"]["error_level"] if "error_level" in case["data"] else True
                    )

                print(f"  ✅ Passed: {case['name']}")

    def test_severity_handling(self):
        """Test that different severity levels are handled correctly"""
        severities = ["FATAL", "ERROR", "WARNING", "EVENT"]

        for severity in severities:
            test_data = {
                "sn": "TEST_ROBOT_SEVERITY",
                "error_level": severity,
                "error_type": "TestError",
                "error_detail": f"Testing {severity} level",
                "error_id": f"test_{severity.lower()}",
                "timestamp": 1640995800,
            }

            response = self.processor.process(test_data)
            assert response.status == CallbackStatus.SUCCESS
            print(f"✅ {severity} severity handled correctly")


class TestRobotPoseProcessor:
    """Test RobotPoseProcessor"""

    def setup_method(self):
        """Setup for each test"""
        self.processor = RobotPoseProcessor()
        self.test_data = TestDataLoader().get_robot_pose_data()

    def test_normal_positions(self):
        """Test normal position updates"""
        normal_cases = self.test_data.get("normal_positions", [])

        for case in normal_cases:
            print(f"\n🧪 Testing position: {case['name']}")

            response = self.processor.process(case["data"])

            assert TestValidator.validate_callback_response(response.to_dict())
            assert response.status == CallbackStatus.SUCCESS

            # Check position data
            if "data" in response.to_dict():
                position = response.data["position"]
                assert position["x"] == case["data"]["x"]
                assert position["y"] == case["data"]["y"]
                assert position["yaw"] == case["data"]["yaw"]

            print(f"✅ Passed: {case['name']}")

    def test_boundary_positions(self):
        """Test boundary and extreme positions"""
        boundary_cases = self.test_data.get("boundary_positions", [])

        for case in boundary_cases:
            print(f"\n🧪 Testing boundary: {case['name']}")

            response = self.processor.process(case["data"])
            assert response.status == CallbackStatus.SUCCESS
            print(f"✅ Passed: {case['name']}")

    def test_precision_handling(self):
        """Test high precision coordinate handling"""
        precision_cases = self.test_data.get("precision_positions", [])

        for case in precision_cases:
            print(f"\n🧪 Testing precision: {case['name']}")

            response = self.processor.process(case["data"])
            assert response.status == CallbackStatus.SUCCESS
            print(f"✅ Passed: {case['name']}")


class TestRobotPowerProcessor:
    """Test RobotPowerProcessor"""

    def setup_method(self):
        """Setup for each test"""
        self.processor = RobotPowerProcessor()
        self.test_data = TestDataLoader().get_robot_power_data()

    def test_normal_power_levels(self):
        """Test normal power level processing"""
        normal_cases = self.test_data.get("normal_power_levels", [])

        for case in normal_cases:
            print(f"\n🧪 Testing power: {case['name']}")

            response = self.processor.process(case["data"])

            assert TestValidator.validate_callback_response(response.to_dict())
            assert response.status == CallbackStatus.SUCCESS

            # Check power data
            if "data" in response.to_dict():
                assert response.data["power"] == case["data"]["power"]
                assert response.data["charge_state"] == case["data"]["charge_state"]

            print(f"✅ Passed: {case['name']}")

    def test_low_battery_scenarios(self):
        """Test low battery alert scenarios"""
        low_battery_cases = self.test_data.get("low_battery_alerts", [])

        for case in low_battery_cases:
            print(f"\n🧪 Testing low battery: {case['name']}")

            response = self.processor.process(case["data"])
            assert response.status == CallbackStatus.SUCCESS
            print(f"✅ Passed: {case['name']}")

    def test_charging_scenarios(self):
        """Test charging state scenarios"""
        charging_cases = self.test_data.get("charging_scenarios", [])

        for case in charging_cases:
            print(f"\n🧪 Testing charging: {case['name']}")

            response = self.processor.process(case["data"])
            assert response.status == CallbackStatus.SUCCESS
            print(f"✅ Passed: {case['name']}")

    def test_edge_cases(self):
        """Test edge cases for power processing"""
        edge_cases = self.test_data.get("edge_cases", [])

        for case in edge_cases:
            print(f"\n🧪 Testing power edge case: {case['name']}")

            response = self.processor.process(case["data"])
            # Edge cases should still be processed without crashing
            assert response.status in [CallbackStatus.SUCCESS, CallbackStatus.WARNING]
            print(f"✅ Passed: {case['name']}")


# Test runner function
def run_processor_tests():
    """Run all processor tests"""
    setup_test_logging("DEBUG")

    print("=" * 60)
    print("RUNNING PROCESSOR UNIT TESTS")
    print("=" * 60)

    # Test each processor
    test_classes = [TestRobotStatusProcessor, TestRobotErrorProcessor, TestRobotPoseProcessor, TestRobotPowerProcessor]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{'='*40}")
        print(f"TESTING {test_class.__name__}")
        print(f"{'='*40}")

        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            try:
                test_instance.setup_method()
                method = getattr(test_instance, method_name)
                method()
                passed_tests += 1
                print(f"✅ {method_name} - PASSED")
            except Exception as e:
                print(f"❌ {method_name} - FAILED: {e}")

    print(f"\n{'='*60}")
    print("PROCESSOR TESTS SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_processor_tests()