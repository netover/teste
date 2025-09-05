import configparser
import requests
from requests.auth import HTTPBasicAuth
import os
import logging

class HWAConnector:
    """
    Handles all communication with the HCL Workload Automation (HWA) REST API.
    This class encapsulates methods for reading connection settings, authenticating,
    and making API requests.
    """
    def __init__(self, config_path='config/config.ini'):
        """
        Initializes the connector by reading configuration details from a .ini file.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at '{config_path}'. Please create it via the UI or from the template.")

        config = configparser.ConfigParser()
        config.read(config_path)

        try:
            self.hostname = config.get('tws', 'hostname')
            self.port = config.getint('tws', 'port')
            self.username = config.get('tws', 'username')
            self.password = config.get('tws', 'password')
            self.verify_ssl = config.getboolean('tws', 'verify_ssl', fallback=False)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Configuration file '{config_path}' is missing a required section or option: {e}")

        self.base_url = f"https://{self.hostname}:{self.port}/twsd/v1"
        self.auth = HTTPBasicAuth(self.username, self.password)
        logging.info(f"HWA Connector initialized. SSL verification is {'ENABLED' if self.verify_ssl else 'DISABLED'}.")

    def _make_request(self, method, endpoint, **kwargs):
        """Internal helper for making requests."""
        url = f"{self.base_url}{endpoint}"
        logging.info(f"Making {method} request to: {url}")
        try:
            response = requests.request(method, url, auth=self.auth, verify=self.verify_ssl, **kwargs)
            response.raise_for_status()
            # Return JSON if content exists, otherwise an empty dict for actions that return no body.
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as http_err:
            error_message = f"HTTP error occurred: {http_err}. Response body: {http_err.response.text}"
            logging.error(error_message)
            raise ValueError(error_message)
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request failed: {req_err}")
            raise requests.exceptions.RequestException(f"Request failed: {req_err}")

    def query_job_streams(self, filter_criteria=None):
        """Queries for job streams in the current plan."""
        payload = {"columns": ["jobStreamName", "workstationName", "status", "startTime", "endTime"]}
        if filter_criteria:
            payload["filters"] = {"jobStreamInPlanFilter": filter_criteria}
        return self._make_request('POST', '/plan/current/jobstream/query', json=payload, headers={'How-Many': '500'})

    def get_workstation_status(self, workstation_name):
        """Gets the status of a specific workstation from the model."""
        payload = {"filters": {"workstationFilter": {"workstationName": workstation_name}}}
        workstations = self._make_request('POST', '/model/workstation/query', json=payload)
        return workstations[0] if workstations else None

    def cancel_job(self, job_id, plan_id='current'):
        """
        Sends a 'cancel' command to a specific job in the plan.
        Note: The job_id required here is the internal plan ID (e.g., a UUID),
        not the simple job name.
        """
        # This endpoint structure is based on observed patterns and may need validation.
        endpoint = f"/plan/{plan_id}/job/{job_id}/action"
        payload = {"action": "cancel"}
        logging.info(f"Sending 'cancel' action to job ID: {job_id}")
        return self._make_request('POST', endpoint, json=payload)

    # --- Placeholder for future methods ---
    def submit_jobstream(self, jobstream_definition):
        """Submits a new jobstream to the plan."""
        logging.warning("submit_jobstream is not yet implemented.")
        pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("--- HWA Connector Standalone Test ---")

    if not os.path.exists('config/config.ini'):
        print("\n[TEST INFO] 'config/config.ini' not found. This is expected if not configured.")
    else:
        try:
            print("\n[TEST INFO] 'config/config.ini' found. Attempting to connect...")
            connector = HWAConnector()

            print("\n[TEST INFO] Example: Querying for workstation 'CPU_MASTER'...")
            ws_status = connector.get_workstation_status("CPU_MASTER")
            if ws_status:
                print(f"[SUCCESS] Retrieved status for CPU_MASTER: {ws_status.get('status')}")
            else:
                print("[INFO] Workstation 'CPU_MASTER' not found.")

            print("\n[TEST INFO] Example: Demonstrating call to cancel job (will likely fail without a real job ID)...")
            try:
                # This call is expected to fail with a 404 or similar error without a valid, real-time job ID.
                connector.cancel_job("dummy-job-id-12345")
            except ValueError as e:
                print(f"[INFO] Call to cancel_job failed as expected: {e}")

        except (FileNotFoundError, ValueError, requests.exceptions.RequestException) as e:
            print(f"\n[ERROR] An error occurred during the test: {e}")
    print("\n--- Test Complete ---")
