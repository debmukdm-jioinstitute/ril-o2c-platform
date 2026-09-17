"""Cracker feedstock economics engine.

Computes revenue, cost, contribution margin and EBITDA for a given feedstock choice and
market-price scenario. Deliberately does NOT rank feedstocks by any fixed rule — the ranking
in `compare_feedstocks` falls straight out of the numbers for whatever prices are supplied.
This sits downstream of/alongside the company's existing LP optimizer: it explains and
stress-tests the economics an optimizer would work with, it does not replace it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from models.feedstock.yields import YIELD_PROFILES, FeedstockYieldProfile


@dataclass
class CrackerEconomicsInputs:
    feedstock: str
    feedstock_price: float  # in the unit the profile expects (usd_ton or usd_mmbtu)
    throughput_tons_day: float  # feedstock intake rate
    ethylene_price_usd_ton: float
    propylene_price_usd_ton: float
    byproduct_price_usd_ton: float  # blended realizable value of other co-products
    conversion_cost_usd_ton_feedstock: float  # cash opex to crack, ex-feedstock, ex-logistics
    logistics_cost_usd_ton_feedstock: float
    fx_usdinr: float = 83.5
    operating_days: int = 330  # accounts for planned/unplanned downtime in an annualized run


@dataclass
class CrackerEconomicsResult:
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
    inputs: CrackerEconomicsInputs = field(repr=False)


def _feedstock_cost_per_ton_feedstock(profile: FeedstockYieldProfile, price: float) -> float:
    if profile.price_unit == "usd_mmbtu":
        if profile.mmbtu_per_ton is None:
            raise ValueError(f"{profile.feedstock} priced per mmbtu but mmbtu_per_ton not set.")
        return price * profile.mmbtu_per_ton
    return price


def compute_cracker_economics(inputs: CrackerEconomicsInputs) -> CrackerEconomicsResult:
    if inputs.feedstock not in YIELD_PROFILES:
        raise ValueError(f"Unknown feedstock '{inputs.feedstock}'. Choose from {list(YIELD_PROFILES)}.")
    profile = YIELD_PROFILES[inputs.feedstock]

    ethylene_tpd = inputs.throughput_tons_day * profile.ethylene_yield_pct
    propylene_tpd = inputs.throughput_tons_day * profile.propylene_yield_pct
    byproduct_tpd = inputs.throughput_tons_day * profile.other_byproduct_pct

    feedstock_cost_per_ton = _feedstock_cost_per_ton_feedstock(profile, inputs.feedstock_price)
    feedstock_cost_day = feedstock_cost_per_ton * inputs.throughput_tons_day
    conversion_cost_day = inputs.conversion_cost_usd_ton_feedstock * inputs.throughput_tons_day
    logistics_cost_day = inputs.logistics_cost_usd_ton_feedstock * inputs.throughput_tons_day

    revenue_day = (
        ethylene_tpd * inputs.ethylene_price_usd_ton
        + propylene_tpd * inputs.propylene_price_usd_ton
        + byproduct_tpd * inputs.byproduct_price_usd_ton
    )

    total_cash_cost_day = feedstock_cost_day + conversion_cost_day + logistics_cost_day
    contribution_margin_day = revenue_day - total_cash_cost_day
    ebitda_day = contribution_margin_day  # no fixed-cost layer modeled at this granularity

    cm_per_ton_ethylene = contribution_margin_day / ethylene_tpd if ethylene_tpd > 0 else float("nan")
    ebitda_year = ebitda_day * inputs.operating_days
    ebitda_inr_cr_year = ebitda_year * inputs.fx_usdinr / 1e7  # USD -> INR -> crore

    margin_pct = (contribution_margin_day / revenue_day * 100) if revenue_day > 0 else float("nan")

    return CrackerEconomicsResult(
        feedstock=inputs.feedstock,
        ethylene_tons_day=ethylene_tpd,
        propylene_tons_day=propylene_tpd,
        byproduct_tons_day=byproduct_tpd,
        feedstock_cost_usd_day=feedstock_cost_day,
        conversion_cost_usd_day=conversion_cost_day,
        logistics_cost_usd_day=logistics_cost_day,
        revenue_usd_day=revenue_day,
        contribution_margin_usd_day=contribution_margin_day,
        contribution_margin_usd_ton_ethylene=cm_per_ton_ethylene,
        ebitda_usd_day=ebitda_day,
        ebitda_usd_year=ebitda_year,
        ebitda_inr_cr_year=ebitda_inr_cr_year,
        margin_pct_of_revenue=margin_pct,
        inputs=inputs,
    )


def compare_feedstocks(
    scenarios: dict[str, CrackerEconomicsInputs],
) -> pd.DataFrame:
    """Run compute_cracker_economics for each supplied feedstock scenario and return a
    comparison table sorted by contribution margin per ton of ethylene (best first). The
    caller decides which feedstocks to include and at what prices — nothing here assumes
    one feedstock is structurally better.
    """
    rows = []
    for label, inp in scenarios.items():
        r = compute_cracker_economics(inp)
        rows.append({
            "scenario": label,
            "feedstock": r.feedstock,
            "ethylene_tons_day": round(r.ethylene_tons_day, 1),
            "propylene_tons_day": round(r.propylene_tons_day, 1),
            "revenue_usd_day": round(r.revenue_usd_day, 0),
            "feedstock_cost_usd_day": round(r.feedstock_cost_usd_day, 0),
            "contribution_margin_usd_day": round(r.contribution_margin_usd_day, 0),
            "cm_usd_per_ton_ethylene": round(r.contribution_margin_usd_ton_ethylene, 1),
            "ebitda_usd_year": round(r.ebitda_usd_year, 0),
            "ebitda_inr_cr_year": round(r.ebitda_inr_cr_year, 1),
            "margin_pct_of_revenue": round(r.margin_pct_of_revenue, 2),
        })
    df = pd.DataFrame(rows).sort_values("cm_usd_per_ton_ethylene", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)
    return df
