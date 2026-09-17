"""Capacity expansion project-finance model.

Builds a month-by-month cash-flow schedule spanning construction (capex phased evenly to
commissioning), ramp-up (utilization climbing per the supplied ramp curve), and steady-state
operation, then discounts it to NPV/IRR/payback. Reuses the same feedstock-economics accounting
identity as Phase 3 (`models.feedstock.economics.compute_cracker_economics`) for every month's
EBITDA — one formula, not a second copy, so this model and the single-scenario feedstock
economics engine can never quietly disagree on how EBITDA is computed.

This supersedes the flat-annuity NPV/IRR the Monte Carlo engine (Phase 4,
`simulation/financial_mc.py`) uses for speed across 10,000+ scenarios — that model intentionally
trades ramp-up/capex-phasing detail for throughput; this one restores it for the small number of
named scenarios (base case, delay variants, accelerated) the spec asks for.

Simplifications, stated here and echoed in every result's assumptions:
- Pre-tax, unlevered free cash flow. No depreciation, tax shield, or debt schedule modeled.
- Capex spent already (`spent_capex_usd`) is sunk and excluded from NPV — only the remaining
  spend (plus any acceleration cost) is discounted forward from the valuation date.
- Construction-period capex is spread evenly across the months to commissioning; ramp-up
  utilization follows whatever curve is supplied (or `financial.ramp_up.default_ramp_curve`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
from scipy.optimize import brentq

from financial.capex_schedule import CapexStatus, monthly_capex_outflow_schedule
from financial.ramp_up import validate_ramp_curve
from models.feedstock.economics import CrackerEconomicsInputs, compute_cracker_economics

DAYS_PER_MONTH = 365.25 / 12  # average month length, used to convert daily EBITDA to monthly


@dataclass
class OperatingAssumptions:
    feedstock: str
    nameplate_throughput_tons_day: float
    feedstock_price: float
    ethylene_price_usd_ton: float
    propylene_price_usd_ton: float
    byproduct_price_usd_ton: float
    conversion_cost_usd_ton_feedstock: float
    logistics_cost_usd_ton_feedstock: float
    fx_usdinr: float = 83.5


@dataclass
class CapexProjectInputs:
    capex: CapexStatus
    operating: OperatingAssumptions
    wacc: float
    valuation_date: date
    planned_commissioning_date: date
    ramp_curve: list[float]  # utilization fractions [0,1], one per month post-commissioning
    post_ramp_operating_life_years: float
    delay_days: int = 0
    acceleration_days: int = 0
    acceleration_cost_usd: float = 0.0

    def __post_init__(self) -> None:
        validate_ramp_curve(self.ramp_curve)
        if self.wacc <= 0 or self.wacc >= 1:
            raise ValueError("wacc must be in (0, 1)")
        if self.post_ramp_operating_life_years < 0:
            raise ValueError("post_ramp_operating_life_years must be >= 0")
        if self.acceleration_days < 0 or self.acceleration_cost_usd < 0:
            raise ValueError("acceleration_days and acceleration_cost_usd must be >= 0")


@dataclass
class MonthlyScheduleRow:
    month_index: int
    calendar_date: date
    phase: str  # "construction" | "ramp_up" | "steady_state"
    utilisation_pct: float
    capex_outflow_usd: float
    ebitda_usd: float
    fcf_usd: float
    cumulative_fcf_usd: float
    discount_factor: float
    pv_usd: float


@dataclass
class CapexProjectResult:
    npv_usd: float
    irr_annual: float | None
    payback_months: int | None
    total_capex_deployed_usd: float  # remaining + acceleration, i.e. what's actually discounted
    steady_state_annual_ebitda_usd: float
    commissioning_date: date
    months_to_commission: int
    schedule: list[MonthlyScheduleRow] = field(repr=False)


def _monthly_ebitda_usd(operating: OperatingAssumptions, utilisation_frac: float) -> float:
    if utilisation_frac <= 0:
        return 0.0
    inputs = CrackerEconomicsInputs(
        feedstock=operating.feedstock,
        feedstock_price=operating.feedstock_price,
        throughput_tons_day=operating.nameplate_throughput_tons_day * utilisation_frac,
        ethylene_price_usd_ton=operating.ethylene_price_usd_ton,
        propylene_price_usd_ton=operating.propylene_price_usd_ton,
        byproduct_price_usd_ton=operating.byproduct_price_usd_ton,
        conversion_cost_usd_ton_feedstock=operating.conversion_cost_usd_ton_feedstock,
        logistics_cost_usd_ton_feedstock=operating.logistics_cost_usd_ton_feedstock,
        fx_usdinr=operating.fx_usdinr,
    )
    result = compute_cracker_economics(inputs)
    return result.ebitda_usd_day * DAYS_PER_MONTH


def _add_months(d: date, months: float) -> date:
    total_days = int(round(months * DAYS_PER_MONTH))
    return d + timedelta(days=total_days)


def build_monthly_schedule(inputs: CapexProjectInputs) -> tuple[list[MonthlyScheduleRow], date, int]:
    effective_commissioning_date = inputs.planned_commissioning_date
    if inputs.delay_days:
        effective_commissioning_date = effective_commissioning_date + timedelta(days=inputs.delay_days)
    if inputs.acceleration_days:
        effective_commissioning_date = effective_commissioning_date - timedelta(days=inputs.acceleration_days)

    months_to_commission = max(
        0, round((effective_commissioning_date - inputs.valuation_date).days / DAYS_PER_MONTH)
    )
    remaining_capex = inputs.capex.remaining_capex_usd + inputs.acceleration_cost_usd
    if months_to_commission > 0:
        capex_schedule = monthly_capex_outflow_schedule(remaining_capex, months_to_commission)
        n_construction = months_to_commission
    elif remaining_capex > 0:
        # Commissioning is already due, but there's still capex to place — give it one month
        # rather than discarding it (monthly_capex_outflow_schedule's own fallback for this case).
        capex_schedule = monthly_capex_outflow_schedule(remaining_capex, 0)
        n_construction = 1
    else:
        # Already commissioned with nothing left to spend: no construction phase at all.
        capex_schedule = np.array([])
        n_construction = 0

    ramp_months = len(inputs.ramp_curve)
    steady_months = max(0, round(inputs.post_ramp_operating_life_years * 12))
    total_months = n_construction + ramp_months + steady_months

    monthly_rate = (1 + inputs.wacc) ** (1 / 12) - 1

    rows: list[MonthlyScheduleRow] = []
    cumulative_fcf = 0.0
    for t in range(total_months):
        calendar_date = _add_months(inputs.valuation_date, t + 1)

        if t < n_construction:
            phase = "construction"
            utilisation = 0.0
            capex_out = float(capex_schedule[t]) if t < len(capex_schedule) else 0.0
        elif t < n_construction + ramp_months:
            phase = "ramp_up"
            utilisation = inputs.ramp_curve[t - n_construction]
            capex_out = 0.0
        else:
            phase = "steady_state"
            utilisation = inputs.ramp_curve[-1] if inputs.ramp_curve else 1.0
            capex_out = 0.0

        ebitda = _monthly_ebitda_usd(inputs.operating, utilisation)
        fcf = ebitda - capex_out
        cumulative_fcf += fcf
        discount_factor = 1 / (1 + monthly_rate) ** (t + 1)

        rows.append(MonthlyScheduleRow(
            month_index=t, calendar_date=calendar_date, phase=phase,
            utilisation_pct=utilisation * 100, capex_outflow_usd=capex_out,
            ebitda_usd=ebitda, fcf_usd=fcf, cumulative_fcf_usd=cumulative_fcf,
            discount_factor=discount_factor, pv_usd=fcf * discount_factor,
        ))

    return rows, effective_commissioning_date, n_construction


def run_capex_project(inputs: CapexProjectInputs) -> CapexProjectResult:
    schedule, commissioning_date, n_construction = build_monthly_schedule(inputs)

    npv = sum(row.pv_usd for row in schedule)

    fcf_arr = np.array([row.fcf_usd for row in schedule])

    def npv_at_monthly_rate(r: float) -> float:
        t = np.arange(1, len(fcf_arr) + 1)
        return float((fcf_arr / (1 + r) ** t).sum())

    irr_annual: float | None = None
    lo, hi = (1 + -0.5) ** (1 / 12) - 1, (1 + 5.0) ** (1 / 12) - 1
    try:
        f_lo, f_hi = npv_at_monthly_rate(lo), npv_at_monthly_rate(hi)
        if f_lo * f_hi < 0:
            monthly_irr = brentq(npv_at_monthly_rate, lo, hi, xtol=1e-8)
            irr_annual = (1 + monthly_irr) ** 12 - 1
    except (ValueError, FloatingPointError):
        irr_annual = None

    payback_months: int | None = None
    for row in schedule:
        if row.cumulative_fcf_usd >= 0:
            payback_months = row.month_index + 1
            break

    steady_rows = [r for r in schedule if r.phase == "steady_state"]
    steady_annual_ebitda = (steady_rows[0].ebitda_usd * 12) if steady_rows else (
        schedule[-1].ebitda_usd * 12 if schedule else 0.0
    )

    total_deployed = inputs.capex.remaining_capex_usd + inputs.acceleration_cost_usd

    return CapexProjectResult(
        npv_usd=npv, irr_annual=irr_annual, payback_months=payback_months,
        total_capex_deployed_usd=total_deployed,
        steady_state_annual_ebitda_usd=steady_annual_ebitda,
        commissioning_date=commissioning_date, months_to_commission=n_construction,
        schedule=schedule,
    )
