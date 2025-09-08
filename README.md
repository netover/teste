# HWA Neuromorphic Dashboard

This project is a lightweight, web-based dashboard for monitoring and interacting with an HCL Workload Automation (HWA) or Tivoli Workload Scheduler (TWS) environment. It features a real-time monitoring system, predictive analytics, and runs as a standalone desktop application.

![Dashboard Screenshot](https://via.placeholder.com/800x450.png?text=Dashboard+Screenshot)

## Features

-   **Modern Web UI:** A responsive dashboard accessible from `http://localhost:63136`.
-   **Real-time Monitoring:** A WebSocket-based system provides real-time job status updates and alerts without needing to refresh the page.
-   **Predictive Analytics:** Services to predict job failures and forecast future workload (under development).
-   **Dynamic & Configurable Dashboard:** The dashboard layout is built from a JSON configuration file.
-   **Dashboard Editor:** A built-in editor allows you to add, remove, and reorder dashboard widgets.
-   **System Tray Integration:** Runs in the background with a tray icon for easy access.
-   **Secure Credential Storage:** Passwords are encrypted using the `cryptography` library.

## How to Run

### Prerequisites
-   Python 3.12+
-   Node.js and npm
-   Redis (for real-time features)

### Setup & Installation
1.  Clone the repository and navigate into the project directory.
2.  Install backend and frontend dependencies. This single command installs the project in editable mode (`-e`) and includes the development dependencies (`[dev]`).
    ```bash
    pip install -e ".[dev]"
    ```
3.  Install the frontend-specific dependencies:
    ```bash
    npm install
    ```
4.  Copy the configuration template `config/config.ini.template` to `config/config.ini` and update it with your HWA, Database, and Redis connection details.
5.  Run the application:
    ```bash
    python main.py
    ```
6.  The application will open in your default web browser.

### Environment Variables (Recommended)
For production-like environments, it is recommended to use environment variables for configuration, as they are more secure than plain text files. The application will prioritize environment variables over the `config.ini` file.

You can create a `.env` file in the project root for local development:
```
HWA_HOSTNAME=your_hostname
HWA_PORT=31116
HWA_USERNAME=your_user
HWA_PASSWORD=your_secret_password
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
REDIS_URL=redis://host:port
API_KEY=a_very_secret_key
```

## Testing

The test suite uses `pytest`. Due to a known conflict between the `pytest-playwright` and `pytest-asyncio` plugins, the tests must be run in two separate batches to ensure the asyncio event loop is handled correctly.

**1. Run App, Core, and Frontend Tests:**
```bash
PYTHONPATH=. pytest tests/test_app.py tests/test_core.py tests/test_frontend.py
```

**2. Run Monitoring and ML Tests:**
```bash
PYTHONPATH=. pytest tests/test_monitoring.py tests/test_ml.py
```

Running these two commands constitutes a full, successful test run.

## API Connector

The `src/hwa_connector.py` module provides a simple SDK for interacting with the HWA API.

**Example Usage:**
```python
from src.hwa_connector import HWAClient

# The client will automatically load details from config/config.ini
async with HWAClient() as client:
    # Get all job streams
    job_streams = await client.plan.query_job_streams()

    # Get all workstations
    workstations = await client.model.query_workstations()
```

## How to Build

To build the executable yourself:
1.  Ensure all dependencies are installed as described in the Setup section.
2.  Install PyInstaller: `pip install pyinstaller`.
3.  Run the build command from the project's root directory:
    ```bash
    pyinstaller build.spec
    ```
4.  The final executable will be in the `dist/` directory.

## Deployment Model

This application is designed as a **standalone desktop tool**, not a web service to be deployed in a cloud environment. The primary distribution method is a single executable built with PyInstaller.

Reflecting this deployment model, the project does not use a Continuous Integration (CI) pipeline. The CI workflow was disabled to simplify the development process and focus on its role as a local monitoring tool. All testing and validation are expected to be performed in the local development environment before a build is created.

## Developer Notes

### Frontend Build Process
An attempt was made to implement a Webpack build process to bundle frontend assets. This failed due to persistent, unresolvable errors within Webpack's internal `enhanced-resolve` module, likely caused by an incompatibility in the Node.js environment.

As a result, the build process has been reverted. The application currently loads individual JavaScript files directly in the browser. This is functional for development but is not optimized for production performance. This can be revisited in a different development environment.
