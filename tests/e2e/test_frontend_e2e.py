import pytest
from playwright.sync_api import Page, expect

# --- Test Data ---

# The layout required for these tests, sent to the API at the start of each test.
INITIAL_DASHBOARD_LAYOUT = [
    {
        "id": "widget_abend",
        "type": "summary_count",
        "label": "Jobs Abend",
        "api_metric": "abend_count",
    },
    {
        "id": "widget_running",
        "type": "summary_count",
        "label": "Jobs Running",
        "api_metric": "running_count",
    },
]

# Mock data returned by the dashboard_data API during tests.
MOCK_DASHBOARD_DATA = {
    "abend_count": 1,
    "running_count": 5,
    "job_streams": [
        {"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"},
    ],
    "jobs_abend": [{"id": "job123", "jobStreamName": "CRITICAL_JOB", "workstationName": "CPU1", "status": "ABEND"}],
}


@pytest.mark.e2e
def test_dashboard_loads_and_displays_data(page: Page, backend_server):
    """
    Tests that the main dashboard loads, mocks the data API, and displays the data correctly.
    """
    base_url, _, _ = backend_server

    # --- Test Setup ---
    # Set the required layout for this test via API.
    setup_response = page.request.post(f"{base_url}/api/layout", data=INITIAL_DASHBOARD_LAYOUT)
    expect(setup_response).to_be_ok()
    # Intercept the data API call to return mock data.
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))

    # --- Start Test ---
    page.goto(base_url)

    # Assert that the widget data is displayed correctly
    expect(page.locator("#widget_abend .widget-value")).to_have_text("1")
    expect(page.locator("#widget_running .widget-value")).to_have_text("5")
    # Assert that the job stream grid is populated
    expect(page.locator("#job-streams-grid .job-stream-card")).to_have_count(1)


@pytest.mark.e2e
def test_cancel_job_flow(page: Page, backend_server):
    """
    Tests the flow for cancelling a job from a modal.
    """
    base_url, _, _ = backend_server

    # --- Test Setup ---
    # Set the required layout for this test via API.
    setup_response = page.request.post(f"{base_url}/api/layout", data=INITIAL_DASHBOARD_LAYOUT)
    expect(setup_response).to_be_ok()
    # Mock the API endpoints needed for this test.
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))
    page.route("**/api/plan/current/job/job123/action/cancel",
               lambda route: route.fulfill(json={"success": True, "message": "Cancel command sent."}))

    # --- Start Test ---
    page.goto(base_url)

    # Wait for the job stream card to be visible and click it
    job_card = page.locator('.job-stream-card[data-job-id="job123"]')
    expect(job_card).to_be_visible()
    job_card.click()

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
