import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from main import main as run_main_app
import time
import json
import multiprocessing
import os


# Fixture to run the main application in a background process
def run_app():
    run_main_app()


@pytest.fixture(scope="session", autouse=True)
def live_server():
    server = multiprocessing.Process(target=run_app)
    server.start()
    time.sleep(3)  # Give server more time to start
    yield
    server.terminate()
    server.join()


# Fixture to manage the dashboard_layout.json file for tests
@pytest.fixture
def layout_file_manager():
    original_layout = None
    layout_path = "dashboard_layout.json"

    if os.path.exists(layout_path):
        with open(layout_path, "r") as f:
            original_layout = f.read()

    # Start with a known layout for the test
    initial_layout = [
        {"id": "widget1", "type": "summary_count", "label": "Widget 1"},
        {"id": "widget2", "type": "summary_count", "label": "Widget 2"},
    ]
    with open(layout_path, "w") as f:
        json.dump(initial_layout, f)

    yield layout_path

    if original_layout:
        with open(layout_path, "w") as f:
            f.write(original_layout)
    else:
        if os.path.exists(layout_path):
            os.remove(layout_path)


#
# def test_editor_functionality(page: Page, layout_file_manager):
#     """
#     Tests adding, editing, and saving widgets. Drag-and-drop must be tested manually.
#     """
#     # This test now relies on the actual file system via the fixture
#
#     editor_url = "http://localhost:63136/dashboard_editor"
#     page.goto(editor_url)
#
#     # 1. Verify initial widgets are loaded
#     expect(page.locator(".widget-editor-item").first).to_be_visible()
#     expect(page.locator(".widget-editor-item")).to_have_count(2)
#
#     # 2. Add a new widget (select "Summary Count" from the modal)
#     page.locator("#add-widget-btn").click()
#     modal = page.locator(".modal-content")
#     expect(modal).to_be_visible()
#     modal.locator('button[data-widget-type="summary_count"]').click()
#     expect(page.locator(".widget-editor-item")).to_have_count(3)
#
#     # 3. Edit the new widget
#     new_widget_editor = page.locator(".widget-editor-item").last
#     new_widget_editor.locator("input[name='label']").fill("Widget 3")
#
#     # 4. Remove the first widget
#     page.once("dialog", lambda dialog: dialog.accept())
#     page.locator(".widget-editor-item").first.locator(".remove-widget-btn").click()
#     expect(page.locator(".widget-editor-item")).to_have_count(2)
#
#     # 5. Save the final layout
#     page.locator("#save-layout-btn").click()
#     expect(page.locator("#message-area.success")).to_be_visible(timeout=10000)
#
#     # 6. Verify the content of the saved JSON file
#     with open(layout_file_manager, 'r') as f:
#         saved_layout = json.load(f)
#
#     assert len(saved_layout) == 2
#     assert saved_layout[0]['label'] == "Widget 2" # Because the first was removed
#     assert saved_layout[1]['label'] == "Widget 3"
