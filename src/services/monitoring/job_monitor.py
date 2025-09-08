import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, asdict
import redis.asyncio as redis

from src.core import config
from src.core.database import AsyncSessionLocal
from src.hwa_connector import HWAClient, HWAConnectionError, HWAAPIError
from src.models.database import JobStatusHistory

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
    def __init__(self, poll_interval: int = 30):
        self.redis_client: redis.Redis = None
        self.monitoring_active = False
        self.poll_interval = poll_interval
        self.job_cache: Dict[str, dict] = {}
        self.is_initialized = False

    async def initialize(self):
        if self.is_initialized:
            return
        self.redis_client = await redis.from_url(config.REDIS_URL, decode_responses=True)
        self.is_initialized = True
        logging.info(f"JobMonitoringService initialized with Redis at {config.REDIS_URL}")

    async def start_monitoring(self):
        if self.monitoring_active:
            logging.warning("Monitoring is already active.")
            return
        self.monitoring_active = True
        logging.info(f"Job monitoring service started with a poll interval of {self.poll_interval} seconds.")

        while self.monitoring_active:
            try:
                await self._poll_job_status()
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    def stop_monitoring(self):
        self.monitoring_active = False
        logging.info("Job monitoring service stopped.")

    async def _poll_job_status(self):
        logging.debug("Polling for job status...")
        try:
            async with HWAClient(
                hostname=config.HWA_HOSTNAME, port=config.HWA_PORT,
                username=config.HWA_USERNAME, password=config.HWA_PASSWORD
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
        await self._store_status_history(event)
        await self._check_alert_rules(event)
        await self._publish_realtime_update(event)

    async def _store_status_history(self, event: JobStatusEvent):
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    history_entry = JobStatusHistory(**event.to_dict())
                    session.add(history_entry)
        except Exception as e:
            logging.error(f"Failed to store job status history: {e}", exc_info=True)

    async def _check_alert_rules(self, event: JobStatusEvent):
        if (event.new_status in config.CRITICAL_STATUSES and event.old_status not in config.CRITICAL_STATUSES):
            alert_data = {"type": "alert_notification", "data": {"severity": "HIGH", "title": "Job Failure", "job_name": event.job_name, "status": event.new_status, "workstation": event.workstation, "timestamp": event.timestamp.isoformat(), "message": f"Job '{event.job_name}' on workstation '{event.workstation}' failed with status: {event.new_status}."}}
            await self._send_alert(alert_data)

    async def _send_alert(self, alert_data: dict):
        if self.redis_client:
            await self.redis_client.publish("alert_notifications", json.dumps(alert_data))
            logging.warning(f"ALERT SENT: {alert_data['data']['message']}")

    async def _publish_realtime_update(self, event: JobStatusEvent):
        update_data = {"type": "job_status_update", "data": event.to_dict()}
        if self.redis_client:
            await self.redis_client.publish("job_updates", json.dumps(update_data))

job_monitor = JobMonitoringService()
