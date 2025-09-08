import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from playwright.sync_api import Page, expect
from main import main as run_main_app
import time
import json
import multiprocessing

# This is a hack to make sure the tests can find the src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Fixture to run the main application in a background process
def run_app():
    # Force the app to run in console mode for the test environment
    os.environ["FORCE_CONSOLE_MODE"] = "1"
    run_main_app()

@pytest.fixture(scope="session", autouse=True)
def live_server():
    server = multiprocessing.Process(target=run_app)
    server.start()
    # Give the server time to start up
    time.sleep(5)
    yield
    server.terminate()
    server.join()

MOCK_DASHBOARD_DATA = {
    "abend_count": 1, "running_count": 1, "total_job_stream_count": 2,
    "total_workstation_count": 1,
    "job_streams": [
        {"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"},
        {"id": "job456", "jobStreamName": "DAILY_REPORT", "workstationName": "CPU1", "status": "EXEC"},
    ],
    "workstations": [{"name": "CPU1", "type": "Master", "status": "LINKED"}],
    "jobs_abend": [{"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"}],
    "jobs_running": [{"id": "job456", "jobStreamName": "DAILY_REPORT", "workstationName": "CPU1", "status": "EXEC"}],
}

def test_dashboard_loads_and_displays_data(page: Page):
    """
    Tests that the main dashboard loads, mocks the data API, and displays the data correctly.
    """
    layout_path = "dashboard_layout.json"
    if os.path.exists(layout_path):
        os.remove(layout_path)

    test_layout = [
        {"id": "widget_abend", "type": "summary_count", "api_metric": "abend_count"},
        {"id": "widget_running", "type": "summary_count", "api_metric": "running_count"},
    ]
    with open(layout_path, "w") as f:
        json.dump(test_layout, f)

    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))
    page.goto("http://localhost:63136/")

    expect(page.locator("#job-streams-grid .job-stream-card").first).to_be_visible()

    expect(page.locator("#widget_abend .widget-value")).to_have_text("1")
    expect(page.locator("#widget_running .widget-value")).to_have_text("1")
    expect(page.locator("#job-streams-grid .job-stream-card")).to_have_count(2)
    expect(page.locator("#workstations-grid .workstation-card")).to_have_count(1)

    os.remove(layout_path)

def test_cancel_job_flow(page: Page):
    """
    Tests the flow for cancelling a job from a modal.
    """
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))
    page.route("**/api/plan/current/job/job123/action/cancel",
               lambda route: route.fulfill(json={"success": True, "message": "Cancel command sent."}))

    page.goto("http://localhost:63136/")

    expect(page.locator("#job-streams-grid .job-stream-card").first).to_be_visible()

    page.locator('.job-stream-card[data-job-id="job123"]').click()

    modal = page.locator(".modal-content")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text("CRITICAL_JOB")

    page.once("dialog", lambda dialog: dialog.accept())
    modal.locator('button[data-action="cancel"]').click()

    expect(modal).not_to_be_visible()
