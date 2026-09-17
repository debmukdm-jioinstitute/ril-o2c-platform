"""Forecaster interface and result container.

Every forecasting model in this package implements `Forecaster`. Nothing outside this
package is allowed to claim a forecast is certain — `ForecastResult` always carries a
prediction interval and a governance envelope (spec modules 1, 15, 16).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.schemas.governance import ModelGovernance


@dataclass
class ForecastResult:
    series_name: str
    dates: pd.DatetimeIndex
    point_forecast: np.ndarray
    lower_90: np.ndarray
    upper_90: np.ndarray
    governance: ModelGovernance
    fitted_values: np.ndarray | None = None  # in-sample fit, for diagnostics
    extra: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": self.dates,
                "forecast": self.point_forecast,
                "lower_90": self.lower_90,
                "upper_90": self.upper_90,
            }
        ).set_index("date")


class Forecaster(ABC):
    """Base class for all point/interval forecasters (naive, MA, ARIMA, ML, ensemble)."""

    name: str = "base"

    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        self._is_fitted = False

    @abstractmethod
    def fit(self, history: pd.Series) -> "Forecaster":
        ...

    @abstractmethod
    def predict(self, horizon: int) -> ForecastResult:
        ...

    def fit_predict(self, history: pd.Series, horizon: int) -> ForecastResult:
        self.fit(history)
        return self.predict(horizon)

    def _require_fitted(self) -> None:
        if not self._is_fitted:
            raise RuntimeError(f"{self.name} forecaster must be fit() before predict().")

    def _governance(self, history: pd.Series, horizon: int, data_quality, assumptions: list[str],
                     confidence_level: float = 0.90) -> ModelGovernance:
        return ModelGovernance(
            model_name=self.name,
            data_period_start=history.index.min().date(),
            data_period_end=history.index.max().date(),
            forecast_horizon_days=horizon,
            confidence_level=confidence_level,
            assumptions=assumptions,
            data_quality=data_quality,
            random_seed=self.random_seed,
        )
