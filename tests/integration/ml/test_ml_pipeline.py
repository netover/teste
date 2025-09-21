import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
import time

from src.api_server import app
from src.services.ml.predictor import MODEL_DIR as PREDICTOR_MODEL_DIR
from src.services.ml.forecasting import FORECAST_MODEL_DIR

# Use the FastAPI TestClient
client = TestClient(app)

@pytest.fixture(scope="module")
def ml_test_env():
    """
    Fixture to create and clean up directories for ML models and test results.
    """
    # Define a temporary directory for celery results
    CELERY_RESULT_DIR = Path("./celery_test_results")

    # Setup: remove directories if they exist
    if PREDICTOR_MODEL_DIR.exists():
        shutil.rmtree(PREDICTOR_MODEL_DIR)
    if CELERY_RESULT_DIR.exists():
        shutil.rmtree(CELERY_RESULT_DIR)

    # Re-create directories
    PREDICTOR_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    FORECAST_MODEL_DIR.mkdir(exist_ok=True)
    CELERY_RESULT_DIR.mkdir(exist_ok=True)

    yield CELERY_RESULT_DIR

    # Teardown: remove directories after tests run
    shutil.rmtree(PREDICTOR_MODEL_DIR)
    shutil.rmtree(CELERY_RESULT_DIR)


def test_training_pipeline(ml_test_env, monkeypatch):
    """
    An integration test for the full ML training pipeline.
    It calls the training endpoint and polls for a successful result,
    then verifies that the model artifacts were created.

    Note: This test runs the actual training process, which can be slow.
    It's marked as an integration test and might be skipped in faster test runs.
    """
    # Configure Celery to run tasks eagerly and use a file-based backend for this test
    from src.tasks.celery_app import celery_app
    monkeypatch.setattr(celery_app.conf, "task_always_eager", True)
    monkeypatch.setattr(celery_app.conf, "task_store_eager_result", True)
    monkeypatch.setattr(celery_app.conf, "broker_url", "memory://")
    monkeypatch.setattr(celery_app.conf, "result_backend", f"file://{ml_test_env.resolve()}")

    # 1. Dispatch the training task
    response = client.post("/api/ml/train")
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    task_id = data["task_id"]

    # 2. Poll for task completion
    start_time = time.time()
    timeout = 300  # 5-minute timeout for training, as Prophet can be slow
    status = ""
    while time.time() - start_time < timeout:
        status_response = client.get(f"/api/ml/train/status/{task_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        status = status_data["status"]
        if status == "SUCCESS":
            break
        elif status == "FAILURE":
            pytest.fail(f"ML training task failed: {status_data.get('result')}")
        time.sleep(2)
    else:
        pytest.fail("Timed out waiting for ML training task to complete.")

    assert status == "SUCCESS"

    # 3. Verify that model artifacts were created
    assert (PREDICTOR_MODEL_DIR / "failure_predictor.joblib").exists()
    assert (PREDICTOR_MODEL_DIR / "feature_scaler.joblib").exists()

    # Check that at least one forecaster model was created
    # The mock data generator creates models for "CPU1_IO", "CPU2_BATCH", etc.
    forecast_models = list(FORECAST_MODEL_DIR.glob("*.joblib"))
    assert len(forecast_models) > 0
    print(f"Found forecaster models: {[p.name for p in forecast_models]}")
