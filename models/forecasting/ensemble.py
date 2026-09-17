"""Ensemble forecaster: combines multiple base forecasters. Default is a simple mean, but
weights can be supplied (e.g. inverse-backtest-RMSE) — the ensemble never invents its own
point estimate, it only aggregates the members it's given.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.schemas.governance import DataQualityStatus
from models.forecasting.base import Forecaster, ForecastResult


class EnsembleForecaster(Forecaster):
    name = "ensemble"

    def __init__(self, members: list[Forecaster], weights: list[float] | None = None, random_seed: int = 42):
        super().__init__(random_seed)
        if not members:
            raise ValueError("Ensemble requires at least one member forecaster.")
        self.members = members
        self.weights = weights or [1.0 / len(members)] * len(members)
        if len(self.weights) != len(members):
            raise ValueError("weights must match number of members")
        w_sum = sum(self.weights)
        self.weights = [w / w_sum for w in self.weights]

    def fit(self, history: pd.Series) -> "EnsembleForecaster":
        self._history = history.dropna()
        for m in self.members:
            m.fit(self._history)
        self._is_fitted = True
        return self

    def predict(self, horizon: int, data_quality: DataQualityStatus = DataQualityStatus.SYNTHETIC) -> ForecastResult:
        self._require_fitted()
        member_results = [m.predict(horizon, data_quality) for m in self.members]

        points = np.array([r.point_forecast for r in member_results])
        lowers = np.array([r.lower_90 for r in member_results])
        uppers = np.array([r.upper_90 for r in member_results])
        w = np.array(self.weights).reshape(-1, 1)

        point = (points * w).sum(axis=0)
        # Combine intervals conservatively: widest lower/upper across weighted members plus
        # inter-model disagreement, so the ensemble doesn't understate uncertainty by averaging
        # away genuine model disagreement.
        weighted_lower = (lowers * w).sum(axis=0)
        weighted_upper = (uppers * w).sum(axis=0)
        disagreement = points.std(axis=0)
        lower = weighted_lower - disagreement
        upper = weighted_upper + disagreement

        governance = self._governance(
            self._history, horizon, data_quality,
            assumptions=[f"Weighted average of {[m.name for m in self.members]} "
                         f"with weights {[round(w, 3) for w in self.weights]}.",
                         "Interval = weighted member intervals widened by cross-model disagreement (std of point forecasts)."],
        )
        return ForecastResult(
            series_name=str(self._history.name), dates=member_results[0].dates,
            point_forecast=point, lower_90=lower, upper_90=upper, governance=governance,
            extra={"member_names": [m.name for m in self.members], "weights": self.weights},
        )
