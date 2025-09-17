import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
import json
from pathlib import Path

from src.api_server import app
from src.api.hwa import get_hwa_client
from src.core import config

# Use FastAPI's TestClient
client = TestClient(app)

# --- Fixtures ---

@pytest.fixture
def mock_hwa_client():
    """Fixture to provide a mocked HWAClient."""
    client = AsyncMock()
    client.plan = AsyncMock()
    client.model = AsyncMock()
    client.plan.query_job_streams.return_value = [
        {"jobStreamName": "JOB1", "status": "ABEND"},
        {"jobStreamName": "JOB2", "status": "EXEC"},
    ]
    client.model.query_workstations.return_value = [
        {"name": "CPU1", "status": "LINKED"}
    ]
    return client

@pytest.fixture(autouse=True)
def override_hwa_dependency(mock_hwa_client):
    """Fixture to automatically override the HWA client dependency for all tests in this module."""
    async def override_dependency():
        yield mock_hwa_client
    app.dependency_overrides[get_hwa_client] = override_dependency
    yield
    app.dependency_overrides.clear()

# --- Tests ---

@pytest.mark.integration
def test_dashboard_data_endpoint(monkeypatch, tmp_path):
    """
    Tests the /api/dashboard_data endpoint, ensuring it works with temporary config files.
    """
    # Create a dummy config file in the temporary directory
    config_path = tmp_path / "config.ini"
    config_path.write_text("[tws]\nhostname=test\nport=123\nusername=test\npassword=dummy_password")
    monkeypatch.setattr(config, "CONFIG_FILE", config_path)

    response = client.get("/api/dashboard_data")

    assert response.status_code == 200
    data = response.json()
    assert data["abend_count"] == 1
    assert data["running_count"] == 1

@pytest.mark.integration
def test_get_layout_endpoint(monkeypatch, tmp_path):
    """
    Tests the /api/dashboard_layout GET endpoint using a temporary layout file.
    """
    layout_path = tmp_path / "dashboard_layout.json"
    test_layout = [{"id": "test_widget"}]
    layout_path.write_text(json.dumps(test_layout))
    monkeypatch.setattr(config, "LAYOUT_FILE", layout_path)

    response = client.get("/api/dashboard_layout")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == "test_widget"

@pytest.mark.integration
def test_save_layout_endpoint(monkeypatch, tmp_path):
    """
    Tests the /api/dashboard_layout POST endpoint using a temporary layout file.
    """
    layout_path = tmp_path / "dashboard_layout.json"
    monkeypatch.setattr(config, "LAYOUT_FILE", layout_path)

    new_layout = [{"id": "saved_widget", "label": "Saved"}]
    response = client.post("/api/dashboard_layout", json=new_layout)
    assert response.status_code == 200

    saved_data = json.loads(layout_path.read_text())
    assert saved_data[0]["id"] == "saved_widget"
