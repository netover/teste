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

        Args:
            config_path (str): The path to the configuration file.

        Raises:
            FileNotFoundError: If the configuration file cannot be found.
            ValueError: If the config file is missing required sections or options.
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
            # Read the SSL verification setting as a boolean. Fallback to False if not present.
            self.verify_ssl = config.getboolean('tws', 'verify_ssl', fallback=False)
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Configuration file '{config_path}' is missing a required section or option: {e}")

        self.base_url = f"https://{self.hostname}:{self.port}/twsd/v1"
        self.auth = HTTPBasicAuth(self.username, self.password)
        logging.info(f"HWA Connector initialized. SSL verification is {'ENABLED' if self.verify_ssl else 'DISABLED'}.")

    def query_job_streams(self, filter_criteria=None):
        """
        Queries for job streams in the current plan using the TWS API.

        Args:
            filter_criteria (dict, optional): A dictionary defining filters for the query.

        Returns:
            list: A list of job stream objects returned from the API.

        Raises:
            requests.exceptions.RequestException: For network-level errors.
            ValueError: For application-level errors (e.g., non-200 HTTP status code).
        """
        endpoint = f"{self.base_url}/plan/current/jobstream/query"

        payload = { "columns": ["jobStreamName", "workstationName", "status", "startTime", "endTime"] }
        if filter_criteria:
            payload["filters"] = { "jobStreamInPlanFilter": filter_criteria }

        headers = {
            'Content-Type': 'application/json',
            'How-Many': '500'
        }

        logging.info(f"Querying job streams from endpoint: {endpoint}")
        try:
            # The 'verify' parameter is now controlled by the 'verify_ssl' setting in config.ini
            response = requests.post(endpoint, json=payload, auth=self.auth, headers=headers, verify=self.verify_ssl)

            response.raise_for_status()

            logging.info(f"Successfully retrieved {len(response.json())} job streams.")
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            error_message = f"HTTP error occurred: {http_err}. Response body: {response.text}"
            logging.error(error_message)
            raise ValueError(error_message)
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Request failed: {req_err}")
            raise requests.exceptions.RequestException(f"Request failed: {req_err}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("--- HWA Connector Standalone Test ---")

    if not os.path.exists('config/config.ini'):
        print("\n[TEST INFO] 'config/config.ini' not found. This is expected if not configured.")
        print("Please use the application's UI to configure or copy 'config.ini.template' and fill in your details.")
    else:
        try:
            print("\n[TEST INFO] 'config/config.ini' found. Attempting to connect...")
            connector = HWAConnector()

            print("\n[TEST INFO] Querying for all job streams...")
            job_streams = connector.query_job_streams()

            print(f"\n[SUCCESS] Retrieved {len(job_streams)} job streams.")

            if job_streams:
                print("\n--- First 5 Job Streams ---")
                for i, js in enumerate(job_streams[:5]):
                    print(f"  {i+1}. Name: {js.get('jobStreamName', 'N/A')}, "
                          f"Workstation: {js.get('workstationName', 'N/A')}, "
                          f"Status: {js.get('status', 'N/A')}")
                print("---------------------------")

        except (FileNotFoundError, ValueError, requests.exceptions.RequestException) as e:
            print(f"\n[ERROR] An error occurred during the test: {e}")
    print("\n--- Test Complete ---")
