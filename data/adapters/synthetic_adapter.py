from __future__ import annotations

import pandas as pd

from app.schemas.governance import DataQualityStatus
from data.adapters.base import DataAdapter
from data.synthetic.generator import generate_market_dataset


class SyntheticAdapter(DataAdapter):
    data_quality = DataQualityStatus.SYNTHETIC

    def __init__(self, start: str = "2019-01-01", end: str = "2026-09-17", seed: int = 42):
        self._dataset = generate_market_dataset(start=start, end=end, seed=seed)

    def load_prices(self) -> pd.DataFrame:
        return self._dataset.prices.copy()

    def load_operational(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "demand_index": self._dataset.demand_index,
                "utilisation_pct": self._dataset.utilisation_pct,
                "freight_usd_ton": self._dataset.freight_usd_ton,
                "project_delay_days": self._dataset.project_delay_days,
            }
        )
