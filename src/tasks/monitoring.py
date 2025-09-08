import logging
from src.tasks.celery_app import celery_app
from src.services.monitoring.job_monitor import job_monitor
import asyncio

@celery_app.task(name="tasks.poll_job_statuses")
def poll_job_statuses_task():
    """
    Celery task to poll for HWA job statuses.
    """
    logging.info("Celery task 'poll_job_statuses_task' started.")
    try:
        # We need to run the async poll method in an event loop.
        asyncio.run(job_monitor.initialize()) # Ensure client is initialized
        asyncio.run(job_monitor._poll_job_status())
        logging.info("Celery task 'poll_job_statuses_task' finished successfully.")
    except Exception as e:
        logging.error(f"Error in Celery task 'poll_job_statuses_task': {e}", exc_info=True)
        raise
