"""Synthetic market data generator.

Produces daily price/FX/operational series for the O2C decision-intelligence platform when
no real RIL data is supplied. Every series is clearly labeled synthetic at the point of use
(see app.schemas.governance.DataQualityStatus) — this module never claims to represent actual
market history.

Method: correlated geometric Brownian motion (GBM) in log-returns, driven by a Cholesky
factorization of a configurable correlation matrix, plus a slow mean-reverting (OU) drift
component per series so long-run levels don't wander to economically absurd values. This is a
standard, auditable approach for scenario/demo data — not a market forecast.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from data.common.correlation import nearest_psd_cholesky

# Series covered, with plausible anchor levels (USD unless noted), annualized volatility, and
# annualized OU mean-reversion speed (kappa; half-life = ln(2)/kappa). Levels are illustrative
# order-of-magnitude anchors for a demo, not market quotes. Reversion speeds are calibrated so
# multi-year synthetic paths stay in a plausible commodity range rather than drifting freely
# like an unconstrained random walk (which weak reversion would allow over a 5-7 year history).
SERIES_SPEC: dict[str, dict[str, float]] = {
    "crude_brent_usd_bbl":     {"level": 82.0,  "vol": 0.32, "mean_rev": 1.2},
    "ethane_usd_mmbtu":        {"level": 8.5,   "vol": 0.40, "mean_rev": 1.5},
    "naphtha_usd_ton":         {"level": 640.0, "vol": 0.30, "mean_rev": 1.3},
    "propane_usd_ton":         {"level": 520.0, "vol": 0.35, "mean_rev": 1.4},
    "butane_usd_ton":          {"level": 540.0, "vol": 0.35, "mean_rev": 1.4},
    "natural_gas_usd_mmbtu":   {"level": 2.8,   "vol": 0.45, "mean_rev": 1.6},
    "ethylene_usd_ton":        {"level": 950.0, "vol": 0.28, "mean_rev": 1.0},
    "propylene_usd_ton":       {"level": 900.0, "vol": 0.28, "mean_rev": 1.0},
    "fx_usdinr":               {"level": 83.5,  "vol": 0.07, "mean_rev": 0.4},
}

# Correlation matrix across the same series order. Crude/naphtha/propane/butane move together
# (all crude-linked); ethane/gas track each other (US gas-linked); ethylene/propylene track
# crude-linked feedstocks with a lag proxy folded into the same-day correlation; FX is weakly
# linked. This is an assumption set, not an estimated matrix — override via `correlation`.
DEFAULT_CORRELATION = pd.DataFrame(
    [
        # crude  ethane naph  prop  but   gas   ethy  propy fx
        [1.00, 0.15, 0.85, 0.80, 0.78, 0.20, 0.55, 0.55, -0.20],
        [0.15, 1.00, 0.20, 0.25, 0.25, 0.75, 0.15, 0.15, -0.05],
        [0.85, 0.20, 1.00, 0.82, 0.80, 0.22, 0.60, 0.58, -0.18],
        [0.80, 0.25, 0.82, 1.00, 0.88, 0.28, 0.50, 0.52, -0.15],
        [0.78, 0.25, 0.80, 0.88, 1.00, 0.28, 0.48, 0.50, -0.15],
        [0.20, 0.75, 0.22, 0.28, 0.28, 1.00, 0.18, 0.18, -0.05],
        [0.55, 0.15, 0.60, 0.50, 0.48, 0.18, 1.00, 0.90, -0.10],
        [0.55, 0.15, 0.58, 0.52, 0.50, 0.18, 0.90, 1.00, -0.10],
        [-0.20, -0.05, -0.18, -0.15, -0.15, -0.05, -0.10, -0.10, 1.00],
    ],
    index=list(SERIES_SPEC.keys()),
    columns=list(SERIES_SPEC.keys()),
)


@dataclass
class SyntheticMarketDataset:
    prices: pd.DataFrame  # date-indexed, one column per series
    demand_index: pd.Series
    utilisation_pct: pd.Series
    freight_usd_ton: pd.Series
    project_delay_days: pd.Series
    is_synthetic: bool = True
    seed: int = 42
    metadata: dict = field(default_factory=dict)


def generate_market_dataset(
    start: str = "2019-01-01",
    end: str = "2026-09-17",
    seed: int = 42,
    correlation: pd.DataFrame | None = None,
) -> SyntheticMarketDataset:
    """Generate a correlated daily synthetic market dataset.

    Deterministic given `seed`: same seed + date range always reproduces identical output,
    which is required for audit trails and reproducible backtests (spec module 14).
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, end=end)
    n = len(dates)

    corr = correlation if correlation is not None else DEFAULT_CORRELATION
    names = list(SERIES_SPEC.keys())
    chol = nearest_psd_cholesky(corr.loc[names, names].to_numpy())

    independent_shocks = rng.standard_normal(size=(n, len(names)))
    correlated_shocks = independent_shocks @ chol.T  # shape (n, k), corr structure applied

    dt = 1 / 252
    log_levels = np.zeros((n, len(names)))
    anchors = np.array([SERIES_SPEC[s]["level"] for s in names])
    vols = np.array([SERIES_SPEC[s]["vol"] for s in names])
    mean_rev = np.array([SERIES_SPEC[s]["mean_rev"] for s in names])
    log_anchor = np.log(anchors)

    log_levels[0] = log_anchor
    for t in range(1, n):
        prev = log_levels[t - 1]
        # OU pull back to long-run anchor + GBM-style diffusion shock, in log space.
        drift = mean_rev * (log_anchor - prev) * dt
        diffusion = vols * np.sqrt(dt) * correlated_shocks[t]
        log_levels[t] = prev + drift + diffusion

    prices = pd.DataFrame(np.exp(log_levels), index=dates, columns=names)

    # Operational series: demand index (100 = base), utilisation %, freight, project delay days.
    demand_shock = rng.normal(0, 0.008, size=n).cumsum()
    demand_index = pd.Series(100 * np.exp(demand_shock * 0.05), index=dates, name="demand_index")

    util_base = 92.0
    util_noise = rng.normal(0, 1.2, size=n)
    utilisation_pct = pd.Series(
        np.clip(util_base + pd.Series(util_noise).rolling(20, min_periods=1).mean().to_numpy(), 60, 100),
        index=dates,
        name="utilisation_pct",
    )

    freight_base = 45.0
    freight = pd.Series(
        freight_base * (1 + 0.3 * (prices["crude_brent_usd_bbl"] / SERIES_SPEC["crude_brent_usd_bbl"]["level"] - 1)),
        index=dates,
        name="freight_usd_ton",
    )

    # Project delay: rare Poisson-arrival delay events, days, non-negative, sparse.
    delay_events = rng.poisson(lam=0.002, size=n)
    project_delay_days = pd.Series((delay_events * rng.integers(5, 60, size=n)), index=dates, name="project_delay_days")

    return SyntheticMarketDataset(
        prices=prices,
        demand_index=demand_index,
        utilisation_pct=utilisation_pct,
        freight_usd_ton=freight,
        project_delay_days=project_delay_days,
        seed=seed,
        metadata={
            "generator": "data.synthetic.generator.generate_market_dataset",
            "start": start,
            "end": end,
            "n_obs": n,
            "series": names,
            "label": "Demo/Synthetic Data",
        },
    )
