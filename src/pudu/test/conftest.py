"""
pytest configuration and fixtures for Pudu pipeline tests
"""

import os
import sys
from pathlib import Path
import pytest

# Add the src directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

@pytest.fixture
def sample_robot_sn():
    """Sample robot serial number for testing"""
    return "811064412050012"

@pytest.fixture
def sample_time_range():
    """Sample time range for testing"""
    return {
        'start_time': '2024-09-01 00:00:00',
        'end_time': '2024-09-01 23:59:59'
    }

@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        'database_config': 'test_database_config.yaml',
        'mock_mode': True
    }