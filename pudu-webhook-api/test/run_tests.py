#!/usr/bin/env python3
"""
Main test runner for Pudu Webhook API testing framework
Runs all tests in sequence and provides comprehensive reporting
"""

import sys
import os
import argparse
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test.utils.test_helpers import setup_test_logging
from test.unit.test_processors import run_processor_tests
from test.unit.test_database_writer import run_database_tests
from test.unit.test_notification_sender import run_notification_tests
from test.integration.test_webhook_endpoint import run_webhook_endpoint_tests
from test.integration.test_complete_flow import run_complete_flow_tests

class TestSuite:
    """Complete test suite runner"""

    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def run_unit_tests(self):
        """Run all unit tests"""
        print("\n" + "="*80)
        print("🧪 RUNNING UNIT TESTS")
        print("="*80)

        unit_tests = [
            ("Processors", run_processor_tests),
            ("Database Writer", run_database_tests),
            ("Notification Sender", run_notification_tests)
        ]

        for test_name, test_function in unit_tests:
            print(f"\n{'='*60}")
            print(f"Running {test_name} Tests")
            print(f"{'='*60}")

            try:
                test_function()
                self.test_results[test_name] = "PASSED"
            except Exception as e:
                print(f"❌ {test_name} tests failed: {e}")
                self.test_results[test_name] = f"FAILED: {e}"

    def run_integration_tests(self, run_endpoint_tests=False):
        """Run integration tests"""
        print("\n" + "="*80)
        print("🔗 RUNNING INTEGRATION TESTS")
        print("="*80)

        integration_tests = [
            ("Complete Flow", run_complete_flow_tests)
        ]

        # Only run endpoint tests if specifically requested
        if run_endpoint_tests:
            integration_tests.append(("Webhook Endpoint", run_webhook_endpoint_tests))

        for test_name, test_function in integration_tests:
            print(f"\n{'='*60}")
            print(f"Running {test_name} Tests")
            print(f"{'='*60}")

            try:
                test_function()
                self.test_results[test_name] = "PASSED"
            except Exception as e:
                print(f"❌ {test_name} tests failed: {e}")
                self.test_results[test_name] = f"FAILED: {e}"

    def run_all_tests(self, run_endpoint_tests=False):
        """Run complete test suite"""
        self.start_time = time.time()

        print("="*80)
        print("🚀 PUDU WEBHOOK API TEST SUITE")
        print("="*80)
        print("📋 Test Categories:")
        print("  • Unit Tests: Processors, Database Writer, Notification Sender")
        print("  • Integration Tests: Complete Flow" + (", Webhook Endpoint" if run_endpoint_tests else ""))
        print("="*80)

        # Run unit tests
        self.run_unit_tests()

        # Run integration tests
        self.run_integration_tests(run_endpoint_tests)

        self.end_time = time.time()

        # Print final summary
        self.print_final_summary()

    def print_final_summary(self):
        """Print comprehensive test summary"""
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0

        print("\n" + "="*80)
        print("📊 FINAL TEST SUITE SUMMARY")
        print("="*80)

        passed_tests = sum(1 for result in self.test_results.values() if result == "PASSED")
        total_tests = len(self.test_results)

        print(f"⏱️  Total execution time: {duration:.2f} seconds")
        print(f"📈 Test categories: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {total_tests - passed_tests}")
        print(f"📊 Success rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests")

        print(f"\n{'='*60}")
        print("DETAILED RESULTS:")
        print(f"{'='*60}")

        for test_name, result in self.test_results.items():
            if result == "PASSED":
                print(f"✅ {test_name}: {result}")
            else:
                print(f"❌ {test_name}: {result}")

        # Print recommendations
        failed_tests = [name for name, result in self.test_results.items() if result != "PASSED"]

        if failed_tests:
            print(f"\n{'='*60}")
            print("🔧 RECOMMENDATIONS:")
            print(f"{'='*60}")

            for failed_test in failed_tests:
                if "Processors" in failed_test:
                    print("• Check processor logic and test data validation")
                elif "Database" in failed_test:
                    print("• Verify database schema and configuration files")
                elif "Notification" in failed_test:
                    print("• Check notification service configuration and mock setup")
                elif "Endpoint" in failed_test:
                    print("• Ensure webhook server is running on localhost:8000")
                elif "Flow" in failed_test:
                    print("• Check complete integration pipeline configuration")
        else:
            print(f"\n🎉 ALL TESTS PASSED! The webhook API is ready for deployment.")

        print("="*80)

def main():
    """Main test runner entry point"""
    parser = argparse.ArgumentParser(description="Pudu Webhook API Test Suite")
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration-only",
        action="store_true",
        help="Run only integration tests"
    )
    parser.add_argument(
        "--include-endpoint",
        action="store_true",
        help="Include webhook endpoint tests (requires running server)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else args.log_level
    setup_test_logging(log_level)

    # Create test suite
    test_suite = TestSuite()

    # Run requested tests
    if args.unit_only:
        test_suite.start_time = time.time()
        test_suite.run_unit_tests()
        test_suite.end_time = time.time()
        test_suite.print_final_summary()
    elif args.integration_only:
        test_suite.start_time = time.time()
        test_suite.run_integration_tests(args.include_endpoint)
        test_suite.end_time = time.time()
        test_suite.print_final_summary()
    else:
        # Run all tests
        test_suite.run_all_tests(args.include_endpoint)

if __name__ == "__main__":
    main()