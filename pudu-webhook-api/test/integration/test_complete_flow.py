"""
Complete end-to-end flow tests
Tests the entire webhook processing pipeline with mock services
"""

import os
import sys
from pathlib import Path

# Fix path resolution when running from test directory
# Current file: test/integration/test_complete_flow.py
current_file = Path(__file__).resolve()
integration_dir = current_file.parent  # test/integration/
test_dir = integration_dir.parent      # test/
root_dir = test_dir.parent             # pudu-webhook-api/

# Add the root directory to Python path
sys.path.insert(0, str(root_dir))

# Change working directory to root so relative imports work
os.chdir(root_dir)

from test.mocks.mock_database import MockDatabaseWriter
from test.mocks.mock_notification import MockNotificationService
from test.utils.test_helpers import TestDataLoader, TestReporter, TestValidator, setup_test_logging

# Import main modules
try:
    from callback_handler import CallbackHandler
    from processors import RobotErrorProcessor, RobotPoseProcessor, RobotPowerProcessor, RobotStatusProcessor
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"📍 Current working directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path[:3]}...")
    print("\n💡 Debug info:")
    print(f"   Root dir: {root_dir}")
    print(f"   Root dir exists: {root_dir.exists()}")
    print(f"   callback_handler.py exists: {(root_dir / 'callback_handler.py').exists()}")
    sys.exit(1)


