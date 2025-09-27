from celery import Celery
from src.core.settings import settings

# In testing mode, we use a different broker and backend.
# The settings object automatically handles loading from environment variables.
if settings.TESTING:
    celery_app = Celery(
        "tasks",
        broker="memory://",
        backend=settings.CELERY_RESULT_BACKEND_OVERRIDE or "file:///tmp/celery-results",
    )
    celery_app.conf.update(
        task_always_eager=True,
        task_store_eager_result=True,
    )
else:
    celery_app = Celery(
        "tasks",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=['src.tasks.ml_training'] # List of modules to import when the worker starts
    )
    celery_app.conf.update(
        task_track_started=True,
        result_expires=3600, # Expire results after 1 hour
    )