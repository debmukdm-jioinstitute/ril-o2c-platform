from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.financial import (
    AVAILABLE_FEEDSTOCKS,
    CapexProjectRequest,
    CapexProjectResponse,
    MonthlyScheduleRowOut,
    ScenarioComparisonResponse,
    ScenarioSummaryOut,
)
from app.schemas.governance import DataQualityStatus, ModelGovernance
from app.services.audit import log_model_run
from financial.capex_schedule import CapexStatus
from financial.project_model import CapexProjectInputs, OperatingAssumptions, run_capex_project
from financial.ramp_up import default_ramp_curve
from financial.scenarios import run_standard_scenarios

router = APIRouter(prefix="/api/financial", tags=["financial"])

_ASSUMPTIONS = [
    "Pre-tax, unlevered free cash flow — no depreciation, tax shield, or debt schedule modeled.",
    "Already-spent capex is treated as sunk and excluded from NPV; only remaining capex "
    "(plus acceleration cost, if any) is discounted forward from the valuation date.",
    "Construction-period capex is spread evenly across the months to commissioning; ramp-up "
    "utilization follows the supplied (or default linear) ramp curve.",
]


def _build_inputs(req: CapexProjectRequest) -> CapexProjectInputs:
    if req.operating.feedstock not in AVAILABLE_FEEDSTOCKS:
        raise HTTPException(400, f"Unknown feedstock '{req.operating.feedstock}'. Choose from {AVAILABLE_FEEDSTOCKS}.")
    capex = CapexStatus(
        total_capex_usd=req.capex.total_capex_usd,
        committed_capex_usd=req.capex.committed_capex_usd,
        spent_capex_usd=req.capex.spent_capex_usd,
        construction_progress_pct=req.capex.construction_progress_pct,
    )
    operating = OperatingAssumptions(
        feedstock=req.operating.feedstock,
        nameplate_throughput_tons_day=req.operating.nameplate_throughput_tons_day,
        feedstock_price=req.operating.feedstock_price,
        ethylene_price_usd_ton=req.operating.ethylene_price_usd_ton,
        propylene_price_usd_ton=req.operating.propylene_price_usd_ton,
        byproduct_price_usd_ton=req.operating.byproduct_price_usd_ton,
        conversion_cost_usd_ton_feedstock=req.operating.conversion_cost_usd_ton_feedstock,
        logistics_cost_usd_ton_feedstock=req.operating.logistics_cost_usd_ton_feedstock,
        fx_usdinr=req.operating.fx_usdinr,
    )
    ramp_curve = default_ramp_curve(req.ramp_up_months, req.ramp_start_utilisation_pct, 100.0)
    return CapexProjectInputs(
        capex=capex, operating=operating, wacc=req.wacc,
        valuation_date=req.valuation_date, planned_commissioning_date=req.planned_commissioning_date,
        ramp_curve=ramp_curve, post_ramp_operating_life_years=req.post_ramp_operating_life_years,
        delay_days=req.delay_days, acceleration_days=req.acceleration_days,
        acceleration_cost_usd=req.acceleration_cost_usd,
    )


def _governance(req: CapexProjectRequest, model_name: str) -> ModelGovernance:
    return ModelGovernance(
        model_name=model_name,
        data_period_start=req.valuation_date,
        data_period_end=req.valuation_date,
        forecast_horizon_days=int(req.post_ramp_operating_life_years * 365),
        confidence_level=None,
        generated_at=datetime.now(timezone.utc),
        assumptions=_ASSUMPTIONS,
        data_quality=DataQualityStatus.SYNTHETIC,
        random_seed=None,
    )


@router.get("/feedstocks")
def list_financial_feedstocks():
    return {"feedstocks": AVAILABLE_FEEDSTOCKS}


@router.post("/project", response_model=CapexProjectResponse)
def project(req: CapexProjectRequest, db: Session = Depends(get_db)):
    inputs = _build_inputs(req)
    try:
        result = run_capex_project(inputs)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    governance = _governance(req, "capacity_expansion_financial_model")
    log_model_run(
        db, governance, module="financial",
        inputs=req.model_dump(mode="json"),
        outputs_summary={"npv_usd": result.npv_usd, "irr_annual": result.irr_annual, "payback_months": result.payback_months},
    )

    return CapexProjectResponse(
        npv_usd=result.npv_usd, irr_annual=result.irr_annual, payback_months=result.payback_months,
        total_capex_deployed_usd=result.total_capex_deployed_usd,
        steady_state_annual_ebitda_usd=result.steady_state_annual_ebitda_usd,
        commissioning_date=result.commissioning_date, months_to_commission=result.months_to_commission,
        schedule=[
            MonthlyScheduleRowOut(
                month_index=r.month_index, calendar_date=r.calendar_date, phase=r.phase,
                utilisation_pct=r.utilisation_pct, capex_outflow_usd=r.capex_outflow_usd,
                ebitda_usd=r.ebitda_usd, fcf_usd=r.fcf_usd, cumulative_fcf_usd=r.cumulative_fcf_usd,
                pv_usd=r.pv_usd,
            ) for r in result.schedule
        ],
        governance=governance,
    )


@router.post("/scenarios", response_model=ScenarioComparisonResponse)
def scenarios(req: CapexProjectRequest, db: Session = Depends(get_db)):
    inputs = _build_inputs(req)
    try:
        outcomes = run_standard_scenarios(inputs)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    governance = _governance(req, "capacity_expansion_scenario_comparison")
    log_model_run(
        db, governance, module="financial",
        inputs=req.model_dump(mode="json"),
        outputs_summary={name: o.npv_delta_vs_base_usd for name, o in outcomes.items()},
    )

    return ScenarioComparisonResponse(
        scenarios={
            name: ScenarioSummaryOut(
                name=o.name, npv_usd=o.result.npv_usd, irr_annual=o.result.irr_annual,
                payback_months=o.result.payback_months,
                steady_state_annual_ebitda_usd=o.result.steady_state_annual_ebitda_usd,
                commissioning_date=o.result.commissioning_date,
                npv_delta_vs_base_usd=o.npv_delta_vs_base_usd,
                irr_delta_vs_base_pp=o.irr_delta_vs_base_pp,
                payback_delta_months=o.payback_delta_months,
                ebitda_impact_delta_usd=o.ebitda_impact_delta_usd,
            ) for name, o in outcomes.items()
        },
        governance=governance,
    )
