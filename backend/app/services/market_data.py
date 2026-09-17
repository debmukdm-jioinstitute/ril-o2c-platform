"""Loads the active market dataset (synthetic by default; live in production — see
RIL_DATA_SOURCE_MODE) once per process and serves it to forecasting/feedstock endpoints.
Swapping `RIL_DATA_SOURCE_MODE` changes the adapter without touching any downstream code
(spec module 13).
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from app.core.config import get_settings
from app.schemas.governance import DataQualityStatus
from data.adapters import get_adapter


@lru_cache
def _adapter():
    settings = get_settings()
    if settings.data_source_mode == "synthetic":
        return get_adapter("synthetic", seed=settings.random_seed)
    if settings.data_source_mode == "live":
        return get_adapter("live", seed=settings.random_seed, eia_api_key=settings.eia_api_key)
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


def data_quality() -> DataQualityStatus:
    """Adapter-wide fallback quality — prefer data_quality_for(series_name) wherever a
    specific series is known, since the live adapter mixes real and synthetic series."""
    return _adapter().data_quality


def data_quality_for(series_name: str) -> DataQualityStatus:
    return _adapter().data_quality_for(series_name)


def live_status() -> dict[str, bool] | None:
    """Per-live-series fetch health, when the active adapter tracks it (only LiveMarketAdapter
    does) — None otherwise. Surfaced on /api/health for operational transparency."""
    adapter = _adapter()
    status_fn = getattr(adapter, "live_status", None)
    return status_fn() if status_fn else None
