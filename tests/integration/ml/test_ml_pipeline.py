import pytest
import time
from httpx import Client
from pathlib import Path

# This test does not require asyncio, so the mark is removed to avoid conflicts.

def test_train_model_e2e(backend_server, monkeypatch):
    """
    End-to-end test for the ML model training pipeline, run synchronously.
    It triggers training, polls for completion, and verifies artifacts.
    """
    base_url, predictor_model_dir, forecaster_model_dir = backend_server

    # No need to monkeypatch anymore, as the fixture sets environment variables
    # that the service modules will pick up on import in the server process.

    with Client(base_url=base_url, timeout=60.0) as client:
        # Step 1: Trigger the training job
        response = client.post("/api/ml/train")
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        assert task_id is not None

        # Step 2: Poll the status endpoint.
        for _ in range(10): # Poll for a maximum of 10 seconds
            status_response = client.get(f"/api/ml/train/status/{task_id}")
            assert status_response.status_code == 200
            result = status_response.json()
            if result["status"] == "SUCCESS":
                break
            if result["status"] == "FAILURE":
                pytest.fail(f"Task failed. Full result: {result}")
            time.sleep(1)
        else:
            pytest.fail(f"Task did not succeed within the polling timeout. Last status: {result.get('status', 'UNKNOWN')}")

        assert result["status"] == "SUCCESS"
        assert "failure_predictor" in result["result"]
        assert result["result"]["failure_predictor"]["accuracy"] > 0

        # Step 3: Verify that the model artifacts were created in the temp directories
        # provided by the backend_server fixture.
        failure_model_path = Path(predictor_model_dir) / "failure_predictor.joblib"
        scaler_path = Path(predictor_model_dir) / "feature_scaler.joblib"
        forecast_model_path = Path(forecaster_model_dir) / "CPU1_IO_job_count.joblib"

        assert failure_model_path.exists(), f"Failure predictor model not found at {failure_model_path}"
        assert scaler_path.exists(), f"Feature scaler not found at {scaler_path}"
        assert forecast_model_path.exists(), f"Forecast model not found at {forecast_model_path}"
