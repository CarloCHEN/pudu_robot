#!/usr/bin/env python3
"""
Updated test runner for Pudu Robot Data Pipeline - runs comprehensive tests against real functions with JSON data
"""

import argparse
import sys
import time
from pathlib import Path

# Add the src directory to the path so we can import modules
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

def run_test_file(test_file_path):
    """Run a specific test file"""
    if test_file_path.exists():
        try:
            print(f"\n➤ Running {test_file_path.name}")

            # Import and run the test module
            spec = None
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("test_module", test_file_path)
                test_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(test_module)

                # Look for main test runner function - updated function names
                if hasattr(test_module, 'run_change_detection_tests'):
                    passed, failed = test_module.run_change_detection_tests()
                elif hasattr(test_module, 'run_batch_insert_tests'):
                    passed, failed = test_module.run_batch_insert_tests()
                elif hasattr(test_module, 'run_notification_tests'):
                    passed, failed = test_module.run_notification_tests()
                elif hasattr(test_module, 'run_data_processing_tests'):
                    passed, failed = test_module.run_data_processing_tests()
                elif hasattr(test_module, 'run_data_validation_tests'):
                    passed, failed = test_module.run_data_validation_tests()
                elif hasattr(test_module, 'run_rds_functions_tests'):
                    passed, failed = test_module.run_rds_functions_tests()
                elif hasattr(test_module, 'run_real_scenario_tests'):
                    passed, failed = test_module.run_real_scenario_tests()
                elif hasattr(test_module, 'run_integration_tests'):
                    passed, failed = test_module.run_integration_tests()
                else:
                    print(f"⚠️ No test runner function found in {test_file_path.name}")
                    return False

                return failed == 0

            except ImportError as e:
                print(f"❌ Import error in {test_file_path.name}: {e}")
                return False

        except Exception as e:
            print(f"❌ Error running {test_file_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"⚠️ {test_file_path.name} - NOT FOUND")
        return False

def run_unit_tests():
    """Run updated unit tests with JSON data"""
    print("\n" + "=" * 60)
    print("🧪 RUNNING UPDATED UNIT TESTS WITH JSON DATA")
    print("=" * 60)

    test_files = [
        "unit/test_change_detection.py",
        "unit/test_data_processing.py",
        "unit/test_notifications.py",
        "unit/test_data_validation.py",
        "unit/test_batch_insert.py",
        "unit/test_rds_functions.py",
        "unit/test_real_scenarios.py"
    ]

    passed = 0
    failed = 0
    test_dir = Path(__file__).parent

    for test_file in test_files:
        test_path = test_dir / test_file
        if run_test_file(test_path):
            passed += 1
            print(f"✅ {test_file} - PASSED")
        else:
            failed += 1
            print(f"❌ {test_file} - FAILED")

    return passed, failed

def run_integration_tests():
    """Run updated integration tests with JSON data"""
    print("\n" + "=" * 60)
    print("🔗 RUNNING UPDATED INTEGRATION TESTS WITH JSON DATA")
    print("=" * 60)

    test_files = [
        "integration/test_pipeline.py"
    ]

    passed = 0
    failed = 0
    test_dir = Path(__file__).parent

    for test_file in test_files:
        test_path = test_dir / test_file
        if run_test_file(test_path):
            passed += 1
            print(f"✅ {test_file} - PASSED")
        else:
            failed += 1
            print(f"❌ {test_file} - FAILED")

    return passed, failed

def validate_test_environment():
    """Validate that test environment is properly set up"""
    print("🔍 Validating test environment...")

    test_dir = Path(__file__).parent

    # Check that JSON test data files exist
    required_json_files = [
        "test_data/robot_status_data.json",
        "test_data/robot_task_data.json",
        "test_data/robot_event_data.json",
        "test_data/robot_charging_data.json",
        "test_data/location_data.json",
        "test_data/comprehensive_test_data.json"
    ]

    missing_files = []
    for json_file in required_json_files:
        json_path = test_dir / json_file
        if not json_path.exists():
            missing_files.append(json_file)

    if missing_files:
        print(f"❌ Missing JSON test data files: {missing_files}")
        return False

    # Check that test_helpers.py exists
    helpers_path = test_dir / "utils" / "test_helpers.py"
    if not helpers_path.exists():
        print("❌ Missing test_helpers.py")
        return False

    # Try to import test helpers
    try:
        sys.path.insert(0, str(test_dir))
        from utils.test_helpers import TestDataLoader, TestValidator
        loader = TestDataLoader()

        # Test that we can load data
        robot_data = loader.get_robot_status_data()
        if not robot_data:
            print("❌ Could not load robot status data from JSON")
            return False

    except Exception as e:
        print(f"❌ Could not import or use test helpers: {e}")
        return False

    print("✅ Test environment validation successful")
    return True

def main():
    """Main test runner with environment validation"""
    parser = argparse.ArgumentParser(description="Updated Pudu Pipeline Test Suite with JSON Data")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--test-file", help="Run specific test file (e.g., unit/test_change_detection.py)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip environment validation")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    start_time = time.time()
    total_passed = 0
    total_failed = 0

    print("=" * 80)
    print("🚀 PUDU ROBOT DATA PIPELINE TEST SUITE (UPDATED WITH JSON DATA)")
    print("=" * 80)
    print(f"📂 Test directory: {Path(__file__).parent}")
    print(f"📁 Source path: {src_path}")
    print("=" * 80)

    # Validate test environment unless skipped
    if not args.skip_validation:
        if not validate_test_environment():
            print("\n❌ Test environment validation failed")
            print("   Please ensure all JSON test data files are present")
            return 1

    if args.test_file:
        print(f"\n🎯 Running specific test file: {args.test_file}")
        test_path = Path(__file__).parent / args.test_file
        if run_test_file(test_path):
            total_passed = 1
        else:
            total_failed = 1
    else:
        if not args.integration_only:
            unit_passed, unit_failed = run_unit_tests()
            total_passed += unit_passed
            total_failed += unit_failed

        if not args.unit_only:
            int_passed, int_failed = run_integration_tests()
            total_passed += int_passed
            total_failed += int_failed

    end_time = time.time()
    duration = end_time - start_time

    print("\n" + "=" * 80)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 80)
    print(f"⏱️  Total execution time: {duration:.2f} seconds")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"📊 Success rate: {(total_passed/(total_passed+total_failed)*100):.1f}%" if (total_passed+total_failed) > 0 else "No tests")

    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ The Pudu pipeline is ready for deployment")
        print("📊 All tests now use realistic JSON data instead of mocks")
        print("🔧 Tests validate actual business logic and data flows")
    else:
        print(f"\n⚠️  {total_failed} test(s) failed")
        print("❌ Please review failed tests before deployment")

    print("=" * 80)
    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())