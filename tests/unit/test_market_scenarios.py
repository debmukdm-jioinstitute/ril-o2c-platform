import numpy as np
import pandas as pd
import pytest

from simulation.market_scenarios import (
    MARKET_VARS,
    draw_market_scenarios,
)


def test_shape_and_columns():
    scenarios = draw_market_scenarios(n_scenarios=5000, horizon_years=1.0, seed=42)
    for var in MARKET_VARS:
        assert var in scenarios.levels.columns
    assert "freight" in scenarios.levels.columns
    assert "project_delay_days" in scenarios.levels.columns
    assert len(scenarios.levels) == 5000


def test_positivity_and_bounds():
    scenarios = draw_market_scenarios(n_scenarios=5000, horizon_years=1.0, seed=42)
    levels = scenarios.levels
    for var in ["crude", "ethane", "naphtha", "natural_gas", "fx", "ethylene", "propylene", "demand"]:
        assert (levels[var] > 0).all()
    assert (levels["utilisation"] >= 0).all()
    assert (levels["utilisation"] <= 100).all()
    assert (levels["freight"] >= 0).all()
    assert (levels["project_delay_days"] >= 0).all()


def test_reproducible_given_seed():
    a = draw_market_scenarios(n_scenarios=2000, horizon_years=1.0, seed=1)
    b = draw_market_scenarios(n_scenarios=2000, horizon_years=1.0, seed=1)
    pd.testing.assert_frame_equal(a.levels, b.levels)


def test_correlation_is_applied_not_independent():
    scenarios = draw_market_scenarios(n_scenarios=100_000, horizon_years=1.0, seed=1)
    levels = scenarios.levels
    corr = np.corrcoef(np.log(levels["crude"]), np.log(levels["naphtha"]))[0, 1]
    # Target correlation for crude/naphtha is 0.85 in DEFAULT_MARKET_CORRELATION.
    assert corr == pytest.approx(0.85, abs=0.03)
    # A near-zero-correlation pair (fx vs utilisation, target 0.0) should NOT show the same
    # strength of association — this is the "not independently randomized" guarantee reversed:
    # highly correlated vars are correlated, unrelated ones aren't spuriously correlated.
    corr_fx_util = np.corrcoef(np.log(levels["fx"]), levels["utilisation"])[0, 1]
    assert abs(corr_fx_util) < 0.05


def test_rejects_too_few_scenarios_is_caller_responsibility():
    # draw_market_scenarios itself has no floor (the >=10k floor is enforced by
    # simulation.monte_carlo.run_monte_carlo) — but it must still reject nonsensical input.
    with pytest.raises(ValueError):
        draw_market_scenarios(n_scenarios=0, horizon_years=1.0, seed=1)
    with pytest.raises(ValueError):
        draw_market_scenarios(n_scenarios=10, horizon_years=0, seed=1)


def test_higher_horizon_widens_distribution():
    short = draw_market_scenarios(n_scenarios=20_000, horizon_years=0.25, seed=42)
    long = draw_market_scenarios(n_scenarios=20_000, horizon_years=2.0, seed=42)
    assert short.levels["crude"].std() < long.levels["crude"].std()
