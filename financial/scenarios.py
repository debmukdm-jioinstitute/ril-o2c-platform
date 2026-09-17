"""Named capacity-expansion scenarios: base case, schedule delays, and accelerated
commissioning — the exact scenario set the spec asks for. Each is run through
`financial.project_model.run_capex_project`; the "economic value/cost" of a scenario is simply
its NPV (and IRR/payback/EBITDA) delta against the base case.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from financial.project_model import CapexProjectInputs, CapexProjectResult, run_capex_project

DELAY_SCENARIOS_DAYS = {
    "delay_1_month": 30,
    "delay_3_month": 90,
    "delay_6_month": 180,
}


@dataclass
class ScenarioOutcome:
    name: str
    result: CapexProjectResult
    npv_delta_vs_base_usd: float
    irr_delta_vs_base_pp: float | None  # percentage points, None if either IRR undefined
    payback_delta_months: int | None  # None if either payback never reached
    ebitda_impact_delta_usd: float


def run_standard_scenarios(base_inputs: CapexProjectInputs) -> dict[str, ScenarioOutcome]:
    """Runs base case + every delay variant + (if the base inputs carry a nonzero
    acceleration_days/acceleration_cost_usd) an accelerated-commissioning scenario. Delay
    scenarios always start from a clean (delay=0, acceleration=0) copy of `base_inputs` — they
    don't stack with whatever delay/acceleration `base_inputs` itself carries, so "base case" in
    the returned dict is always the true zero-delay, zero-acceleration case.
    """
    clean_base = replace(base_inputs, delay_days=0, acceleration_days=0, acceleration_cost_usd=0.0)
    base_result = run_capex_project(clean_base)

    outcomes: dict[str, ScenarioOutcome] = {
        "base_case": ScenarioOutcome(
            name="base_case", result=base_result, npv_delta_vs_base_usd=0.0,
            irr_delta_vs_base_pp=0.0, payback_delta_months=0, ebitda_impact_delta_usd=0.0,
        )
    }

    for name, delay_days in DELAY_SCENARIOS_DAYS.items():
        scenario_inputs = replace(clean_base, delay_days=delay_days)
        outcomes[name] = _compare(name, scenario_inputs, base_result)

    if base_inputs.acceleration_days > 0 and base_inputs.acceleration_cost_usd > 0:
        accelerated_inputs = replace(
            clean_base,
            acceleration_days=base_inputs.acceleration_days,
            acceleration_cost_usd=base_inputs.acceleration_cost_usd,
        )
        outcomes["accelerated"] = _compare("accelerated", accelerated_inputs, base_result)

    return outcomes


def _compare(name: str, scenario_inputs: CapexProjectInputs, base_result: CapexProjectResult) -> ScenarioOutcome:
    result = run_capex_project(scenario_inputs)
    irr_delta = (
        (result.irr_annual - base_result.irr_annual)
        if result.irr_annual is not None and base_result.irr_annual is not None
        else None
    )
    payback_delta = (
        (result.payback_months - base_result.payback_months)
        if result.payback_months is not None and base_result.payback_months is not None
        else None
    )
    return ScenarioOutcome(
        name=name, result=result,
        npv_delta_vs_base_usd=result.npv_usd - base_result.npv_usd,
        irr_delta_vs_base_pp=irr_delta,
        payback_delta_months=payback_delta,
        ebitda_impact_delta_usd=result.steady_state_annual_ebitda_usd - base_result.steady_state_annual_ebitda_usd,
    )
