import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from app import app
import json
from unittest.mock import patch, MagicMock

# Use FastAPI's TestClient
client = TestClient(app)

@patch('app.HWAClient')
def test_dashboard_data_endpoint(mock_hwa_client):
    """
    Tests the /api/dashboard_data endpoint, mocking the HWAClient.
    """
    # Create dummy config file to prevent 404
    if not os.path.exists('config'):
        os.makedirs('config')
    with open('config/config.ini', 'w') as f:
        f.write('[tws]\nhostname=test\nport=123\nusername=test\npassword=test')

    # Configure the mock to return sample data
    mock_instance = MagicMock()
    mock_instance.plan.query_job_streams.return_value = [
        {"jobStreamName": "JOB1", "status": "ABEND"},
        {"jobStreamName": "JOB2", "status": "EXEC"}
    ]
    mock_instance.model.query_workstations.return_value = [{"name": "CPU1", "status": "LINKED"}]
    mock_hwa_client.return_value = mock_instance

    # Make the request
    response = client.get('/api/dashboard_data')

    # Cleanup
    os.remove('config/config.ini')

    assert response.status_code == 200
    data = response.json()

    # Assertions
    assert data['abend_count'] == 1
    assert data['running_count'] == 1
    assert data['total_job_stream_count'] == 2
    assert data['total_workstation_count'] == 1
    assert len(data['jobs_abend']) == 1
    assert data['jobs_abend'][0]['jobStreamName'] == 'JOB1'

def test_get_layout_endpoint():
    """
    Tests the /api/dashboard_layout GET endpoint.
    """
    # Create a dummy layout file for the test
    test_layout = [{"id": "test_widget"}]
    with open('dashboard_layout.json', 'w') as f:
        json.dump(test_layout, f)

    response = client.get('/api/dashboard_layout')
    assert response.status_code == 200
    data = response.json()
    assert data[0]['id'] == 'test_widget'

    os.remove('dashboard_layout.json')

def test_save_layout_endpoint():
    """
    Tests the /api/dashboard_layout POST endpoint.
    """
    new_layout = [{"id": "saved_widget", "label": "Saved"}]
    response = client.post('/api/dashboard_layout', json=new_layout)
    assert response.status_code == 200

    # Verify the file was written correctly
    with open('dashboard_layout.json', 'r') as f:
        saved_data = json.load(f)
    assert saved_data[0]['id'] == 'saved_widget'

    os.remove('dashboard_layout.json')
