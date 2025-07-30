"""
pytest configuration and fixtures
"""

import os
import sys
from pathlib import Path

import pytest

# Add the parent directory to the path so we can import the main modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_robot_sn():
    """Sample robot serial number for testing"""
    return "PUDU_TEST_001"


@pytest.fixture
def sample_timestamp():
    """Sample timestamp for testing"""
    return 1640995800


@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {"callback_code": "test_callback_code_123", "host": "localhost", "port": 8000, "debug": True}
