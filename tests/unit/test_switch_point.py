import numpy as np
import pytest

from models.feedstock import CrackerEconomicsInputs
from models.feedstock.switch_point import breakeven_feedstock_price, sensitivity_grid_2d


def base_inputs(feedstock: str, price: float) -> CrackerEconomicsInputs:
    return CrackerEconomicsInputs(
        feedstock=feedstock, feedstock_price=price, throughput_tons_day=3000,
        ethylene_price_usd_ton=950, propylene_price_usd_ton=900, byproduct_price_usd_ton=500,
        conversion_cost_usd_ton_feedstock=60, logistics_cost_usd_ton_feedstock=15,
    )


def test_breakeven_price_is_consistent():
    inputs_a = base_inputs("ethane", 8.5)
    inputs_b = base_inputs("naphtha", 640)
    breakeven = breakeven_feedstock_price(inputs_a, inputs_b, price_bounds_b=(200, 1200))

    from dataclasses import replace
    from models.feedstock.economics import compute_cracker_economics
    cm_a = compute_cracker_economics(inputs_a).contribution_margin_usd_ton_ethylene
    cm_b_at_breakeven = compute_cracker_economics(replace(inputs_b, feedstock_price=breakeven)).contribution_margin_usd_ton_ethylene
    assert cm_a == pytest.approx(cm_b_at_breakeven, rel=1e-3)


def test_breakeven_raises_outside_bounds():
    inputs_a = base_inputs("ethane", 8.5)
    inputs_b = base_inputs("naphtha", 640)
    with pytest.raises(ValueError):
        breakeven_feedstock_price(inputs_a, inputs_b, price_bounds_b=(630, 650))


def test_sensitivity_grid_shape_and_symmetry():
    inputs_a = base_inputs("propane", 520)
    inputs_b = base_inputs("butane", 540)
    price_range_a = np.linspace(400, 700, 6)
    price_range_b = np.linspace(400, 700, 7)
    grid = sensitivity_grid_2d(inputs_a, inputs_b, price_range_a, price_range_b)
    assert len(grid) == 6 * 7
    assert set(grid["preferred"].unique()) <= {"propane", "butane"}
    # Raising A's price only should weakly reduce how often A is preferred at fixed B price.
    low_a = grid[grid["price_a"] == price_range_a.min()]["cm_diff_a_minus_b"].mean()
    high_a = grid[grid["price_a"] == price_range_a.max()]["cm_diff_a_minus_b"].mean()
    assert low_a > high_a
