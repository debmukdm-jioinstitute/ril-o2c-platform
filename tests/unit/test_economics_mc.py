import numpy as np
import pytest

from models.feedstock.economics import CrackerEconomicsInputs, compute_cracker_economics
from simulation.economics_mc import MCEconomicsInputs, compute_mc_economics


def test_unsupported_feedstock_raises():
    inputs = MCEconomicsInputs(
        feedstock="propane", throughput_tons_day=3000,
        ethylene_price=np.array([950.0]), propylene_price=np.array([900.0]),
        byproduct_price_usd_ton=500, feedstock_price=np.array([520.0]),
        conversion_cost_usd_ton_feedstock=60, conversion_cost_gas_linked_fraction=0.3,
        natural_gas_price=np.array([2.8]), natural_gas_base=2.8,
        logistics_cost_usd_ton_feedstock=15, freight_usd_ton=np.array([0.0]),
        utilisation_pct=np.array([100.0]), fx_usdinr=np.array([83.5]),
    )
    with pytest.raises(ValueError):
        compute_mc_economics(inputs)


def test_matches_scalar_engine_when_scenario_equals_base_case():
    """With utilisation=100%, gas at base (no conversion-cost drag), and freight=0 (all
    logistics folded into the fixed component), the vectorized MC formulas must reduce to
    exactly the same numbers as the single-scenario engine — same accounting identity."""
    scalar_inputs = CrackerEconomicsInputs(
        feedstock="naphtha", feedstock_price=640, throughput_tons_day=3000,
        ethylene_price_usd_ton=950, propylene_price_usd_ton=900, byproduct_price_usd_ton=500,
        conversion_cost_usd_ton_feedstock=60, logistics_cost_usd_ton_feedstock=15,
        fx_usdinr=83.5, operating_days=330,
    )
    scalar_result = compute_cracker_economics(scalar_inputs)

    mc_inputs = MCEconomicsInputs(
        feedstock="naphtha", throughput_tons_day=3000,
        ethylene_price=np.array([950.0]), propylene_price=np.array([900.0]),
        byproduct_price_usd_ton=500, feedstock_price=np.array([640.0]),
        conversion_cost_usd_ton_feedstock=60, conversion_cost_gas_linked_fraction=0.3,
        natural_gas_price=np.array([2.8]), natural_gas_base=2.8,  # ratio = 1 -> no drag
        logistics_cost_usd_ton_feedstock=15, freight_usd_ton=np.array([0.0]),
        utilisation_pct=np.array([100.0]), fx_usdinr=np.array([83.5]), operating_days=330,
    )
    mc_result = compute_mc_economics(mc_inputs)

    assert mc_result.revenue_usd_day[0] == pytest.approx(scalar_result.revenue_usd_day)
    assert mc_result.contribution_margin_usd_day[0] == pytest.approx(scalar_result.contribution_margin_usd_day)
    assert mc_result.ebitda_usd_year[0] == pytest.approx(scalar_result.ebitda_usd_year)
    assert mc_result.margin_pct_of_revenue[0] == pytest.approx(scalar_result.margin_pct_of_revenue)


def test_utilisation_scales_throughput():
    base = MCEconomicsInputs(
        feedstock="ethane", throughput_tons_day=3000,
        ethylene_price=np.array([950.0, 950.0]), propylene_price=np.array([900.0, 900.0]),
        byproduct_price_usd_ton=500, feedstock_price=np.array([8.5, 8.5]),
        conversion_cost_usd_ton_feedstock=60, conversion_cost_gas_linked_fraction=0.3,
        natural_gas_price=np.array([2.8, 2.8]), natural_gas_base=2.8,
        logistics_cost_usd_ton_feedstock=15, freight_usd_ton=np.array([0.0, 0.0]),
        utilisation_pct=np.array([100.0, 50.0]), fx_usdinr=np.array([83.5, 83.5]),
    )
    result = compute_mc_economics(base)
    assert result.ethylene_tons_day[1] == pytest.approx(result.ethylene_tons_day[0] * 0.5)


def test_gas_linked_conversion_cost_increases_with_gas_price():
    inputs = MCEconomicsInputs(
        feedstock="ethane", throughput_tons_day=3000,
        ethylene_price=np.array([950.0, 950.0]), propylene_price=np.array([900.0, 900.0]),
        byproduct_price_usd_ton=500, feedstock_price=np.array([8.5, 8.5]),
        conversion_cost_usd_ton_feedstock=60, conversion_cost_gas_linked_fraction=0.5,
        natural_gas_price=np.array([2.8, 5.6]), natural_gas_base=2.8,
        logistics_cost_usd_ton_feedstock=15, freight_usd_ton=np.array([0.0, 0.0]),
        utilisation_pct=np.array([100.0, 100.0]), fx_usdinr=np.array([83.5, 83.5]),
    )
    result = compute_mc_economics(inputs)
    assert result.conversion_cost_usd_day[1] > result.conversion_cost_usd_day[0]
