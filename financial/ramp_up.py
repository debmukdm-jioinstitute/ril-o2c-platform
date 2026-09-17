"""Production ramp-up curves for the capacity expansion financial model.

A newly commissioned cracker doesn't run at nameplate capacity from day one — utilization
climbs over months as the plant is debottlenecked and offtake builds. `default_ramp_curve`
gives a simple, explicit linear ramp; callers who have a real ramp schedule (from engineering)
should pass it directly to `CapexProject` instead of relying on the default.
"""
from __future__ import annotations

import numpy as np


def default_ramp_curve(ramp_up_months: int, start_utilisation_pct: float = 30.0, end_utilisation_pct: float = 100.0) -> list[float]:
    """Linear ramp from `start_utilisation_pct` to `end_utilisation_pct` over
    `ramp_up_months` months (inclusive of both endpoints). Returns utilization *fractions*
    (0-1), one per month, in commissioning order.
    """
    if ramp_up_months < 1:
        raise ValueError("ramp_up_months must be >= 1")
    if not 0 <= start_utilisation_pct <= end_utilisation_pct <= 100:
        raise ValueError("require 0 <= start_utilisation_pct <= end_utilisation_pct <= 100")
    if ramp_up_months == 1:
        return [end_utilisation_pct / 100]
    curve = np.linspace(start_utilisation_pct, end_utilisation_pct, ramp_up_months)
    return (curve / 100).tolist()


def validate_ramp_curve(curve: list[float]) -> None:
    if len(curve) < 1:
        raise ValueError("ramp curve must have at least one month")
    if any(f < 0 or f > 1 for f in curve):
        raise ValueError("ramp curve values must be fractions in [0, 1]")
