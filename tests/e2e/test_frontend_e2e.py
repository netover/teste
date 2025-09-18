import pytest
from playwright.sync_api import Page, expect
import json
from pathlib import Path

# Mock data to be returned by the API during tests
MOCK_DASHBOARD_DATA = {
    "abend_count": 1,
    "running_count": 1,
    "total_job_stream_count": 2,
    "total_workstation_count": 1,
    "job_streams": [
        {"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"},
        {"id": "job456", "jobStreamName": "DAILY_REPORT", "workstationName": "CPU1", "status": "EXEC"},
    ],
    "workstations": [{"name": "CPU1", "type": "Master", "status": "LINKED"}],
    "jobs_abend": [{"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"}],
    "jobs_running": [{"id": "job456", "jobStreamName": "DAILY_REPORT", "workstationName": "CPU1", "status": "EXEC"}],
}

@pytest.mark.e2e
def test_dashboard_loads_and_displays_data(page: Page, backend_server, frontend_server, tmp_path: Path, monkeypatch):
    """
    Tests that the main dashboard loads, mocks the data API, and displays the data correctly.
    This test relies on the backend and frontend servers being run by pytest-xprocess.
    """
    # Create a temporary layout file for the test to ensure a predictable state
    layout_path = tmp_path / "dashboard_layout.json"
    test_layout = [
        {"id": "widget_abend", "type": "summary_count", "api_metric": "abend_count", "label": "Abend"},
        {"id": "widget_running", "type": "summary_count", "api_metric": "running_count", "label": "Running"},
    ]
    layout_path.write_text(json.dumps(test_layout))

    # Monkeypatch the config to use our temporary layout file
    from src.core import config
    monkeypatch.setattr(config, "LAYOUT_FILE", layout_path)

    # Intercept the API call and return our mock data
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))

    # Go to the page
    page.goto("http://localhost:63136/")

    # Assert that the data is displayed correctly
    expect(page.locator("#widget_abend .widget-value")).to_have_text("1")
    expect(page.locator("#widget_running .widget-value")).to_have_text("1")
    expect(page.locator("#job-streams-grid .job-stream-card")).to_have_count(2)
    expect(page.locator("#workstations-grid .workstation-card")).to_have_count(1)

@pytest.mark.e2e
def test_cancel_job_flow(page: Page, backend_server, frontend_server):
    """
    Tests the flow for cancelling a job from a modal.
    """
    # Mock the API endpoints needed for this test
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))
    page.route("**/api/plan/current/job/job123/action/cancel",
               lambda route: route.fulfill(json={"success": True, "message": "Cancel command sent."}))

    # Go to the page
    page.goto("http://localhost:63136/")

    # Wait for the job stream card to be visible
    expect(page.locator('.job-stream-card[data-job-id="job123"]')).to_be_visible()

    # Click the card to open the modal
    page.locator('.job-stream-card[data-job-id="job123"]').click()

    # Check that the modal is visible and contains the correct job name
    modal = page.locator(".modal-content")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text("CRITICAL_JOB")

    # Accept the confirmation dialog that pops up when cancelling
    page.once("dialog", lambda dialog: dialog.accept())

    # Click the cancel button in the modal
    modal.locator('button[data-action="cancel"]').click()

    # Assert that the modal is no longer visible
    expect(modal).not_to_be_visible()
