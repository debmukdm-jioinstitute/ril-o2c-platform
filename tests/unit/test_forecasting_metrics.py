import numpy as np
import pytest

from models.forecasting.metrics import (
    compute_all,
    directional_accuracy,
    mae,
    mape,
    prediction_interval_coverage,
    rmse,
)


def test_mae_rmse_exact():
    actual = np.array([10.0, 20.0, 30.0])
    predicted = np.array([12.0, 18.0, 33.0])
    assert mae(actual, predicted) == pytest.approx(7 / 3)
    assert rmse(actual, predicted) == pytest.approx(np.sqrt((4 + 4 + 9) / 3))


def test_mape_none_when_zero_actual():
    actual = np.array([0.0, 1.0])
    predicted = np.array([1.0, 1.0])
    assert mape(actual, predicted) is None


def test_mape_normal_case():
    actual = np.array([100.0, 200.0])
    predicted = np.array([110.0, 190.0])
    # |100-110|/100=10%, |200-190|/200=5% -> mean 7.5%
    assert mape(actual, predicted) == pytest.approx(7.5)


def test_directional_accuracy_perfect():
    actual = np.array([1.0, 2.0, 1.5, 3.0])
    predicted = np.array([1.0, 2.5, 1.2, 4.0])  # same up/down/up pattern
    assert directional_accuracy(actual, predicted) == 100.0


def test_directional_accuracy_needs_two_points():
    assert directional_accuracy(np.array([1.0]), np.array([1.0])) is None


def test_prediction_interval_coverage():
    actual = np.array([1.0, 2.0, 3.0, 4.0])
    lower = np.array([0.0, 0.0, 0.0, 10.0])
    upper = np.array([5.0, 5.0, 5.0, 20.0])
    assert prediction_interval_coverage(actual, lower, upper) == 75.0


def test_compute_all_keys():
    actual = np.array([1.0, 2.0, 3.0])
    predicted = np.array([1.1, 1.9, 3.2])
    lower = actual - 1
    upper = actual + 1
    result = compute_all(actual, predicted, lower, upper)
    assert set(result.keys()) >= {
        "mae", "rmse", "mape", "directional_accuracy_pct", "n_obs", "prediction_interval_coverage_pct"
    }
