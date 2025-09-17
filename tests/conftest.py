import pytest
import os
import fakeredis.aioredis

@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """Sets the application environment to 'testing' for all tests."""
    os.environ["APP_ENV"] = "testing"

@pytest.fixture(scope="function")
def redis_client():
    """Provides a fake Redis client for tests."""
    return fakeredis.aioredis.FakeRedis()
