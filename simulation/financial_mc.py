"""Per-scenario NPV/IRR for the Monte Carlo engine.

Simplified project cash-flow model: capex spent at t=0, then a flat annuity of the scenario's
EBITDA for `project_life_years`, discounted at `wacc`. Project delay (drawn per scenario in
simulation.market_scenarios) pushes the entire cash-flow stream back by `delay_days / 365`
years — a simplification (no ramp-up curve, no capex phasing) that intentionally keeps the
Monte Carlo engine fast across 10,000+ scenarios. Phase 5 (capacity expansion financial model)
is where a proper multi-year ramp-up and phased capex schedule belongs; that model can reuse
this module's IRR solver.

NPV is fully vectorized (a discount-factor matrix computed once). IRR is not — root-finding is
inherently per-scenario — but each root-find is a handful of evaluations of a closed-form
function, so 10,000 scenarios still solve in well under a second.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq


@dataclass
class ProjectFinanceAssumptions:
    capex_usd: float
    project_life_years: int
    wacc: float  # annual discount rate, e.g. 0.11 for 11%


def compute_npv(
    ebitda_usd_year: np.ndarray,
    delay_days: np.ndarray,
    assumptions: ProjectFinanceAssumptions,
) -> np.ndarray:
    delay_years = delay_days / 365.0
    years = np.arange(1, assumptions.project_life_years + 1)
    # discount_exponents[i, t] = (t+1) + delay_years[i]
    discount_exponents = years[None, :] + delay_years[:, None]
    fcf = ebitda_usd_year[:, None] * np.ones((1, assumptions.project_life_years))
    pv = fcf / (1 + assumptions.wacc) ** discount_exponents
    return pv.sum(axis=1) - assumptions.capex_usd


def compute_irr(
    ebitda_usd_year: np.ndarray,
    delay_days: np.ndarray,
    assumptions: ProjectFinanceAssumptions,
    bounds: tuple[float, float] = (-0.5, 5.0),
) -> np.ndarray:
    # Bounds deliberately stop well short of -100%: rates near -100% make (1+r)^-t blow up
    # (dividing by a near-zero base), which can manufacture a mathematically "valid" but
    # economically meaningless root for almost any cash flow. -50%..+500% covers every
    # practically interpretable project IRR.
    delay_years = delay_days / 365.0
    years = np.arange(1, assumptions.project_life_years + 1)
    n = len(ebitda_usd_year)
    irr = np.full(n, np.nan)
    lo, hi = bounds

    for i in range(n):
        def npv_at_rate(r: float, _ebitda=ebitda_usd_year[i], _delay=delay_years[i]) -> float:
            pv = (_ebitda / (1 + r) ** (years + _delay)).sum()
            return pv - assumptions.capex_usd

        try:
            f_lo, f_hi = npv_at_rate(lo), npv_at_rate(hi)
            if f_lo == 0:
                irr[i] = lo
            elif f_hi == 0:
                irr[i] = hi
            elif f_lo * f_hi < 0:
                irr[i] = brentq(npv_at_rate, lo, hi, xtol=1e-5)
            # else: no sign change in bounds -> IRR undefined/out of range, left as NaN
        except (ValueError, FloatingPointError):
            continue

    return irr
