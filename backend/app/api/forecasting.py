from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import get_db
from app.schemas.forecasting import (
    AVAILABLE_MODELS,
    AVAILABLE_SERIES,
    BacktestRequest,
    BacktestResponse,
    BacktestWindowOut,
    ForecastRequest,
    ForecastResponse,
)
from app.services.audit import log_model_run
from app.services.market_data import data_quality_for, get_price_series
from app.services.response_cache import TTLCache
from models.forecasting import MODEL_REGISTRY
from models.forecasting.backtest import rolling_backtest

router = APIRouter(prefix="/api/forecasting", tags=["forecasting"])
logger = logging.getLogger(__name__)

# Forecasts are expensive (ARIMA's MLE order search in particular; see git history for
# measured cost on constrained hosting) and the underlying data doesn't change faster than
# once per business day (live) or at all (synthetic) — recomputing on every request for the
# same series/model/horizon is pure waste. 1 hour balances "fresh enough" against "fast enough".
_FORECAST_CACHE_TTL_SECONDS = 3600
_forecast_cache = TTLCache()

# The frontend's default dropdown state on page load — see frontend/app/page.tsx. Warmed at
# startup (see main.py's lifespan handler) so the first real visitor after a cold start
# (Render free tier sleeps the whole process after 15 min idle, so this recurs constantly for
# a low-traffic demo, not just on deploy) gets an instant cached response instead of paying
# the full compute cost themselves.
DEFAULT_WARMUP_COMBO = ("crude_brent_usd_bbl", "ensemble", 90)


@router.get("/series")
def list_series():
    return {"series": AVAILABLE_SERIES, "models": AVAILABLE_MODELS}


@router.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest, db: Session = Depends(get_db)):
    if req.model not in MODEL_REGISTRY:
        raise HTTPException(400, f"Unknown model '{req.model}'. Choose from {AVAILABLE_MODELS}.")
    settings = get_settings()
    try:
        history = get_price_series(req.series_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    def compute() -> ForecastResponse:
        model = MODEL_REGISTRY[req.model](settings.random_seed)
        result = model.fit_predict(history, req.horizon_days)
        result.governance.data_quality = data_quality_for(req.series_name)

        log_model_run(
            db, result.governance, module="forecasting",
            inputs=req.model_dump(),
            outputs_summary={"last_point": float(result.point_forecast[-1]), "n_points": len(result.point_forecast)},
        )

        return ForecastResponse(
            series_name=req.series_name, model=req.model,
            dates=[d.date() for d in result.dates],
            point_forecast=result.point_forecast.tolist(),
            lower_90=result.lower_90.tolist(),
            upper_90=result.upper_90.tolist(),
            governance=result.governance,
        )

    cache_key = (req.series_name, req.model, req.horizon_days, settings.random_seed)
    return _forecast_cache.get_or_compute(cache_key, _FORECAST_CACHE_TTL_SECONDS, compute)


@router.post("/backtest", response_model=BacktestResponse)
def backtest(req: BacktestRequest):
    if req.model not in MODEL_REGISTRY:
        raise HTTPException(400, f"Unknown model '{req.model}'. Choose from {AVAILABLE_MODELS}.")
    settings = get_settings()
    try:
        history = get_price_series(req.series_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    def factory():
        return MODEL_REGISTRY[req.model](settings.random_seed)

    try:
        report = rolling_backtest(
            history, factory, min_train_size=req.min_train_days,
            horizon=req.horizon_days, step=req.step_days, max_windows=req.max_windows,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return BacktestResponse(
        series_name=req.series_name, model=req.model,
        windows=[
            BacktestWindowOut(
                window_index=w.window_index, train_end=w.train_end.date(),
                test_start=w.test_start.date(), test_end=w.test_end.date(), metrics=w.metrics,
            ) for w in report.windows
        ],
        aggregate_metrics=report.aggregate_metrics,
    )


def warmup_default_forecast() -> None:
    """Populate the forecast cache for DEFAULT_WARMUP_COMBO. Called from main.py's startup
    task, outside any HTTP request — deliberately skips audit logging (no request-scoped DB
    session available here, and this isn't a user-initiated computation worth auditing).
    """
    series_name, model_name, horizon_days = DEFAULT_WARMUP_COMBO
    settings = get_settings()
    try:
        history = get_price_series(series_name)
        model = MODEL_REGISTRY[model_name](settings.random_seed)
        result = model.fit_predict(history, horizon_days)
        result.governance.data_quality = data_quality_for(series_name)
        response = ForecastResponse(
            series_name=series_name, model=model_name,
            dates=[d.date() for d in result.dates],
            point_forecast=result.point_forecast.tolist(),
            lower_90=result.lower_90.tolist(),
            upper_90=result.upper_90.tolist(),
            governance=result.governance,
        )
        cache_key = (series_name, model_name, horizon_days, settings.random_seed)
        _forecast_cache.get_or_compute(cache_key, _FORECAST_CACHE_TTL_SECONDS, lambda: response)
        logger.info("Warmed default forecast cache for %s", DEFAULT_WARMUP_COMBO)
    except Exception:
        logger.warning("Default forecast warmup failed (non-fatal)", exc_info=True)
