import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from playwright.sync_api import Page, expect
import threading
from app import app
import time
import os
import json
import multiprocessing
import re

# Fixture to run the Flask app in a background process
def run_app():
    # Ensure the app is created with the correct paths for testing
    test_app = app
    app.run(host="0.0.0.0", port=63136, debug=False)

@pytest.fixture(scope="session", autouse=True)
def live_server():
    server = multiprocessing.Process(target=run_app)
    server.start()
    time.sleep(2) # Give the server a moment to start
    yield
    server.terminate()
    server.join()

# Fixture to manage the dashboard_layout.json file for tests
@pytest.fixture
def layout_file_manager():
    original_layout = None
    layout_path = 'dashboard_layout.json'

    # Save original if it exists
    if os.path.exists(layout_path):
        with open(layout_path, 'r') as f:
            original_layout = f.read()

    # Provide a clean slate for the test
    with open(layout_path, 'w') as f:
        json.dump([], f)

    yield layout_path

    # Restore original layout
    if original_layout:
        with open(layout_path, 'w') as f:
            f.write(original_layout)
    else:
        os.remove(layout_path)


def test_dashboard_editor_flow(page: Page, layout_file_manager):
    """
    Tests the full user flow for editing the dashboard layout.
    """
    editor_url = "http://localhost:63136/dashboard_editor"
    dashboard_url = "http://localhost:63136/"

    # 1. Navigate to the editor and check for initial state
    page.goto(editor_url)
    expect(page.locator("#widget-list p")).to_contain_text("No widgets in this layout.")

    # 2. Add a new widget
    page.locator("#add-widget-btn").click()
    widget_item = page.locator(".widget-editor-item")
    expect(widget_item).to_be_visible()
    expect(widget_item.locator('input[name="label"]')).to_have_value("New Widget")

    # 3. Edit the widget's properties
    widget_item.locator('input[name="label"]').fill("Test Widget")
    widget_item.locator('input[name="icon"]').fill("fas fa-flask")
    widget_item.locator('input[name="color_class"]').fill("color-purple")
    widget_item.locator('input[name="api_metric"]').fill("test_metric")

    # 4. Save the new layout
    page.locator("#save-layout-btn").click()
    expect(page.locator("#message-area.success")).to_be_visible()
    expect(page.locator("#message-area")).to_contain_text("Layout saved successfully!")

    # 5. Navigate to the main dashboard to verify the change
    page.goto(dashboard_url)

    # Mock the dashboard data to include our new metric
    def mock_dashboard_data(route):
        # Ensure the mock response contains all keys expected by the frontend
        mock_data = {
            "test_metric": 123,
            "job_streams": [],
            "workstations": [],
            "abend_count": 0,
            "running_count": 0
        }
        route.fulfill(json=mock_data)
    page.route("**/api/dashboard_data", mock_dashboard_data)

    # Manually trigger a data fetch in the browser context now that the mock is ready
    page.evaluate("window.fetchData()")

    # 6. Check if the new widget is rendered correctly
    new_widget = page.locator(".widget:has-text('Test Widget')")
    expect(new_widget).to_be_visible()
    expect(new_widget.locator(".widget-icon")).to_have_class(re.compile(r"fas fa-flask"))
    expect(new_widget).to_have_class(re.compile(r".*color-purple.*"))
    expect(new_widget.locator(".widget-value")).to_have_text("123")

    # 7. Go back and remove the widget
    page.goto(editor_url)
    expect(page.locator(".widget-editor-item")).to_have_count(1)

    # Set up a handler for the confirmation dialog
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator(".remove-widget-btn").click()

    expect(page.locator(".widget-editor-item")).to_have_count(0)

    # 8. Save the empty layout
    page.locator("#save-layout-btn").click()
    expect(page.locator("#message-area.success")).to_be_visible()

    # 9. Verify the widget is gone from the dashboard
    page.goto(dashboard_url)
    expect(page.locator(".widget:has-text('Test Widget')")).not_to_be_visible()
