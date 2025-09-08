import pytest
from unittest.mock import MagicMock, AsyncMock

from src.services.monitoring.job_monitor import JobMonitoringService, JobStatusEvent
from src.services.monitoring.websocket import WebSocketManager

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# --- Fixtures ---


@pytest.fixture
def service():
    """Provides a fresh JobMonitoringService instance for each test."""
    service_instance = JobMonitoringService(poll_interval=0.1)
    service_instance.redis_client = AsyncMock()
    return service_instance


@pytest.fixture
def manager():
    """Provides a fresh WebSocketManager instance for each test."""
    manager_instance = WebSocketManager()
    manager_instance.redis_client = AsyncMock()
    return manager_instance


# --- Tests for JobMonitoringService ---


async def test_poll_job_status_detects_new_job(mocker, service):
    """Verify that a newly appeared job is detected and processed."""
    mock_hwa_client = mocker.patch("src.services.monitoring.job_monitor.HWAClient")
    mock_hwa_client.return_value.__aenter__.return_value.plan.query_job_streams = (
        AsyncMock(
            return_value=[
                {
                    "jobStreamName": "JOB_A",
                    "status": "EXEC",
                    "id": "123",
                    "workstationName": "CPU1",
                }
            ]
        )
    )

    service._handle_status_change = AsyncMock()

    await service._poll_job_status()

    service._handle_status_change.assert_called_once()
    call_args = service._handle_status_change.call_args[0][0]
    assert isinstance(call_args, JobStatusEvent)
    assert call_args.job_name == "JOB_A"
    assert call_args.old_status == "NEW"
    assert call_args.new_status == "EXEC"


async def test_poll_job_status_detects_status_change(mocker, service):
    """Verify that a change in a job's status is detected."""
    service.job_cache = {
        "JOB_A": {
            "jobStreamName": "JOB_A",
            "status": "PEND",
            "id": "123",
            "workstationName": "CPU1",
        }
    }

    mock_hwa_client = mocker.patch("src.services.monitoring.job_monitor.HWAClient")
    mock_hwa_client.return_value.__aenter__.return_value.plan.query_job_streams = (
        AsyncMock(
            return_value=[
                {
                    "jobStreamName": "JOB_A",
                    "status": "EXEC",
                    "id": "123",
                    "workstationName": "CPU1",
                }
            ]
        )
    )

    service._handle_status_change = AsyncMock()

    await service._poll_job_status()

    service._handle_status_change.assert_called_once()
    call_args = service._handle_status_change.call_args[0][0]
    assert call_args.job_name == "JOB_A"
    assert call_args.old_status == "PEND"
    assert call_args.new_status == "EXEC"


async def test_handle_status_change_publishes_and_alerts(service):
    """Verify that a critical status change triggers both a real-time update and an alert."""
    event = JobStatusEvent(
        job_id="123",
        job_name="JOB_A",
        old_status="EXEC",
        new_status="ABEND",
        workstation="CPU1",
        timestamp=MagicMock(),
    )
    service._publish_realtime_update = AsyncMock()
    service._send_alert = AsyncMock()
    service._store_status_history = AsyncMock()

    await service._handle_status_change(event)

    service._publish_realtime_update.assert_called_once_with(event)
    service._send_alert.assert_called_once()
    service._store_status_history.assert_called_once_with(event)


# --- Tests for WebSocketManager ---


async def test_connect_disconnect(manager):
    """Verify that the manager can connect and disconnect a user's WebSocket."""
    user_id = "test_user_1"
    mock_ws = AsyncMock()

    await manager.connect(mock_ws, user_id)
    assert user_id in manager.active_connections
    assert mock_ws in manager.active_connections[user_id]
    mock_ws.accept.assert_called_once()

    await manager.disconnect(mock_ws, user_id)
    assert user_id not in manager.active_connections
