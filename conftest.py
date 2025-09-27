import pytest
from xprocess import ProcessStarter
import os
import re
import time
from src.core.config import BASE_DIR

# Define a fixture for the backend server process
@pytest.fixture(scope="function")
def backend_server(xprocess, tmp_path_factory, request):
    """
    Fixture to run an ISOLATED FastAPI backend server for each test function.
    It creates a unique process name and a dedicated environment for each test
    to prevent any state pollution (e.g., modified layout files).
    """
    server_name = f"backend_server_{request.node.name}"

    # Create temporary directories for test-specific data
    predictor_model_dir = tmp_path_factory.mktemp("predictor_models")
    forecaster_model_dir = tmp_path_factory.mktemp("forecaster_models")
    celery_result_dir = tmp_path_factory.mktemp("celery_results")

    # Build a dedicated environment for the subprocess
    proc_env = os.environ.copy()
    proc_env.update({
        "APP_ENV": "production",
        "FORCE_CONSOLE_MODE": "1",
        "HWA_HOSTNAME": "test_host",
        "HWA_PORT": "12345",
        "HWA_USERNAME": "test_user",
        "HWA_PASSWORD": "test_password",
        # LAYOUT_FILE_OVERRIDE is removed. Tests will now manage state via API.
        "MODEL_DIR_OVERRIDE": str(predictor_model_dir),
        "FORECAST_MODEL_DIR_OVERRIDE": str(forecaster_model_dir),
        "CELERY_RESULT_BACKEND_OVERRIDE": f"file://{celery_result_dir}",
    })

    class Starter(ProcessStarter):
        cwd = str(BASE_DIR)
        pattern = r"Uvicorn running on http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:(\d+)"
        args = ["python", str(BASE_DIR / "main.py")]
        env = proc_env

    # Start the process and get its info
    pid, log_path = xprocess.ensure(server_name, Starter)

    # Poll the log file to get the port
    base_url = None
    for _ in range(20):  # Poll for up to 10 seconds
        with open(log_path) as f:
            log_content = f.read()
            match = re.search(Starter.pattern, log_content)
            if match:
                port = match.group(1)
                base_url = f"http://127.0.0.1:{port}"
                break
        time.sleep(0.5)

    if not base_url:
        pytest.fail("Failed to determine backend server address from log file.")

    # Yield all the necessary info for the test
    yield base_url, predictor_model_dir, forecaster_model_dir

    # xprocess handles process cleanup automatically
    xprocess.getinfo(server_name).terminate()
