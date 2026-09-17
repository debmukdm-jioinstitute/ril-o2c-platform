from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator

from app.schemas.governance import ModelGovernance
from models.feedstock.yields import YIELD_PROFILES

AVAILABLE_FEEDSTOCKS = list(YIELD_PROFILES.keys())


class CapexStatusIn(BaseModel):
    total_capex_usd: float = Field(..., gt=0)
    committed_capex_usd: float = Field(..., ge=0)
    spent_capex_usd: float = Field(..., ge=0)
    construction_progress_pct: float = Field(..., ge=0, le=100)

    @model_validator(mode="after")
    def _check_ordering(self):
        if not self.spent_capex_usd <= self.committed_capex_usd <= self.total_capex_usd:
            raise ValueError("require spent_capex_usd <= committed_capex_usd <= total_capex_usd")
        return self


class OperatingAssumptionsIn(BaseModel):
    feedstock: str = Field(..., description=f"One of {AVAILABLE_FEEDSTOCKS}")
    nameplate_throughput_tons_day: float = Field(..., gt=0)
    feedstock_price: float = Field(..., gt=0)
    ethylene_price_usd_ton: float = Field(..., gt=0)
    propylene_price_usd_ton: float = Field(..., gt=0)
    byproduct_price_usd_ton: float = Field(..., gt=0)
    conversion_cost_usd_ton_feedstock: float = Field(..., ge=0)
    logistics_cost_usd_ton_feedstock: float = Field(..., ge=0)
    fx_usdinr: float = Field(default=83.5, gt=0)


class CapexProjectRequest(BaseModel):
    capex: CapexStatusIn
    operating: OperatingAssumptionsIn
    wacc: float = Field(..., gt=0, lt=1)
    valuation_date: date
    planned_commissioning_date: date
    ramp_up_months: int = Field(default=6, ge=1, le=60)
    ramp_start_utilisation_pct: float = Field(default=30.0, ge=0, le=100)
    post_ramp_operating_life_years: float = Field(..., ge=0, le=60)
    delay_days: int = Field(default=0, ge=0)
    acceleration_days: int = Field(default=0, ge=0)
    acceleration_cost_usd: float = Field(default=0.0, ge=0)


class MonthlyScheduleRowOut(BaseModel):
    month_index: int
    calendar_date: date
    phase: str
    utilisation_pct: float
    capex_outflow_usd: float
    ebitda_usd: float
    fcf_usd: float
    cumulative_fcf_usd: float
    pv_usd: float


class CapexProjectResponse(BaseModel):
    npv_usd: float
    irr_annual: float | None
    payback_months: int | None
    total_capex_deployed_usd: float
    steady_state_annual_ebitda_usd: float
    commissioning_date: date
    months_to_commission: int
    schedule: list[MonthlyScheduleRowOut]
    governance: ModelGovernance


class ScenarioSummaryOut(BaseModel):
    name: str
    npv_usd: float
    irr_annual: float | None
    payback_months: int | None
    steady_state_annual_ebitda_usd: float
    commissioning_date: date
    npv_delta_vs_base_usd: float
    irr_delta_vs_base_pp: float | None
    payback_delta_months: int | None
    ebitda_impact_delta_usd: float


class ScenarioComparisonResponse(BaseModel):
    scenarios: dict[str, ScenarioSummaryOut]
    governance: ModelGovernance
