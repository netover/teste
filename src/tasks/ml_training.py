import logging
from celery import Task
from src.tasks.celery_app import celery_app
from src.services.ml.trainer import model_trainer


class TrainAllModelsTask(Task):
    """
    A Celery task to trigger the training of all machine learning models.
    This class-based approach allows for easier testing and dependency injection.
    """

    name = "tasks.train_all_models"

    def run(self, *args, **kwargs):
        """
        The main execution logic of the task.
        """
        logging.info(f"Celery task '{self.name}' started.")
        try:
            # The training service is synchronous, so we call it directly.
            result = model_trainer.trigger_all_training()

            # Convert dataclass objects to dicts for JSON serialization
            if 'failure_predictor' in result:
                metrics = result['failure_predictor']
                # Manually convert to dict to avoid issues with asdict and potential
                # object identity problems across different module loads.
                result['failure_predictor'] = {
                    "accuracy": metrics.accuracy,
                    "feature_importance": metrics.feature_importance,
                }

            logging.info(f"Celery task '{self.name}' finished successfully.")
            return result
        except Exception as e:
            logging.error(f"Error in Celery task '{self.name}': {e}", exc_info=True)
            # The exception will be propagated and can be handled by Celery's retry mechanisms.
            raise
        finally:
            logging.info(f"Celery task '{self.name}' execution block finished.")


# In production, Celery's auto-discovery mechanism needs a task instance.
# We register the class-based task with the default celery_app instance.
# The `register_task` method returns the task instance.
train_all_models_task = celery_app.register_task(TrainAllModelsTask())
