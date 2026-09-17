"""CSV / Excel adapters for user-supplied data (real or extended-demo). Expected schema:
a `date` column plus any subset of the series/operational column names produced by
data.synthetic.generator.SERIES_SPEC and SyntheticAdapter.load_operational().
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.schemas.governance import DataQualityStatus
from data.adapters.base import DataAdapter

OPERATIONAL_COLUMNS = ["demand_index", "utilisation_pct", "freight_usd_ton", "project_delay_days"]


class _FileAdapterBase(DataAdapter):
    data_quality = DataQualityStatus.REAL_UNVALIDATED

    def __init__(self, df: pd.DataFrame):
        if "date" not in df.columns:
            raise ValueError("Input file must contain a 'date' column")
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        self._df = df.set_index("date").sort_index()

    def load_prices(self) -> pd.DataFrame:
        cols = [c for c in self._df.columns if c not in OPERATIONAL_COLUMNS]
        return self._df[cols]

    def load_operational(self) -> pd.DataFrame:
        cols = [c for c in OPERATIONAL_COLUMNS if c in self._df.columns]
        return self._df[cols]


class CSVAdapter(_FileAdapterBase):
    def __init__(self, path: str | Path):
        super().__init__(pd.read_csv(path))


class ExcelAdapter(_FileAdapterBase):
    def __init__(self, path: str | Path, sheet_name: str | int = 0):
        super().__init__(pd.read_excel(path, sheet_name=sheet_name))
