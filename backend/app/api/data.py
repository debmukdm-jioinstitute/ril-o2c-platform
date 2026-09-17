from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.market_data import data_quality, data_quality_for, get_all_prices, get_operational_data, live_status

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/prices")
def prices(series: list[str] | None = Query(default=None), tail_days: int = Query(default=500, ge=1, le=5000)):
    df = get_all_prices()
    if series:
        missing = [s for s in series if s not in df.columns]
        if missing:
            raise HTTPException(400, f"Unknown series: {missing}. Available: {list(df.columns)}")
        df = df[series]
    df = df.tail(tail_days)
    return {
        "data_quality": data_quality().value,  # deprecated: blanket fallback, see data_quality_by_series
        "data_quality_by_series": {col: data_quality_for(col).value for col in df.columns},
        "live_status": live_status(),
        "dates": [d.date().isoformat() for d in df.index],
        "series": {col: df[col].round(4).tolist() for col in df.columns},
    }


@router.get("/operational")
def operational(tail_days: int = Query(default=500, ge=1, le=5000)):
    df = get_operational_data().tail(tail_days)
    return {
        "data_quality": data_quality().value,
        "dates": [d.date().isoformat() for d in df.index],
        "series": {col: df[col].round(4).tolist() for col in df.columns},
    }
