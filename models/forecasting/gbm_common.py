"""Shared recursive-forecast driver for gradient-boosting forecasters. Both XGBoost and
LightGBM subclasses implement `_fit_point`/`_fit_quantile`/`_predict_row`; this class handles
feature construction, recursive multi-step forecasting, and interval assembly identically
for both, so behavioral differences come only from the underlying booster.
"""
from __future__ import annotations

from abc import abstractmethod

import numpy as np
import pandas as pd

from app.schemas.governance import DataQualityStatus
from models.forecasting.base import Forecaster, ForecastResult
from models.forecasting.features import FEATURE_COLUMNS, build_feature_row, build_features


class _GBMForecasterBase(Forecaster):
    def fit(self, history: pd.Series) -> "_GBMForecasterBase":
        self._history = history.dropna()
        feat_df = build_features(self._history).dropna()
        X = feat_df[FEATURE_COLUMNS]
        y = feat_df["y"]
        self._model_point = self._fit_point(X, y)
        self._model_lo = self._fit_quantile(X, y, alpha=0.05)
        self._model_hi = self._fit_quantile(X, y, alpha=0.95)
        self._is_fitted = True
        return self

    @abstractmethod
    def _fit_point(self, X: pd.DataFrame, y: pd.Series):
        ...

    @abstractmethod
    def _fit_quantile(self, X: pd.DataFrame, y: pd.Series, alpha: float):
        ...

    @abstractmethod
    def _predict_row(self, model, row: pd.DataFrame) -> float:
        ...

    def predict(self, horizon: int, data_quality: DataQualityStatus = DataQualityStatus.SYNTHETIC) -> ForecastResult:
        self._require_fitted()
        last_date = self._history.index[-1]
        future_dates = pd.bdate_range(start=last_date, periods=horizon + 1)[1:]

        working = self._history.copy()
        point_preds, lo_preds, hi_preds = [], [], []
        for d in future_dates:
            row = build_feature_row(working, d)
            p = self._predict_row(self._model_point, row)
            lo = self._predict_row(self._model_lo, row)
            hi = self._predict_row(self._model_hi, row)
            # Quantile crossing can happen with independently-fit quantile models; enforce order.
            lo, hi = min(lo, hi, p), max(lo, hi, p)
            point_preds.append(p)
            lo_preds.append(lo)
            hi_preds.append(hi)
            working = pd.concat([working, pd.Series([p], index=[d])])

        governance = self._governance(
            self._history, horizon, data_quality,
            assumptions=["Recursive one-step-ahead forecasting: each step's prediction feeds "
                         "next step's lag features, so errors can compound over long horizons.",
                         "90% interval from independently-fit 5th/95th percentile quantile models."],
        )
        return ForecastResult(
            series_name=str(self._history.name), dates=future_dates,
            point_forecast=np.array(point_preds), lower_90=np.array(lo_preds),
            upper_90=np.array(hi_preds), governance=governance,
        )
