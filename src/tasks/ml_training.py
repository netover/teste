import logging
from src.tasks.celery_app import celery_app
from src.services.ml.trainer import model_trainer

@celery_app.task(name="tasks.train_all_models")
def train_all_models_task():
    """
    A Celery task to trigger the training of all machine learning models.
    """
    logging.info("Celery task 'train_all_models_task' started.")
    try:
        # The training service is now synchronous, so we can call it directly.
        result = model_trainer.trigger_all_training()
        logging.info("Celery task 'train_all_models_task' finished successfully.")
        return result
    except Exception as e:
        logging.error(f"Error in Celery task 'train_all_models_task': {e}", exc_info=True)
        # We can retry the task later if needed
        raise
