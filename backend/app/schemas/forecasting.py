from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.governance import ModelGovernance
from data.synthetic.generator import SERIES_SPEC
from models.forecasting import MODEL_REGISTRY

AVAILABLE_SERIES = list(SERIES_SPEC.keys())
AVAILABLE_MODELS = list(MODEL_REGISTRY.keys())


class ForecastRequest(BaseModel):
    series_name: str = Field(..., description=f"One of {AVAILABLE_SERIES}")
    model: str = Field(default="ensemble", description=f"One of {AVAILABLE_MODELS}")
    horizon_days: int = Field(default=90, ge=1, le=365)


class ForecastResponse(BaseModel):
    series_name: str
    model: str
    dates: list[date]
    point_forecast: list[float]
    lower_90: list[float]
    upper_90: list[float]
    governance: ModelGovernance


class BacktestRequest(BaseModel):
    series_name: str
    model: str = "ensemble"
    horizon_days: int = Field(default=30, ge=1, le=180)
    min_train_days: int = Field(default=365, ge=60)
    step_days: int = Field(default=30, ge=1)
    max_windows: int | None = Field(default=12, ge=1)


class BacktestWindowOut(BaseModel):
    window_index: int
    train_end: date
    test_start: date
    test_end: date
    metrics: dict


class BacktestResponse(BaseModel):
    series_name: str
    model: str
    windows: list[BacktestWindowOut]
    aggregate_metrics: dict
