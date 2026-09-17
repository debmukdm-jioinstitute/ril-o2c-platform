import numpy as np

from data.synthetic.generator import SERIES_SPEC, generate_market_dataset


def test_deterministic_given_seed():
    a = generate_market_dataset(start="2022-01-01", end="2023-01-01", seed=7)
    b = generate_market_dataset(start="2022-01-01", end="2023-01-01", seed=7)
    assert a.prices.equals(b.prices)


def test_different_seed_differs():
    a = generate_market_dataset(start="2022-01-01", end="2023-01-01", seed=1)
    b = generate_market_dataset(start="2022-01-01", end="2023-01-01", seed=2)
    assert not a.prices.equals(b.prices)


def test_all_series_present_and_positive():
    ds = generate_market_dataset(start="2022-01-01", end="2023-01-01", seed=42)
    assert set(ds.prices.columns) == set(SERIES_SPEC.keys())
    assert (ds.prices > 0).all().all()
    assert not ds.prices.isna().any().any()


def test_operational_series_bounds():
    ds = generate_market_dataset(start="2022-01-01", end="2023-06-01", seed=42)
    assert (ds.utilisation_pct <= 100).all()
    assert (ds.utilisation_pct >= 60).all()
    assert (ds.project_delay_days >= 0).all()


def test_labeled_synthetic():
    ds = generate_market_dataset(seed=1)
    assert ds.is_synthetic is True
    assert ds.metadata["label"] == "Demo/Synthetic Data"
