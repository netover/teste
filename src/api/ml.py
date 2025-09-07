import logging
from fastapi import APIRouter, HTTPException, Body, Depends
from typing import List, Dict, Any
from celery.result import AsyncResult

from src.services.ml import models
from src.security import get_api_key
from src.services.ml.predictor import job_predictor
from src.services.ml.forecasting import workload_forecaster
from src.tasks.ml_training import train_all_models_task

router = APIRouter(
    prefix="/api/ml",
    tags=["Machine Learning"],
)

@router.post("/train", status_code=202, dependencies=[Depends(get_api_key)])
def dispatch_model_training() -> Dict[str, str]:
    """
    Dispatches a background task to train all ML models.
    Returns immediately with the ID of the task.
    """
    try:
        logging.info("API endpoint '/train' called. Dispatching Celery task.")
        task = train_all_models_task.delay()
        return {"message": "Model training task dispatched.", "task_id": task.id}
    except Exception as e:
        logging.error(f"Error dispatching training task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to dispatch training task.")

@router.get("/train/status/{task_id}", dependencies=[Depends(get_api_key)])
def get_training_status(task_id: str) -> Dict[str, Any]:
    """
    Checks the status of a model training task.
    """
    task_result = AsyncResult(task_id, app=train_all_models_task.app)

    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None
    }

    if task_result.successful():
        response["result"] = task_result.get()
    elif task_result.failed():
        # The result of a failed task is the exception object.
        # We should return a serializable representation of it.
        response["result"] = {
            "error": str(task_result.result),
            "traceback": task_result.traceback
        }

    return response


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
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error during workload forecasting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during forecasting.")
