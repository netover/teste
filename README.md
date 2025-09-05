# HWA Neuromorphic Dashboard

This project is a lightweight, web-based dashboard for monitoring and interacting with an HCL Workload Automation (HWA) or Tivoli Workload Scheduler (TWS) environment. It runs as a standalone desktop application with a system tray icon, providing a modern, easy-to-use interface.

![Dashboard Screenshot](https://via.placeholder.com/800x450.png?text=Dashboard+Screenshot)

## Features

-   **Web-based UI:** Modern, responsive dashboard accessible from `http://localhost:63136`.
-   **Dynamic & Configurable Dashboard:** The dashboard is built from a JSON configuration file (`dashboard_layout.json`).
-   **Dashboard Editor:** A built-in, user-friendly editor allows you to add, remove, edit, and reorder widgets on your dashboard.
-   **Real-time Monitoring:** Queries and displays the status of job streams and workstations automatically.
-   **System Tray Integration:** Runs in the background with a tray icon for easy access ("Open Dashboard", "Exit").
-   **Secure Credential Storage:** Passwords are encrypted using the `cryptography` library.
-   **Automated Setup:** The application automatically creates default configuration and layout files on first run.

## How to Run

### 1. From Source

**Prerequisites:**
-   Python 3.8+
-   `pip`

**Setup:**
1.  Clone the repository and navigate into the project directory.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the application:
    ```bash
    python app.py
    ```
4.  On the first run, `config/config.ini` and `dashboard_layout.json` will be created automatically.
5.  The application will open in your default web browser. Navigate to the **Configuration** page (`http://localhost:63136/config`) to enter your HWA/TWS connection details.

### 2. From Executable (If built)

1.  Run `hwa_dashboard.exe`.
2.  The application will automatically create the necessary `config` directory and files if they don't exist.
3.  Open the dashboard from the system tray icon and navigate to the **Configuration** page to set up your connection.

## Dashboard Editor

You can customize the dashboard by navigating to the **Dashboard Editor** page (`http://localhost:63136/dashboard_editor`).

![Editor Screenshot](https://via.placeholder.com/800x450.png?text=Editor+Screenshot)

In the editor, you can:
-   **Add New Widgets:** Click the "Add New Widget" button.
-   **Remove Widgets:** Click the trash icon on any widget.
-   **Reorder Widgets:** Drag and drop widgets to change their order.
-   **Edit Properties:** Change the Label, Icon (from Font Awesome), Color Class, and the API Metric the widget should display.
-   **Save:** Click "Save Layout" to apply your changes.

## API Connector

The `src/hwa_connector.py` module provides a simple SDK for interacting with the HWA API.

### Example Usage:
```python
from src.hwa_connector import HWAClient

# The client will automatically load details from config/config.ini
client = HWAClient()

# Get all job streams
job_streams = client.plan.query_job_streams()

# Get all workstations
workstations = client.model.query_workstations()

# Cancel a job
client.plan.cancel_job(job_id='some_job_id')
```

## How to Build

To build the executable yourself:
1.  Ensure you have all dependencies from `requirements.txt` installed.
2.  Install PyInstaller: `pip install pyinstaller`.
3.  Run the build command from the project's root directory:
    ```bash
    pyinstaller build.spec
    ```
4.  The final executable will be in the `dist/` directory.
