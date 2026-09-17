"""Adapter interface. Every data source (CSV, Excel, API, synthetic) implements this so the
rest of the platform never cares where prices came from — only DataAdapter.load_prices().
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from app.schemas.governance import DataQualityStatus


class DataAdapter(ABC):
    data_quality: DataQualityStatus

    @abstractmethod
    def load_prices(self) -> pd.DataFrame:
        """Return a date-indexed DataFrame, one column per series (see SERIES_SPEC names)."""

    @abstractmethod
    def load_operational(self) -> pd.DataFrame:
        """Return date-indexed operational series: demand_index, utilisation_pct,
        freight_usd_ton, project_delay_days."""

    def source_label(self) -> str:
        return self.data_quality.value

    def data_quality_for(self, series_name: str) -> DataQualityStatus:
        """Per-series data quality. Defaults to the adapter-wide value; adapters that mix
        real and synthetic series in one dataset (see LiveMarketAdapter) override this so a
        forecast on a genuinely live series isn't mislabeled synthetic, and vice versa.
        """
        return self.data_quality
