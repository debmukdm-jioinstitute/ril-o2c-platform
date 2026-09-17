from __future__ import annotations

import numpy as np
import pandas as pd

from app.schemas.governance import DataQualityStatus
from models.forecasting.base import Forecaster, ForecastResult


class MovingAverageForecaster(Forecaster):
    name = "moving_average"

    def __init__(self, window: int = 20, random_seed: int = 42):
        super().__init__(random_seed)
        self.window = window

    def fit(self, history: pd.Series) -> "MovingAverageForecaster":
        self._history = history.dropna()
        rolling = self._history.rolling(self.window, min_periods=max(2, self.window // 2))
        fitted = rolling.mean()
        self._fitted_values = fitted.to_numpy()
        resid = (self._history - fitted).dropna()
        self._resid_std = float(resid.std()) if len(resid) > 1 else float(self._history.std())
        self._forecast_level = float(self._history.tail(self.window).mean())
        self._is_fitted = True
        return self

    def predict(self, horizon: int, data_quality: DataQualityStatus = DataQualityStatus.SYNTHETIC) -> ForecastResult:
        self._require_fitted()
        last_date = self._history.index[-1]
        future_dates = pd.bdate_range(start=last_date, periods=horizon + 1)[1:]

        point = np.full(horizon, self._forecast_level)
        steps = np.arange(1, horizon + 1)
        se = self._resid_std * np.sqrt(steps)
        z90 = 1.645
        lower = point - z90 * se
        upper = point + z90 * se

        governance = self._governance(
            self._history, horizon, data_quality,
            assumptions=[f"Forecast held flat at the trailing {self.window}-day mean.",
                         "Interval widens with sqrt(horizon), same as the random-walk baseline."],
        )
        return ForecastResult(
            series_name=str(self._history.name), dates=future_dates,
            point_forecast=point, lower_90=lower, upper_90=upper, governance=governance,
            fitted_values=self._fitted_values,
        )
