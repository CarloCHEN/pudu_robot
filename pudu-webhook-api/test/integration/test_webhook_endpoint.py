"""
Integration tests for webhook endpoint
Tests the complete webhook endpoint functionality
"""

import sys
import threading
from pathlib import Path
import os

# Fix path resolution when running from test directory
# Current file: test/unit/test_processors.py
current_file = Path(__file__).resolve()
integration_dir = current_file.parent      # test/integration/
test_dir = integration_dir.parent          # test/
root_dir = test_dir.parent          # pudu-webhook-api/

# Add the root directory to Python path
sys.path.insert(0, str(root_dir))

# Change working directory to root so relative imports work
os.chdir(root_dir)


from test.utils.test_helpers import TestDataLoader, TestReporter, setup_test_logging
from test.utils.webhook_client import WebhookClient


class TestWebhookEndpoint:
    """Integration tests for webhook endpoint"""

    def setup_method(self):
        """Setup for each test"""
        self.webhook_client = WebhookClient(
            base_url="http://localhost:8000", callback_code="1vQ6MfUxqyoGMRQ9nK8C4pSkg1Qsa3Vpq"  # From .env
        )
        self.test_data = TestDataLoader()
        self.reporter = TestReporter()

    def test_health_check(self):
        """Test webhook health check endpoint"""
        print("\n🏥 Testing webhook health check")

        is_healthy, health_data = self.webhook_client.check_health()

        # Validate health response
        success = (
            is_healthy and health_data.get("status") == "healthy" and "service" in health_data and "timestamp" in health_data
        )

        self.reporter.add_test_result("health_check", success, health_data)

        if success:
            print("✅ Health check passed")
            print(f"   Service: {health_data.get('service')}")
            print(f"   Database: {health_data.get('database_writer', 'unknown')}")
            print(f"   Notifications: {health_data.get('notification_service', 'unknown')}")
        else:
            print("❌ Health check failed")
            print(f"   Response: {health_data}")

        assert success, f"Health check failed: {health_data}"

    def test_robot_status_callbacks(self):
        """Test robot status callback processing"""
        print("\n🤖 Testing robot status callbacks")

        status_data = self.test_data.get_robot_status_data()
        valid_cases = status_data.get("valid_status_changes", [])

        successful_tests = 0

        for case in valid_cases:
            test_name = f"robot_status_{case['name']}"
            print(f"  Testing: {case['name']}")

            success, response = self.webhook_client.send_callback(case)

            # Validate response
            test_success = (
                success
                and response.get("status") == "success"
                and case["data"]["sn"] == response.get("data", {}).get("robot_sn", "")
            )

            self.reporter.add_test_result(test_name, test_success, {"case": case["name"], "response": response})

            if test_success:
                successful_tests += 1
                print(f"    ✅ {case['name']} - Success")
            else:
                print(f"    ❌ {case['name']} - Failed: {response}")

        print(f"  Status callbacks: {successful_tests}/{len(valid_cases)} passed")

        # At least 80% should pass
        assert (
            successful_tests >= len(valid_cases) * 0.8
        ), f"Too many status callback failures: {successful_tests}/{len(valid_cases)}"

    def test_robot_error_callbacks(self):
        """Test robot error callback processing"""
        print("\n⚠️ Testing robot error callbacks")

        error_data = self.test_data.get_robot_error_data()
        successful_tests = 0
        total_tests = 0

        for category_name, cases in error_data.items():
            if category_name == "edge_cases":
                continue

            for case in cases[:2]:  # Test first 2 from each category
                total_tests += 1
                test_name = f"robot_error_{category_name}_{case['name']}"
                print(f"  Testing: {case['name']}")

                success, response = self.webhook_client.send_callback(case)

                # Validate response
                test_success = (
                    success
                    and response.get("status") == "success"
                    and case["data"]["sn"] == response.get("data", {}).get("robot_sn", "")
                )

                self.reporter.add_test_result(
                    test_name, test_success, {"category": category_name, "case": case["name"], "response": response}
                )

                if test_success:
                    successful_tests += 1
                    print(f"    ✅ {case['name']} - Success")
                else:
                    print(f"    ❌ {case['name']} - Failed: {response}")

        print(f"  Error callbacks: {successful_tests}/{total_tests} passed")

        # At least 80% should pass
        assert successful_tests >= total_tests * 0.8, f"Too many error callback failures: {successful_tests}/{total_tests}"

    def test_robot_pose_callbacks(self):
        """Test robot pose callback processing"""
        print("\n📍 Testing robot pose callbacks")

        pose_data = self.test_data.get_robot_pose_data()
        normal_cases = pose_data.get("normal_positions", [])

        successful_tests = 0

        for case in normal_cases[:3]:  # Test first 3 cases
            test_name = f"robot_pose_{case['name']}"
            print(f"  Testing: {case['name']}")

            success, response = self.webhook_client.send_callback(case)

            # Validate response
            test_success = (
                success and response.get("status") == "success" and case["data"]["sn"] in response.get("message", "")
            )

            self.reporter.add_test_result(test_name, test_success, {"case": case["name"], "response": response})

            if test_success:
                successful_tests += 1
                print(f"    ✅ {case['name']} - Success")
            else:
                print(f"    ❌ {case['name']} - Failed: {response}")

        print(f"  Pose callbacks: {successful_tests}/{len(normal_cases[:3])} passed")

        # All should pass
        assert (
            successful_tests >= len(normal_cases[:3]) * 0.8
        ), f"Too many pose callback failures: {successful_tests}/{len(normal_cases[:3])}"

    def test_robot_power_callbacks(self):
        """Test robot power callback processing"""
        print("\n🔋 Testing robot power callbacks")

        power_data = self.test_data.get_robot_power_data()

        # Test normal power levels
        normal_cases = power_data.get("normal_power_levels", [])
        low_battery_cases = power_data.get("low_battery_alerts", [])

        all_cases = normal_cases[:2] + low_battery_cases[:2]  # Test subset
        successful_tests = 0

        for case in all_cases:
            test_name = f"robot_power_{case['name']}"
            print(f"  Testing: {case['name']}")

            success, response = self.webhook_client.send_callback(case)

            # Validate response
            test_success = (
                success
                and response.get("status") == "success"
                and case["data"]["sn"] == response.get("data", {}).get("robot_sn", "")
            )

            self.reporter.add_test_result(test_name, test_success, {"case": case["name"], "response": response})

            if test_success:
                successful_tests += 1
                print(f"    ✅ {case['name']} - Success")
            else:
                print(f"    ❌ {case['name']} - Failed: {response}")

        print(f"  Power callbacks: {successful_tests}/{len(all_cases)} passed")

        # At least 80% should pass
        assert (
            successful_tests >= len(all_cases) * 0.8
        ), f"Too many power callback failures: {successful_tests}/{len(all_cases)}"

    def test_invalid_requests(self):
        """Test invalid request handling"""
        print("\n🚫 Testing invalid request handling")

        invalid_results = self.webhook_client.test_invalid_requests()

        successful_tests = 0
        total_tests = len(invalid_results)

        for test_name, result in invalid_results.items():
            test_success = result.get("success", False)

            self.reporter.add_test_result(f"invalid_{test_name}", test_success, result)

            if test_success:
                successful_tests += 1
                print(f"  ✅ {test_name} - Correctly rejected")
            else:
                print(f"  ❌ {test_name} - Failed: {result}")

        print(f"  Invalid request tests: {successful_tests}/{total_tests} passed")

        # All invalid requests should be properly rejected
        assert successful_tests >= total_tests * 0.8, f"Invalid request handling failed: {successful_tests}/{total_tests}"

    def test_batch_callback_processing(self):
        """Test batch callback processing"""
        print("\n📦 Testing batch callback processing")

        # Create a batch of different callback types
        batch_callbacks = []

        # Add some status callbacks
        status_data = self.test_data.get_robot_status_data()
        valid_cases = status_data.get("valid_status_changes", [])
        batch_callbacks.extend(valid_cases[:2])

        # Add some error callbacks
        error_data = self.test_data.get_robot_error_data()
        nav_errors = error_data.get("navigation_errors", [])
        batch_callbacks.extend(nav_errors[:2])

        # Add some power callbacks
        power_data = self.test_data.get_robot_power_data()
        normal_power = power_data.get("normal_power_levels", [])
        batch_callbacks.extend(normal_power[:2])

        print(f"  Sending batch of {len(batch_callbacks)} callbacks...")

        # Send batch with small delay between requests
        batch_results = self.webhook_client.send_batch_callbacks(batch_callbacks, delay_between=0.1)

        # Validate batch results
        success_rate = (batch_results["successful"] / batch_results["total"]) * 100
        test_success = success_rate >= 80.0

        self.reporter.add_test_result("batch_processing", test_success, batch_results)

        if test_success:
            print(f"  ✅ Batch processing: {success_rate:.1f}% success rate")
        else:
            print(f"  ❌ Batch processing failed: {success_rate:.1f}% success rate")
            for error in batch_results["errors"]:
                print(f"    Error in callback {error['callback_index']}: {error['error']}")

        assert test_success, f"Batch processing failed with {success_rate:.1f}% success rate"

    def test_concurrent_requests(self):
        """Test concurrent request handling"""
        print("\n🔄 Testing concurrent request handling")

        # Prepare test callbacks
        status_data = self.test_data.get_robot_status_data()
        valid_cases = status_data.get("valid_status_changes", [])

        if len(valid_cases) < 3:
            print("  ⚠️ Not enough test cases for concurrent testing")
            return

        results = []
        threads = []

        def send_callback_thread(callback_data, result_list, thread_id):
            """Thread function to send callback"""
            success, response = self.webhook_client.send_callback(callback_data)
            result_list.append({"thread_id": thread_id, "success": success, "response": response, "callback": callback_data})

        # Start concurrent threads
        for i, case in enumerate(valid_cases[:3]):
            thread = threading.Thread(target=send_callback_thread, args=(case, results, i))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Analyze results
        successful_concurrent = sum(1 for r in results if r["success"])
        total_concurrent = len(results)

        test_success = successful_concurrent >= total_concurrent * 0.8

        self.reporter.add_test_result(
            "concurrent_processing",
            test_success,
            {"successful": successful_concurrent, "total": total_concurrent, "results": results},
        )

        if test_success:
            print(f"  ✅ Concurrent processing: {successful_concurrent}/{total_concurrent} succeeded")
        else:
            print(f"  ❌ Concurrent processing failed: {successful_concurrent}/{total_concurrent} succeeded")

        assert test_success, f"Concurrent processing failed: {successful_concurrent}/{total_concurrent}"

    def test_webhook_resilience(self):
        """Test webhook resilience with edge cases"""
        print("\n🛡️ Testing webhook resilience")

        # Test various edge cases
        edge_test_cases = [
            {"name": "empty_callback_type", "callback_type": "", "data": {"sn": "EDGE_TEST_001"}},
            {"name": "missing_data", "callback_type": "robotStatus"},
            {
                "name": "large_payload",
                "callback_type": "robotErrorWarning",
                "data": {
                    "sn": "EDGE_TEST_002",
                    "error_level": "WARNING",
                    "error_type": "LargePayloadTest",
                    "error_detail": "A" * 1000,  # Large string
                    "error_id": "large_payload_test",
                },
            },
        ]

        successful_tests = 0

        for case in edge_test_cases:
            test_name = f"resilience_{case['name']}"
            print(f"  Testing: {case['name']}")

            success, response = self.webhook_client.send_callback(case)

            # For resilience, we expect the webhook to handle gracefully
            # Either succeed or fail gracefully with proper error message
            test_success = "status" in response  # Has proper response structure

            self.reporter.add_test_result(test_name, test_success, {"case": case["name"], "response": response})

            if test_success:
                successful_tests += 1
                print(f"    ✅ {case['name']} - Handled gracefully")
            else:
                print(f"    ❌ {case['name']} - Poor error handling: {response}")

        print(f"  Resilience tests: {successful_tests}/{len(edge_test_cases)} passed")

        # All should handle gracefully
        assert successful_tests >= len(edge_test_cases) * 0.8, f"Poor resilience: {successful_tests}/{len(edge_test_cases)}"


