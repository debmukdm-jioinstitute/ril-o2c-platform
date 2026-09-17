from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException

from app.schemas.feedstock import (
    AVAILABLE_FEEDSTOCKS,
    CompareRequest,
    EconomicsRequest,
    EconomicsResponse,
    SwitchPointRequest,
)
from models.feedstock import CrackerEconomicsInputs, compare_feedstocks, compute_cracker_economics
from models.feedstock.switch_point import sensitivity_grid_2d

router = APIRouter(prefix="/api/feedstock", tags=["feedstock"])


def _to_inputs(req: EconomicsRequest) -> CrackerEconomicsInputs:
    if req.feedstock not in AVAILABLE_FEEDSTOCKS:
        raise HTTPException(400, f"Unknown feedstock '{req.feedstock}'. Choose from {AVAILABLE_FEEDSTOCKS}.")
    return CrackerEconomicsInputs(**req.model_dump())


@router.get("/profiles")
def list_feedstocks():
    return {"feedstocks": AVAILABLE_FEEDSTOCKS}


@router.post("/economics", response_model=EconomicsResponse)
def economics(req: EconomicsRequest):
    result = compute_cracker_economics(_to_inputs(req))
    return EconomicsResponse(
        feedstock=result.feedstock,
        ethylene_tons_day=result.ethylene_tons_day,
        propylene_tons_day=result.propylene_tons_day,
        byproduct_tons_day=result.byproduct_tons_day,
        feedstock_cost_usd_day=result.feedstock_cost_usd_day,
        conversion_cost_usd_day=result.conversion_cost_usd_day,
        logistics_cost_usd_day=result.logistics_cost_usd_day,
        revenue_usd_day=result.revenue_usd_day,
        contribution_margin_usd_day=result.contribution_margin_usd_day,
        contribution_margin_usd_ton_ethylene=result.contribution_margin_usd_ton_ethylene,
        ebitda_usd_day=result.ebitda_usd_day,
        ebitda_usd_year=result.ebitda_usd_year,
        ebitda_inr_cr_year=result.ebitda_inr_cr_year,
        margin_pct_of_revenue=result.margin_pct_of_revenue,
    )


@router.post("/compare")
def compare(req: CompareRequest):
    scenarios = {label: _to_inputs(r) for label, r in req.scenarios.items()}
    df = compare_feedstocks(scenarios)
    return {"comparison": df.to_dict(orient="records")}


@router.post("/switch-point")
def switch_point(req: SwitchPointRequest):
    inputs_a = _to_inputs(req.scenario_a)
    inputs_b = _to_inputs(req.scenario_b)
    price_range_a = np.linspace(req.price_min_a, req.price_max_a, req.grid_points)
    price_range_b = np.linspace(req.price_min_b, req.price_max_b, req.grid_points)
    grid = sensitivity_grid_2d(inputs_a, inputs_b, price_range_a, price_range_b)
    return {
        "feedstock_a": inputs_a.feedstock,
        "feedstock_b": inputs_b.feedstock,
        "grid": grid.to_dict(orient="records"),
    }
