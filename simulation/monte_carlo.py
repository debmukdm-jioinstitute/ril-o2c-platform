"""Monte Carlo scenario engine orchestrator: draws correlated market scenarios, runs each
through the feedstock economics and project-finance formulas, and summarizes the resulting
EBITDA/revenue/margin/NPV/IRR distributions. This is the module referenced throughout the rest
of the platform as "the stochastic scenario engine" (spec module 4).

Governance note: reuses app.schemas.governance.ModelGovernance, the same envelope every
forecaster attaches to its output (see models/forecasting/base.py) — Monte Carlo results get
identical provenance/assumption disclosure, not a bespoke format.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from app.schemas.governance import DataQualityStatus, ModelGovernance
from simulation.distributions import (
    DistributionSummary,
    nearest_scenario_to_percentile,
    probability_of_breach,
    summarize,
)
from simulation.economics_mc import MCEconomicsInputs, compute_mc_economics
from simulation.financial_mc import ProjectFinanceAssumptions, compute_irr, compute_npv
from simulation.market_scenarios import (
    DEFAULT_ASSUMPTIONS,
    DEFAULT_MARKET_CORRELATION,
    FreightAssumption,
    MarketVariableAssumption,
    ProjectDelayAssumption,
    draw_market_scenarios,
)

MIN_SCENARIOS = 10_000


@dataclass
class MonteCarloInputs:
    feedstock: str  # "ethane" | "naphtha" — see simulation.economics_mc.MC_SUPPORTED_FEEDSTOCKS
    throughput_tons_day: float
    byproduct_price_usd_ton: float
    conversion_cost_usd_ton_feedstock: float
    logistics_cost_usd_ton_feedstock: float
    capex_usd: float
    project_life_years: int
    wacc: float
    conversion_cost_gas_linked_fraction: float = 0.3
    operating_days: float = 330
    horizon_years: float = 1.0
    n_scenarios: int = MIN_SCENARIOS
    seed: int = 42
    market_assumptions: dict[str, MarketVariableAssumption] | None = None
    correlation: pd.DataFrame | None = None
    freight: FreightAssumption | None = None
    project_delay: ProjectDelayAssumption | None = None
    ebitda_threshold_usd_year: float | None = None  # for probability-of-breach
    ebitda_threshold_direction: str = "below"


@dataclass
class MonteCarloResult:
    n_scenarios: int
    seed: int
    revenue: DistributionSummary
    ebitda_usd_year: DistributionSummary
    margin_pct: DistributionSummary
    npv: DistributionSummary
    irr: DistributionSummary
    probability_ebitda_breach: float | None
    downside_scenario_index: int  # P5 EBITDA scenario
    upside_scenario_index: int  # P95 EBITDA scenario
    raw: dict[str, np.ndarray] = field(repr=False)  # full arrays, for export/reverse stress testing
    governance: ModelGovernance = field(repr=False, default=None)  # type: ignore[assignment]


def run_monte_carlo(inputs: MonteCarloInputs) -> MonteCarloResult:
    if inputs.n_scenarios < MIN_SCENARIOS:
        raise ValueError(
            f"n_scenarios must be >= {MIN_SCENARIOS} (spec requirement: at least 10,000 "
            f"scenarios per run). Got {inputs.n_scenarios}."
        )

    market = draw_market_scenarios(
        n_scenarios=inputs.n_scenarios,
        horizon_years=inputs.horizon_years,
        seed=inputs.seed,
        assumptions=inputs.market_assumptions,
        correlation=inputs.correlation,
        freight=inputs.freight,
        project_delay=inputs.project_delay,
    )
    levels = market.levels
    assumptions = inputs.market_assumptions or DEFAULT_ASSUMPTIONS

    feedstock_price = levels["ethane"] if inputs.feedstock == "ethane" else levels["naphtha"]

    econ = compute_mc_economics(MCEconomicsInputs(
        feedstock=inputs.feedstock,
        throughput_tons_day=inputs.throughput_tons_day,
        ethylene_price=levels["ethylene"].to_numpy(),
        propylene_price=levels["propylene"].to_numpy(),
        byproduct_price_usd_ton=inputs.byproduct_price_usd_ton,
        feedstock_price=feedstock_price.to_numpy(),
        conversion_cost_usd_ton_feedstock=inputs.conversion_cost_usd_ton_feedstock,
        conversion_cost_gas_linked_fraction=inputs.conversion_cost_gas_linked_fraction,
        natural_gas_price=levels["natural_gas"].to_numpy(),
        natural_gas_base=assumptions["natural_gas"].base,
        logistics_cost_usd_ton_feedstock=inputs.logistics_cost_usd_ton_feedstock,
        freight_usd_ton=levels["freight"].to_numpy(),
        utilisation_pct=levels["utilisation"].to_numpy(),
        fx_usdinr=levels["fx"].to_numpy(),
        operating_days=inputs.operating_days,
    ))

    finance = ProjectFinanceAssumptions(
        capex_usd=inputs.capex_usd, project_life_years=inputs.project_life_years, wacc=inputs.wacc,
    )
    delay_days = levels["project_delay_days"].to_numpy()
    npv = compute_npv(econ.ebitda_usd_year, delay_days, finance)
    irr = compute_irr(econ.ebitda_usd_year, delay_days, finance)

    prob_breach = None
    if inputs.ebitda_threshold_usd_year is not None:
        prob_breach = probability_of_breach(
            econ.ebitda_usd_year, inputs.ebitda_threshold_usd_year, inputs.ebitda_threshold_direction,
        )

    downside_idx = nearest_scenario_to_percentile(econ.ebitda_usd_year, 5)
    upside_idx = nearest_scenario_to_percentile(econ.ebitda_usd_year, 95)

    governance = ModelGovernance(
        model_name="monte_carlo_scenario_engine",
        data_period_start=date.today(),
        data_period_end=date.today(),
        forecast_horizon_days=int(inputs.horizon_years * 365),
        confidence_level=0.90,
        assumptions=[
            f"{inputs.n_scenarios:,} correlated scenarios over a {inputs.horizon_years:.2f}-year horizon.",
            "Market variables (crude/ethane/naphtha/gas/FX/ethylene/propylene/demand/utilisation) "
            "drawn jointly via Cholesky factorization of a configurable correlation matrix — "
            "never independently randomized.",
            "Freight modeled as crude-linked + idiosyncratic noise; project delay drawn "
            "independently (execution risk, not a market variable) — see simulation/market_scenarios.py.",
            "NPV/IRR use a flat EBITDA annuity over the project life, shifted by the scenario's "
            "delay — no ramp-up curve modeled yet (planned for the capacity expansion financial model).",
        ],
        data_quality=DataQualityStatus.SYNTHETIC,
        random_seed=inputs.seed,
    )

    irr_clean = irr[~np.isnan(irr)]
    return MonteCarloResult(
        n_scenarios=inputs.n_scenarios,
        seed=inputs.seed,
        revenue=summarize(econ.revenue_usd_day),
        ebitda_usd_year=summarize(econ.ebitda_usd_year),
        margin_pct=summarize(econ.margin_pct_of_revenue),
        npv=summarize(npv),
        irr=summarize(irr_clean) if len(irr_clean) > 0 else DistributionSummary(
            mean=float("nan"), std=float("nan"), min=float("nan"), max=float("nan"), percentiles={},
        ),
        probability_ebitda_breach=prob_breach,
        downside_scenario_index=downside_idx,
        upside_scenario_index=upside_idx,
        raw={
            "revenue_usd_day": econ.revenue_usd_day,
            "ebitda_usd_year": econ.ebitda_usd_year,
            "margin_pct": econ.margin_pct_of_revenue,
            "npv": npv,
            "irr": irr,
            "crude": levels["crude"].to_numpy(),
            "ethane": levels["ethane"].to_numpy(),
            "naphtha": levels["naphtha"].to_numpy(),
            "natural_gas": levels["natural_gas"].to_numpy(),
            "fx": levels["fx"].to_numpy(),
            "ethylene": levels["ethylene"].to_numpy(),
            "propylene": levels["propylene"].to_numpy(),
            "demand": levels["demand"].to_numpy(),
            "utilisation": levels["utilisation"].to_numpy(),
            "freight": levels["freight"].to_numpy(),
            "project_delay_days": delay_days,
        },
        governance=governance,
    )
