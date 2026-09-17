from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.simulation import MonteCarloRequest, MonteCarloResponse
from app.services.audit import log_model_run
from simulation.economics_mc import MC_SUPPORTED_FEEDSTOCKS
from simulation.monte_carlo import MonteCarloInputs, run_monte_carlo

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


def _case_snapshot(result, index: int) -> dict:
    return {key: float(arr[index]) for key, arr in result.raw.items()}


@router.get("/feedstocks")
def list_mc_feedstocks():
    return {"feedstocks": list(MC_SUPPORTED_FEEDSTOCKS)}


@router.post("/monte-carlo", response_model=MonteCarloResponse)
def monte_carlo(req: MonteCarloRequest, db: Session = Depends(get_db)):
    if req.feedstock not in MC_SUPPORTED_FEEDSTOCKS:
        raise HTTPException(400, f"Unknown feedstock '{req.feedstock}'. Choose from {MC_SUPPORTED_FEEDSTOCKS}.")

    inputs = MonteCarloInputs(
        feedstock=req.feedstock,
        throughput_tons_day=req.throughput_tons_day,
        byproduct_price_usd_ton=req.byproduct_price_usd_ton,
        conversion_cost_usd_ton_feedstock=req.conversion_cost_usd_ton_feedstock,
        conversion_cost_gas_linked_fraction=req.conversion_cost_gas_linked_fraction,
        logistics_cost_usd_ton_feedstock=req.logistics_cost_usd_ton_feedstock,
        operating_days=req.operating_days,
        capex_usd=req.capex_usd,
        project_life_years=req.project_life_years,
        wacc=req.wacc,
        horizon_years=req.horizon_years,
        n_scenarios=req.n_scenarios,
        seed=req.seed,
        ebitda_threshold_usd_year=req.ebitda_threshold_usd_year,
        ebitda_threshold_direction=req.ebitda_threshold_direction,
    )
    try:
        result = run_monte_carlo(inputs)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    log_model_run(
        db, result.governance, module="monte_carlo",
        inputs=req.model_dump(),
        outputs_summary={
            "ebitda_mean_usd_year": result.ebitda_usd_year.mean,
            "npv_mean": result.npv.mean,
            "probability_ebitda_breach": result.probability_ebitda_breach,
        },
    )

    return MonteCarloResponse(
        n_scenarios=result.n_scenarios,
        seed=result.seed,
        revenue=result.revenue.to_dict(),
        ebitda_usd_year=result.ebitda_usd_year.to_dict(),
        margin_pct=result.margin_pct.to_dict(),
        npv=result.npv.to_dict(),
        irr=result.irr.to_dict(),
        probability_ebitda_breach=result.probability_ebitda_breach,
        downside_case=_case_snapshot(result, result.downside_scenario_index),
        upside_case=_case_snapshot(result, result.upside_scenario_index),
        governance=result.governance,
    )
