import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from playwright.sync_api import Page, expect
import threading
from app import app
import time

# Sample data to be returned by mocked API
MOCK_DASHBOARD_DATA = {
    "abend_count": 1,
    "running_count": 1,
    "total_job_stream_count": 2,
    "total_workstation_count": 1,
    "job_streams": [
        {
            "id": "job123",
            "jobStreamName": "CRITICAL_JOB",
            "workstationName": "CPU1",
            "status": "ABEND",
            "startTime": "2025-09-04T22:00:00Z"
        },
        {
            "id": "job456",
            "jobStreamName": "DAILY_REPORT",
            "workstationName": "CPU1",
            "status": "EXEC",
            "startTime": "2025-09-04T22:05:00Z"
        }
    ],
    "workstations": [
        {"name": "CPU1", "type": "Master", "status": "LINKED"}
    ],
    "jobs_abend": [
        {
            "id": "job123",
            "jobStreamName": "CRITICAL_JOB",
            "workstationName": "CPU1",
            "status": "ABEND",
            "startTime": "2025-09-04T22:00:00Z"
        }
    ],
    "jobs_running": [
         {
            "id": "job456",
            "jobStreamName": "DAILY_REPORT",
            "workstationName": "CPU1",
            "status": "EXEC",
            "startTime": "2025-09-04T22:05:00Z"
        }
    ]
}

import multiprocessing

def run_app():
    app.run(host="0.0.0.0", port=63136, debug=False)

# Fixture to run the Flask app in a background process
@pytest.fixture(scope="session", autouse=True)
def live_server():
    server = multiprocessing.Process(target=run_app)
    server.start()
    time.sleep(2)
    yield
    server.terminate()
    server.join()


def test_cancel_job_flow(page: Page):
    """
    Tests the full user flow for cancelling a job from the dashboard.
    """
    # 1. Mock the API endpoints before navigating to the page
    def mock_dashboard_data(route):
        route.fulfill(json=MOCK_DASHBOARD_DATA, status=200)

    def mock_cancel_job(route):
        route.fulfill(json={"success": True, "message": "Cancel command sent successfully."}, status=200)

    page.route("**/api/dashboard_data", mock_dashboard_data)
    page.route("**/api/plan/current/job/job123/action/cancel", mock_cancel_job)

    # 2. Navigate to the dashboard
    page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
    page.goto("http://localhost:63136/")

    # 3. Wait for the job stream grid to be populated
    expect(page.locator("#job-streams-grid .job-stream-card")).to_have_count(2)

    # 4. Find and click the job stream card to open the modal
    job_to_cancel_card = page.locator('.job-stream-card[data-job-id="job123"]')
    expect(job_to_cancel_card).to_be_visible()
    job_to_cancel_card.click()

    # 5. The modal should appear. Verify its content.
    modal = page.locator(".modal-content")
    expect(modal).to_be_visible()
    expect(modal.locator("h2")).to_have_text("Job Stream Details")
    expect(modal).to_contain_text("Name: CRITICAL_JOB")
    expect(modal).to_contain_text("Job ID: job123")

    # 6. Click the "Cancel Job" button
    cancel_button = modal.locator("#cancel-job-btn")
    expect(cancel_button).to_be_visible()

    # Set up a handler for the confirmation dialog
    page.once("dialog", lambda dialog: dialog.accept())

    cancel_button.click()

    # 7. The success alert should be handled (if any) or check for modal closure
    # Since we mocked the API, we can check that the modal closes.
    expect(modal).not_to_be_visible()
