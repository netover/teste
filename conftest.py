import pytest
from xprocess import ProcessStarter
import os
from src.core.config import BASE_DIR # Import the project's base directory

# Define a fixture for the backend server process
@pytest.fixture(scope="session")
def backend_server(xprocess):
    """Fixture to run the FastAPI backend server."""
    class Starter(ProcessStarter):
        # Command to start the server
        cwd = str(BASE_DIR)
        # Set environment variables to provide dummy config for the server process
        env = {
            "FORCE_CONSOLE_MODE": "1",
            "APP_ENV": "development",
            "HWA_HOSTNAME": "test_host",
            "HWA_PORT": "12345",
            "HWA_USERNAME": "test_user",
            "HWA_PASSWORD": "test_password",
            **os.environ
        }
        pattern = "Uvicorn running on"
        # Use an absolute path to the script to avoid cwd issues
        args = ["python", str(BASE_DIR / "main.py")]

    # xprocess will manage the lifecycle of this process
    xprocess.ensure("backend_server", Starter)
    yield
    # Teardown is handled by xprocess
    xprocess.getinfo("backend_server").terminate()


# Define a fixture for the frontend dev server process
@pytest.fixture(scope="session")
def frontend_server(xprocess):
    """Fixture to run the Vite frontend dev server."""
    class Starter(ProcessStarter):
        # Command to start the server
        cwd = str(BASE_DIR) # npm needs to run from the root
        pattern = "ready in"
        # Use npx to ensure vite is found in the path
        args = ["npx", "vite"]

    # xprocess will manage the lifecycle of this process
    xprocess.ensure("frontend_server", Starter)
    yield
    # Teardown is handled by xprocess
    xprocess.getinfo("frontend_server").terminate()
