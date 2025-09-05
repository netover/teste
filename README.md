# HWA Neuromorphic Dashboard

This project is a lightweight, web-based dashboard for monitoring an HCL Workload Automation (HWA) or Tivoli Workload Scheduler (TWS) environment via its REST API.

The application runs as a background process with a system tray icon, and the dashboard is accessed through a local web URL.

## Features

-   **Web-based UI:** Modern, responsive dashboard accessible from `http://localhost:63136`.
-   **Real-time Monitoring:** Queries and displays the status of job streams automatically.
-   **System Tray Integration:** Runs in the background with a tray icon for easy access ("Open Dashboard", "Exit").
-   **Easy Configuration:** All connection settings are in a simple `config.ini` file.

## How to Run

### 1. From Source

**Prerequisites:**
-   Python 3
-   `pip`

**Setup:**
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Configure your connection:
    -   Copy `config/config.ini.template` to `config/config.ini`.
    -   Edit `config/config.ini` with your HWA/TWS hostname, port, username, and password.
3.  Run the application:
    ```bash
    python3 app.py
    ```
    The application will start, and the dashboard should open in your default web browser.

### 2. From Executable (If built)

1.  Run `hwa_dashboard.exe`.
2.  The first time you run it, a `config` directory with `config.ini.template` might be created.
3.  Copy the template to `config.ini` and fill in your details.
4.  Restart the application. The dashboard can be accessed from the system tray icon or by navigating to `http://localhost:63136`.

## API Connector Capabilities

The core of the application's backend is the `HWAConnector` class found in `src/hwa_connector.py`. It can be used as a standalone library to interact with the HWA/TWS API. Its main features include:

-   **`query_job_streams()`**: Fetches a list of all job streams in the current plan.
-   **`get_workstation_status(workstation_name)`**: Retrieves the status and details of a specific agent/workstation.
-   **`cancel_job(job_id)`**: Sends a 'cancel' command to a job in the plan (requires the internal plan job ID).

The file can be run directly (`python3 src/hwa_connector.py`) to see a demonstration of these capabilities.

## How to Build

To build the executable yourself:
1.  Make sure you have all dependencies from `requirements.txt`.
2.  Install PyInstaller: `pip install pyinstaller`.
3.  Run the build command:
    ```bash
    pyinstaller build.spec
    ```
    The final executable will be in the `dist/` directory.
