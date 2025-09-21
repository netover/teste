import pytest
from pytest_httpserver import HTTPServer
from src.hwa_connector import HWAClient, HWAAPIError, HWAAuthenticationError

# A sample successful JSON response for a job stream query
SAMPLE_JS_RESPONSE = [
    {"jobStreamName": "JOB_A", "workstationName": "CPU1", "status": "SUCC"},
    {"jobStreamName": "JOB_B", "workstationName": "CPU1", "status": "EXEC"},
]

# A sample JSON error response for an authentication failure
SAMPLE_AUTH_ERROR_RESPONSE = {
    "message": "AWSJCS005E The user is not authorized to access the specified object.",
    "messageId": "AWSJCS005E"
}


@pytest.mark.asyncio
async def test_query_job_streams_success(httpserver: HTTPServer):
    """
    Tests that HWAClient can successfully query and parse job streams.
    """
    # The endpoint and method must match what HWAClient actually calls
    httpserver.expect_request(
        "/twsd/v1/plan/current/jobstream/query",
        method="POST",
    ).respond_with_json(SAMPLE_JS_RESPONSE)

    # The client should connect to our mock server
    client = HWAClient(
        hostname=httpserver.host,
        port=httpserver.port,
        username="testuser",
        password="testpassword",
        protocol="http"
    )

    async with client as active_client:
        job_streams = await active_client.plan.query_job_streams()
        assert len(job_streams) == 2
        assert job_streams[0]["jobStreamName"] == "JOB_A"
        assert job_streams[1]["status"] == "EXEC"

@pytest.mark.asyncio
async def test_query_job_streams_auth_error(httpserver: HTTPServer):
    """
    Tests that HWAClient raises HWAAuthenticationError on a 401 response.
    """
    httpserver.expect_request(
        "/twsd/v1/plan/current/jobstream/query",
        method="POST",
    ).respond_with_json(SAMPLE_AUTH_ERROR_RESPONSE, status=401)

    client = HWAClient(
        hostname=httpserver.host,
        port=httpserver.port,
        username="testuser",
        password="testpassword",
        protocol="http"
    )

    async with client as active_client:
        with pytest.raises(HWAAuthenticationError, match="Authentication failed: 401"):
            await active_client.plan.query_job_streams()
