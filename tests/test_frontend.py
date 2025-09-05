import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from playwright.sync_api import Page, expect
from app import app
import time
import json
import multiprocessing

# Fixture to run the Flask app in a background process
def run_app():
    test_app = app
    app.run(host="0.0.0.0", port=63136, debug=False)

@pytest.fixture(scope="session", autouse=True)
def live_server():
    server = multiprocessing.Process(target=run_app)
    server.start()
    time.sleep(2)
    yield
    server.terminate()
    server.join()

MOCK_DASHBOARD_DATA = {
    "abend_count": 1,
    "running_count": 1,
    "total_job_stream_count": 2,
    "total_workstation_count": 1,
    "job_streams": [
        {"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"},
        {"id": "job456", "jobStreamName": "DAILY_REPORT", "workstationName": "CPU1", "status": "EXEC"}
    ],
    "workstations": [{"name": "CPU1", "type": "Master", "status": "LINKED"}],
    "jobs_abend": [{"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"}],
    "jobs_running": [{"id": "job456", "jobStreamName": "DAILY_REPORT", "workstationName": "CPU1", "status": "EXEC"}]
}

def test_dashboard_loads_and_displays_data(page: Page):
    """
    Tests that the main dashboard loads, mocks the data API, and displays the data correctly.
    """
    # Create a dummy layout file for the test
    test_layout = [
        {"id": "widget_abend", "api_metric": "abend_count"},
        {"id": "widget_running", "api_metric": "running_count"}
    ]
    with open('dashboard_layout.json', 'w') as f:
        json.dump(test_layout, f)

    # Mock the API endpoint
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))

    page.goto("http://localhost:63136/")

    # Cleanup
    os.remove('dashboard_layout.json')

    # Check if widgets are rendered and updated
    expect(page.locator("#widget_abend .widget-value")).to_have_text("1")
    expect(page.locator("#widget_running .widget-value")).to_have_text("1")

    # Check if job stream and workstation grids are populated
    expect(page.locator("#job-streams-grid .job-stream-card")).to_have_count(2)
    expect(page.locator("#workstations-grid .workstation-card")).to_have_count(1)
    expect(page.locator("#job-streams-grid")).to_contain_text("CRITICAL_JOB")
    expect(page.locator("#workstations-grid")).to_contain_text("CPU1")

def test_cancel_job_flow(page: Page):
    """
    Tests the flow for cancelling a job from a modal.
    """
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))
    page.route("**/api/plan/current/job/job123/action/cancel",
               lambda route: route.fulfill(json={"success": True, "message": "Cancel command sent."}))

    page.goto("http://localhost:63136/")

    # Click on the abended job stream to open the detail modal
    page.locator('.job-stream-card[data-job-id="job123"]').click()

    # Verify modal content and click cancel
    modal = page.locator(".modal-content")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text("CRITICAL_JOB")

    page.once("dialog", lambda dialog: dialog.accept())
    modal.locator("#cancel-job-btn").click()

    # The original modal should close after cancellation
    expect(modal).not_to_be_visible()
