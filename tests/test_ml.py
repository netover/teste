import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch

from src.services.ml.predictor import JobFailurePredictorML
from src.services.ml.forecasting import WorkloadForecaster
from src.services.ml.models import TrainingMetrics, JobFailurePrediction, WorkstationForecastResponse

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_job_history_df():
    """Provides a mock DataFrame for job history with enough data for stratification."""
    data = {
        "timestamp": pd.to_datetime([f"2023-01-{i+1:02d}" for i in range(10)]),
        "job_name": [f"JOB_{chr(65+i)}" for i in range(10)],
        "failed": [0, 1, 0, 0, 1, 0, 1, 0, 0, 1]  # 4 failed, 6 succeeded
    }
    return pd.DataFrame(data)

@pytest.fixture
def mock_workload_history_df():
    """Provides a mock DataFrame for workload history."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        "workstation": ["CPU1", "CPU1"],
        "job_count": [100, 110],
        "total_runtime": [12000, 13000],
        "cpu_usage": [0.5, 0.6]
    })

class TestJobFailurePredictor:

    async def test_train_failure_model(self, mocker, mock_job_history_df):
        """Tests the training process of the failure predictor."""
        mocker.patch('joblib.dump') # Mock joblib to prevent actual file writing
        predictor = JobFailurePredictorML()

        metrics = await predictor.train_failure_prediction_model(mock_job_history_df)

        assert isinstance(metrics, TrainingMetrics)
        assert metrics.accuracy >= 0
        assert "avg_runtime" in metrics.feature_importance

    async def test_predict_job_failure(self, mocker):
        """Tests the prediction method of the failure predictor."""
        # Mock the loading of a pre-trained model
        mocker.patch('joblib.load', return_value=mocker.MagicMock())
        mocker.patch('pathlib.Path.exists', return_value=True)

        predictor = JobFailurePredictorML()
        await predictor._load_model() # Manually trigger loading the mocked model

        # Mock the model's prediction methods
        predictor.failure_model.predict_proba = mocker.MagicMock(return_value=[[0.8, 0.2]])
        predictor.failure_model.predict = mocker.MagicMock(return_value=[0])
        predictor.failure_model.feature_importances_ = np.random.rand(len(predictor.feature_columns))

        job_data = {"jobStreamName": "TEST_JOB"}
        prediction = await predictor.predict_job_failure(job_data)

        assert isinstance(prediction, JobFailurePrediction)
        assert prediction.job_name == "TEST_JOB"
        assert prediction.prediction == "LIKELY_TO_SUCCEED"
        assert prediction.failure_probability == 0.2


class TestWorkloadForecaster:

    async def test_train_workload_forecast(self, mocker, mock_workload_history_df):
        """Tests the training process of the workload forecaster."""
        mocker.patch('joblib.dump') # Mock joblib to prevent file writing
        forecaster = WorkloadForecaster()

        await forecaster.train_workload_forecast(mock_workload_history_df)

        # Check if models were created for each metric
        assert "CPU1_job_count" in forecaster.models
        assert "CPU1_total_runtime" in forecaster.models
        assert "CPU1_cpu_usage" in forecaster.models

    async def test_forecast_workload(self, mocker, mock_workload_history_df):
        """Tests the forecasting method."""
        mocker.patch('joblib.dump')
        mocker.patch('pathlib.Path.exists', return_value=False) # Ensure it trains, not loads

        forecaster = WorkloadForecaster()
        # Train a mock model first
        await forecaster.train_workload_forecast(mock_workload_history_df)

        response = await forecaster.forecast_workload("CPU1", days_ahead=7)

        assert isinstance(response, WorkstationForecastResponse)
        assert response.workstation == "CPU1"
        assert "job_count" in response.forecasts
        assert len(response.forecasts["job_count"].predictions) == 7
