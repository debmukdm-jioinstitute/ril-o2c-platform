"""ORM tables. Two concerns live here: (1) market price history so forecasting/economics can
be re-run reproducibly against a fixed snapshot, and (2) an audit trail of every model run so
outputs are always traceable back to inputs, code version and timestamp (spec module 14).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MarketPriceObservation(Base):
    __tablename__ = "market_price_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_name: Mapped[str] = mapped_column(String(64), index=True)
    obs_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="synthetic")  # synthetic|csv|excel|api


class ModelRunLog(Base):
    """Audit trail: one row per model invocation (forecast, economics run, MC simulation, ...)."""
    __tablename__ = "model_run_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(16), default="1.0.0")
    module: Mapped[str] = mapped_column(String(32))  # forecasting|feedstock|monte_carlo|financial|...
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_quality: Mapped[str] = mapped_column(String(32), default="synthetic")
    inputs_json: Mapped[dict] = mapped_column(JSON, default=dict)
    outputs_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    forecast_points: Mapped[list["ForecastPoint"]] = relationship(back_populates="run")


class ForecastPoint(Base):
    __tablename__ = "forecast_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("model_run_log.id"), index=True)
    series_name: Mapped[str] = mapped_column(String(64), index=True)
    forecast_date: Mapped[date] = mapped_column(Date, index=True)
    point_forecast: Mapped[float] = mapped_column(Float)
    lower_90: Mapped[float] = mapped_column(Float)
    upper_90: Mapped[float] = mapped_column(Float)

    run: Mapped["ModelRunLog"] = relationship(back_populates="forecast_points")
