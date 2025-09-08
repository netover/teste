import httpx
import logging
from typing import Optional


# --- Custom Exceptions ---
class HWAError(Exception):
    """Base exception class for HWA client errors."""

    pass


class HWAConnectionError(HWAError):
    """Raised for network-related errors (e.g., DNS failure, refused connection)."""

    pass


class HWAAuthenticationError(HWAError):
    """Raised for authentication errors (e.g., 401 Unauthorized)."""

    pass


class HWAAPIError(HWAError):
    """Raised for other HTTP status code errors from the API."""

    def __init__(self, message, status_code, response_text):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


# --- Base Client and Services Structure ---
class HWAClient:
    """
    Main client for interacting with the HCL Workload Automation (HWA) REST API.
    """

    def __init__(
        self,
        hostname: str,
        port: int,
        username: str,
        password: Optional[str],
        verify_ssl: bool = False,
    ):
        if not all([hostname, port, username]):
            raise ValueError(
                "Hostname, port, and username are required to initialize HWAClient."
            )

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{self.hostname}:{self.port}/twsd/v1"
        self.client = None
        self.plan = PlanService(self)
        self.model = ModelService(self)

    async def __aenter__(self):
        """Initializes the async client."""
        transport = httpx.AsyncHTTPTransport(retries=3, verify=self.verify_ssl)
        self.client = httpx.AsyncClient(
            auth=(self.username, self.password),
            transport=transport,
            base_url=self.base_url,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Closes the async client."""
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method, endpoint, **kwargs):
        """Internal helper for making all API requests."""
        if not self.client:
            raise HWAConnectionError(
                "Client is not initialized. Use 'async with HWAClient(...)' context manager."
            )

        logging.debug(f"Request: {method} {self.base_url}{endpoint}")
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as http_err:
            logging.error(
                f"HTTP error: {http_err.response.status_code} for {http_err.request.url}. Response: {http_err.response.text}"
            )
            if http_err.response.status_code in (401, 403):
                raise HWAAuthenticationError(
                    f"Authentication failed: {http_err.response.status_code}"
                ) from http_err
            else:
                raise HWAAPIError(
                    f"API returned an error: {http_err.response.status_code}",
                    status_code=http_err.response.status_code,
                    response_text=http_err.response.text,
                ) from http_err
        except httpx.RequestError as req_err:
            logging.error(f"Request failed: {req_err}")
            raise HWAConnectionError(f"Network request failed: {req_err}") from req_err


# --- Service Classes ---
class PlanService:
    def __init__(self, client: HWAClient):
        self.client = client

    async def query_job_streams(self, filter_criteria=None):
        endpoint = "/plan/current/jobstream/query"
        payload = {
            "columns": [
                "jobStreamName",
                "workstationName",
                "status",
                "startTime",
                "endTime",
                "jobInPlanOnCriticalPathFilter",
            ]
        }
        if filter_criteria:
            payload["filters"] = {"jobStreamInPlanFilter": filter_criteria}
        return await self.client._make_request(
            "POST", endpoint, json=payload, headers={"How-Many": "500"}
        )

    async def get_job_log(self, job_id, plan_id="current"):
        endpoint = f"/plan/{plan_id}/job/{job_id}/joblog"
        return await self.client._make_request("GET", endpoint)

    async def _job_action(self, action: str, job_id: str, plan_id: str = "current"):
        endpoint = f"/plan/{plan_id}/job/{job_id}/action/{action}"
        return await self.client._make_request("PUT", endpoint)

    async def cancel_job(self, job_id, plan_id="current"):
        return await self._job_action("cancel", job_id, plan_id)

    async def rerun_job(self, job_id, plan_id="current"):
        return await self._job_action("rerun", job_id, plan_id)

    async def hold_job(self, job_id, plan_id="current"):
        return await self._job_action("hold", job_id, plan_id)

    async def release_job(self, job_id, plan_id="current"):
        return await self._job_action("release", job_id, plan_id)

    async def execute_oql_query(self, oql_query, plan_id="current"):
        endpoint = f"/plan/{plan_id}/query"
        params = {"oql": oql_query}
        return await self.client._make_request(
            "GET", endpoint, params=params, headers={"How-Many": "1000"}
        )


class ModelService:
    def __init__(self, client: HWAClient):
        self.client = client

    async def query_workstations(self, filter_criteria=None):
        endpoint = "/model/workstation/query"
        payload = {"columns": ["workstationName", "status"]}
        if filter_criteria:
            payload["filters"] = {"workstationFilter": filter_criteria}
        return await self.client._make_request("POST", endpoint, json=payload)

    async def execute_oql_query(self, oql_query):
        endpoint = "/model/query"
        params = {"oql": oql_query}
        return await self.client._make_request(
            "GET", endpoint, params=params, headers={"How-Many": "1000"}
        )
