"""Naive (random-walk) baseline. Every other model must beat this to be worth using —
it's the floor, not a serious forecast, and is reported alongside every comparison.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.schemas.governance import DataQualityStatus
from models.forecasting.base import Forecaster, ForecastResult


class NaiveForecaster(Forecaster):
    name = "naive_random_walk"

    def fit(self, history: pd.Series) -> "NaiveForecaster":
        self._history = history.dropna()
        # Residual std of a random walk = std of first differences.
        self._resid_std = float(self._history.diff().dropna().std())
        self._last_value = float(self._history.iloc[-1])
        self._is_fitted = True
        return self

    def predict(self, horizon: int, data_quality: DataQualityStatus = DataQualityStatus.SYNTHETIC) -> ForecastResult:
        self._require_fitted()
        last_date = self._history.index[-1]
        future_dates = pd.bdate_range(start=last_date, periods=horizon + 1)[1:]

        point = np.full(horizon, self._last_value)
        # Random-walk variance grows linearly with the forecast step -> std grows with sqrt(h).
        steps = np.arange(1, horizon + 1)
        se = self._resid_std * np.sqrt(steps)
        z90 = 1.645
        lower = point - z90 * se
        upper = point + z90 * se

        governance = self._governance(
            self._history, horizon, data_quality,
            assumptions=["Random walk: tomorrow's price = today's price plus noise.",
                         "Interval widens with sqrt(horizon) per random-walk theory."],
        )
        return ForecastResult(
            series_name=str(self._history.name), dates=future_dates,
            point_forecast=point, lower_90=lower, upper_90=upper, governance=governance,
        )
