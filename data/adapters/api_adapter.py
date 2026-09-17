"""Placeholder for a live market-data API adapter. No API is wired up in this prototype —
wire a real provider's client in here and implement the two methods; the rest of the
platform only depends on the DataAdapter interface, so nothing else changes.
"""
from __future__ import annotations

import pandas as pd

from app.schemas.governance import DataQualityStatus
from data.adapters.base import DataAdapter


class APIAdapter(DataAdapter):
    data_quality = DataQualityStatus.REAL_UNVALIDATED

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    def load_prices(self) -> pd.DataFrame:
        raise NotImplementedError(
            "No market-data API is configured. Supply an implementation for your provider "
            "(e.g. Platts, ICIS, Bloomberg) or use SyntheticAdapter / CSVAdapter instead."
        )

    def load_operational(self) -> pd.DataFrame:
        raise NotImplementedError("See load_prices().")
