import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import redis.asyncio as redis

from src.hwa_connector import HWAClient
# from src.models.database import JobStatusHistory, AlertRule # Will be implemented next
from src.services.monitoring.websocket import ws_manager

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
        d['timestamp'] = self.timestamp.isoformat()
        return d

class JobMonitoringService:
    def __init__(self, poll_interval: int = 30):
        self.redis_client: redis.Redis = None
        self.monitoring_active = False
        self.poll_interval = poll_interval
        self.job_cache: Dict[str, dict] = {}

    async def initialize(self, redis_url: str = "redis://localhost:6379"):
        """Initialize monitoring service with a Redis connection."""
        self.redis_client = await redis.from_url(redis_url, decode_responses=True)
        logging.info("JobMonitoringService initialized with Redis.")

    async def start_monitoring(self):
        """Start continuous job monitoring in a background task."""
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
        """Stop the monitoring service."""
        self.monitoring_active = False
        logging.info("Job monitoring service stopped.")

    async def _poll_job_status(self):
        """Poll HWA for current job status."""
        logging.debug("Polling for job status...")
        try:
            async with HWAClient() as client:
                current_jobs = await client.plan.query_job_streams()
        except Exception as e:
            logging.error(f"Failed to query HWA for job streams: {e}")
            return # Don't proceed if HWA connection fails

        new_cache = {job.get('jobStreamName'): job for job in current_jobs if job.get('jobStreamName')}

        # Process updates for jobs that are still present
        for job_name, job_data in new_cache.items():
            if job_name in self.job_cache:
                old_job = self.job_cache[job_name]
                if old_job.get('status') != job_data.get('status'):
                    await self._process_job_update(job_data, old_job)
            else:
                # New job detected
                await self._process_job_update(job_data, None)

        self.job_cache = new_cache
        logging.debug(f"Job cache updated with {len(self.job_cache)} jobs.")

    async def _process_job_update(self, job_data: dict, old_job_data: Optional[dict]):
        """Process an individual job for status changes."""
        event = JobStatusEvent(
            job_id=job_data.get('id', job_data.get('jobStreamName')),
            job_name=job_data.get('jobStreamName'),
            old_status=old_job_data.get('status', 'NEW') if old_job_data else 'NEW',
            new_status=job_data.get('status', 'UNKNOWN'),
            workstation=job_data.get('workstationName', ''),
            timestamp=datetime.now()
        )
        await self._handle_status_change(event)

    async def _handle_status_change(self, event: JobStatusEvent):
        """Handle a job status change event by logging, storing, alerting, and publishing."""
        logging.info(f"Job Status Change: {event.job_name} | {event.old_status} -> {event.new_status}")

        # Store in database
        await self._store_status_history(event)

        # Check for alert conditions
        await self._check_alert_rules(event)

        # Publish the update to the real-time channel
        await self._publish_realtime_update(event)

    async def _store_status_history(self, event: JobStatusEvent):
        """Store job status change in the database."""
        # This will use SQLAlchemy to create and save a JobStatusHistory entry.
        # Example:
        # from src.core.database import SessionLocal
        # from src.models.database import JobStatusHistory
        # async with SessionLocal() as db:
        #     history_entry = JobStatusHistory(**event.to_dict())
        #     db.add(history_entry)
        #     await db.commit()
        logging.info(f"Database storage for job {event.job_name} is currently stubbed.")
        pass

    async def _check_alert_rules(self, event: JobStatusEvent):
        """Check if the status change triggers any defined alert rules."""
        critical_statuses = ['ABEND', 'ERROR', 'FAIL']
        if event.new_status in critical_statuses and event.old_status not in critical_statuses:
            alert_data = {
                "type": "alert_notification",
                "data": {
                    "severity": "HIGH",
                    "title": "Job Failure",
                    "job_name": event.job_name,
                    "status": event.new_status,
                    "workstation": event.workstation,
                    "timestamp": event.timestamp.isoformat(),
                    "message": f"Job '{event.job_name}' on workstation '{event.workstation}' failed with status: {event.new_status}."
                }
            }
            await self._send_alert(alert_data)

    async def _send_alert(self, alert_data: dict):
        """Publish an alert to the Redis alert channel."""
        if self.redis_client:
            await self.redis_client.publish("alert_notifications", json.dumps(alert_data))
            logging.warning(f"ALERT SENT: {alert_data['data']['message']}")

    async def _publish_realtime_update(self, event: JobStatusEvent):
        """Publish a job status update to the Redis job updates channel."""
        update_data = {
            "type": "job_status_update",
            "data": event.to_dict()
        }
        if self.redis_client:
            await self.redis_client.publish("job_updates", json.dumps(update_data))

# Global monitoring service instance
job_monitor = JobMonitoringService()
