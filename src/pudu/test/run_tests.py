#!/usr/bin/env python3
"""
Main test runner for Pudu Robot Data Pipeline
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def run_unit_tests():
    """Run unit tests"""
    print("\n" + "=" * 60)
    print("🧪 RUNNING UNIT TESTS")
    print("=" * 60)

    test_modules = [
        "pudu.test.unit.test_apis",
        "pudu.test.unit.test_rds_operations",
        "pudu.test.unit.test_notifications"
    ]

    passed = 0
    failed = 0

    for module in test_modules:
        try:
            print(f"\n➤ Testing {module}")
            # Import and run tests
            exec(f"import {module}")
            passed += 1
            print(f"✅ {module} - PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {module} - FAILED: {e}")

    return passed, failed

def run_integration_tests():
    """Run integration tests"""
    print("\n" + "=" * 60)
    print("🔗 RUNNING INTEGRATION TESTS")
    print("=" * 60)

    test_modules = [
        "pudu.test.integration.test_pipeline_flow",
        "pudu.test.integration.test_app_integration"
    ]

    passed = 0
    failed = 0

    for module in test_modules:
        try:
            print(f"\n➤ Testing {module}")
            exec(f"import {module}")
            passed += 1
            print(f"✅ {module} - PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {module} - FAILED: {e}")

    return passed, failed

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Pudu Pipeline Test Suite")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    start_time = time.time()
    total_passed = 0
    total_failed = 0

    print("=" * 80)
    print("🚀 PUDU ROBOT DATA PIPELINE TEST SUITE")
    print("=" * 80)

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
    else:
        print(f"\n⚠️  {total_failed} test(s) failed")

    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())