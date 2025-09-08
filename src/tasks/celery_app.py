from celery import Celery
from src.core import config

# Create a Celery instance
# The first argument is the name of the current module, which is '__main__' when run directly.
# The 'broker' argument specifies the URL of the message broker (Redis in our case).
# The 'backend' argument specifies the result backend, also Redis.
celery_app = Celery(
    "tasks",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
    include=['src.tasks.ml_training'] # List of modules to import when the worker starts
)

# Optional Celery configuration
celery_app.conf.update(
    task_track_started=True,
    result_expires=3600, # Expire results after 1 hour
)
