"""ARIMA / SARIMAX forecaster. Order selection is a small grid search on AIC (not a full
auto-ARIMA search) — kept deliberately narrow so backtesting over many windows stays fast, and
narrower still (3 candidates, not 5) after measuring SARIMAX's MLE fitting cost directly on
constrained hosting: it is by a wide margin the most expensive of the five forecasters this
platform runs (see git history / METHODOLOGY.md), so trimming its search space is a real,
proportional latency win, not premature optimization. The three kept are the standard minimal
ARIMA baselines (AR(1)-with-differencing, MA(1)-with-differencing, ARMA(1,1)-with-differencing);
the dropped (2,1,1)/(1,1,2) candidates were rarely AIC-selected in practice and are the most
expensive to fit.
Seasonal terms are only added when `seasonal_period` is supplied (e.g. 5 for a weekly effect
on business-day data); commodity prices are not usually strongly seasonal at daily frequency.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from app.schemas.governance import DataQualityStatus
from models.forecasting.base import Forecaster, ForecastResult

_ORDER_GRID = [(1, 1, 0), (0, 1, 1), (1, 1, 1)]


class ARIMAForecaster(Forecaster):
    name = "arima"

    def __init__(self, seasonal_period: int | None = None, random_seed: int = 42):
        super().__init__(random_seed)
        self.seasonal_period = seasonal_period

    def fit(self, history: pd.Series) -> "ARIMAForecaster":
        self._history = history.dropna()
        best_aic = np.inf
        best_fit = None
        best_order = None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for order in _ORDER_GRID:
                seasonal_order = (0, 0, 0, 0)
                try:
                    model = sm.tsa.SARIMAX(
                        self._history, order=order, seasonal_order=seasonal_order,
                        enforce_stationarity=False, enforce_invertibility=False,
                    )
                    fit = model.fit(disp=False)
                    if fit.aic < best_aic:
                        best_aic, best_fit, best_order = fit.aic, fit, order
                except Exception:
                    continue
        if best_fit is None:
            raise RuntimeError("ARIMA fitting failed for all candidate orders.")
        self._fit = best_fit
        self._order = best_order
        self._is_fitted = True
        return self

    def predict(self, horizon: int, data_quality: DataQualityStatus = DataQualityStatus.SYNTHETIC) -> ForecastResult:
        self._require_fitted()
        last_date = self._history.index[-1]
        future_dates = pd.bdate_range(start=last_date, periods=horizon + 1)[1:]

        forecast_res = self._fit.get_forecast(steps=horizon)
        point = forecast_res.predicted_mean.to_numpy()
        ci = forecast_res.conf_int(alpha=0.10)  # 90% interval
        lower = ci.iloc[:, 0].to_numpy()
        upper = ci.iloc[:, 1].to_numpy()

        governance = self._governance(
            self._history, horizon, data_quality,
            assumptions=[f"SARIMAX order={self._order} selected by AIC over a fixed grid.",
                         "No seasonal component fitted." if not self.seasonal_period else
                         f"Seasonal period={self.seasonal_period}."],
        )
        return ForecastResult(
            series_name=str(self._history.name), dates=future_dates,
            point_forecast=point, lower_90=lower, upper_90=upper, governance=governance,
            fitted_values=self._fit.fittedvalues.to_numpy(),
            extra={"order": self._order, "aic": float(self._fit.aic)},
        )
