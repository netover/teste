import pytest
from xprocess import ProcessStarter
import os
import re
import time
from src.core.config import BASE_DIR

# Define a fixture for the backend server process
@pytest.fixture(scope="function")
def backend_server(xprocess, tmp_path_factory):
    """
    Fixture to run the FastAPI backend server for a single test function.
    It creates temporary directories for models, sets them as environment variables,
    and ensures the server is running and ready for the test.
    """
    # Create dedicated temp dirs for models for test isolation
    predictor_model_dir = tmp_path_factory.mktemp("predictor_models")
    forecaster_model_dir = tmp_path_factory.mktemp("forecaster_models")
    celery_result_dir = tmp_path_factory.mktemp("celery_results")


    # Set environment variables that the server process will inherit
    os.environ["APP_ENV"] = "production"
    os.environ["FORCE_CONSOLE_MODE"] = "1"
    os.environ["HWA_HOSTNAME"] = "test_host"
    os.environ["HWA_PORT"] = "12345"
    os.environ["HWA_USERNAME"] = "test_user"
    os.environ["HWA_PASSWORD"] = "test_password"
    os.environ["LAYOUT_FILE_OVERRIDE"] = str(BASE_DIR / "tests/e2e/test_layout.json")
    os.environ["MODEL_DIR_OVERRIDE"] = str(predictor_model_dir)
    os.environ["FORECAST_MODEL_DIR_OVERRIDE"] = str(forecaster_model_dir)
    os.environ["CELERY_RESULT_BACKEND_OVERRIDE"] = f"file://{celery_result_dir}"


    class Starter(ProcessStarter):
        cwd = str(BASE_DIR)
        pattern = r"Uvicorn running on http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:(\d+)"
        args = ["python", str(BASE_DIR / "main.py")]

    # Start the process and get its info
    pid, log_path = xprocess.ensure("backend_server", Starter)

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

    # Clean up the process and environment variables
    xprocess.getinfo("backend_server").terminate()
    del os.environ["MODEL_DIR_OVERRIDE"]
    del os.environ["FORECAST_MODEL_DIR_OVERRIDE"]
    del os.environ["CELERY_RESULT_BACKEND_OVERRIDE"]
