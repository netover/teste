import pytest
import pytest_asyncio
from datetime import datetime

from src.services.monitoring.job_monitor import JobMonitoringService, JobStatusEvent
from src.database.schema import JobStatusHistory
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


@pytest_asyncio.fixture(scope="function")
async def test_db_session():
    """
    Pytest fixture to set up a clean, in-memory SQLite database for a test function.
    It creates all tables, yields a session factory, and then tears down the database.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(JobStatusHistory.metadata.create_all)

    TestAsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield TestAsyncSessionLocal

    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_store_job_status_history(test_db_session, monkeypatch):
    """
    Tests that the _store_status_history method correctly writes a
    JobStatusEvent to the database using an isolated in-memory DB.
    """
    # Monkeypatch the session factory used by the service to use our test DB session
    monkeypatch.setattr(
        "src.services.monitoring.job_monitor.AsyncSessionLocal", test_db_session
    )

    # Create a JobMonitoringService instance
    service = JobMonitoringService()

    # Create a sample event
    event = JobStatusEvent(
        job_id="test_job_123",
        job_stream_name="TEST_JOB",
        old_status="PENDING",
        new_status="SUCCESS",
        workstation="CPU1",
        timestamp=datetime.utcnow(),
    )

    # Call the method to store the event
    await service._store_status_history(event)

    # Verify the data was written correctly using the same test DB session
    async with test_db_session() as session:
        result = await session.execute(
            select(JobStatusHistory).where(JobStatusHistory.job_id == "test_job_123")
        )
        saved_entry = result.scalar_one_or_none()

        assert saved_entry is not None
        assert saved_entry.job_stream_name == "TEST_JOB"
        assert saved_entry.status == "SUCCESS"
        assert saved_entry.workstation_name == "CPU1"
