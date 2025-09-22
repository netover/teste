import os
from celery import Celery
from src.core import config

# In testing mode, we use a different broker and backend
if os.environ.get("TESTING"):
    backend_override = os.environ.get("CELERY_RESULT_BACKEND_OVERRIDE")
    celery_app = Celery(
        "tasks",
        broker="memory://",
        backend=backend_override or "file:///tmp/celery-results",
    )
    celery_app.conf.update(
        task_always_eager=True,
        task_store_eager_result=True,
    )
else:
    celery_app = Celery(
        "tasks",
        broker=config.REDIS_URL,
        backend=config.REDIS_URL,
        include=['src.tasks.ml_training'] # List of modules to import when the worker starts
    )
    celery_app.conf.update(
        task_track_started=True,
        result_expires=3600, # Expire results after 1 hour
    )
