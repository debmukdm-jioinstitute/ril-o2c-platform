"""Warm up the heavier forecasters (ARIMA/XGBoost/LightGBM) once at process startup.

Measured directly against the deployed backend: the first fit of each of these libraries in a
freshly started process is dramatically slower than every subsequent fit (tens of seconds vs.
single-digit seconds) — consistent with one-time C-extension / thread-pool initialization
overhead (statsmodels' Cython/LAPACK bindings, XGBoost's and LightGBM's native thread pools),
not the actual model-fitting cost, which is what get measured on every call after the first.

Paying that cost at startup (in the background, while the server is already accepting other
requests) means the first real user forecast request doesn't have to pay it — see main.py's
lifespan handler for how this is invoked.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _dummy_series(n: int = 250) -> pd.Series:
    idx = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
    rng = np.random.default_rng(0)
    values = 100 + np.cumsum(rng.normal(0, 1, size=n))
    return pd.Series(values, index=idx, name="warmup")


def warmup_models() -> None:
    history = _dummy_series()

    from models.forecasting.arima_model import ARIMAForecaster
    from models.forecasting.xgboost_model import XGBoostForecaster

    for name, cls in [("arima", ARIMAForecaster), ("xgboost", XGBoostForecaster)]:
        try:
            cls(random_seed=0).fit_predict(history, horizon=5)
            logger.info("Warmed up %s forecaster", name)
        except Exception:
            logger.warning("Warmup failed for %s (non-fatal, first real request will be slower)", name, exc_info=True)

    try:
        from models.forecasting import _LIGHTGBM_AVAILABLE
        if _LIGHTGBM_AVAILABLE:
            from models.forecasting.lightgbm_model import LightGBMForecaster
            LightGBMForecaster(random_seed=0).fit_predict(history, horizon=5)
            logger.info("Warmed up lightgbm forecaster")
    except Exception:
        logger.warning("Warmup failed for lightgbm (non-fatal, first real request will be slower)", exc_info=True)
