import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict

from src.services.ml.predictor import job_predictor
from src.services.ml.forecasting import workload_forecaster
from src.services.ml.models import TrainingMetrics

class ModelTrainingService:
    """
    A service to orchestrate the training of all machine learning models.
    """

    def __init__(self):
        logging.info("ModelTrainingService initialized.")

    def trigger_all_training(self) -> Dict[str, TrainingMetrics]:
        """
        Triggers the training for all available models.
        """
        logging.info("Starting training for all models...")
        failure_metrics = self.trigger_failure_prediction_training()
        self.trigger_workload_forecasting_training()
        logging.info("All model training processes triggered.")
        return {
            "failure_predictor": failure_metrics
        }

    def trigger_failure_prediction_training(self) -> TrainingMetrics:
        """
        Generates mock historical data and trains the failure prediction model.
        """
        logging.info("Generating data for failure prediction training...")
        historical_data = self._generate_mock_job_history(days=30, num_jobs=50)
        logging.info(f"Generated {len(historical_data)} historical job records.")

        metrics = job_predictor.train_failure_prediction_model(historical_data)
        return metrics

    def trigger_workload_forecasting_training(self):
        """
        Generates mock historical data and trains the workload forecasting models.
        """
        logging.info("Generating data for workload forecast training...")
        historical_data = self._generate_mock_workload_history(days=90)
        logging.info(f"Generated {len(historical_data)} historical workload records.")

        workload_forecaster.train_workload_forecast(historical_data)


    def _generate_mock_job_history(self, days: int, num_jobs: int) -> pd.DataFrame:
        """Generates a Pandas DataFrame of fake job history."""
        data = []
        job_names = [f"JOB_{chr(65+i)}" for i in range(num_jobs)]
        end_date = datetime.now()

        for i in range(days * num_jobs * 2): # More data points
            job_name = np.random.choice(job_names)
            timestamp = end_date - timedelta(days=np.random.uniform(0, days))
            status = np.random.choice(['SUCCESS', 'ABEND'], p=[0.9, 0.1])

            data.append({
                "timestamp": timestamp,
                "job_name": job_name,
                "failed": 1 if status == 'ABEND' else 0,
                "avg_runtime": np.random.normal(300, 50),
                "runtime_variance": np.random.normal(20, 5),
                "failure_rate_7d": np.random.uniform(0, 0.3),
                "workstation_load": np.random.rand(),
                "consecutive_failures": np.random.randint(0, 3) if status == 'ABEND' else 0,
                "sla_breach_history": np.random.randint(0, 5)
            })
        return pd.DataFrame(data)

    def _generate_mock_workload_history(self, days: int) -> pd.DataFrame:
        """Generates a Pandas DataFrame of fake workload history for forecasting."""
        data = []
        workstations = ["CPU1_IO", "CPU2_BATCH", "CPU3_REPORTS"]
        end_date = datetime.now()

        for day in range(days):
            date = end_date - timedelta(days=day)
            for ws in workstations:
                # Add some seasonality (e.g., more jobs on weekdays)
                weekday_factor = 1.5 if date.weekday() < 5 else 0.8

                job_count = int(np.random.normal(100, 20) * weekday_factor)
                total_runtime = int(job_count * np.random.normal(120, 30))
                cpu_usage = np.random.uniform(0.4, 0.8) * weekday_factor

                data.append({
                    "date": date.date(),
                    "workstation": ws,
                    "job_count": job_count,
                    "total_runtime": total_runtime,
                    "cpu_usage": min(cpu_usage, 1.0)
                })
        return pd.DataFrame(data)

# Global instance of the training service
model_trainer = ModelTrainingService()
