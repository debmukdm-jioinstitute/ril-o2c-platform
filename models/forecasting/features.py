"""Shared lag/rolling feature engineering for the gradient-boosting forecasters. Kept in one
place so XGBoost and LightGBM see identical inputs — differences in their results reflect the
model, not feature drift between two copy-pasted implementations.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = (1, 2, 3, 5, 10, 20)
ROLL_WINDOWS = (5, 10, 20)


def build_features(series: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": series})
    for lag in LAGS:
        df[f"lag_{lag}"] = series.shift(lag)
    for w in ROLL_WINDOWS:
        df[f"roll_mean_{w}"] = series.shift(1).rolling(w).mean()
        df[f"roll_std_{w}"] = series.shift(1).rolling(w).std()
    df["day_of_week"] = series.index.dayofweek
    df["day_of_month"] = series.index.day
    return df


def build_feature_row(history_tail: pd.Series, next_date: pd.Timestamp) -> pd.DataFrame:
    """One feature row for recursive one-step-ahead prediction, given the trailing history
    (must contain at least max(LAGS, ROLL_WINDOWS) most recent observed/predicted values)."""
    row = {}
    for lag in LAGS:
        row[f"lag_{lag}"] = history_tail.iloc[-lag]
    for w in ROLL_WINDOWS:
        tail = history_tail.iloc[-w:]
        row[f"roll_mean_{w}"] = tail.mean()
        row[f"roll_std_{w}"] = tail.std()
    row["day_of_week"] = next_date.dayofweek
    row["day_of_month"] = next_date.day
    # Column order must match build_features()[FEATURE_COLUMNS] exactly — XGBoost/LightGBM
    # validate feature order against what they were trained on, not just feature names.
    return pd.DataFrame([row])[FEATURE_COLUMNS]


FEATURE_COLUMNS = (
    [f"lag_{l}" for l in LAGS]
    + [f"roll_mean_{w}" for w in ROLL_WINDOWS]
    + [f"roll_std_{w}" for w in ROLL_WINDOWS]
    + ["day_of_week", "day_of_month"]
)
