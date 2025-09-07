import configparser
import httpx
import os
import logging
import asyncio

from src.security import load_key, decrypt_password

# --- Base Client and Services Structure ---

class HWAClient:
    """
    Main client for interacting with the HCL Workload Automation (HWA) REST API.
    This client handles the connection and authentication details and provides
    access to different API services. It is designed to be used as an async context manager.
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
            encrypted_pass = config.get('tws', 'password')
            self.verify_ssl = config.getboolean('tws', 'verify_ssl', fallback=False)

            key = load_key()
            self.password = decrypt_password(encrypted_pass.encode('utf-8'), key)

        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            raise ValueError(f"Config file is missing a required section/option: {e}")

        self.base_url = f"https://{self.hostname}:{self.port}/twsd/v1"
        self.client = None

        # Initialize service handlers
        self.plan = PlanService(self)
        self.model = ModelService(self)

    async def __aenter__(self):
        """Initializes the async client when entering the context."""
        retries = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        transport = httpx.AsyncHTTPTransport(retries=3, verify=self.verify_ssl)

        self.client = httpx.AsyncClient(
            auth=(self.username, self.password),
            transport=transport,
            base_url=self.base_url
        )
        logging.info(f"HWA Async Client initialized. SSL verification: {'ENABLED' if self.verify_ssl else 'DISABLED'}.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the async client when exiting the context."""
        if self.client:
            await self.client.aclose()
            logging.info("HWA Async Client closed.")

    async def _make_request(self, method, endpoint, **kwargs):
        """Internal helper for making all API requests."""
        logging.info(f"Request: {method} {self.base_url}{endpoint}")
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as http_err:
            error_message = f"HTTP error: {http_err}. Response: {http_err.response.text}"
            logging.error(error_message)
            raise ValueError(error_message) from http_err
        except httpx.RequestError as req_err:
            logging.error(f"Request failed: {req_err}")
            raise httpx.RequestError(f"Request failed: {req_err}") from req_err


class PlanService:
    """
    Service for interacting with objects in the HWA Plan.
    """
    def __init__(self, client: HWAClient):
        self.client = client

    async def query_job_streams(self, filter_criteria=None):
        """Queries for job streams in the current plan."""
        endpoint = "/plan/current/jobstream/query"
        payload = {"columns": ["jobStreamName", "workstationName", "status", "startTime", "endTime", "jobInPlanOnCriticalPathFilter"]}
        if filter_criteria:
            payload["filters"] = {"jobStreamInPlanFilter": filter_criteria}
        return await self.client._make_request('POST', endpoint, json=payload, headers={'How-Many': '500'})

    async def get_job_log(self, job_id, plan_id='current'):
        """Retrieves the log for a specific job in the plan."""
        endpoint = f"/plan/{plan_id}/job/{job_id}/joblog"
        return await self.client._make_request('GET', endpoint)

    async def get_critical_jobs(self, plan_id='current', filter_criteria=None):
        """Queries for critical jobs in the specified plan."""
        endpoint = f"/plan/{plan_id}/criticaljob/query"
        payload = {"columns": ["jobInPlanOnCriticalNetwork"]}
        if filter_criteria:
            payload["filters"] = {"criticalJobInPlanFilter": filter_criteria}
        return await self.client._make_request('POST', endpoint, json=payload)

    async def _job_action(self, action: str, job_id: str, plan_id: str = 'current'):
        """Helper to perform an action on a job."""
        endpoint = f"/plan/{plan_id}/job/{job_id}/action/{action}"
        logging.info(f"Sending '{action}' action to job ID: {job_id}")
        return await self.client._make_request('PUT', endpoint)

    async def cancel_job(self, job_id, plan_id='current'):
        return await self._job_action('cancel', job_id, plan_id)

    async def rerun_job(self, job_id, plan_id='current'):
        return await self._job_action('rerun', job_id, plan_id)

    async def hold_job(self, job_id, plan_id='current'):
        return await self._job_action('hold', job_id, plan_id)

    async def release_job(self, job_id, plan_id='current'):
        return await self._job_action('release', job_id, plan_id)

    async def execute_oql_query(self, oql_query, plan_id='current'):
        """Executes a raw OQL query against the plan."""
        endpoint = f"/plan/{plan_id}/query"
        params = {'oql': oql_query}
        logging.info(f"Executing OQL query: {oql_query}")
        return await self.client._make_request('GET', endpoint, params=params, headers={'How-Many': '1000'})


class ModelService:
    """
    Service for interacting with objects in the HWA Database (Model).
    """
    def __init__(self, client: HWAClient):
        self.client = client

    async def query_workstations(self, filter_criteria=None):
        """Queries for workstations defined in the model."""
        endpoint = "/model/workstation/query"
        payload = {"columns": ["workstationName", "status"]}
        if filter_criteria:
            payload["filters"] = {"workstationFilter": filter_criteria}
        return await self.client._make_request('POST', endpoint, json=payload)

    async def execute_oql_query(self, oql_query):
        """Executes a raw OQL query against the model."""
        endpoint = "/model/query"
        params = {'oql': oql_query}
        logging.info(f"Executing OQL query against model: {oql_query}")
        return await self.client._make_request('GET', endpoint, params=params, headers={'How-Many': '1000'})


async def main_test():
    """Async main function for standalone testing."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("--- HWA Client SDK Standalone Test (Async) ---")

    if not os.path.exists('config/config.ini'):
        print("\n[TEST INFO] 'config/config.ini' not found.")
        return

    try:
        print("\n[TEST INFO] Initializing HWAClient...")
        async with HWAClient() as client:
            print("\n[TEST INFO] Example: Querying for all workstations via ModelService...")
            workstations = await client.model.query_workstations()
            if workstations:
                print(f"[SUCCESS] Retrieved {len(workstations)} workstations.")
                online_workstations = [w for w in workstations if w.get('status', '').lower() == 'link']
                print(f"    -> {len(online_workstations)} are online ('LINK').")
            else:
                print("[INFO] No workstations found.")

            print("\n[TEST INFO] Example: Querying for critical jobs via PlanService...")
            critical_jobs = await client.plan.get_critical_jobs()
            print(f"[SUCCESS] Retrieved {len(critical_jobs)} critical jobs.")

    except (FileNotFoundError, ValueError, httpx.RequestError) as e:
        print(f"\n[ERROR] An error occurred during the test: {e}")
    print("\n--- Test Complete ---")

if __name__ == '__main__':
    asyncio.run(main_test())
