import logging
from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List, Dict

from src.services.ml import models
from src.security import get_api_key
from src.services.ml.predictor import job_predictor
from src.services.ml.forecasting import workload_forecaster
from src.services.ml.trainer import model_trainer

router = APIRouter(
    prefix="/api/ml",
    tags=["Machine Learning"],
)

@router.post("/train", response_model=models.TrainingMetrics, dependencies=[Depends(get_api_key)])
def train_all_models():
    """
    Triggers the training process for the job failure prediction model.
    This is a long-running, protected operation that should be handled by a background worker.
    """
    try:
        logging.info("API endpoint '/train' called. Triggering model training.")
        # This will later be replaced by:
        # from src.tasks.ml_training import train_all_models_task
        # train_all_models_task.delay()
        # return {"message": "Model training task has been dispatched."}
        metrics = model_trainer.trigger_failure_prediction_training()
        return metrics
    except Exception as e:
        logging.error(f"Error during model training endpoint call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during model training.")

@router.post("/predict/failure", response_model=models.JobFailurePrediction)
def predict_job_failure(
    job_data: Dict = Body(
        ...,
        example={
            "jobStreamName": "CRITICAL_JOB_01",
            "avg_runtime": 450,
            "runtime_variance": 100,
            "failure_rate_7d": 0.3,
            "workstation_load": 0.85,
            "consecutive_failures": 2,
            "sla_breach_history": 4
        }
    )
):
    """
    Predicts the failure probability for a given job's real-time data.
    """
    try:
        prediction = job_predictor.predict_job_failure(job_data)
        return prediction
    except RuntimeError as e:
        # This happens if the model is not trained yet
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error during failure prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during prediction.")

@router.get("/forecast/workload/{workstation_name}", response_model=models.WorkstationForecastResponse)
def get_workload_forecast(workstation_name: str, days_ahead: int = 7):
    """
    Generates a workload forecast for a given workstation.
    Assumes models have been pre-trained.
    """
    try:
        forecast = workload_forecaster.forecast_workload(workstation_name, days_ahead)
        return forecast
    except ValueError as e:
        # This happens if models for the workstation are not trained
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error during workload forecasting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during forecasting.")
