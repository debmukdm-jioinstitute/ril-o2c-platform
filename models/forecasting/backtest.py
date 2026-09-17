"""Rolling-window backtesting and train/val/test splitting for forecasters.

Time series data must never be split randomly — splits and backtest windows here are strictly
chronological, so a model is always evaluated on data it could not have seen during training.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from models.forecasting.base import Forecaster
from models.forecasting.metrics import compute_all


@dataclass
class TrainValTestSplit:
    train: pd.Series
    val: pd.Series
    test: pd.Series


def split_train_val_test(series: pd.Series, val_frac: float = 0.15, test_frac: float = 0.15) -> TrainValTestSplit:
    if not 0 < val_frac + test_frac < 1:
        raise ValueError("val_frac + test_frac must be in (0, 1)")
    series = series.dropna().sort_index()
    n = len(series)
    n_test = int(n * test_frac)
    n_val = int(n * val_frac)
    n_train = n - n_val - n_test
    if n_train < 30:
        raise ValueError("Training window too short after split (<30 obs). Use more history or smaller val/test fractions.")
    return TrainValTestSplit(
        train=series.iloc[:n_train],
        val=series.iloc[n_train:n_train + n_val],
        test=series.iloc[n_train + n_val:],
    )


@dataclass
class BacktestWindowResult:
    window_index: int
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    metrics: dict


@dataclass
class BacktestReport:
    model_name: str
    windows: list[BacktestWindowResult]
    aggregate_metrics: dict

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for w in self.windows:
            row = {"window": w.window_index, "train_end": w.train_end,
                   "test_start": w.test_start, "test_end": w.test_end}
            row.update(w.metrics)
            rows.append(row)
        return pd.DataFrame(rows)


def rolling_backtest(
    series: pd.Series,
    model_factory: Callable[[], Forecaster],
    min_train_size: int,
    horizon: int,
    step: int,
    max_windows: int | None = None,
) -> BacktestReport:
    """Walk-forward validation: for each window, fit on all data up to `train_end`, forecast
    `horizon` steps ahead, score against the actuals that follow, then slide forward by `step`.
    """
    series = series.dropna().sort_index()
    n = len(series)
    if min_train_size + horizon > n:
        raise ValueError("min_train_size + horizon exceeds available series length.")

    starts = list(range(min_train_size, n - horizon + 1, step))
    if max_windows is not None:
        starts = starts[-max_windows:]

    window_results: list[BacktestWindowResult] = []
    all_actuals, all_preds, all_lo, all_hi = [], [], [], []

    for i, train_end_idx in enumerate(starts):
        train = series.iloc[:train_end_idx]
        test = series.iloc[train_end_idx:train_end_idx + horizon]
        model = model_factory()
        try:
            result = model.fit_predict(train, horizon)
        except Exception as exc:
            window_results.append(BacktestWindowResult(
                window_index=i, train_end=train.index[-1],
                test_start=test.index[0], test_end=test.index[-1],
                metrics={"error": str(exc)},
            ))
            continue

        actual = test.to_numpy()
        pred = result.point_forecast[: len(actual)]
        lo = result.lower_90[: len(actual)]
        hi = result.upper_90[: len(actual)]

        metrics = compute_all(actual, pred, lo, hi)
        window_results.append(BacktestWindowResult(
            window_index=i, train_end=train.index[-1],
            test_start=test.index[0], test_end=test.index[-1], metrics=metrics,
        ))
        all_actuals.append(actual)
        all_preds.append(pred)
        all_lo.append(lo)
        all_hi.append(hi)

    if all_actuals:
        aggregate = compute_all(
            np.concatenate(all_actuals), np.concatenate(all_preds),
            np.concatenate(all_lo), np.concatenate(all_hi),
        )
    else:
        aggregate = {"error": "All backtest windows failed."}

    model_name = model_factory().name
    return BacktestReport(model_name=model_name, windows=window_results, aggregate_metrics=aggregate)
