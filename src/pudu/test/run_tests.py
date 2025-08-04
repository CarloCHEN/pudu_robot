#!/usr/bin/env python3
"""
Enhanced test runner for Pudu Robot Data Pipeline
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Correct path: from src/pudu/test/ to src/
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

def run_test_file(test_file_path):
    """Run a specific test file"""
    if test_file_path.exists():
        try:
            print(f"\n➤ Running {test_file_path.name}")

            # Read and execute the test file
            with open(test_file_path, 'r') as f:
                code = f.read()

            # Create a new namespace for execution
            namespace = {'__file__': str(test_file_path), '__name__': '__main__'}
            exec(code, namespace)

            return True
        except Exception as e:
            print(f"❌ Error running {test_file_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"⚠️ {test_file_path.name} - NOT FOUND")
        return False

def run_unit_tests():
    """Run unit tests"""
    print("\n" + "=" * 60)
    print("🧪 RUNNING UNIT TESTS")
    print("=" * 60)

    test_files = [
        "unit/test_data_validation.py",
        "unit/test_change_detection.py",
        "unit/test_notifications.py",
        "unit/test_data_processing.py"
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
    """Run integration tests"""
    print("\n" + "=" * 60)
    print("🔗 RUNNING INTEGRATION TESTS")
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

def main():
    """Enhanced main test runner"""
    parser = argparse.ArgumentParser(description="Pudu Pipeline Test Suite")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--test-file", help="Run specific test file (e.g., unit/test_apis.py)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    start_time = time.time()
    total_passed = 0
    total_failed = 0

    print("=" * 80)
    print("🚀 PUDU ROBOT DATA PIPELINE TEST SUITE")
    print("=" * 80)
    print(f"📂 Test directory: {Path(__file__).parent}")
    print(f"📁 Source path: {src_path}")
    print("=" * 80)

    if args.test_file:
        print(f"Running specific test file: {args.test_file}")
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
    else:
        print(f"\n⚠️  {total_failed} test(s) failed")
        print("❌ Please review failed tests before deployment")

    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())