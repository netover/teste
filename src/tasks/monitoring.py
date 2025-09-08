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
        # Ensure the service is initialized before polling.
        asyncio.run(job_monitor.initialize())
        asyncio.run(job_monitor.poll_and_process_jobs())
        logging.info("Celery task 'poll_job_statuses_task' finished successfully.")
    except Exception as e:
        logging.error(f"Error in Celery task 'poll_job_statuses_task': {e}", exc_info=True)
        raise
