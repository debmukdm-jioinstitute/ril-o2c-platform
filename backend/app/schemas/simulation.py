from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.governance import ModelGovernance
from simulation.economics_mc import MC_SUPPORTED_FEEDSTOCKS
from simulation.monte_carlo import MIN_SCENARIOS


class MonteCarloRequest(BaseModel):
    feedstock: str = Field(default="ethane", description=f"One of {MC_SUPPORTED_FEEDSTOCKS}")
    throughput_tons_day: float = Field(..., gt=0)
    byproduct_price_usd_ton: float = Field(..., gt=0)
    conversion_cost_usd_ton_feedstock: float = Field(..., ge=0)
    conversion_cost_gas_linked_fraction: float = Field(default=0.3, ge=0, le=1)
    logistics_cost_usd_ton_feedstock: float = Field(..., ge=0)
    operating_days: float = Field(default=330, gt=0, le=366)

    capex_usd: float = Field(..., gt=0)
    project_life_years: int = Field(..., ge=1, le=50)
    wacc: float = Field(..., gt=0, lt=1)

    horizon_years: float = Field(default=1.0, gt=0, le=10)
    n_scenarios: int = Field(default=MIN_SCENARIOS, ge=MIN_SCENARIOS, le=200_000)
    seed: int = Field(default=42)

    ebitda_threshold_usd_year: float | None = Field(default=None)
    ebitda_threshold_direction: str = Field(default="below", pattern="^(below|above)$")


class DistributionOut(BaseModel):
    mean: float
    std: float
    min: float
    max: float
    percentiles: dict[int, float]


class MonteCarloResponse(BaseModel):
    n_scenarios: int
    seed: int
    revenue: DistributionOut
    ebitda_usd_year: DistributionOut
    margin_pct: DistributionOut
    npv: DistributionOut
    irr: DistributionOut
    probability_ebitda_breach: float | None
    downside_case: dict
    upside_case: dict
    governance: ModelGovernance
