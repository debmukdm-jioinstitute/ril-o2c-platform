from dataclasses import replace
from datetime import date

import pytest

from financial.capex_schedule import CapexStatus
from financial.project_model import CapexProjectInputs, OperatingAssumptions, run_capex_project
from financial.ramp_up import default_ramp_curve
from models.feedstock.economics import CrackerEconomicsInputs, compute_cracker_economics


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


def test_rejects_bad_wacc():
    with pytest.raises(ValueError):
        base_inputs(wacc=1.5)


def test_rejects_negative_acceleration():
    with pytest.raises(ValueError):
        base_inputs(acceleration_days=-5)


def test_commissioning_date_respects_delay_and_acceleration():
    result_base = run_capex_project(base_inputs())
    assert result_base.commissioning_date == date(2027, 1, 1)

    result_delayed = run_capex_project(base_inputs(delay_days=90))
    assert (result_delayed.commissioning_date - result_base.commissioning_date).days == 90

    result_accel = run_capex_project(base_inputs(acceleration_days=60, acceleration_cost_usd=50_000_000))
    assert (result_base.commissioning_date - result_accel.commissioning_date).days == 60


def test_payback_after_commissioning():
    result = run_capex_project(base_inputs())
    assert result.payback_months is not None
    assert result.payback_months >= result.months_to_commission


def test_delay_reduces_npv_holding_capex_constant():
    base = run_capex_project(base_inputs())
    delayed = run_capex_project(base_inputs(delay_days=180))
    assert delayed.npv_usd < base.npv_usd


def test_higher_wacc_reduces_npv():
    low = run_capex_project(base_inputs(wacc=0.08))
    high = run_capex_project(base_inputs(wacc=0.25))
    assert high.npv_usd < low.npv_usd


def test_steady_state_ebitda_matches_scalar_engine_at_full_utilisation():
    result = run_capex_project(base_inputs())
    scalar = compute_cracker_economics(CrackerEconomicsInputs(
        feedstock="ethane", feedstock_price=8.5, throughput_tons_day=3000,
        ethylene_price_usd_ton=950, propylene_price_usd_ton=900, byproduct_price_usd_ton=500,
        conversion_cost_usd_ton_feedstock=60, logistics_cost_usd_ton_feedstock=15, fx_usdinr=83.5,
    ))
    # steady-state ebitda/year should equal daily ebitda * 365.25 (avg year), not the scalar
    # engine's own operating_days=330 default — the project model runs steady-state 12 months
    # a year at full utilisation, not with planned downtime baked in (that would be a throughput
    # assumption, not a separate input in this model).
    expected_annual = scalar.ebitda_usd_day * 365.25
    assert result.steady_state_annual_ebitda_usd == pytest.approx(expected_annual, rel=1e-6)


def test_zero_remaining_capex_and_immediate_commissioning_does_not_crash():
    capex = CapexStatus(
        total_capex_usd=1_000_000_000, committed_capex_usd=1_000_000_000,
        spent_capex_usd=1_000_000_000, construction_progress_pct=100,
    )
    inputs = base_inputs(capex=capex, planned_commissioning_date=date(2025, 12, 1))  # before valuation_date
    result = run_capex_project(inputs)
    assert result.months_to_commission == 0
    assert result.total_capex_deployed_usd == 0
    assert result.schedule[0].phase == "ramp_up"


def test_no_ebitda_during_construction():
    result = run_capex_project(base_inputs())
    construction_rows = [r for r in result.schedule if r.phase == "construction"]
    assert len(construction_rows) > 0
    assert all(r.ebitda_usd == 0 for r in construction_rows)
    assert all(r.capex_outflow_usd > 0 for r in construction_rows)


def test_capex_schedule_sums_to_remaining_plus_acceleration():
    inputs = base_inputs(acceleration_days=30, acceleration_cost_usd=100_000_000)
    result = run_capex_project(inputs)
    total_capex_in_schedule = sum(r.capex_outflow_usd for r in result.schedule)
    assert total_capex_in_schedule == pytest.approx(inputs.capex.remaining_capex_usd + 100_000_000, rel=1e-6)
