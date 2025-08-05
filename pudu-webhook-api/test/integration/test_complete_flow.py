"""
Complete end-to-end flow tests
Tests the entire webhook processing pipeline with mock services
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test.mocks.mock_database import MockDatabaseWriter
from test.mocks.mock_notification import MockNotificationService
from test.utils.test_helpers import TestDataLoader, TestReporter, TestValidator, setup_test_logging

from callback_handler import CallbackHandler


class TestCompleteFlow:
    """Test complete webhook processing flow"""

    def setup_method(self):
        """Setup for each test"""
        self.callback_handler = CallbackHandler()
        self.mock_db_writer = MockDatabaseWriter()
        self.mock_notification_service = MockNotificationService()
        self.test_data = TestDataLoader()
        self.reporter = TestReporter()

    def test_robot_status_complete_flow(self):
        """Test complete robot status processing flow"""
        print("\n🔄 Testing complete robot status flow")

        status_data = self.test_data.get_robot_status_data()
        valid_cases = status_data.get("valid_status_changes", [])

        for case in valid_cases[:3]:  # Test first 3 cases
            test_name = f"complete_status_{case['name']}"
            print(f"  Testing: {case['name']}")

            # Clear previous data
            self.mock_db_writer.clear_written_data()
            self.mock_notification_service.clear_notifications()

            try:
                # Step 1: Process callback
                callback_response = self.callback_handler.process_callback(case)
                assert callback_response.status.value == "success"

                # Step 2: Write to database
                database_names, table_names, primary_key_values = self.callback_handler.write_to_database(case, self.mock_db_writer)

                # Step 3: Send notification (using mock import)
                with patch("notifications.notification_sender.send_webhook_notification") as mock_sender:

                    def mock_send_notification(callback_type, callback_data, payload, notification_service):
                        # Simulate notification sending
                        robot_sn = callback_data.get("sn")
                        if robot_sn:
                            return self.mock_notification_service.send_notification(
                                robot_id=robot_sn,
                                notification_type="robot_status",
                                title=f"Robot {case['data']['run_status']}",
                                content=f"Robot {robot_sn} status changed",
                                severity=case.get("expected_severity", "event"),
                                status=case.get("expected_status", "normal"),
                                payload=payload
                            )
                        return False

                    mock_sender.side_effect = mock_send_notification
                    for database_name, table_name in zip(database_names, table_names):
                        payload = {
                            "database_name": database_name,
                            "table_name": table_name,
                            "primary_key_values": primary_key_values
                        }
                        notification_sent = mock_sender(case["callback_type"], case["data"], payload, self.mock_notification_service)
                        assert notification_sent == True

                # Validate complete flow
                flow_success = True
                flow_details = {}

                # Check callback processing
                if callback_response.status.value != "success":
                    flow_success = False
                    flow_details["callback_processing"] = "Failed"
                else:
                    flow_details["callback_processing"] = "Success"

                # Check database write
                written_data = self.mock_db_writer.get_written_data()
                if not TestValidator.validate_database_write(written_data, "mnt_robots_management", case["data"]["sn"]):
                    flow_success = False
                    flow_details["database_write"] = "Failed"
                else:
                    flow_details["database_write"] = "Success"

                # Check notification
                sent_notifications = self.mock_notification_service.get_sent_notifications(case["data"]["sn"])
                if len(sent_notifications) != len(database_names):
                    flow_success = False
                    flow_details["notification_send"] = "Failed"
                else:
                    flow_details["notification_send"] = "Success"

                self.reporter.add_test_result(test_name, flow_success, flow_details)

                if flow_success:
                    print(f"    ✅ Complete flow successful for {case['name']}")
                else:
                    print(f"    ❌ Flow failed for {case['name']}: {flow_details}")

            except Exception as e:
                self.reporter.add_test_result(test_name, False, {"error": str(e)})
                print(f"    ❌ Exception in flow for {case['name']}: {e}")

    def test_robot_error_complete_flow(self):
        """Test complete robot error processing flow"""
        print("\n⚠️ Testing complete robot error flow")

        error_data = self.test_data.get_robot_error_data()

        # Test one case from each error category
        categories_to_test = ["navigation_errors", "hardware_errors", "sensor_errors"]

        for category in categories_to_test:
            cases = error_data.get(category, [])
            if not cases:
                continue

            case = cases[0]  # Test first case from category
            test_name = f"complete_error_{category}"
            print(f"  Testing: {category} - {case['name']}")

            # Clear previous data
            self.mock_db_writer.clear_written_data()
            self.mock_notification_service.clear_notifications()

            try:
                # Step 1: Process callback
                callback_response = self.callback_handler.process_callback(case)

                # Step 2: Write to database
                database_names, table_names, primary_key_values = self.callback_handler.write_to_database(case, self.mock_db_writer)

                # Step 3: Send notification
                with patch("notifications.notification_sender.send_webhook_notification") as mock_sender:

                    def mock_send_notification(callback_type, callback_data, notification_service):
                        robot_sn = callback_data.get("sn")
                        if robot_sn:
                            return self.mock_notification_service.send_notification(
                                robot_id=robot_sn,
                                notification_type="robot_status",
                                title=f"Robot Error: {callback_data.get('error_type', 'Unknown')}",
                                content=f"Robot {robot_sn} error: {callback_data.get('error_detail', '')}",
                                severity=case.get("expected_severity", "error"),
                                status="abnormal",
                            )
                        return False
                    for database_name, table_name in zip(database_names, table_names):
                        payload = {
                            "database_name": database_name,
                            "table_name": table_name,
                            "primary_key_values": primary_key_values
                        }
                        notification_sent = mock_sender(case["callback_type"], case["data"], payload, self.mock_notification_service)
                        assert notification_sent == True

                # Validate complete flow
                flow_success = True
                flow_details = {}

                # Check callback processing
                if callback_response.status.value != "success":
                    flow_success = False
                    flow_details["callback_processing"] = "Failed"

                # Check database write (events go to mnt_robot_events table)
                written_data = self.mock_db_writer.get_written_data()
                if not TestValidator.validate_database_write(written_data, "mnt_robot_events", case["data"]["sn"]):
                    flow_success = False
                    flow_details["database_write"] = "Failed"

                # Check notification
                sent_notifications = self.mock_notification_service.get_sent_notifications(case["data"]["sn"])
                if len(sent_notifications) != len(database_names):
                    flow_success = False
                    flow_details["notification_send"] = "Failed"

                self.reporter.add_test_result(test_name, flow_success, flow_details)

                if flow_success:
                    print(f"    ✅ Complete error flow successful for {category}")
                else:
                    print(f"    ❌ Error flow failed for {category}: {flow_details}")

            except Exception as e:
                self.reporter.add_test_result(test_name, False, {"error": str(e)})
                print(f"    ❌ Exception in error flow for {category}: {e}")

    def test_robot_power_complete_flow(self):
        """Test complete robot power processing flow"""
        print("\n🔋 Testing complete robot power flow")

        power_data = self.test_data.get_robot_power_data()
        low_battery_cases = power_data.get("low_battery_alerts", [])

        for case in low_battery_cases[:2]:  # Test first 2 low battery cases
            test_name = f"complete_power_{case['name']}"
            print(f"  Testing: {case['name']}")

            # Clear previous data
            self.mock_db_writer.clear_written_data()
            self.mock_notification_service.clear_notifications()

            try:
                # Step 1: Process callback
                callback_response = self.callback_handler.process_callback(case)

                # Step 2: Write to database
                database_names, table_names, primary_key_values = self.callback_handler.write_to_database(case, self.mock_db_writer)

                # Step 3: Send notification
                with patch("notifications.notification_sender.send_webhook_notification") as mock_sender:

                    def mock_send_notification(callback_type, callback_data, notification_service):
                        robot_sn = callback_data.get("sn")
                        power_level = callback_data.get("power", 0)
                        if robot_sn and case.get("expected_notification", False):
                            return self.mock_notification_service.send_notification(
                                robot_id=robot_sn,
                                notification_type="robot_status",
                                title=f"Battery Alert: {power_level}%",
                                content=f"Robot {robot_sn} battery at {power_level}%",
                                severity=case.get("expected_severity", "warning"),
                                status="warning",
                            )
                        return True  # Return True even if no notification needed

                    mock_sender.side_effect = mock_send_notification
                    for database_name, table_name in zip(database_names, table_names):
                        payload = {
                            "database_name": database_name,
                            "table_name": table_name,
                            "primary_key_values": primary_key_values
                        }
                        notification_sent = mock_sender(case["callback_type"], case["data"], payload, self.mock_notification_service)
                        assert notification_sent == True

                # Validate complete flow
                flow_success = True
                flow_details = {}

                # Check callback processing
                if callback_response.status.value != "success":
                    flow_success = False
                    flow_details["callback_processing"] = "Failed"

                # Check database write
                written_data = self.mock_db_writer.get_written_data()
                if not TestValidator.validate_database_write(written_data, "mnt_robots_management", case["data"]["sn"]):
                    flow_success = False
                    flow_details["database_write"] = "Failed"

                # Check notification (only if expected)
                sent_notifications = self.mock_notification_service.get_sent_notifications(case["data"]["sn"])
                if case.get("expected_notification", False):
                    if len(sent_notifications) != len(database_names):
                        flow_success = False
                        flow_details["notification_send"] = "Failed - Expected notification"
                else:
                    flow_details["notification_send"] = "Skipped (as expected)"

                self.reporter.add_test_result(test_name, flow_success, flow_details)

                if flow_success:
                    print(f"    ✅ Complete power flow successful for {case['name']}")
                else:
                    print(f"    ❌ Power flow failed for {case['name']}: {flow_details}")

            except Exception as e:
                self.reporter.add_test_result(test_name, False, {"error": str(e)})
                print(f"    ❌ Exception in power flow for {case['name']}: {e}")

    def test_mixed_callback_flow(self):
        """Test processing mixed callback types in sequence"""
        print("\n🔀 Testing mixed callback processing flow")

        # Create a sequence of different callback types
        mixed_callbacks = []

        # Add robot status
        status_data = self.test_data.get_robot_status_data()
        mixed_callbacks.append(status_data["valid_status_changes"][0])

        # Add robot error
        error_data = self.test_data.get_robot_error_data()
        mixed_callbacks.append(error_data["navigation_errors"][0])

        # Add robot pose
        pose_data = self.test_data.get_robot_pose_data()
        mixed_callbacks.append(pose_data["normal_positions"][0])

        # Add robot power
        power_data = self.test_data.get_robot_power_data()
        mixed_callbacks.append(power_data["normal_power_levels"][0])

        # Clear all data
        self.mock_db_writer.clear_written_data()
        self.mock_notification_service.clear_notifications()

        processed_callbacks = 0

        for i, callback in enumerate(mixed_callbacks):
            print(f"  Processing callback {i+1}: {callback['callback_type']}")

            try:
                # Process callback
                response = self.callback_handler.process_callback(callback)
                if response.status.value == "success":
                    processed_callbacks += 1

                # Write to database
                database_names, table_names, primary_key_values = self.callback_handler.write_to_database(callback, self.mock_db_writer)

                # Simulate notification (simplified)
                robot_sn = callback["data"].get("sn")
                if robot_sn and callback["callback_type"] != "notifyRobotPose":
                    for database_name, table_name in zip(database_names, table_names):
                        payload = {
                            "database_name": database_name,
                            "table_name": table_name,
                            "primary_key_values": primary_key_values
                        }
                        self.mock_notification_service.send_notification(
                            robot_id=robot_sn,
                            notification_type="robot_status",
                            title=f"Mixed Test {callback['callback_type']}",
                            content=f"Robot {robot_sn} callback processed",
                            severity="event",
                            status="normal",
                            payload=payload
                        )

            except Exception as e:
                print(f"    ❌ Error processing callback {i+1}: {e}")

        # Validate mixed flow results
        flow_success = processed_callbacks >= len(mixed_callbacks) * 0.8

        written_data = self.mock_db_writer.get_written_data()
        management_records = len(written_data.get("mnt_robots_management", []))
        event_records = len(written_data.get("mnt_robot_events", []))
        total_notifications = len(self.mock_notification_service.get_sent_notifications())

        flow_details = {
            "processed_callbacks": processed_callbacks,
            "total_callbacks": len(mixed_callbacks),
            "management_records": management_records,
            "event_records": event_records,
            "notifications_sent": total_notifications,
        }

        self.reporter.add_test_result("mixed_callback_flow", flow_success, flow_details)

        if flow_success:
            print(f"    ✅ Mixed flow successful: {processed_callbacks}/{len(mixed_callbacks)} processed")
            print(f"    📊 DB Records: {management_records} mgmt, {event_records} events")
            print(f"    📨 Notifications: {total_notifications}")
        else:
            print(f"    ❌ Mixed flow failed: {processed_callbacks}/{len(mixed_callbacks)} processed")

    def test_error_resilience_flow(self):
        """Test system resilience with error conditions"""
        print("\n🛡️ Testing error resilience flow")

        # Test various error scenarios
        error_scenarios = [
            {"name": "invalid_callback_type", "callback_type": "invalidCallbackType", "data": {"sn": "RESILIENCE_TEST_001"}},
            {"name": "missing_robot_sn", "callback_type": "robotStatus", "data": {"run_status": "ONLINE"}},
            {
                "name": "corrupted_data",
                "callback_type": "robotErrorWarning",
                "data": {"sn": "RESILIENCE_TEST_002", "error_level": None, "error_type": "", "error_detail": None},
            },
        ]

        resilient_responses = 0

        for scenario in error_scenarios:
            test_name = f"resilience_{scenario['name']}"
            print(f"  Testing: {scenario['name']}")

            try:
                # Clear previous data
                self.mock_db_writer.clear_written_data()
                self.mock_notification_service.clear_notifications()

                # Process callback (should handle gracefully)
                response = self.callback_handler.process_callback(scenario)

                # Try database write (should handle gracefully)
                try:
                    database_names, table_names, primary_key_values = self.callback_handler.write_to_database(scenario, self.mock_db_writer)
                except Exception as db_error:
                    print(f"    📝 Database write handled error: {db_error}")

                # Check if response is properly structured
                if hasattr(response, "status") and hasattr(response, "message"):
                    resilient_responses += 1
                    print(f"    ✅ {scenario['name']} handled gracefully: {response.status.value}")
                else:
                    print(f"    ❌ {scenario['name']} not handled gracefully")

                self.reporter.add_test_result(
                    test_name,
                    True,
                    {
                        "scenario": scenario["name"],
                        "response_status": response.status.value if hasattr(response, "status") else "unknown",
                        "response_message": response.message if hasattr(response, "message") else "unknown",
                    },
                )

            except Exception as e:
                print(f"    ⚠️ {scenario['name']} caused exception: {e}")
                self.reporter.add_test_result(test_name, False, {"scenario": scenario["name"], "exception": str(e)})

        print(f"  Resilience: {resilient_responses}/{len(error_scenarios)} scenarios handled gracefully")

    def test_data_consistency_flow(self):
        """Test data consistency across processing pipeline"""
        print("\n🔍 Testing data consistency flow")

        # Use a robot status callback for consistency testing
        test_callback = {
            "callback_type": "robotStatus",
            "data": {"sn": "CONSISTENCY_TEST_ROBOT", "run_status": "ONLINE", "timestamp": 1640995800},
        }

        # Clear all data
        self.mock_db_writer.clear_written_data()
        self.mock_notification_service.clear_notifications()

        # Process through complete pipeline
        callback_response = self.callback_handler.process_callback(test_callback)
        database_names, table_names, primary_key_values = self.callback_handler.write_to_database(test_callback, self.mock_db_writer)

        # Send mock notification
        for database_name, table_name in zip(database_names, table_names):
            payload = {
                "database_name": database_name,
                "table_name": table_name,
                "primary_key_values": primary_key_values
            }
            self.mock_notification_service.send_notification(
                robot_id="CONSISTENCY_TEST_ROBOT",
                notification_type="robot_status",
                title="Robot Online",
                content="Robot CONSISTENCY_TEST_ROBOT is now online",
                severity="success",
                status="online",
                payload=payload
            )

        # Validate data consistency
        consistency_checks = {
            "callback_robot_sn": None,
            "database_robot_sn": None,
            "notification_robot_id": None,
            "timestamp_consistency": False,
            "status_consistency": False,
        }

        # Check callback response data
        if callback_response.data and "robot_sn" in callback_response.data:
            consistency_checks["callback_robot_sn"] = callback_response.data["robot_sn"]

        # Check database data
        written_data = self.mock_db_writer.get_written_data()
        mgmt_records = written_data.get("mnt_robots_management", [])
        if mgmt_records:
            consistency_checks["database_robot_sn"] = mgmt_records[0].get("robot_sn")

        # Check notification data
        notifications = self.mock_notification_service.get_sent_notifications("CONSISTENCY_TEST_ROBOT")
        if notifications:
            consistency_checks["notification_robot_id"] = notifications[0]["robot_id"]

        # Validate consistency
        robot_sn_consistent = (
            consistency_checks["callback_robot_sn"]
            == consistency_checks["database_robot_sn"]
            == consistency_checks["notification_robot_id"]
            == "CONSISTENCY_TEST_ROBOT"
        )

        # Check timestamp consistency
        if callback_response.timestamp and mgmt_records:
            consistency_checks["timestamp_consistency"] = True

        # Check status consistency
        if (
            callback_response.data
            and callback_response.data.get("status") == "online"
            and mgmt_records
            and mgmt_records[0].get("status") == "online"
        ):
            consistency_checks["status_consistency"] = True

        overall_consistency = (
            robot_sn_consistent and consistency_checks["timestamp_consistency"] and consistency_checks["status_consistency"]
        )

        self.reporter.add_test_result("data_consistency", overall_consistency, consistency_checks)

        if overall_consistency:
            print("    ✅ Data consistency maintained across pipeline")
        else:
            print("    ❌ Data consistency issues detected:")
            for check, value in consistency_checks.items():
                print(f"      {check}: {value}")

    def test_performance_flow(self):
        """Test performance with multiple rapid callbacks"""
        print("\n⚡ Testing performance flow")

        import time

        # Prepare multiple callbacks
        status_data = self.test_data.get_robot_status_data()
        test_callbacks = status_data["valid_status_changes"][:5]  # Use first 5

        # Clear all data
        self.mock_db_writer.clear_written_data()
        self.mock_notification_service.clear_notifications()

        start_time = time.time()
        processed_count = 0

        # Process callbacks rapidly
        for callback in test_callbacks:
            try:
                # Process callback
                response = self.callback_handler.process_callback(callback)
                if response.status.value == "success":
                    processed_count += 1

                # Write to database
                database_names, table_names, primary_key_values = self.callback_handler.write_to_database(callback, self.mock_db_writer)

                # Send notification
                robot_sn = callback["data"].get("sn")
                if robot_sn:
                    for database_name, table_name in zip(database_names, table_names):
                        payload = {
                            "database_name": database_name,
                            "table_name": table_name,
                            "primary_key_values": primary_key_values
                        }
                        self.mock_notification_service.send_notification(
                            robot_id=robot_sn,
                            notification_type="robot_status",
                            title="Performance Test",
                            content=f"Robot {robot_sn} status update",
                            severity="event",
                            status="normal",
                            payload=payload
                        )

            except Exception as e:
                print(f"    ⚠️ Error processing callback: {e}")

        end_time = time.time()
        processing_time = end_time - start_time
        throughput = processed_count / processing_time if processing_time > 0 else 0

        # Performance validation
        performance_success = (
            processed_count >= len(test_callbacks) * 0.9  # 90% success rate
            and throughput >= 5  # At least 5 callbacks per second
        )

        performance_details = {
            "processed_count": processed_count,
            "total_callbacks": len(test_callbacks),
            "processing_time": processing_time,
            "throughput": throughput,
            "database_records": len(self.mock_db_writer.get_written_data().get("mnt_robots_management", [])),
            "notifications_sent": len(self.mock_notification_service.get_sent_notifications()),
        }

        self.reporter.add_test_result("performance_flow", performance_success, performance_details)

        if performance_success:
            print(f"    ✅ Performance test passed:")
            print(f"      Processed: {processed_count}/{len(test_callbacks)} callbacks")
            print(f"      Time: {processing_time:.3f}s")
            print(f"      Throughput: {throughput:.1f} callbacks/sec")
        else:
            print(f"    ❌ Performance test failed:")
            print(f"      Processed: {processed_count}/{len(test_callbacks)} callbacks")
            print(f"      Time: {processing_time:.3f}s")
            print(f"      Throughput: {throughput:.1f} callbacks/sec")


# Test runner function
def run_complete_flow_tests():
    """Run all complete flow integration tests"""
    setup_test_logging("INFO")

    print("=" * 60)
    print("RUNNING COMPLETE FLOW INTEGRATION TESTS")
    print("=" * 60)
    print("🔄 Testing end-to-end webhook processing pipeline")
    print("📝 Using mock database and notification services")
    print("🧪 Validating data flow consistency")
    print("=" * 60)

    test_instance = TestCompleteFlow()
    test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

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

    # Print summaries
    print(f"\n{'='*60}")
    print("MOCK SERVICE SUMMARIES")
    print(f"{'='*60}")

    test_instance.mock_db_writer.print_summary()
    test_instance.mock_notification_service.print_summary()

    # Print test summary
    test_instance.reporter.print_summary()

    print(f"\n{'='*60}")
    print("COMPLETE FLOW TESTS COMPLETED")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_complete_flow_tests()