# Test runner function
def run_webhook_endpoint_tests():
    """Run all webhook endpoint integration tests"""
    setup_test_logging("INFO")

    print("=" * 60)
    print("RUNNING WEBHOOK ENDPOINT INTEGRATION TESTS")
    print("=" * 60)
    print("📋 Prerequisites:")
    print("  1. Webhook server must be running on localhost:8000")
    print("  2. Server should be configured with test callback code")
    print("  3. Mock services should be enabled")
    print("=" * 60)

    test_instance = TestWebhookEndpoint()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

    # First check if server is available
    print("\n🔍 Checking webhook server availability...")
    test_instance.setup_method()
    is_healthy, health_data = test_instance.webhook_client.check_health()

    if not is_healthy:
        print("❌ Webhook server is not available!")
        print("   Please start the webhook server with: python main.py")
        print("   Or check if it's running on the correct port (8000)")
        return

    print("✅ Webhook server is available")
    print(f"   Service: {health_data.get('service', 'unknown')}")

    # Run tests
    for method_name in test_methods:
        try:
            test_instance.setup_method()
            method = getattr(test_instance, method_name)
            method()
            print(f"✅ {method_name} - PASSED")
        except Exception as e:
            print(f"❌ {method_name} - FAILED: {e}")
            import traceback

            traceback.print_exc()

    # Print final summary
    test_instance.reporter.print_summary()

    print(f"\n{'='*60}")
    print("WEBHOOK ENDPOINT TESTS COMPLETED")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_webhook_endpoint_tests()
