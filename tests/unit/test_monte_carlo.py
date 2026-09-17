import numpy as np
import pytest

from simulation.monte_carlo import MonteCarloInputs, run_monte_carlo


def base_inputs(**overrides) -> MonteCarloInputs:
    defaults = dict(
        feedstock="ethane", throughput_tons_day=3000, byproduct_price_usd_ton=500,
        conversion_cost_usd_ton_feedstock=60, logistics_cost_usd_ton_feedstock=15,
        capex_usd=2_000_000_000.0, project_life_years=15, wacc=0.11,
        n_scenarios=10_000, seed=42,
    )
    defaults.update(overrides)
    return MonteCarloInputs(**defaults)


def test_rejects_too_few_scenarios():
    with pytest.raises(ValueError):
        run_monte_carlo(base_inputs(n_scenarios=500))


def test_reproducible_given_seed():
    a = run_monte_carlo(base_inputs())
    b = run_monte_carlo(base_inputs())
    assert a.ebitda_usd_year.mean == pytest.approx(b.ebitda_usd_year.mean)
    assert a.npv.percentiles == b.npv.percentiles


def test_percentiles_are_ordered():
    result = run_monte_carlo(base_inputs())
    p = result.ebitda_usd_year.percentiles
    assert p[5] <= p[25] <= p[50] <= p[75] <= p[95]


def test_probability_of_breach_in_range():
    result = run_monte_carlo(base_inputs(ebitda_threshold_usd_year=100_000_000, ebitda_threshold_direction="below"))
    assert 0.0 <= result.probability_ebitda_breach <= 1.0


def test_probability_of_breach_none_when_no_threshold():
    result = run_monte_carlo(base_inputs())
    assert result.probability_ebitda_breach is None


def test_downside_upside_indices_valid_and_ordered():
    result = run_monte_carlo(base_inputs())
    n = result.n_scenarios
    assert 0 <= result.downside_scenario_index < n
    assert 0 <= result.upside_scenario_index < n
    ebitda = result.raw["ebitda_usd_year"]
    assert ebitda[result.downside_scenario_index] < ebitda[result.upside_scenario_index]


def test_governance_envelope_present():
    result = run_monte_carlo(base_inputs())
    assert result.governance.model_name == "monte_carlo_scenario_engine"
    assert result.governance.data_quality.value == "synthetic"
    assert result.governance.random_seed == 42
    assert len(result.governance.assumptions) >= 3


def test_raw_arrays_length_matches_n_scenarios():
    result = run_monte_carlo(base_inputs(n_scenarios=12_000))
    for key, arr in result.raw.items():
        assert len(arr) == 12_000, key


def test_naphtha_feedstock_also_works():
    result = run_monte_carlo(base_inputs(feedstock="naphtha"))
    assert result.ebitda_usd_year.mean == result.ebitda_usd_year.mean  # not NaN


def test_higher_wacc_reduces_npv():
    low = run_monte_carlo(base_inputs(wacc=0.08))
    high = run_monte_carlo(base_inputs(wacc=0.20))
    assert high.npv.mean < low.npv.mean
