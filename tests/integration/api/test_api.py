import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
import json
from pathlib import Path

from src.api_server import app
from src.api.hwa import get_hwa_client
from src.core import config
from src.core.settings import settings

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
    # Also mock the OQL query methods to prevent RecursionError during JSON serialization
    client.plan.execute_oql_query = AsyncMock(return_value=[])
    client.model.execute_oql_query = AsyncMock(return_value=[])
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
def test_dashboard_data_endpoint(monkeypatch):
    """
    Tests the /api/dashboard_data endpoint, ensuring it works with the new settings model.
    """
    # Patch the settings object to ensure required values are present for the test
    monkeypatch.setattr(settings, "HWA_HOSTNAME", "test_host")
    monkeypatch.setattr(settings, "HWA_USERNAME", "test_user")
    monkeypatch.setattr(settings, "HWA_PASSWORD", "test_pass")

    response = client.get("/api/dashboard_data")

    assert response.status_code == 200
    data = response.json()
    assert data["abend_count"] == 1
    assert data["running_count"] == 1

@pytest.mark.integration
def test_get_layout_endpoint(monkeypatch, tmp_path):
    """
    Tests the /api/layout GET endpoint using a temporary layout file.
    """
    layout_path = tmp_path / "dashboard_layout.json"
    test_layout = [{"id": "test_widget"}]
    layout_path.write_text(json.dumps(test_layout))
    # Mock the get_layout_file function to return our temporary path
    monkeypatch.setattr(config, "get_layout_file", lambda: layout_path)

    response = client.get("/api/layout")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["id"] == "test_widget"


@pytest.mark.integration
def test_save_layout_endpoint(monkeypatch, tmp_path):
    """
    Tests the /api/layout POST endpoint using a temporary layout file.
    """
    layout_path = tmp_path / "dashboard_layout.json"
    # Mock the get_layout_file function to return our temporary path
    monkeypatch.setattr(config, "get_layout_file", lambda: layout_path)

    new_layout = [{"id": "saved_widget", "label": "Saved"}]
    response = client.post("/api/layout", json=new_layout)
    assert response.status_code == 200

    saved_data = json.loads(layout_path.read_text())
    assert saved_data[0]["id"] == "saved_widget"


@pytest.mark.integration
def test_api_key_security(monkeypatch):
    """
    Tests that the API key dependency correctly protects endpoints.
    """
    # Set a known API key for the test
    test_key = "test-key-123"
    monkeypatch.setattr(settings, "API_KEY", test_key)

    # 1. Test with no API key provided
    response_no_key = client.get("/api/oql?q=workstation")
    assert response_no_key.status_code == 401
    assert "API Key is missing" in response_no_key.json()["detail"]

    # 2. Test with an incorrect API key
    response_wrong_key = client.get("/api/oql?q=workstation", headers={"X-API-Key": "wrong-key"})
    assert response_wrong_key.status_code == 401
    assert "Invalid or missing API Key" in response_wrong_key.json()["detail"]

    # 3. Test with the correct API key (mocking the HWA client to avoid a real call)
    response_correct_key = client.get("/api/oql?q=workstation", headers={"X-API-Key": test_key})
    # Expect a 200 OK because the security dependency passed
    assert response_correct_key.status_code == 200