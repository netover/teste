import pytest
from playwright.sync_api import Page, expect

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
def test_dashboard_loads_and_displays_data(page: Page, backend_server):
    """
    Tests that the main dashboard loads, mocks the data API, and displays the data correctly.
    The test layout is now loaded via an environment variable in the conftest.py server fixture.
    """
    # Intercept the API call and return our mock data
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))

    # Go to the page
    page.goto("http://localhost:63136/")

    # For debugging: print the page content to see what's being rendered
    print(page.content())

    # Assert that the data is displayed correctly
    expect(page.locator("#widget_abend .widget-value")).to_have_text("1")
    expect(page.locator("#widget_running .widget-value")).to_have_text("1")
    expect(page.locator("#job-streams-grid .job-stream-card")).to_have_count(2)
    expect(page.locator("#workstations-grid .workstation-card")).to_have_count(1)


@pytest.mark.e2e
def test_cancel_job_flow(page: Page, backend_server):
    """
    Tests the flow for cancelling a job from a modal.
    This test now performs a full end-to-end request to the backend,
    relying on the HWAClient to be mocked at a lower level if needed.
    """
    # Mock the API endpoints. The job action is mocked to prevent the test
    # from making a real external call, verifying our backend endpoint is reachable
    # and returns the expected success format.
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))
    page.route("**/api/plan/current/job/job123/action/cancel",
               lambda route: route.fulfill(json={"success": True, "message": "'Cancel' command sent."}))

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

    # Listen for dialogs and handle them
    dialog_messages = []
    def handle_dialog(dialog):
        dialog_messages.append(dialog.message)
        dialog.accept()

    page.on("dialog", handle_dialog)

    # Click the cancel button in the modal
    modal.locator('button[data-action="cancel"]').click()

    # Wait for both dialogs to have been handled
    for _ in range(50):  # Poll for 5 seconds
        if len(dialog_messages) >= 2:
            break
        page.wait_for_timeout(100)
    else:
        pytest.fail("Timed out waiting for both dialogs to appear.")

    # Check the dialog messages
    assert "Are you sure you want to cancel" in dialog_messages[0]
    assert "'Cancel' command sent." in dialog_messages[1]

    # Assert that the modal is no longer visible
    expect(modal).not_to_be_visible()
