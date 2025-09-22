import os
from celery import Celery


def create_celery_app():
    """
    Factory function to create and configure a Celery app instance.
    The configuration (broker, backend) depends on the 'TESTING' environment variable.
    """
    # Check for a specific environment variable to determine if we are in a test environment
    if os.environ.get("TESTING"):
        # For testing, we don't use auto-discovery. Tasks will be created explicitly.
        app = Celery(
            "tasks",
            broker="memory://",
            backend="file:///tmp/celery-results",
        )
        # For eager mode in testing, which is critical for integration tests.
        app.conf.update(
            task_always_eager=True,
            task_store_eager_result=True,  # Ensure results are stored in eager mode
        )
    else:
        # For production, use Redis as the broker and backend and auto-discover tasks.
        app = Celery(
            "tasks",
            broker="redis://localhost:6379/0",
            backend="redis://localhost:6379/0",
            include=["src.tasks.ml_training"],
        )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
    return app


# Create a default instance for the application to use.
# In a testing context, this will be replaced by a test-specific instance.
celery_app = create_celery_app()
