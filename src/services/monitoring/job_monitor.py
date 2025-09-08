import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict
import redis.asyncio as redis
from prometheus_client import Counter

from src.core import config
from src.core.database import AsyncSessionLocal
from src.hwa_connector import HWAClient, HWAConnectionError, HWAAPIError
from src.models.database import JobStatusHistory

# --- Prometheus Metrics ---
job_status_changes_counter = Counter(
    "hwa_job_status_changes_total",
    "Total number of job status changes processed",
    ["job_name", "workstation", "old_status", "new_status"],
)

@dataclass
class JobStatusEvent:
    job_id: str
    job_name: str
    old_status: str
    new_status: str
    workstation: str
    timestamp: datetime
    duration: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

class JobMonitoringService:
    """
    A service that contains the core logic for polling and processing job status updates.
    The scheduling of the polling is handled by an external process (e.g., Celery Beat).
    """
    def __init__(self):
        self.redis_client: redis.Redis = None
        self.job_cache: Dict[str, dict] = {}
        self.is_initialized = False

    async def initialize(self):
        """Initializes the service, primarily for the Redis connection."""
        if self.is_initialized:
            return
        self.redis_client = await redis.from_url(config.REDIS_URL, decode_responses=True)
        self.is_initialized = True
        logging.info(f"JobMonitoringService initialized with Redis at {config.REDIS_URL}")

    async def poll_and_process_jobs(self):
        """The core logic of the service: poll HWA and process any changes."""
        logging.info("Polling for job status...")
        try:
            # HWAClient is now used with a context manager within the poll
            async with HWAClient(
                hostname=config.HWA_HOSTNAME,
                port=config.HWA_PORT,
                username=config.HWA_USERNAME,
                password=config.HWA_PASSWORD
            ) as client:
                current_jobs = await client.plan.query_job_streams()
        except (HWAConnectionError, HWAAPIError) as e:
            logging.error(f"Failed to query HWA for job streams: {e}")
            return
        except Exception as e:
            logging.error(f"An unexpected error occurred during HWA query: {e}", exc_info=True)
            return

        new_cache = {job.get("jobStreamName"): job for job in current_jobs if job.get("jobStreamName")}

        for job_name, job_data in new_cache.items():
            if job_name in self.job_cache:
                old_job = self.job_cache[job_name]
                if old_job.get("status") != job_data.get("status"):
                    await self._process_job_update(job_data, old_job)
            else:
                await self._process_job_update(job_data, None)

        self.job_cache = new_cache
        logging.info(f"Job status poll complete. Cache updated with {len(self.job_cache)} jobs.")

    async def _process_job_update(self, job_data: dict, old_job_data: Optional[dict]):
        event = JobStatusEvent(
            job_id=job_data.get("id", job_data.get("jobStreamName")),
            job_name=job_data.get("jobStreamName"),
            old_status=old_job_data.get("status", "NEW") if old_job_data else "NEW",
            new_status=job_data.get("status", "UNKNOWN"),
            workstation=job_data.get("workstationName", ""),
            timestamp=datetime.now(),
        )
        await self._handle_status_change(event)

    async def _handle_status_change(self, event: JobStatusEvent):
        logging.info(f"Job Status Change: {event.job_name} | {event.old_status} -> {event.new_status}")
        job_status_changes_counter.labels(
            job_name=event.job_name,
            workstation=event.workstation,
            old_status=event.old_status,
            new_status=event.new_status,
        ).inc()
        await self._store_status_history(event)
        await self._check_alert_rules(event)
        await self._publish_realtime_update(event)

    async def _store_status_history(self, event: JobStatusEvent):
        logging.debug(f"Storing history for job {event.job_name}")
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    history_entry = JobStatusHistory(
                        job_id=event.job_id,
                        job_name=event.job_name,
                        old_status=event.old_status,
                        new_status=event.new_status,
                        workstation=event.workstation,
                        duration=event.duration,
                        error_message=event.error_message,
                    )
                    session.add(history_entry)
        except Exception as e:
            logging.error(f"Failed to store job status history for '{event.job_name}': {e}", exc_info=True)

    async def _check_alert_rules(self, event: JobStatusEvent):
        if (event.new_status in config.CRITICAL_STATUSES and event.old_status not in config.CRITICAL_STATUSES):
            alert_data = {
                "type": "alert_notification",
                "data": {"severity": "HIGH", "title": "Job Failure", "job_name": event.job_name, "status": event.new_status, "workstation": event.workstation, "timestamp": event.timestamp.isoformat(), "message": f"Job '{event.job_name}' on workstation '{event.workstation}' failed with status: {event.new_status}."},
            }
            await self._send_alert(alert_data)

    async def _send_alert(self, alert_data: dict):
        if self.redis_client:
            await self.redis_client.publish("alert_notifications", json.dumps(alert_data))
            logging.warning(f"ALERT SENT: {alert_data['data']['message']}")

    async def _publish_realtime_update(self, event: JobStatusEvent):
        update_data = {"type": "job_status_update", "data": event.to_dict()}
        if self.redis_client:
            await self.redis_client.publish("job_updates", json.dumps(update_data))

# Global monitoring service instance
job_monitor = JobMonitoringService()
