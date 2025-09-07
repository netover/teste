from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class RiskFactor(BaseModel):
    """
    Represents a single factor contributing to a prediction's risk.
    """
    factor: str
    value: Any
    importance: float
    description: str

class JobFailurePrediction(BaseModel):
    """
    Schema for the output of a job failure prediction.
    """
    job_name: str
    failure_probability: float = Field(..., ge=0, le=1)
    prediction: str # e.g., "LIKELY_TO_FAIL"
    confidence: float = Field(..., ge=0, le=1)
    risk_factors: List[RiskFactor]
    recommendation: str

class AnomalyDetectionResult(BaseModel):
    """
    Schema for a single detected anomaly.
    """
    job_name: str
    anomaly_score: float
    anomaly_type: str
    description: str

class TrainingMetrics(BaseModel):
    """
    Schema for reporting metrics after a model training run.
    """
    accuracy: float
    feature_importance: Dict[str, float]

class ForecastDatapoint(BaseModel):
    """
    Represents a single point in a time-series forecast.
    """
    ds: datetime  # Date string
    yhat: float
    yhat_lower: float
    yhat_upper: float

class WorkloadForecast(BaseModel):
    """
    Contains the forecast results for a single metric (e.g., job_count).
    """
    predictions: List[ForecastDatapoint]
    trend: str
    seasonality_strength: float

class WorkstationForecastResponse(BaseModel):
    """
    The full response for a workstation workload forecast request.
    """
    workstation: str
    forecast_period: str
    generated_at: datetime
    forecasts: Dict[str, WorkloadForecast] # Keys: "job_count", "total_runtime", etc.
