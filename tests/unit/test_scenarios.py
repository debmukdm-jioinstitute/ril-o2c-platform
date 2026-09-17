from datetime import date

import pytest

from financial.capex_schedule import CapexStatus
from financial.project_model import CapexProjectInputs, OperatingAssumptions
from financial.ramp_up import default_ramp_curve
from financial.scenarios import DELAY_SCENARIOS_DAYS, run_standard_scenarios


def base_inputs(**overrides) -> CapexProjectInputs:
    capex = CapexStatus(
        total_capex_usd=2_000_000_000, committed_capex_usd=1_500_000_000,
        spent_capex_usd=500_000_000, construction_progress_pct=25,
    )
    operating = OperatingAssumptions(
        feedstock="ethane", nameplate_throughput_tons_day=3000, feedstock_price=8.5,
        ethylene_price_usd_ton=950, propylene_price_usd_ton=900, byproduct_price_usd_ton=500,
        conversion_cost_usd_ton_feedstock=60, logistics_cost_usd_ton_feedstock=15, fx_usdinr=83.5,
    )
    defaults = dict(
        capex=capex, operating=operating, wacc=0.11,
        valuation_date=date(2026, 1, 1), planned_commissioning_date=date(2027, 1, 1),
        ramp_curve=default_ramp_curve(6, 30, 100), post_ramp_operating_life_years=15,
    )
    defaults.update(overrides)
    return CapexProjectInputs(**defaults)


def test_base_case_has_zero_deltas():
    outcomes = run_standard_scenarios(base_inputs())
    base = outcomes["base_case"]
    assert base.npv_delta_vs_base_usd == 0.0
    assert base.ebitda_impact_delta_usd == 0.0


def test_all_delay_scenarios_present_and_worse_than_base():
    outcomes = run_standard_scenarios(base_inputs())
    for name in DELAY_SCENARIOS_DAYS:
        assert name in outcomes
        assert outcomes[name].npv_delta_vs_base_usd < 0, name


def test_longer_delay_is_monotonically_worse():
    outcomes = run_standard_scenarios(base_inputs())
    npv_1m = outcomes["delay_1_month"].npv_delta_vs_base_usd
    npv_3m = outcomes["delay_3_month"].npv_delta_vs_base_usd
    npv_6m = outcomes["delay_6_month"].npv_delta_vs_base_usd
    assert npv_1m > npv_3m > npv_6m


def test_accelerated_scenario_only_present_when_requested():
    outcomes_no_accel = run_standard_scenarios(base_inputs())
    assert "accelerated" not in outcomes_no_accel

    outcomes_with_accel = run_standard_scenarios(
        base_inputs(acceleration_days=60, acceleration_cost_usd=80_000_000)
    )
    assert "accelerated" in outcomes_with_accel


def test_accelerated_commissions_earlier():
    outcomes = run_standard_scenarios(base_inputs(acceleration_days=60, acceleration_cost_usd=80_000_000))
    base_commission = outcomes["base_case"].result.commissioning_date
    accel_commission = outcomes["accelerated"].result.commissioning_date
    assert (base_commission - accel_commission).days == 60


def test_delay_scenarios_do_not_stack_with_base_inputs_own_delay():
    # base_inputs itself carries delay_days=45; run_standard_scenarios must still produce a
    # true zero-delay base case, not one that inherits the 45-day delay.
    outcomes = run_standard_scenarios(base_inputs(delay_days=45))
    assert outcomes["base_case"].result.months_to_commission == run_standard_scenarios(base_inputs())["base_case"].result.months_to_commission
