"""Forecast accuracy metrics. Pure functions, no side effects — used identically by
backtesting and by live predicted-vs-realized monitoring (spec module 7).
"""
from __future__ import annotations

import numpy as np


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def mape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    """None when actual contains zeros (MAPE undefined) rather than silently returning inf."""
    if np.any(actual == 0):
        return None
    return float(np.mean(np.abs((actual - predicted) / actual)) * 100)


def directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    """Share of periods where the forecast got the sign of the change right.
    Needs >= 2 points; returns None otherwise.
    """
    if len(actual) < 2:
        return None
    actual_dir = np.sign(np.diff(actual))
    pred_dir = np.sign(np.diff(predicted))
    mask = actual_dir != 0
    if mask.sum() == 0:
        return None
    return float(np.mean(actual_dir[mask] == pred_dir[mask]) * 100)


def prediction_interval_coverage(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    """Empirical coverage: fraction of actuals that fell inside the stated interval.
    Used to check forecast calibration — a nominal 90% interval should cover ~90% of actuals.
    """
    within = (actual >= lower) & (actual <= upper)
    return float(np.mean(within) * 100)


def compute_all(actual: np.ndarray, predicted: np.ndarray, lower: np.ndarray | None = None,
                 upper: np.ndarray | None = None) -> dict:
    result = {
        "mae": mae(actual, predicted),
        "rmse": rmse(actual, predicted),
        "mape": mape(actual, predicted),
        "directional_accuracy_pct": directional_accuracy(actual, predicted),
        "n_obs": int(len(actual)),
    }
    if lower is not None and upper is not None:
        result["prediction_interval_coverage_pct"] = prediction_interval_coverage(actual, lower, upper)
    return result
