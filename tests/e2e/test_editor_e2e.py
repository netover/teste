import pytest
from playwright.sync_api import Page, expect

# Define the starting layout for this test to ensure it's self-contained and complete.
INITIAL_EDITOR_LAYOUT = [
    {
        "id": "widget_running_start",
        "type": "summary_count",
        "label": "Jobs Running",
        "icon": "fas fa-running",
        "api_metric": "running_count",
        "modal_data_key": "jobs_running",
        "modal_title": "Running Jobs",
        "modal_item_renderer": "renderJobItem",
        "color_class": "color-blue",
    },
    {
        "id": "widget_abend_start",
        "type": "summary_count",
        "label": "Jobs Abend",
        "icon": "fas fa-exclamation-triangle",
        "api_metric": "abend_count",
        "modal_data_key": "jobs_abend",
        "modal_title": "Abended Jobs",
        "modal_item_renderer": "renderJobItem",
        "color_class": "color-red",
    }
]

@pytest.mark.e2e
def test_editor_functionality(page: Page, backend_server):
    """
    Tests adding, editing, and saving widgets by intercepting the initial layout API call.
    """
    base_url, _, _ = backend_server

    # --- Test Setup: Intercept the initial GET request to provide a known starting layout ---
    page.route(f"**/api/layout",
               lambda route: route.fulfill(json=INITIAL_EDITOR_LAYOUT)
               if route.request.method == "GET"
               else route.continue_()) # Let POST requests pass through to the server

    # --- Start Test ---
    editor_url = f"{base_url}/dashboard_editor"
    page.goto(editor_url)

    # 1. Verify initial widgets are loaded from the mocked route
    expect(page.locator(".widget-editor-item").first).to_be_visible()
    expect(page.locator(".widget-editor-item")).to_have_count(2)

    # 2. Add a new widget
    page.locator("#add-widget-btn").click()
    modal = page.locator(".modal-content")
    expect(modal).to_be_visible()
    modal.locator("#widget-type-select").select_option("summary_count")
    modal.locator("#create-widget-btn").click()
    expect(page.locator(".widget-editor-item")).to_have_count(3)

    # 3. Remove the first widget ("Jobs Running") to ensure order changes are handled
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator('.widget-editor-item[data-widget-id="widget_running_start"] .remove-widget-btn').click()
    expect(page.locator(".widget-editor-item")).to_have_count(2)

    # 4. Edit the new widget's label *after* other list manipulations
    new_widget_editor = page.locator(".widget-editor-item").last
    new_widget_editor.locator("input[name='label']").fill("New Widget Label")

    # 5. Save the final layout (this will be a real POST to the test server)
    page.locator("#save-layout-btn").click()
    expect(page.locator(".message-area.success")).to_be_visible(timeout=5000)
    expect(page.locator(".message-area.success")).to_have_text("Layout saved successfully!")

    # 6. Verify the content of the saved JSON file by making a real API call
    response = page.request.get(f"{base_url}/api/layout")
    expect(response).to_be_ok()
    saved_layout = response.json()

    assert len(saved_layout) == 2
    # The first widget from the original layout ("Jobs Running") was removed.
    # The second widget ("Jobs Abend") should now be the first item.
    assert saved_layout[0]['label'] == "Jobs Abend"
    # Check that the newly added and edited widget is last.
    assert saved_layout[1]['label'] == "New Widget Label"