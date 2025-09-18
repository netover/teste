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
1.  **Clone the repository** and navigate into the project directory.
2.  **Install backend dependencies** using pip. This command installs the project in editable mode (`-e`) and includes the development dependencies (`[dev]`).
    ```bash
    pip install -e ".[dev]"
    ```
3.  **Install frontend dependencies** using npm:
    ```bash
    npm install
    ```
4.  **Copy the configuration template** `config/config.ini.template` to `config/config.ini` and update it with your HWA, Database, and Redis connection details.
5.  **Build frontend assets.** The frontend is now built using Vite. For production or standalone use, you must build the optimized assets first.
    ```bash
    npm run build
    ```
6.  **Run the application:**
    ```bash
    python main.py
    ```
    The application will open in your default web browser.

### Development Mode
For active development, you can run the backend server and the Vite frontend server separately. This enables hot-reloading for a much faster development experience.

1.  **Run the Vite dev server:**
    ```bash
    npm run dev
    ```
2.  In a separate terminal, **run the Python backend** with the `APP_ENV` variable set to `development`:
    ```bash
    APP_ENV=development python main.py
    ```
This setup allows the Python server to proxy UI requests to the Vite server, enabling seamless development.

## Testing
The test suite uses `pytest`. Due to a known conflict between the `pytest-playwright` and `pytest-asyncio` plugins, the tests must be run in two separate batches.

**1. Run Backend Tests:**
These tests cover the API, core logic, monitoring, and machine learning services.
```bash
PYTHONPATH=. pytest tests/test_app.py tests/test_core.py tests/test_monitoring.py tests/test_ml.py
```

**2. Run Frontend Tests:**
These tests use Playwright to verify the frontend UI. They require the Vite development server to be running.
*Note: These tests are currently unstable in some environments due to issues with `multiprocessing` and the test runner. They have been separated for clarity.*

First, start the Vite dev server:
```bash
npm run dev
```
Then, in another terminal, run the frontend tests:
```bash
PYTHONPATH=. pytest tests/test_frontend.py
```

## How to Build
To build the executable for distribution:
1.  Ensure all dependencies are installed as described in the Setup section.
2.  Build the frontend assets:
    ```bash
    npm run build
    ```
3.  Install PyInstaller: `pip install pyinstaller`.
4.  Run the build command from the project's root directory:
    ```bash
    pyinstaller build.spec
    ```
5.  The final executable will be in the `dist/` directory.
