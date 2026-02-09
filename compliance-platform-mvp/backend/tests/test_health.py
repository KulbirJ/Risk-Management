"""Basic health check tests."""
import pytest


def test_import_app():
    """Test that app can be imported."""
    from app import main
    assert main is not None


def test_basic_math():
    """Basic test to ensure pytest is working."""
    assert 1 + 1 == 2


def test_environment():
    """Test environment setup."""
    import os
    # Check that we're in test environment
    assert os.environ.get('DATABASE_URL') is not None
