"""
Pytest configuration and shared fixtures for LiveRecall tests
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_embedding():
    """Generate a fake 768-dimensional embedding"""
    import random

    return [random.random() for _ in range(768)]
