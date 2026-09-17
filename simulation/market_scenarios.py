"""Correlated market scenario draws for the Monte Carlo engine.

Draws a horizon-ahead *level* (not a full daily path) for each market variable, jointly
correlated via the same Cholesky-factorization technique as the synthetic daily-series
generator (data/synthetic/generator.py) — see data/common/correlation.py. This is
deliberately simpler than simulating a full price path to `horizon_years`: the scenario engine
answers "what does the distribution of outcomes look like at the decision horizon", not "what
does the path there look like", so a single terminal draw per variable per scenario is the
right level of detail and is what makes 10,000+ scenarios cheap to generate.

Variables covered (per spec): crude, ethane, naphtha, natural gas, FX, ethylene, propylene,
demand, utilisation — drawn as one correlated block. Freight and project delay are deliberately
NOT part of this block: freight is modeled as a deterministic function of the crude draw plus
small idiosyncratic noise (freight cost is overwhelmingly a crude/bunker-fuel story, not an
independent market), and project delay is execution/regulatory risk, a different risk class
from market prices — see ProjectDelayModel below. This is a modeling assumption, stated
explicitly here and in every MonteCarloResult's governance envelope, not a hidden default.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from data.common.correlation import draw_correlated_standard_normals

# Order matters: must match CORRELATION_MATRIX's index/columns.
MARKET_VARS = [
    "crude", "ethane", "naphtha", "natural_gas", "fx",
    "ethylene", "propylene", "demand", "utilisation",
]

# Correlation assumptions for the MC block — same qualitative story as
# data/synthetic/generator.DEFAULT_CORRELATION (crude-linked feedstocks move together, ethane
# tracks US gas, ethylene/propylene track crude with demand pulling both up), extended with
# demand and utilisation: demand is positively linked to product prices (higher demand, higher
# achievable prices) and to utilisation (plants run harder when demand is strong).
DEFAULT_MARKET_CORRELATION = pd.DataFrame(
    [
        # crude  ethane naph   gas    fx    ethyl  propy  dem    util
        [1.00,  0.15,  0.85,  0.20, -0.20,  0.55,  0.55,  0.30,  0.10],
        [0.15,  1.00,  0.20,  0.75, -0.05,  0.15,  0.15,  0.10,  0.05],
        [0.85,  0.20,  1.00,  0.22, -0.18,  0.60,  0.58,  0.30,  0.10],
        [0.20,  0.75,  0.22,  1.00, -0.05,  0.18,  0.18,  0.10,  0.05],
        [-0.20, -0.05, -0.18, -0.05, 1.00, -0.10, -0.10, -0.05,  0.00],
        [0.55,  0.15,  0.60,  0.18, -0.10,  1.00,  0.90,  0.45,  0.25],
        [0.55,  0.15,  0.58,  0.18, -0.10,  0.90,  1.00,  0.45,  0.25],
        [0.30,  0.10,  0.30,  0.10, -0.05,  0.45,  0.45,  1.00,  0.35],
        [0.10,  0.05,  0.10,  0.05,  0.00,  0.25,  0.25,  0.35,  1.00],
    ],
    index=MARKET_VARS,
    columns=MARKET_VARS,
)


@dataclass
class MarketVariableAssumption:
    base: float
    vol: float  # annualized volatility (lognormal vars) or absolute std at 1yr (level vars)
    kind: str = "lognormal"  # "lognormal" (prices/FX) or "level" (demand index, utilisation %)


DEFAULT_ASSUMPTIONS: dict[str, MarketVariableAssumption] = {
    "crude":       MarketVariableAssumption(base=82.0,  vol=0.32, kind="lognormal"),
    "ethane":      MarketVariableAssumption(base=8.5,   vol=0.40, kind="lognormal"),
    "naphtha":     MarketVariableAssumption(base=640.0, vol=0.30, kind="lognormal"),
    "natural_gas": MarketVariableAssumption(base=2.8,   vol=0.45, kind="lognormal"),
    "fx":          MarketVariableAssumption(base=83.5,  vol=0.07, kind="lognormal"),
    "ethylene":    MarketVariableAssumption(base=950.0, vol=0.28, kind="lognormal"),
    "propylene":   MarketVariableAssumption(base=900.0, vol=0.28, kind="lognormal"),
    "demand":      MarketVariableAssumption(base=100.0, vol=0.12, kind="lognormal"),
    "utilisation": MarketVariableAssumption(base=92.0,  vol=6.0,  kind="level"),
}


@dataclass
class ProjectDelayAssumption:
    """Sparse Poisson-arrival delay risk: with probability `event_prob` a delay event occurs,
    of magnitude Uniform[min_days, max_days]. Independent of the market block — see module
    docstring for why.
    """
    event_prob: float = 0.15
    min_days: int = 5
    max_days: int = 180


@dataclass
class FreightAssumption:
    base_usd_ton: float = 45.0
    crude_beta: float = 0.30  # freight sensitivity to crude price moves
    idio_vol: float = 0.08    # idiosyncratic noise on top of the crude-linked component


@dataclass
class MarketScenarios:
    """One row per scenario. `levels` holds the drawn value for every MARKET_VARS entry plus
    `freight` and `project_delay_days`; utilisation is already clipped to [0, 100].
    """
    levels: pd.DataFrame
    seed: int
    n_scenarios: int
    correlation: pd.DataFrame
    assumptions: dict[str, MarketVariableAssumption]


def draw_market_scenarios(
    n_scenarios: int,
    horizon_years: float,
    seed: int = 42,
    assumptions: dict[str, MarketVariableAssumption] | None = None,
    correlation: pd.DataFrame | None = None,
    freight: FreightAssumption | None = None,
    project_delay: ProjectDelayAssumption | None = None,
) -> MarketScenarios:
    if n_scenarios < 1:
        raise ValueError("n_scenarios must be >= 1")
    if horizon_years <= 0:
        raise ValueError("horizon_years must be > 0")

    assumptions = assumptions or DEFAULT_ASSUMPTIONS
    correlation = correlation if correlation is not None else DEFAULT_MARKET_CORRELATION
    freight = freight or FreightAssumption()
    project_delay = project_delay or ProjectDelayAssumption()

    missing = set(MARKET_VARS) - set(assumptions)
    if missing:
        raise ValueError(f"assumptions missing entries for: {sorted(missing)}")

    z = draw_correlated_standard_normals(n_scenarios, correlation.loc[MARKET_VARS, MARKET_VARS], seed)

    levels = pd.DataFrame(index=range(n_scenarios))
    for var in MARKET_VARS:
        spec = assumptions[var]
        if spec.kind == "lognormal":
            # Driftless (martingale) terminal draw — consistent with the naive/random-walk
            # forecaster's "no view on direction" assumption elsewhere in this platform.
            levels[var] = spec.base * np.exp(-0.5 * spec.vol ** 2 * horizon_years + spec.vol * np.sqrt(horizon_years) * z[var])
        elif spec.kind == "level":
            levels[var] = spec.base + spec.vol * np.sqrt(horizon_years) * z[var]
        else:
            raise ValueError(f"Unknown variable kind '{spec.kind}' for '{var}'")

    levels["utilisation"] = levels["utilisation"].clip(lower=0, upper=100)

    # Freight: deterministic crude-linked component + independent idiosyncratic noise, matching
    # the synthetic daily generator's treatment (see data/synthetic/generator.py).
    rng = np.random.default_rng(seed + 1)  # offset seed: independent of the correlated block
    crude_relative = levels["crude"] / assumptions["crude"].base - 1
    idio_shock = rng.normal(0, freight.idio_vol * np.sqrt(horizon_years), size=n_scenarios)
    levels["freight"] = freight.base_usd_ton * (1 + freight.crude_beta * crude_relative + idio_shock)
    levels["freight"] = levels["freight"].clip(lower=0)

    # Project delay: independent Bernoulli-then-uniform draw, not correlated with the market
    # block (see module docstring).
    rng_delay = np.random.default_rng(seed + 2)
    event = rng_delay.random(n_scenarios) < project_delay.event_prob
    magnitude = rng_delay.uniform(project_delay.min_days, project_delay.max_days, size=n_scenarios)
    levels["project_delay_days"] = np.where(event, magnitude, 0.0)

    return MarketScenarios(
        levels=levels, seed=seed, n_scenarios=n_scenarios,
        correlation=correlation.loc[MARKET_VARS, MARKET_VARS], assumptions=assumptions,
    )
