import pytest
from pytest_httpserver import HTTPServer

from src.hwa_connector import HWAClient, HWAConnectionError, HWAAuthenticationError, HWAAPIError

# --- Fixtures ---

@pytest.fixture
def hwa_client_factory(httpserver: HTTPServer):
    """Factory fixture to create an HWAClient instance for testing."""
    def _create_client(username="testuser", password="testpassword"):
        return HWAClient(
            hostname=httpserver.host,
            port=httpserver.port,
            username=username,
            password=password,
            protocol="http",  # Use http for testing against the mock server
            verify_ssl=False,
        )
    return _create_client

# --- Test Cases ---

@pytest.mark.asyncio
async def test_query_job_streams_success(httpserver: HTTPServer, hwa_client_factory):
    """Test successful query of job streams."""
    httpserver.expect_request(
        "/twsd/v1/plan/current/jobstream/query",
        method="POST"
    ).respond_with_json([{"jobStreamName": "STREAM1"}])

    async with hwa_client_factory() as client:
        result = await client.plan.query_job_streams()
        assert result == [{"jobStreamName": "STREAM1"}]
        httpserver.check_assertions()

@pytest.mark.asyncio
async def test_query_job_streams_with_filter(httpserver: HTTPServer, hwa_client_factory):
    """Test successful query of job streams with a filter."""
    filter_data = {"jobStreamName": "FILTERED_STREAM"}

    # Construct the full expected payload
    expected_payload = {
        "columns": ["jobStreamName", "workstationName", "status", "startTime", "endTime", "jobInPlanOnCriticalPathFilter"],
        "filters": {"jobStreamInPlanFilter": filter_data}
    }

    httpserver.expect_request(
        "/twsd/v1/plan/current/jobstream/query",
        method="POST",
        json=expected_payload
    ).respond_with_json([{"jobStreamName": "FILTERED_STREAM"}])

    async with hwa_client_factory() as client:
        result = await client.plan.query_job_streams(filter_criteria=filter_data)
        assert result == [{"jobStreamName": "FILTERED_STREAM"}]
        httpserver.check_assertions()


@pytest.mark.asyncio
async def test_get_job_log_success(httpserver: HTTPServer, hwa_client_factory):
    """Test successful retrieval of a job log."""
    httpserver.expect_request(
        "/twsd/v1/plan/current/job/123/joblog",
        method="GET"
    ).respond_with_json({"log": "This is the job log."})

    async with hwa_client_factory() as client:
        result = await client.plan.get_job_log(job_id="123")
        assert result == {"log": "This is the job log."}
        httpserver.check_assertions()

@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["cancel", "rerun", "hold", "release"])
async def test_job_actions_success(httpserver: HTTPServer, hwa_client_factory, action: str):
    """Test successful execution of all job actions."""
    httpserver.expect_request(
        f"/twsd/v1/plan/current/job/123/action/{action}",
        method="PUT"
    ).respond_with_json({"status": "success"})

    async with hwa_client_factory() as client:
        # Dynamically call the method on the client's plan service
        result = await getattr(client.plan, f"{action}_job")(job_id="123")
        assert result == {"status": "success"}
        httpserver.check_assertions()


@pytest.mark.asyncio
async def test_query_workstations_success(httpserver: HTTPServer, hwa_client_factory):
    """Test successful query of workstations."""
    httpserver.expect_request(
        "/twsd/v1/model/workstation/header/query",
        method="POST"
    ).respond_with_json([{"workstationName": "CPU1"}])

    async with hwa_client_factory() as client:
        result = await client.model.query_workstations()
        assert result == [{"workstationName": "CPU1"}]
        httpserver.check_assertions()

# --- Error Handling Tests ---

@pytest.mark.asyncio
async def test_authentication_error(httpserver: HTTPServer, hwa_client_factory):
    """Test that HWAAuthenticationError is raised on 401 status."""
    httpserver.expect_request(
        "/twsd/v1/plan/current/jobstream/query",
        method="POST"
    ).respond_with_data(status=401)

    with pytest.raises(HWAAuthenticationError):
        async with hwa_client_factory() as client:
            await client.plan.query_job_streams()

@pytest.mark.asyncio
async def test_api_error(httpserver: HTTPServer, hwa_client_factory):
    """Test that HWAAPIError is raised on 500 status."""
    httpserver.expect_request(
        "/twsd/v1/plan/current/jobstream/query",
        method="POST"
    ).respond_with_data(status=500, response_data=b"Internal Server Error")

    with pytest.raises(HWAAPIError) as excinfo:
        async with hwa_client_factory() as client:
            await client.plan.query_job_streams()

    assert excinfo.value.status_code == 500
    assert "Internal Server Error" in excinfo.value.response_text

@pytest.mark.asyncio
async def test_connection_error():
    """Test that HWAConnectionError is raised for connection issues."""
    # We don't use httpserver here to simulate a connection failure
    client = HWAClient(
        hostname="nonexistent.host",
        port=12345,
        username="user",
        password="password"
    )

    with pytest.raises(HWAConnectionError):
        async with client:
            await client.plan.query_job_streams()

@pytest.mark.asyncio
async def test_client_not_initialized():
    """Test that an error is raised if the client is used outside the context manager."""
    client = HWAClient(hostname="localhost", port=1234, username="user", password="pw")
    with pytest.raises(HWAConnectionError, match="Client is not initialized"):
        await client.plan.query_job_streams()

def test_client_init_validation():
    """Test that HWAClient raises ValueError for missing required parameters."""
    with pytest.raises(ValueError, match="Hostname, port, and username are required"):
        HWAClient(hostname="", port=123, username="user", password="pw")
    with pytest.raises(ValueError, match="Hostname, port, and username are required"):
        HWAClient(hostname="host", port=None, username="user", password="pw")
    with pytest.raises(ValueError, match="Hostname, port, and username are required"):
        HWAClient(hostname="host", port=123, username="", password="pw")
