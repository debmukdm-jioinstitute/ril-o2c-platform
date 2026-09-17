"""Model governance envelope. Every model-producing endpoint attaches one of these to its
output (spec module 15/16) — no result ships without provenance, and nothing here is ever
allowed to claim certainty it doesn't have.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class DataQualityStatus(str, Enum):
    SYNTHETIC = "synthetic"  # clearly-labeled demo/synthetic data
    REAL_UNVALIDATED = "real_unvalidated"
    REAL_VALIDATED = "real_validated"


class ModelGovernance(BaseModel):
    model_name: str
    model_version: str = "1.0.0"
    data_period_start: date | None = None
    data_period_end: date | None = None
    forecast_horizon_days: int | None = None
    confidence_level: float | None = Field(default=None, ge=0, le=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assumptions: list[str] = Field(default_factory=list)
    data_quality: DataQualityStatus = DataQualityStatus.SYNTHETIC
    random_seed: int | None = None

    def label(self) -> str:
        return "Demo/Synthetic Data" if self.data_quality == DataQualityStatus.SYNTHETIC else "Data"
