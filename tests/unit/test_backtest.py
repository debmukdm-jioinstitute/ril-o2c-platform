import pandas as pd
import pytest

from data.synthetic.generator import generate_market_dataset
from models.forecasting import NaiveForecaster
from models.forecasting.backtest import rolling_backtest, split_train_val_test


@pytest.fixture(scope="module")
def history() -> pd.Series:
    ds = generate_market_dataset(start="2020-01-01", end="2024-01-01", seed=42)
    return ds.prices["naphtha_usd_ton"]


def test_split_is_chronological(history):
    split = split_train_val_test(history, val_frac=0.15, test_frac=0.15)
    assert split.train.index.max() < split.val.index.min()
    assert split.val.index.max() < split.test.index.min()
    assert len(split.train) + len(split.val) + len(split.test) <= len(history)


def test_split_rejects_bad_fractions(history):
    with pytest.raises(ValueError):
        split_train_val_test(history, val_frac=0.6, test_frac=0.6)


def test_rolling_backtest_windows_are_chronological(history):
    report = rolling_backtest(
        history, lambda: NaiveForecaster(random_seed=42),
        min_train_size=500, horizon=10, step=60, max_windows=5,
    )
    assert report.model_name == "naive_random_walk"
    assert len(report.windows) <= 5
    for w in report.windows:
        assert w.train_end < w.test_start
        assert w.test_start <= w.test_end
    assert "mae" in report.aggregate_metrics


def test_rolling_backtest_rejects_too_short_series(history):
    with pytest.raises(ValueError):
        rolling_backtest(history.iloc[:20], lambda: NaiveForecaster(), min_train_size=500, horizon=10, step=10)