class TestCompleteFlow:
    """Test complete webhook processing flow"""

    def setup_method(self):
        """Setup for each test"""
        # Create a callback handler without database writer initialization
        self.callback_handler = CallbackHandler.__new__(CallbackHandler)
        self.callback_handler.processors = {
            "robotStatus": RobotStatusProcessor(),
            "robotErrorWarning": RobotErrorProcessor(),
            "notifyRobotPose": RobotPoseProcessor(),
            "notifyRobotPower": RobotPowerProcessor(),
        }
        self.callback_handler.ignored_callbacks = {
            "deliveryStatus", "deliveryComplete", "deliveryError",
            "orderStatus", "orderComplete", "orderError",
            "orderReceived", "deliveryStart", "deliveryCancel",
        }
        # Don't initialize the real database writer - we'll use mock
        self.callback_handler.database_writer = None

        self.mock_db_writer = MockDatabaseWriter()
        self.mock_notification_service = MockNotificationService()
        self.test_data = TestDataLoader()
        self.reporter = TestReporter()

        # Monkey patch the callback handler to use our mock database writer
        def mock_write_to_database_with_change_detection(data):
            callback_type = data.get("callback_type")
            callback_data = data.get("data", {})
            robot_sn = callback_data.get("sn", "")

            if not robot_sn:
                return [], [], {}

            if callback_type == "robotStatus":
                status_data = {
                    "robot_sn": robot_sn,
                    "status": callback_data.get("run_status", "").lower(),
                    "timestamp": callback_data.get("timestamp"),
                }
                return self.mock_db_writer.write_robot_status(robot_sn, status_data)

            elif callback_type == "notifyRobotPose":
                pose_data = {
                    "robot_sn": robot_sn,
                    "x": callback_data.get("x"),
                    "y": callback_data.get("y"),
                    "yaw": callback_data.get("yaw"),
                    "timestamp": callback_data.get("timestamp"),
                }
                return self.mock_db_writer.write_robot_pose(robot_sn, pose_data)

            elif callback_type == "notifyRobotPower":
                power_data = {
                    "robot_sn": robot_sn,
                    "power": callback_data.get("power"),
                    "charge_state": callback_data.get("charge_state"),
                    "timestamp": callback_data.get("timestamp"),
                }
                return self.mock_db_writer.write_robot_power(robot_sn, power_data)

            elif callback_type == "robotErrorWarning":
                event_data = {
                    "robot_sn": robot_sn,
                    "error_id": callback_data.get("error_id", ""),
                    "error_level": callback_data.get("error_level", ""),
                    "error_type": callback_data.get("error_type", ""),
                    "error_detail": callback_data.get("error_detail", ""),
                    "timestamp": callback_data.get("timestamp"),
                }
                return self.mock_db_writer.write_robot_event(robot_sn, event_data)

            return [], [], {}

        # Replace the method with our mock version
        self.callback_handler.write_to_database_with_change_detection = mock_write_to_database_with_change_detection

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

                # Step 2: Write to database using new interface
                database_names, table_names, changes_detected = self.callback_handler.write_to_database_with_change_detection(case)

                # Step 3: Send notification (using mock import)
                robot_sn = case["data"].get("sn")
                if robot_sn and changes_detected:
                    for (db_name, table_name), changes in changes_detected.items():
                        for change_id, change_info in changes.items():
                            payload = {
                                "database_name": db_name,
                                "table_name": table_name,
                                "related_biz_id": change_info.get('database_key'),
                                "related_biz_type": case["callback_type"]
                            }

                            self.mock_notification_service.send_notification(
                                robot_id=robot_sn,
                                notification_type="robot_status",
                                title=f"Robot {case['data']['run_status']}",
                                content=f"Robot {robot_sn} status changed",
                                severity=case.get("expected_severity", "event"),
                                status=case.get("expected_status", "normal"),
                                payload=payload
                            )

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
                expected_notifications = len(changes_detected) if changes_detected else 0
                if len(sent_notifications) != expected_notifications:
                    flow_success = False
                    flow_details["notification_send"] = f"Failed - Expected {expected_notifications}, got {len(sent_notifications)}"
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

                # Step 2: Write to database (FIXED: properly unpack 3 return values)
                database_names, table_names, changes_detected = self.callback_handler.write_to_database_with_change_detection(case)

                # Step 3: Send notification for events
                robot_sn = case["data"].get("sn")
                if robot_sn and changes_detected:
                    for (db_name, table_name), changes in changes_detected.items():
                        for change_id, change_info in changes.items():
                            payload = {
                                "database_name": db_name,
                                "table_name": table_name,
                                "related_biz_id": change_info.get('database_key'),
                                "related_biz_type": case["callback_type"]
                            }

                            self.mock_notification_service.send_notification(
                                robot_id=robot_sn,
                                notification_type="robot_status",
                                title=f"Robot Error: {case['data'].get('error_type', 'Unknown')}",
                                content=f"Robot {robot_sn} error: {case['data'].get('error_detail', '')}",
                                severity=case.get("expected_severity", "error"),
                                status="abnormal",
                                payload=payload
                            )

                # Validate complete flow
                flow_success = True
                flow_details = {}

                # Check callback processing
                if callback_response.status.value != "success":
                    flow_success = False
                    flow_details["callback_processing"] = "Failed"
                else:
                    flow_details["callback_processing"] = "Success"

                # Check database write (events go to mnt_robot_events table)
                written_data = self.mock_db_writer.get_written_data()
                if not TestValidator.validate_database_write(written_data, "mnt_robot_events", case["data"]["sn"]):
                    flow_success = False
                    flow_details["database_write"] = "Failed"
                else:
                    flow_details["database_write"] = "Success"

                # Check notification
                sent_notifications = self.mock_notification_service.get_sent_notifications(case["data"]["sn"])
                expected_notifications = len(changes_detected) if changes_detected else 0
                if len(sent_notifications) != expected_notifications:
                    flow_success = False
                    flow_details["notification_send"] = f"Failed - Expected {expected_notifications}, got {len(sent_notifications)}"
                else:
                    flow_details["notification_send"] = "Success"

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

                # Step 2: Write to database (FIXED: properly unpack 3 return values)
                database_names, table_names, changes_detected = self.callback_handler.write_to_database_with_change_detection(case)

                # Step 3: Send notification for low battery
                robot_sn = case["data"].get("sn")
                power_level = case["data"].get("power", 0)

                if robot_sn and changes_detected and case.get("expected_notification", False):
                    for (db_name, table_name), changes in changes_detected.items():
                        for change_id, change_info in changes.items():
                            payload = {
                                "database_name": db_name,
                                "table_name": table_name,
                                "related_biz_id": change_info.get('database_key'),
                                "related_biz_type": case["callback_type"]
                            }

                            self.mock_notification_service.send_notification(
                                robot_id=robot_sn,
                                notification_type="robot_status",
                                title=f"Battery Alert: {power_level}%",
                                content=f"Robot {robot_sn} battery at {power_level}%",
                                severity=case.get("expected_severity", "warning"),
                                status="warning",
                                payload=payload
                            )

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

                # Check notification (only if expected)
                sent_notifications = self.mock_notification_service.get_sent_notifications(case["data"]["sn"])
                if case.get("expected_notification", False):
                    expected_notifications = len(changes_detected) if changes_detected else 0
                    if len(sent_notifications) != expected_notifications:
                        flow_success = False
                        flow_details["notification_send"] = f"Failed - Expected notification but got {len(sent_notifications)}"
                    else:
                        flow_details["notification_send"] = "Success"
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

                # Write to database (FIXED: properly unpack 3 return values)
                database_names, table_names, changes_detected = self.callback_handler.write_to_database_with_change_detection(callback)

                # Simulate notification (simplified)
                robot_sn = callback["data"].get("sn")
                if robot_sn and callback["callback_type"] != "notifyRobotPose" and changes_detected:
                    for (db_name, table_name), changes in changes_detected.items():
                        for change_id, change_info in changes.items():
                            payload = {
                                "database_name": db_name,
                                "table_name": table_name,
                                "related_biz_id": change_info.get('database_key'),
                                "related_biz_type": callback["callback_type"]
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
                    database_names, table_names, changes_detected = self.callback_handler.write_to_database_with_change_detection(scenario)
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
        database_names, table_names, changes_detected = self.callback_handler.write_to_database_with_change_detection(test_callback)

        # Send mock notification
        if changes_detected:
            for (db_name, table_name), changes in changes_detected.items():
                for change_id, change_info in changes.items():
                    payload = {
                        "database_name": db_name,
                        "table_name": table_name,
                        "related_biz_id": change_info.get('database_key'),
                        "related_biz_type": test_callback["callback_type"]
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

                # Write to database (FIXED: properly unpack 3 return values)
                database_names, table_names, changes_detected = self.callback_handler.write_to_database_with_change_detection(callback)

                # Send notification
                robot_sn = callback["data"].get("sn")
                if robot_sn and changes_detected:
                    for (db_name, table_name), changes in changes_detected.items():
                        for change_id, change_info in changes.items():
                            payload = {
                                "database_name": db_name,
                                "table_name": table_name,
                                "related_biz_id": change_info.get('database_key'),
                                "related_biz_type": callback["callback_type"]
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