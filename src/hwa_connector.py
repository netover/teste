import configparser
import requests
from requests.auth import HTTPBasicAuth
import os

class HWAConnector:
    """
    Handles connection and communication with the HCL Workload Automation (HWA) REST API.
    """
    def __init__(self, config_path='config/config.ini'):
        """
        Initializes the connector by reading configuration details.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at '{config_path}'. Please create it from the template.")

        config = configparser.ConfigParser()
        config.read(config_path)

        try:
            self.hostname = config.get('tws', 'hostname')
            self.port = config.getint('tws', 'port')
            self.username = config.get('tws', 'username')
            self.password = config.get('tws', 'password')
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Configuration file is missing a required section or option: {e}")

        self.base_url = f"https://{self.hostname}:{self.port}/twsd/v1"
        self.auth = HTTPBasicAuth(self.username, self.password)

    def query_job_streams(self, filter_criteria=None):
        """
        Queries for job streams in the current plan.

        Args:
            filter_criteria (dict, optional): A dictionary for filtering job streams.
                                              Defaults to None, which fetches all.

        Returns:
            list: A list of job stream objects from the API.

        Raises:
            requests.exceptions.RequestException: For connection or HTTP errors.
            ValueError: For non-200 responses from the API.
        """
        endpoint = f"{self.base_url}/plan/current/jobstream/query"

        # Default payload to fetch all job streams if no filter is provided
        payload = { "columns": ["jobStreamName", "workstationName", "status", "startTime", "endTime"] }
        if filter_criteria:
            payload["filters"] = { "jobStreamInPlanFilter": filter_criteria }

        headers = {
            'Content-Type': 'application/json',
            'How-Many': '500' # Request up to 500 records
        }

        try:
            # Note: We disable SSL verification for self-signed certs often used in TWS.
            # This should be changed to a proper certificate path in a production environment.
            response = requests.post(endpoint, json=payload, auth=self.auth, headers=headers, verify=False)

            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as http_err:
            # Add more context to HTTP errors
            error_message = f"HTTP error occurred: {http_err}. Response body: {response.text}"
            raise ValueError(error_message)
        except requests.exceptions.RequestException as req_err:
            # Catch other request exceptions (e.g., connection error)
            raise requests.exceptions.RequestException(f"Request failed: {req_err}")

# Example usage for standalone testing
if __name__ == '__main__':
    print("Attempting to connect to HWA using 'config/config.ini'...")

    # A real config file needs to be created for this to work
    if not os.path.exists('config/config.ini'):
        print("\nERROR: 'config/config.ini' not found.")
        print("Please copy 'config/config.ini.template' to 'config/config.ini' and fill in your details.")
    else:
        try:
            connector = HWAConnector()
            print("Connection object created successfully.")
            print("Querying for all job streams...")

            job_streams = connector.query_job_streams()

            print(f"\nSuccessfully retrieved {len(job_streams)} job streams.")

            if job_streams:
                print("\n--- First 5 Job Streams ---")
                for i, js in enumerate(job_streams[:5]):
                    print(f"  {i+1}. Name: {js.get('jobStreamName', 'N/A')}, "
                          f"Workstation: {js.get('workstationName', 'N/A')}, "
                          f"Status: {js.get('status', 'N/A')}")
                print("---------------------------")

        except (FileNotFoundError, ValueError, requests.exceptions.RequestException) as e:
            print(f"\nAn error occurred: {e}")
