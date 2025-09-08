import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
import json

# Ensure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api_server import app
from src.api.hwa import get_hwa_client

# Use FastAPI's TestClient
client = TestClient(app)

# --- Fixtures ---


@pytest.fixture(scope="function")
def dummy_config_file():
    """Fixture to create and clean up a dummy config file."""
    config_dir = "config"
    config_path = os.path.join(config_dir, "config.ini")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    with open(config_path, "w") as f:
        f.write(
            "[tws]\nhostname=test\nport=123\nusername=test\npassword=dummy_password"
        )
    yield
    os.remove(config_path)


@pytest.fixture(scope="function")
def dummy_layout_file():
    """Fixture to create and clean up a dummy layout file."""
    layout_path = "dashboard_layout.json"
    test_layout = [{"id": "test_widget"}]
    with open(layout_path, "w") as f:
        json.dump(test_layout, f)
    yield layout_path
    os.remove(layout_path)


# --- Tests ---


def test_dashboard_data_endpoint(dummy_config_file):
    """
    Tests the /api/dashboard_data endpoint with a mocked HWAClient.
    """
    # Define an async mock for the HWAClient
    mock_hwa_client = AsyncMock()
    mock_hwa_client.plan = AsyncMock()
    mock_hwa_client.model = AsyncMock()

    # Set the return values for the awaited methods
    mock_hwa_client.plan.query_job_streams.return_value = [
        {"jobStreamName": "JOB1", "status": "ABEND"},
        {"jobStreamName": "JOB2", "status": "EXEC"},
    ]
    mock_hwa_client.model.query_workstations.return_value = [
        {"name": "CPU1", "status": "LINKED"}
    ]

    # This override function will be used by FastAPI's dependency injection
    async def override_dependency():
        yield mock_hwa_client

    app.dependency_overrides[get_hwa_client] = override_dependency

    response = client.get("/api/dashboard_data")

    assert response.status_code == 200
    data = response.json()
    assert data["abend_count"] == 1
    assert data["running_count"] == 1

    app.dependency_overrides.clear()


from pathlib import Path


def test_get_layout_endpoint(dummy_layout_file):
    """
    Tests the /api/dashboard_layout GET endpoint.
    """
    from src.core import config

    config.LAYOUT_FILE = Path(dummy_layout_file)

    response = client.get("/api/dashboard_layout")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == "test_widget"


def test_save_layout_endpoint():
    """
    Tests the /api/dashboard_layout POST endpoint.
    """
    from src.core import config

    layout_path = Path("dashboard_layout.json")
    config.LAYOUT_FILE = layout_path

    new_layout = [{"id": "saved_widget", "label": "Saved"}]
    response = client.post("/api/dashboard_layout", json=new_layout)
    assert response.status_code == 200

    with open(layout_path, "r") as f:
        saved_data = json.load(f)
    assert saved_data[0]["id"] == "saved_widget"

    os.remove(layout_path)
