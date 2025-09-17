import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """Sets the application environment to 'testing' for all tests."""
    os.environ["APP_ENV"] = "testing"
