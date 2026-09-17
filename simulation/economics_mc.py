"""Vectorized feedstock economics for Monte Carlo scenario arrays.

Same accounting identity as models/feedstock/economics.compute_cracker_economics (revenue minus
cash costs), generalized to operate on NumPy arrays (one element per scenario) instead of
scalars, and extended with two scenario-driven cost links the single-scenario engine doesn't
need:

- Conversion cost has a configurable natural-gas-linked fraction (utilities/fuel cost scales
  with gas price; the rest is fixed).
- Logistics cost splits into a fixed handling component (`logistics_cost_usd_ton_feedstock`,
  same field as the single-scenario engine) plus the scenario-drawn `freight` (variable,
  crude-linked — see simulation/market_scenarios.py).

Only ethane and naphtha are supported as MC feedstocks in this phase, because those are the two
feedstocks with a scenario price variable (see simulation.market_scenarios.MARKET_VARS) — the
spec's Monte Carlo variable list does not include propane/butane prices. The single-scenario
switch-point engine (models/feedstock/switch_point.py) still supports all four.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.feedstock.yields import YIELD_PROFILES

MC_SUPPORTED_FEEDSTOCKS = ("ethane", "naphtha")

_FEEDSTOCK_TO_YIELD_KEY = {"ethane": "ethane", "naphtha": "naphtha"}


@dataclass
class MCEconomicsInputs:
    feedstock: str
    throughput_tons_day: float
    ethylene_price: np.ndarray
    propylene_price: np.ndarray
    byproduct_price_usd_ton: float
    feedstock_price: np.ndarray
    conversion_cost_usd_ton_feedstock: float
    conversion_cost_gas_linked_fraction: float
    natural_gas_price: np.ndarray
    natural_gas_base: float
    logistics_cost_usd_ton_feedstock: float
    freight_usd_ton: np.ndarray
    utilisation_pct: np.ndarray
    fx_usdinr: np.ndarray
    operating_days: float = 330


@dataclass
class MCEconomicsResult:
    ethylene_tons_day: np.ndarray
    propylene_tons_day: np.ndarray
    byproduct_tons_day: np.ndarray
    revenue_usd_day: np.ndarray
    feedstock_cost_usd_day: np.ndarray
    conversion_cost_usd_day: np.ndarray
    logistics_cost_usd_day: np.ndarray
    contribution_margin_usd_day: np.ndarray
    ebitda_usd_day: np.ndarray
    ebitda_usd_year: np.ndarray
    ebitda_inr_cr_year: np.ndarray
    margin_pct_of_revenue: np.ndarray


def compute_mc_economics(inputs: MCEconomicsInputs) -> MCEconomicsResult:
    if inputs.feedstock not in MC_SUPPORTED_FEEDSTOCKS:
        raise ValueError(
            f"Monte Carlo economics supports {MC_SUPPORTED_FEEDSTOCKS} only (no scenario price "
            f"variable exists for '{inputs.feedstock}' — see simulation.market_scenarios.MARKET_VARS). "
            "Use models.feedstock.economics for single-scenario propane/butane analysis."
        )
    profile = YIELD_PROFILES[_FEEDSTOCK_TO_YIELD_KEY[inputs.feedstock]]

    effective_throughput = inputs.throughput_tons_day * (inputs.utilisation_pct / 100.0)
    ethylene_tpd = effective_throughput * profile.ethylene_yield_pct
    propylene_tpd = effective_throughput * profile.propylene_yield_pct
    byproduct_tpd = effective_throughput * profile.other_byproduct_pct

    if profile.price_unit == "usd_mmbtu":
        feedstock_cost_per_ton = inputs.feedstock_price * profile.mmbtu_per_ton
    else:
        feedstock_cost_per_ton = inputs.feedstock_price
    feedstock_cost_day = feedstock_cost_per_ton * effective_throughput

    gas_ratio = inputs.natural_gas_price / inputs.natural_gas_base
    f = inputs.conversion_cost_gas_linked_fraction
    conversion_cost_per_ton = inputs.conversion_cost_usd_ton_feedstock * ((1 - f) + f * gas_ratio)
    conversion_cost_day = conversion_cost_per_ton * effective_throughput

    logistics_cost_per_ton = inputs.logistics_cost_usd_ton_feedstock + inputs.freight_usd_ton
    logistics_cost_day = logistics_cost_per_ton * effective_throughput

    revenue_day = (
        ethylene_tpd * inputs.ethylene_price
        + propylene_tpd * inputs.propylene_price
        + byproduct_tpd * inputs.byproduct_price_usd_ton
    )
    total_cash_cost_day = feedstock_cost_day + conversion_cost_day + logistics_cost_day
    contribution_margin_day = revenue_day - total_cash_cost_day
    ebitda_day = contribution_margin_day
    ebitda_year = ebitda_day * inputs.operating_days
    ebitda_inr_cr_year = ebitda_year * inputs.fx_usdinr / 1e7

    with np.errstate(divide="ignore", invalid="ignore"):
        margin_pct = np.where(revenue_day != 0, contribution_margin_day / revenue_day * 100, np.nan)

    return MCEconomicsResult(
        ethylene_tons_day=ethylene_tpd,
        propylene_tons_day=propylene_tpd,
        byproduct_tons_day=byproduct_tpd,
        revenue_usd_day=revenue_day,
        feedstock_cost_usd_day=feedstock_cost_day,
        conversion_cost_usd_day=conversion_cost_day,
        logistics_cost_usd_day=logistics_cost_day,
        contribution_margin_usd_day=contribution_margin_day,
        ebitda_usd_day=ebitda_day,
        ebitda_usd_year=ebitda_year,
        ebitda_inr_cr_year=ebitda_inr_cr_year,
        margin_pct_of_revenue=margin_pct,
    )
