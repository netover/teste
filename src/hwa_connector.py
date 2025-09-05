import configparser
import requests
from requests.auth import HTTPBasicAuth
import os
import logging

# --- Base Client and Services Structure ---

class HWAClient:
    """
    Main client for interacting with the HCL Workload Automation (HWA) REST API.
    This client handles the connection and authentication details and provides
    access to different API services.
    """
    def __init__(self, config_path='config/config.ini'):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at '{config_path}'.")

        config = configparser.ConfigParser()
        config.read(config_path)

        try:
            self.hostname = config.get('tws', 'hostname')
            self.port = config.getint('tws', 'port')
            self.username = config.get('tws', 'username')
            self.password = config.get('tws', 'password')
            self.verify_ssl = config.getboolean('tws', 'verify_ssl', fallback=False)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Config file is missing a required section/option: {e}")

        self.base_url = f"https://{self.hostname}:{self.port}/twsd/v1"
        self.auth = HTTPBasicAuth(self.username, self.password)
        logging.info(f"HWA Client initialized. SSL verification: {'ENABLED' if self.verify_ssl else 'DISABLED'}.")

        # Initialize service handlers
        self.plan = PlanService(self)
        self.model = ModelService(self)

    def _make_request(self, method, endpoint, **kwargs):
        """Internal helper for making all API requests."""
        url = f"{self.base_url}{endpoint}"
        logging.info(f"Request: {method} {url}")
        try:
            response = requests.request(method, url, auth=self.auth, verify=self.verify_ssl, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as http_err:
            error_message = f"HTTP error: {http_err}. Response: {http_err.response.text}"
            logging.error(error_message)
            raise ValueError(error_message)
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request failed: {req_err}")
            raise requests.exceptions.RequestException(f"Request failed: {req_err}")


class PlanService:
    """
    Service for interacting with objects in the HWA Plan.
    """
    def __init__(self, client: HWAClient):
        self.client = client

    def query_job_streams(self, filter_criteria=None):
        """Queries for job streams in the current plan."""
        endpoint = "/plan/current/jobstream/query"
        payload = {"columns": ["jobStreamName", "workstationName", "status", "startTime", "endTime", "jobInPlanOnCriticalPathFilter"]}
        if filter_criteria:
            payload["filters"] = {"jobStreamInPlanFilter": filter_criteria}
        return self.client._make_request('POST', endpoint, json=payload, headers={'How-Many': '500'})

    def get_job_log(self, job_id, plan_id='current'):
        """Retrieves the log for a specific job in the plan."""
        endpoint = f"/plan/{plan_id}/job/{job_id}/joblog"
        return self.client._make_request('GET', endpoint)

    def get_critical_jobs(self, plan_id='current', filter_criteria=None):
        """Queries for critical jobs in the specified plan."""
        endpoint = f"/plan/{plan_id}/criticaljob/query"
        payload = {"columns": ["jobInPlanOnCriticalNetwork"]}
        if filter_criteria:
            payload["filters"] = {"criticalJobInPlanFilter": filter_criteria}
        return self.client._make_request('POST', endpoint, json=payload)

    def cancel_job(self, job_id, plan_id='current'):
        """Sends a 'cancel' command to a specific job in the plan."""
        endpoint = f"/plan/{plan_id}/job/{job_id}/action/cancel"
        logging.info(f"Sending 'cancel' action to job ID: {job_id}")
        return self.client._make_request('PUT', endpoint)


class ModelService:
    """
    Service for interacting with objects in the HWA Database (Model).
    """
    def __init__(self, client: HWAClient):
        self.client = client

    def query_workstations(self, filter_criteria=None):
        """Queries for workstations defined in the model."""
        endpoint = "/model/workstation/query"
        payload = {"columns": ["workstationName", "status"]}
        if filter_criteria:
            payload["filters"] = {"workstationFilter": filter_criteria}
        return self.client._make_request('POST', endpoint, json=payload)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("--- HWA Client SDK Standalone Test ---")

    if not os.path.exists('config/config.ini'):
        print("\n[TEST INFO] 'config/config.ini' not found.")
    else:
        try:
            print("\n[TEST INFO] Initializing HWAClient...")
            client = HWAClient()

            print("\n[TEST INFO] Example: Querying for all workstations via ModelService...")
            workstations = client.model.query_workstations()
            if workstations:
                print(f"[SUCCESS] Retrieved {len(workstations)} workstations.")
                online_workstations = [w for w in workstations if w.get('status', '').lower() == 'link']
                print(f"    -> {len(online_workstations)} are online ('LINK').")
            else:
                print("[INFO] No workstations found.")

            print("\n[TEST INFO] Example: Querying for critical jobs via PlanService...")
            critical_jobs = client.plan.get_critical_jobs()
            print(f"[SUCCESS] Retrieved {len(critical_jobs)} critical jobs.")

        except (FileNotFoundError, ValueError, requests.exceptions.RequestException) as e:
            print(f"\n[ERROR] An error occurred during the test: {e}")
    print("\n--- Test Complete ---")
