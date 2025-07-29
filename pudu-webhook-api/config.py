import os
from typing import Dict, Any

class Config:
    """Configuration class for the Pudu callback API"""

    # Server configuration
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'false'

    # Pudu configuration
    PUDU_CALLBACK_CODE = os.getenv('PUDU_CALLBACK_CODE', '')
    PUDU_API_KEY = os.getenv('PUDU_API_KEY', '')

    # Database configuration (if needed)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///pudu_callbacks.db')

    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'pudu_callbacks.log')

    # Alert configuration
    ALERT_EMAIL = os.getenv('ALERT_EMAIL', '')
    SMTP_SERVER = os.getenv('SMTP_SERVER', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')