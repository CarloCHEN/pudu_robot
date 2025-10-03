# core/services/verification_service.py
import os
import logging
from typing import Dict, Any, Optional
from core.brand_config import BrandConfig

logger = logging.getLogger(__name__)


class VerificationService:
    """
    Handles verification of incoming webhook requests based on brand configuration
    Supports both header-based and body-based verification
    """

    def __init__(self, brand_config: BrandConfig):
        """
        Initialize verification service

        Args:
            brand_config: Brand-specific configuration
        """
        self.config = brand_config
        self.method = brand_config.get_verification_method()
        self.key = brand_config.get_verification_key()

        # Get expected verification value from environment
        env_key = f"{brand_config.brand.upper()}_CALLBACK_CODE"
        self.expected_value = os.getenv(env_key, "")

        if not self.expected_value:
            logger.warning(f"No verification value found in environment variable: {env_key}")

        logger.info(f"Verification service initialized for {brand_config.brand}: method={self.method}, key={self.key}")

    def verify(self, request_data: Dict[str, Any], request_headers: Dict[str, str]) -> tuple[bool, str]:
        """
        Verify incoming request based on brand configuration

        Args:
            request_data: Request body as dictionary
            request_headers: Request headers as dictionary (case-insensitive keys recommended)

        Returns:
            tuple: (is_valid, error_message)
                - is_valid: True if verification passed, False otherwise
                - error_message: Empty string if valid, error description if invalid
        """
        if not self.expected_value:
            error_msg = f"Server configuration error: {self.config.brand.upper()}_CALLBACK_CODE not set"
            logger.error(error_msg)
            return False, error_msg

        if self.method == 'header':
            return self._verify_header(request_headers)
        elif self.method == 'body':
            return self._verify_body(request_data)
        else:
            error_msg = f"Unknown verification method: {self.method}"
            logger.error(error_msg)
            return False, error_msg

    def _verify_header(self, headers: Dict[str, str]) -> tuple[bool, str]:
        """
        Verify using header-based method (e.g., Pudu's callbackcode)

        Args:
            headers: Request headers (should be lowercase keys for consistency)

        Returns:
            tuple: (is_valid, error_message)
        """
        # Lowercase all headers for case-insensitive comparison
        lower_headers = {k.lower(): v for k, v in headers.items()}

        # Try both the exact key and common variations
        received_value = (
            lower_headers.get(self.key.lower()) or
            lower_headers.get(f'x-{self.key.lower()}') or
            lower_headers.get(f'{self.key.lower()}-header')
        )

        if not received_value:
            error_msg = f"Missing {self.key} in request headers"
            logger.error(f"Header verification failed: {error_msg}")
            logger.debug(f"Available headers: {list(lower_headers.keys())}")
            return False, error_msg

        if received_value != self.expected_value:
            error_msg = f"Invalid {self.key}"
            logger.error(f"Header verification failed: received={received_value[:10]}..., expected={self.expected_value[:10]}...")
            return False, error_msg

        logger.debug(f"Header verification passed for {self.key}")
        return True, ""

    def _verify_body(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Verify using body-based method (e.g., Gas's appId)

        Args:
            data: Request body as dictionary

        Returns:
            tuple: (is_valid, error_message)
        """
        received_value = data.get(self.key)

        if not received_value:
            error_msg = f"Missing {self.key} in request body"
            logger.error(f"Body verification failed: {error_msg}")
            logger.debug(f"Available body keys: {list(data.keys())}")
            return False, error_msg

        if str(received_value) != str(self.expected_value):
            error_msg = f"Invalid {self.key}"
            logger.error(f"Body verification failed: received={str(received_value)[:10]}..., expected={str(self.expected_value)[:10]}...")
            return False, error_msg

        logger.debug(f"Body verification passed for {self.key}")
        return True, ""

    def get_verification_info(self) -> Dict[str, str]:
        """
        Get verification configuration info (for debugging/health checks)

        Returns:
            Dictionary with verification configuration details
        """
        return {
            "brand": self.config.brand,
            "method": self.method,
            "key": self.key,
            "configured": bool(self.expected_value)
        }