"""Switch-point engine: dynamic economic break-even boundaries between feedstocks.

Answers "under what combination of market conditions does feedstock A become preferable to
feedstock B?" by computing contribution-margin differences across a grid of market conditions
and, where useful, solving directly for the break-even price of one feedstock given the other.
This complements the existing LP optimizer — it explains the economic boundary the optimizer
operates within, it does not re-solve the allocation problem itself.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from models.feedstock.economics import CrackerEconomicsInputs, compute_cracker_economics


def cm_per_ton_ethylene(inputs: CrackerEconomicsInputs) -> float:
    return compute_cracker_economics(inputs).contribution_margin_usd_ton_ethylene


def breakeven_feedstock_price(
    inputs_a: CrackerEconomicsInputs,
    inputs_b: CrackerEconomicsInputs,
    price_bounds_b: tuple[float, float],
) -> float:
    """Solve for the price of feedstock B (holding everything else in `inputs_b` fixed) at
    which B's contribution margin per ton of ethylene equals A's. Above this price B is worse
    than A; below it, B is better — on a contribution-margin-per-ton-ethylene basis.
    """
    target_cm_a = cm_per_ton_ethylene(inputs_a)

    def gap(price_b: float) -> float:
        candidate = replace(inputs_b, feedstock_price=price_b)
        return cm_per_ton_ethylene(candidate) - target_cm_a

    lo, hi = price_bounds_b
    if gap(lo) * gap(hi) > 0:
        raise ValueError(
            "No break-even price found in the supplied bounds — B is uniformly better or "
            "worse than A across the whole range. Widen price_bounds_b."
        )
    return float(brentq(gap, lo, hi, xtol=1e-4))


def sensitivity_grid_2d(
    inputs_a: CrackerEconomicsInputs,
    inputs_b: CrackerEconomicsInputs,
    price_range_a: np.ndarray,
    price_range_b: np.ndarray,
) -> pd.DataFrame:
    """2D sensitivity map: CM/ton-ethylene(A) - CM/ton-ethylene(B) over a grid of both
    feedstocks' prices. Positive = A preferred, negative = B preferred. Long format, ready
    to pivot into a heatmap or 3D surface.
    """
    rows = []
    for pa in price_range_a:
        cand_a = replace(inputs_a, feedstock_price=pa)
        cm_a = cm_per_ton_ethylene(cand_a)
        for pb in price_range_b:
            cand_b = replace(inputs_b, feedstock_price=pb)
            cm_b = cm_per_ton_ethylene(cand_b)
            rows.append({
                "price_a": pa, "price_b": pb,
                "cm_a_usd_per_ton_ethylene": cm_a,
                "cm_b_usd_per_ton_ethylene": cm_b,
                "cm_diff_a_minus_b": cm_a - cm_b,
                "preferred": inputs_a.feedstock if cm_a >= cm_b else inputs_b.feedstock,
            })
    return pd.DataFrame(rows)


def sensitivity_surface_3d(
    inputs_a: CrackerEconomicsInputs,
    inputs_b: CrackerEconomicsInputs,
    price_range_a: np.ndarray,
    price_range_b: np.ndarray,
) -> dict:
    """Same grid as sensitivity_grid_2d but reshaped into a Z matrix for a 3D surface plot
    (e.g. Plotly Surface): Z[i, j] = cm_diff at (price_range_a[i], price_range_b[j])."""
    z = np.zeros((len(price_range_a), len(price_range_b)))
    for i, pa in enumerate(price_range_a):
        cand_a = replace(inputs_a, feedstock_price=pa)
        cm_a = cm_per_ton_ethylene(cand_a)
        for j, pb in enumerate(price_range_b):
            cand_b = replace(inputs_b, feedstock_price=pb)
            cm_b = cm_per_ton_ethylene(cand_b)
            z[i, j] = cm_a - cm_b
    return {"x_price_a": price_range_a.tolist(), "y_price_b": price_range_b.tolist(), "z_cm_diff": z.tolist()}
