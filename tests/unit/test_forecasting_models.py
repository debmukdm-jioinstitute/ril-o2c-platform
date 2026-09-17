import numpy as np
import pandas as pd
import pytest

from data.synthetic.generator import generate_market_dataset
from models.forecasting import (
    _LIGHTGBM_AVAILABLE,
    ARIMAForecaster,
    EnsembleForecaster,
    LightGBMForecaster,
    MovingAverageForecaster,
    NaiveForecaster,
    XGBoostForecaster,
)

HORIZON = 10

_GBM_CLASSES = [NaiveForecaster, MovingAverageForecaster, XGBoostForecaster]
if _LIGHTGBM_AVAILABLE:
    _GBM_CLASSES.append(LightGBMForecaster)


@pytest.fixture(scope="module")
def history() -> pd.Series:
    ds = generate_market_dataset(start="2022-01-01", end="2024-01-01", seed=42)
    return ds.prices["crude_brent_usd_bbl"]


@pytest.mark.parametrize("cls", _GBM_CLASSES)
def test_forecaster_shapes_and_interval_ordering(history, cls):
    model = cls(random_seed=42)
    result = model.fit_predict(history, HORIZON)
    assert len(result.point_forecast) == HORIZON
    assert len(result.dates) == HORIZON
    assert (result.lower_90 <= result.point_forecast + 1e-9).all()
    assert (result.upper_90 >= result.point_forecast - 1e-9).all()
    assert result.governance.model_name == model.name


def test_arima_forecaster(history):
    model = ARIMAForecaster(random_seed=42)
    result = model.fit_predict(history, HORIZON)
    assert len(result.point_forecast) == HORIZON
    assert (result.upper_90 >= result.lower_90).all()


def test_naive_reproducible(history):
    a = NaiveForecaster(random_seed=42).fit_predict(history, HORIZON)
    b = NaiveForecaster(random_seed=42).fit_predict(history, HORIZON)
    np.testing.assert_array_equal(a.point_forecast, b.point_forecast)


def test_ensemble_combines_members(history):
    members = [NaiveForecaster(random_seed=42), MovingAverageForecaster(random_seed=42)]
    ensemble = EnsembleForecaster(members=members, random_seed=42)
    result = ensemble.fit_predict(history, HORIZON)
    assert len(result.point_forecast) == HORIZON
    assert result.extra["member_names"] == ["naive_random_walk", "moving_average"]
    # Ensemble point should sit between the two members' points (equal weights, both flat lines).
    naive_pt = members[0].predict(HORIZON).point_forecast
    ma_pt = members[1].predict(HORIZON).point_forecast
    assert (result.point_forecast >= np.minimum(naive_pt, ma_pt) - 1e-6).all()
    assert (result.point_forecast <= np.maximum(naive_pt, ma_pt) + 1e-6).all()


def test_ensemble_requires_members():
    with pytest.raises(ValueError):
        EnsembleForecaster(members=[])
