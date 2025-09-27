import pytest
from playwright.sync_api import Page, expect

# --- Test Data ---

# The layout required for these tests, matching the full schema to prevent rendering errors.
INITIAL_DASHBOARD_LAYOUT = [
    {
        "id": "widget_abend",
        "type": "summary_count",
        "label": "Jobs Abend",
        "icon": "fas fa-exclamation-triangle",
        "api_metric": "abend_count",
        "modal_data_key": "jobs_abend",
        "modal_title": "Abended Jobs",
        "modal_item_renderer": "renderJobItem",
        "color_class": "color-red",
    },
    {
        "id": "widget_running",
        "type": "summary_count",
        "label": "Jobs Running",
        "icon": "fas fa-running",
        "api_metric": "running_count",
        "modal_data_key": "jobs_running",
        "modal_title": "Running Jobs",
        "modal_item_renderer": "renderJobItem",
        "color_class": "color-blue",
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
    Tests that the main dashboard loads by mocking all required API endpoints.
    """
    base_url, _, _ = backend_server

    # --- Test Setup: Intercept API calls ---
    page.route("**/api/layout", lambda route: route.fulfill(json=INITIAL_DASHBOARD_LAYOUT))
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))

    # --- Start Test ---
    page.goto(base_url)

    # Assert that the widget data is displayed correctly
    expect(page.locator("#widget_abend .widget-value")).to_have_text("1")
    expect(page.locator("#widget_running .widget-value")).to_have_text("5")
    expect(page.locator("#job-streams-grid .job-stream-card")).to_have_count(1)


@pytest.mark.e2e
def test_cancel_job_flow(page: Page, backend_server):
    """
    Tests the flow for cancelling a job from a modal by mocking all required API endpoints.
    """
    base_url, _, _ = backend_server

    # --- Test Setup: Intercept API calls ---
    page.route("**/api/layout", lambda route: route.fulfill(json=INITIAL_DASHBOARD_LAYOUT))
    page.route("**/api/dashboard_data", lambda route: route.fulfill(json=MOCK_DASHBOARD_DATA))
    page.route("**/api/plan/current/job/job123/action/cancel",
               lambda route: route.fulfill(json={"success": True, "message": "Cancel command sent."}))

    # --- Start Test ---
    page.goto(base_url)

    job_card = page.locator('.job-stream-card[data-job-id="job123"]')
    expect(job_card).to_be_visible()
    job_card.click()

    modal = page.locator(".modal-content")
    expect(modal).to_be_visible()
    expect(modal).to_contain_text("CRITICAL_JOB")

    page.once("dialog", lambda dialog: dialog.accept())
    modal.locator('button[data-action="cancel"]').click()

    expect(modal).not_to_be_visible()