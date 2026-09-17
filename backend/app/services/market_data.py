"""Loads the active market dataset (synthetic by default) once per process and serves it to
forecasting/feedstock endpoints. Swapping `RIL_DATA_SOURCE_MODE` to csv/excel/api changes the
adapter without touching any downstream code (spec module 13).
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from app.core.config import get_settings
from data.adapters import get_adapter


@lru_cache
def _adapter():
    settings = get_settings()
    if settings.data_source_mode == "synthetic":
        return get_adapter("synthetic", seed=settings.random_seed)
    raise RuntimeError(
        f"data_source_mode='{settings.data_source_mode}' requires adapter-specific kwargs "
        "(a file path, or API credentials) — construct that adapter explicitly rather than "
        "via this cached singleton."
    )


def get_price_series(series_name: str) -> pd.Series:
    prices = _adapter().load_prices()
    if series_name not in prices.columns:
        raise ValueError(f"Unknown series '{series_name}'. Available: {list(prices.columns)}")
    return prices[series_name].rename(series_name)


def get_all_prices() -> pd.DataFrame:
    return _adapter().load_prices()


def get_operational_data() -> pd.DataFrame:
    return _adapter().load_operational()


def data_quality():
    return _adapter().data_quality
