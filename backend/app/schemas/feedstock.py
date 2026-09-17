from __future__ import annotations

from pydantic import BaseModel, Field

from models.feedstock import YIELD_PROFILES

AVAILABLE_FEEDSTOCKS = list(YIELD_PROFILES.keys())


class EconomicsRequest(BaseModel):
    feedstock: str = Field(..., description=f"One of {AVAILABLE_FEEDSTOCKS}")
    feedstock_price: float = Field(..., gt=0, description="usd/ton, or usd/mmbtu for ethane")
    throughput_tons_day: float = Field(..., gt=0)
    ethylene_price_usd_ton: float = Field(..., gt=0)
    propylene_price_usd_ton: float = Field(..., gt=0)
    byproduct_price_usd_ton: float = Field(..., gt=0)
    conversion_cost_usd_ton_feedstock: float = Field(..., ge=0)
    logistics_cost_usd_ton_feedstock: float = Field(..., ge=0)
    fx_usdinr: float = Field(default=83.5, gt=0)
    operating_days: int = Field(default=330, ge=1, le=366)


class EconomicsResponse(BaseModel):
    feedstock: str
    ethylene_tons_day: float
    propylene_tons_day: float
    byproduct_tons_day: float
    feedstock_cost_usd_day: float
    conversion_cost_usd_day: float
    logistics_cost_usd_day: float
    revenue_usd_day: float
    contribution_margin_usd_day: float
    contribution_margin_usd_ton_ethylene: float
    ebitda_usd_day: float
    ebitda_usd_year: float
    ebitda_inr_cr_year: float
    margin_pct_of_revenue: float


class CompareRequest(BaseModel):
    scenarios: dict[str, EconomicsRequest]


class SwitchPointRequest(BaseModel):
    scenario_a: EconomicsRequest
    scenario_b: EconomicsRequest
    price_min_a: float = Field(..., gt=0)
    price_max_a: float = Field(..., gt=0)
    price_min_b: float = Field(..., gt=0)
    price_max_b: float = Field(..., gt=0)
    grid_points: int = Field(default=25, ge=5, le=100)
