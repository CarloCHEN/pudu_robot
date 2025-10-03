# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for the Multi-Brand Robot Callback API"""

    # Server configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Brand configuration
    BRAND = os.getenv("BRAND", "pudu")  # Default brand for backward compatibility

    # Brand-specific verification codes
    PUDU_CALLBACK_CODE = os.getenv("PUDU_CALLBACK_CODE", "")
    GAS_CALLBACK_CODE = os.getenv("GAS_CALLBACK_CODE", "")

    # Legacy Pudu configuration (kept for backward compatibility)
    PUDU_API_KEY = os.getenv("PUDU_API_KEY", "")  # not used

    # Database configuration (if needed)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///robot_callbacks.db")

    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "robot_callbacks.log")

    # Alert configuration
    ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    @classmethod
    def get_brand_callback_code(cls, brand: str) -> str:
        """
        Get callback code for specific brand

        Args:
            brand: Brand name (e.g., 'pudu', 'gas')

        Returns:
            Callback code for the brand
        """
        brand_upper = brand.upper()
        return os.getenv(f"{brand_upper}_CALLBACK_CODE", "")

    @classmethod
    def validate_brand_config(cls, brand: str) -> tuple[bool, str]:
        """
        Validate that brand configuration is complete

        Args:
            brand: Brand name to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        callback_code = cls.get_brand_callback_code(brand)

        if not callback_code:
            return False, f"Missing {brand.upper()}_CALLBACK_CODE in environment"

        return True, ""