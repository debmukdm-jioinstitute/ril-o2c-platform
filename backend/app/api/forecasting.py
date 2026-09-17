from __future__ import annotations

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
from models.forecasting import MODEL_REGISTRY
from models.forecasting.backtest import rolling_backtest

router = APIRouter(prefix="/api/forecasting", tags=["forecasting"])


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
