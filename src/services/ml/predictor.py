import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import logging
from pathlib import Path
from typing import List

from src.services.ml.models import (
    JobFailurePrediction,
    RiskFactor,
    TrainingMetrics,
)

# Define the path for saving/loading ML models
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "ml"
FAILURE_MODEL_PATH = MODEL_DIR / "failure_predictor.joblib"
ANOMALY_MODEL_PATH = MODEL_DIR / "anomaly_detector.joblib"
SCALER_PATH = MODEL_DIR / "feature_scaler.joblib"


class JobFailurePredictorML:
    """
    A machine learning service to predict job failures and detect anomalies.
    """

    def __init__(self):
        self.failure_model: RandomForestClassifier = None
        self.anomaly_detector: IsolationForest = None
        self.scaler: StandardScaler = StandardScaler()
        self.feature_columns = [
            "avg_runtime",
            "runtime_variance",
            "failure_rate_7d",
            "workstation_load",
            "time_of_day",
            "day_of_week",
            "consecutive_failures",
            "sla_breach_history",
        ]
        MODEL_DIR.mkdir(exist_ok=True)
        self._load_model()  # Load model on initialization

    def train_failure_prediction_model(
        self, historical_data: pd.DataFrame
    ) -> TrainingMetrics:
        """Trains the ML model to predict job failures based on historical data."""
        logging.info("Starting job failure prediction model training...")

        if historical_data.empty:
            raise ValueError("Historical data cannot be empty for training.")

        features_df = self._engineer_features(historical_data)

        X = features_df[self.feature_columns]
        y = features_df["failed"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.failure_model = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42, class_weight="balanced"
        )
        self.failure_model.fit(X_train_scaled, y_train)

        y_pred = self.failure_model.predict(X_test_scaled)
        report = classification_report(y_test, y_pred, output_dict=True)
        logging.info(
            f"Model performance report:\n{classification_report(y_test, y_pred)}"
        )

        self._save_model()
        logging.info("Job failure prediction model training complete and saved.")

        return TrainingMetrics(
            accuracy=report["accuracy"],
            feature_importance=dict(
                zip(self.feature_columns, self.failure_model.feature_importances_)
            ),
        )

    def predict_job_failure(self, job_data: dict) -> JobFailurePrediction:
        """Predicts the probability of failure for a single job."""
        if not self.failure_model:
            raise RuntimeError(
                "Failure prediction model is not loaded. Please train the model first."
            )

        features = self._extract_job_features(job_data)
        features_scaled = self.scaler.transform([features])

        failure_prob = self.failure_model.predict_proba(features_scaled)[0][1]
        prediction = self.failure_model.predict(features_scaled)[0]

        feature_importance = dict(
            zip(self.feature_columns, self.failure_model.feature_importances_)
        )

        return JobFailurePrediction(
            job_name=job_data.get("jobStreamName"),
            failure_probability=failure_prob,
            prediction="LIKELY_TO_FAIL" if prediction == 1 else "LIKELY_TO_SUCCEED",
            confidence=max(failure_prob, 1 - failure_prob),
            risk_factors=self._identify_risk_factors(features, feature_importance),
            recommendation=self._get_recommendation(failure_prob),
        )

    def _engineer_features(self, historical_data: pd.DataFrame) -> pd.DataFrame:
        """Engineers features from raw historical data for model training."""
        logging.info("Engineering features from historical data...")
        df = historical_data.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["time_of_day"] = df["hour"] / 24.0

        df["avg_runtime"] = df.get("avg_runtime", np.random.uniform(100, 500))
        df["runtime_variance"] = df.get("runtime_variance", np.random.uniform(10, 50))
        df["failure_rate_7d"] = df.get("failure_rate_7d", np.random.uniform(0, 0.2))
        df["workstation_load"] = df.get("workstation_load", np.random.rand())
        df["consecutive_failures"] = df.get("consecutive_failures", 0)
        df["sla_breach_history"] = df.get("sla_breach_history", 0)
        df["failed"] = df.get("failed", np.random.randint(0, 2))

        return df

    def _extract_job_features(self, job_data: dict) -> list:
        """Extracts real-time features for a single job for prediction."""
        return [
            job_data.get("avg_runtime", 300),
            job_data.get("runtime_variance", 50),
            job_data.get("failure_rate_7d", 0.1),
            job_data.get("workstation_load", 0.7),
            datetime.now().hour / 24.0,
            datetime.now().weekday(),
            job_data.get("consecutive_failures", 0),
            job_data.get("sla_breach_history", 0),
        ]

    def _identify_risk_factors(
        self, features: list, importance: dict
    ) -> List[RiskFactor]:
        """Identifies the main risk factors for a prediction based on feature importance."""
        risk_factors = []
        for i, (feature_name, feature_value) in enumerate(
            zip(self.feature_columns, features)
        ):
            if importance.get(feature_name, 0) > 0.05:
                risk_factors.append(
                    RiskFactor(
                        factor=feature_name,
                        value=feature_value,
                        importance=importance[feature_name],
                        description=f"Value of {feature_name} is {feature_value:.2f}",
                    )
                )
        return sorted(risk_factors, key=lambda x: x.importance, reverse=True)

    def _get_recommendation(self, failure_prob: float) -> str:
        """Generates a recommendation based on the failure probability."""
        if failure_prob > 0.75:
            return "CRITICAL: High probability of failure. Immediate investigation recommended."
        elif failure_prob > 0.5:
            return "HIGH RISK: Monitor job closely upon execution."
        else:
            return "LOW RISK: Job is expected to succeed."

    def _save_model(self):
        """Saves the trained models and scaler to disk."""
        logging.info(f"Saving models to {MODEL_DIR}...")
        joblib.dump(self.failure_model, FAILURE_MODEL_PATH)
        joblib.dump(self.scaler, SCALER_PATH)

    def _load_model(self):
        """Loads models and scaler from disk."""
        try:
            if FAILURE_MODEL_PATH.exists() and SCALER_PATH.exists():
                logging.info(f"Loading models from {MODEL_DIR}...")
                self.failure_model = joblib.load(FAILURE_MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
            else:
                logging.warning("Model files not found. Model not loaded.")
        except Exception as e:
            logging.error(f"Error loading model: {e}", exc_info=True)


# Global instance of the predictor
job_predictor = JobFailurePredictorML()
