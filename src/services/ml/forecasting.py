import pandas as pd
from prophet import Prophet
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict
import joblib

from src.services.ml.models import (
    WorkstationForecastResponse,
    WorkloadForecast,
    ForecastDatapoint,
)

# Define the path for saving/loading Prophet models
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "ml"
FORECAST_MODEL_DIR = MODEL_DIR / "forecasters"


class WorkloadForecaster:
    """
    A service to forecast future workload using Prophet.
    """

    def __init__(self):
        self.models: Dict[str, Prophet] = {}
        FORECAST_MODEL_DIR.mkdir(exist_ok=True)
        # We can lazy-load models on demand in the forecast method

    def train_workload_forecast(self, historical_data: pd.DataFrame):
        """
        Trains Prophet models for workload forecasting based on historical data.
        """
        logging.info("Starting workload forecasting model training...")
        if historical_data.empty:
            raise ValueError("Historical data cannot be empty for training.")

        historical_data["date"] = pd.to_datetime(historical_data["date"])

        for workstation in historical_data["workstation"].unique():
            ws_data = historical_data[
                historical_data["workstation"] == workstation
            ].copy()

            for metric in ["job_count", "total_runtime", "cpu_usage"]:
                if metric not in ws_data.columns:
                    continue

                model_data = ws_data[["date", metric]].rename(
                    columns={"date": "ds", metric: "y"}
                )

                model = Prophet(
                    yearly_seasonality=True,
                    weekly_seasonality=True,
                    daily_seasonality=True,
                    changepoint_prior_scale=0.05,
                )
                model.fit(model_data)

                model_key = f"{workstation}_{metric}"
                self.models[model_key] = model
                self._save_model(model, model_key)

        logging.info("Workload forecasting model training complete.")

    def forecast_workload(
        self, workstation: str, days_ahead: int = 7
    ) -> WorkstationForecastResponse:
        """
        Generates a workload forecast for a specific workstation.
        """
        logging.info(
            f"Generating workload forecast for workstation '{workstation}' for {days_ahead} days."
        )
        forecasts: Dict[str, WorkloadForecast] = {}

        for metric in ["job_count", "total_runtime", "cpu_usage"]:
            model_key = f"{workstation}_{metric}"

            if model_key not in self.models:
                self._load_model(model_key)

            if model_key in self.models:
                model = self.models[model_key]
                future = model.make_future_dataframe(periods=days_ahead)
                forecast_df = model.predict(future)

                future_forecast = forecast_df.tail(days_ahead)

                predictions = [
                    ForecastDatapoint(
                        ds=row.ds,
                        yhat=row.yhat,
                        yhat_lower=row.yhat_lower,
                        yhat_upper=row.yhat_upper,
                    )
                    for _, row in future_forecast.iterrows()
                ]

                forecasts[metric] = WorkloadForecast(
                    predictions=predictions,
                    trend="increasing"
                    if forecast_df["trend"].iloc[-1]
                    > forecast_df["trend"].iloc[-days_ahead - 1]
                    else "decreasing",
                    seasonality_strength=float(
                        forecast_df[["weekly", "yearly"]].abs().mean().mean()
                    ),
                )

        if not forecasts:
            raise ValueError(
                f"No models found for workstation '{workstation}'. Please train the models first."
            )

        return WorkstationForecastResponse(
            workstation=workstation,
            forecast_period=f"{days_ahead} days",
            generated_at=datetime.now(),
            forecasts=forecasts,
        )

    def _save_model(self, model: Prophet, model_key: str):
        """Saves a trained Prophet model to disk."""
        model_path = FORECAST_MODEL_DIR / f"{model_key}.joblib"
        logging.info(f"Saving forecast model to {model_path}")
        joblib.dump(model, model_path)

    def _load_model(self, model_key: str):
        """Loads a Prophet model from disk into memory."""
        model_path = FORECAST_MODEL_DIR / f"{model_key}.joblib"
        if model_path.exists():
            logging.info(f"Loading forecast model from {model_path}")
            self.models[model_key] = joblib.load(model_path)
        else:
            logging.warning(f"Forecast model file not found: {model_path}")


# Global instance of the forecaster
workload_forecaster = WorkloadForecaster()
