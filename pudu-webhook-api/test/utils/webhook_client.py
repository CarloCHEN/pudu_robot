"""
Webhook testing client for making requests to the webhook API
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class WebhookClient:
    """Client for testing webhook endpoints"""

    def __init__(self, base_url: str = "http://localhost:8000", callback_code: str = "test_callback_code"):
        self.base_url = base_url.rstrip("/")
        self.callback_code = callback_code
        self.webhook_endpoint = f"{self.base_url}/api/pudu/webhook"
        self.health_endpoint = f"{self.base_url}/api/pudu/webhook/health"

        logger.info(f"WebhookClient initialized")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Webhook endpoint: {self.webhook_endpoint}")
        logger.info(f"Health endpoint: {self.health_endpoint}")

    def send_callback(self, callback_data: Dict[str, Any], timeout: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Send callback to webhook endpoint

        Args:
            callback_data: Callback payload
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, response_data)
        """
        headers = {"Content-Type": "application/json", "CallbackCode": self.callback_code}

        try:
            logger.info(f"🚀 Sending callback: {callback_data.get('callback_type', 'unknown')}")
            logger.info(f"   Robot: {callback_data.get('data', {}).get('sn', 'unknown')}")

            response = requests.post(self.webhook_endpoint, headers=headers, json=callback_data, timeout=timeout)

            response_data = {}
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}

            success = response.status_code == 200

            if success:
                logger.info(f"✅ Callback sent successfully")
                logger.info(f"   Response: {response_data.get('message', 'No message')}")
            else:
                logger.error(f"❌ Callback failed with status {response.status_code}")
                logger.error(f"   Response: {response_data}")

            return success, response_data

        except requests.exceptions.Timeout:
            logger.error(f"❌ Callback request timed out after {timeout}s")
            return False, {"error": "timeout"}
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Connection error - is the webhook server running?")
            return False, {"error": "connection_error"}
        except Exception as e:
            logger.error(f"❌ Unexpected error sending callback: {e}")
            return False, {"error": str(e)}

    def check_health(self, timeout: int = 5) -> Tuple[bool, Dict[str, Any]]:
        """
        Check webhook health endpoint

        Returns:
            Tuple of (is_healthy, health_data)
        """
        try:
            logger.info(f"🏥 Checking webhook health...")

            response = requests.get(self.health_endpoint, timeout=timeout)

            health_data = {}
            try:
                health_data = response.json()
            except json.JSONDecodeError:
                health_data = {"raw_response": response.text}

            is_healthy = response.status_code == 200 and health_data.get("status") == "healthy"

            if is_healthy:
                logger.info(f"✅ Webhook is healthy")
                logger.info(f"   Service: {health_data.get('service', 'unknown')}")
                logger.info(f"   Timestamp: {health_data.get('timestamp', 'unknown')}")
            else:
                logger.error(f"❌ Webhook health check failed")
                logger.error(f"   Status code: {response.status_code}")
                logger.error(f"   Response: {health_data}")

            return is_healthy, health_data

        except requests.exceptions.Timeout:
            logger.error(f"❌ Health check timed out after {timeout}s")
            return False, {"error": "timeout"}
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Connection error - is the webhook server running?")
            return False, {"error": "connection_error"}
        except Exception as e:
            logger.error(f"❌ Unexpected error in health check: {e}")
            return False, {"error": str(e)}

    def send_batch_callbacks(self, callbacks: list, delay_between: float = 0.1) -> Dict[str, Any]:
        """
        Send multiple callbacks with optional delay

        Args:
            callbacks: List of callback data dictionaries
            delay_between: Delay between requests in seconds

        Returns:
            Batch results summary
        """
        results = {"total": len(callbacks), "successful": 0, "failed": 0, "responses": [], "errors": []}

        logger.info(f"📦 Sending batch of {len(callbacks)} callbacks...")

        for i, callback in enumerate(callbacks, 1):
            logger.info(f"Sending callback {i}/{len(callbacks)}")

            success, response = self.send_callback(callback)

            results["responses"].append({"callback": callback, "success": success, "response": response})

            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(
                    {"callback_index": i - 1, "callback_type": callback.get("callback_type", "unknown"), "error": response}
                )

            # Add delay between requests
            if delay_between > 0 and i < len(callbacks):
                time.sleep(delay_between)

        success_rate = (results["successful"] / results["total"]) * 100 if results["total"] > 0 else 0

        logger.info(f"📊 Batch completed:")
        logger.info(f"   Total: {results['total']}")
        logger.info(f"   Successful: {results['successful']}")
        logger.info(f"   Failed: {results['failed']}")
        logger.info(f"   Success rate: {success_rate:.1f}%")

        return results

    def test_invalid_requests(self) -> Dict[str, Any]:
        """Test various invalid request scenarios"""
        test_results = {}

        # Test missing callback code
        logger.info("Testing missing callback code...")
        try:
            response = requests.post(
                self.webhook_endpoint, headers={"Content-Type": "application/json"}, json={"callback_type": "test"}, timeout=5
            )
            test_results["missing_callback_code"] = {
                "status_code": response.status_code,
                "expected": 400,
                "success": response.status_code == 400,
            }
        except Exception as e:
            test_results["missing_callback_code"] = {"error": str(e), "success": False}

        # Test invalid callback code
        logger.info("Testing invalid callback code...")
        try:
            response = requests.post(
                self.webhook_endpoint,
                headers={"Content-Type": "application/json", "CallbackCode": "invalid_code"},
                json={"callback_type": "test"},
                timeout=5,
            )
            test_results["invalid_callback_code"] = {
                "status_code": response.status_code,
                "expected": 401,
                "success": response.status_code == 401,
            }
        except Exception as e:
            test_results["invalid_callback_code"] = {"error": str(e), "success": False}

        # Test invalid JSON
        logger.info("Testing invalid JSON...")
        try:
            response = requests.post(
                self.webhook_endpoint,
                headers={"Content-Type": "application/json", "CallbackCode": self.callback_code},
                data="invalid json",
                timeout=5,
            )
            test_results["invalid_json"] = {
                "status_code": response.status_code,
                "expected": 400,
                "success": response.status_code == 400,
            }
        except Exception as e:
            test_results["invalid_json"] = {"error": str(e), "success": False}

        # Test missing content type
        logger.info("Testing missing content type...")
        try:
            response = requests.post(
                self.webhook_endpoint,
                headers={"CallbackCode": self.callback_code},
                data='{"callback_type": "test"}',
                timeout=5,
            )
            test_results["missing_content_type"] = {
                "status_code": response.status_code,
                "expected": 400,
                "success": response.status_code == 400,
            }
        except Exception as e:
            test_results["missing_content_type"] = {"error": str(e), "success": False}

        return test_results

    def generate_curl_command(self, callback_data: Dict[str, Any]) -> str:
        """Generate curl command for manual testing"""
        json_data = json.dumps(callback_data, indent=2)
        escaped_json = json_data.replace("'", "'\"'\"'")

        # Build curl command without backslashes in f-string
        cmd_parts = [
            f'curl -X POST "{self.webhook_endpoint}"',
            '-H "Content-Type: application/json"',
            f'-H "CallbackCode: {self.callback_code}"',
            f"-d '{escaped_json}'",
        ]

        curl_command = " \\\n  ".join(cmd_parts) + "\n"

        return curl_command
