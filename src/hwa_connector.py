import httpx
import logging
from typing import Optional

from src.core import config

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

    This client handles authentication, request signing, and response parsing.
    It is designed to be used as an async context manager.

    Example:
        async with HWAClient(...) as client:
            job_streams = await client.plan.query_job_streams()

    Attributes:
        plan (PlanService): Service for interacting with Plan endpoints.
        model (ModelService): Service for interacting with Model endpoints.
    """
    def __init__(
        self,
        hostname: str,
        port: int,
        username: str,
        password: Optional[str],
        protocol: str = "https",
        verify_ssl: bool = False,
    ):
        """
        Initializes the HWAClient.

        Args:
            hostname: The hostname or IP address of the HWA master.
            port: The port number for the HWA API.
            username: The username for authentication.
            password: The password for authentication.
            protocol: The protocol to use ('http' or 'https'). Defaults to 'https'.
            verify_ssl: Whether to verify the SSL certificate. Defaults to False.

        Raises:
            ValueError: If hostname, port, or username are not provided.
        """
        if not all([hostname, port, username]):
            raise ValueError("Hostname, port, and username are required to initialize HWAClient.")

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol
        self.verify_ssl = verify_ssl
        self.base_url = f"{self.protocol}://{self.hostname}:{self.port}/twsd/v1"
        self.client = None
        self.plan = PlanService(self)
        self.model = ModelService(self)

    async def __aenter__(self) -> "HWAClient":
        """
        Initializes the async httpx client and enters the context manager.
        """
        transport = httpx.AsyncHTTPTransport(retries=3, verify=self.verify_ssl)
        self.client = httpx.AsyncClient(
            auth=(self.username, self.password),
            transport=transport,
            base_url=self.base_url,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the async httpx client on exiting the context manager.
        """
        if self.client:
            await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, **kwargs):
        """
        Internal helper for making all API requests.

        Handles client initialization checks, request execution, and error handling.

        Args:
            method: The HTTP method (e.g., 'GET', 'POST', 'PUT').
            endpoint: The API endpoint path.
            **kwargs: Additional arguments to pass to the httpx request.

        Returns:
            The JSON response from the API as a dictionary or an empty dictionary.

        Raises:
            HWAConnectionError: If the client is not initialized or a network error occurs.
            HWAAuthenticationError: For 401/403 HTTP status codes.
            HWAAPIError: For other non-2xx HTTP status codes.
        """
        if not self.client:
            raise HWAConnectionError("Client is not initialized. Use 'async with HWAClient(...)' context manager.")

        logging.debug(f"Request: {method} {self.base_url}{endpoint}")
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPStatusError as http_err:
            logging.error(f"HTTP error: {http_err.response.status_code} for {http_err.request.url}. Response: {http_err.response.text}")
            if http_err.response.status_code in (401, 403):
                raise HWAAuthenticationError(f"Authentication failed: {http_err.response.status_code}") from http_err
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
    """
    Provides methods for interacting with the HWA Plan API endpoints.
    """
    def __init__(self, client: HWAClient):
        self.client = client

    async def query_job_streams(self, filter_criteria: Optional[dict] = None) -> dict:
        """
        Queries for job streams in the current plan.

        Args:
            filter_criteria: A dictionary defining filters to apply to the query.

        Returns:
            A dictionary containing the list of job streams matching the query.
        """
        endpoint = "/plan/current/jobstream/query"
        payload = {"columns": ["jobStreamName", "workstationName", "status", "startTime", "endTime", "jobInPlanOnCriticalPathFilter"]}
        if filter_criteria:
            payload["filters"] = {"jobStreamInPlanFilter": filter_criteria}
        return await self.client._make_request(
            "POST", endpoint, json=payload, headers={"How-Many": str(config.HWA_HOW_MANY_LIMIT)}
        )

    async def get_job_log(self, job_id: str, plan_id: str = "current") -> dict:
        """
        Retrieves the log for a specific job in a given plan.

        Args:
            job_id: The unique identifier for the job.
            plan_id: The identifier of the plan (defaults to "current").

        Returns:
            A dictionary containing the job log.
        """
        endpoint = f"/plan/{plan_id}/job/{job_id}/joblog"
        return await self.client._make_request("GET", endpoint)

    async def _job_action(self, action: str, job_id: str, plan_id: str = "current") -> dict:
        """
        Private helper to perform an action on a job in the plan.

        Args:
            action: The action to perform (e.g., 'cancel', 'rerun').
            job_id: The unique identifier for the job.
            plan_id: The identifier of the plan (defaults to "current").

        Returns:
            An empty dictionary on success.
        """
        endpoint = f"/plan/{plan_id}/job/{job_id}/action/{action}"
        return await self.client._make_request("PUT", endpoint)

    async def cancel_job(self, job_id: str, plan_id: str = "current") -> dict:
        """Cancels a job in the plan."""
        return await self._job_action("cancel", job_id, plan_id)

    async def rerun_job(self, job_id: str, plan_id: str = "current") -> dict:
        """Reruns a job in the plan."""
        return await self._job_action("rerun", job_id, plan_id)

    async def hold_job(self, job_id: str, plan_id: str = "current") -> dict:
        """Holds a job in the plan."""
        return await self._job_action("hold", job_id, plan_id)

    async def release_job(self, job_id: str, plan_id: str = "current") -> dict:
        """Releases a job in the plan."""
        return await self._job_action("release", job_id, plan_id)


class ModelService:
    """
    Provides methods for interacting with the HWA Model API endpoints.
    """
    def __init__(self, client: HWAClient):
        self.client = client

    async def query_workstations(self, filter_criteria: Optional[dict] = None) -> dict:
        """
        Queries for workstations defined in the model.

        Args:
            filter_criteria: A dictionary defining filters to apply to the query.

        Returns:
            A dictionary containing the list of workstations matching the query.
        """
        endpoint = "/model/workstation/header/query"
        payload = {"columns": ["workstationName", "status"]}
        if filter_criteria:
            payload["filters"] = {"workstationFilter": filter_criteria}
        return await self.client._make_request("POST", endpoint, json=payload, headers={"How-Many": str(config.HWA_HOW_MANY_LIMIT)})
