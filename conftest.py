import pytest
from xprocess import ProcessStarter
import os
from src.core.config import BASE_DIR # Import the project's base directory

# Define a fixture for the backend server process
@pytest.fixture(scope="session")
def backend_server(xprocess):
    """Fixture to run the FastAPI backend server in production mode for E2E tests."""
    # Set environment variables for the server process.
    os.environ["APP_ENV"] = "production"
    os.environ["FORCE_CONSOLE_MODE"] = "1" # Important: Prevents GUI mode
    os.environ["HWA_HOSTNAME"] = "test_host"
    os.environ["HWA_PORT"] = "12345"
    os.environ["HWA_USERNAME"] = "test_user"
    os.environ["HWA_PASSWORD"] = "test_password"
    os.environ["LAYOUT_FILE_OVERRIDE"] = str(BASE_DIR / "tests/e2e/test_layout.json")

    class Starter(ProcessStarter):
        cwd = str(BASE_DIR)
        pattern = "Uvicorn running on"
        args = ["python", str(BASE_DIR / "main.py")]

    xprocess.ensure("backend_server", Starter)
    yield
    xprocess.getinfo("backend_server").terminate()
