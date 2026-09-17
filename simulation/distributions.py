"""Summary statistics over a Monte Carlo output distribution: percentiles, probability of
threshold breach, and locating the scenario nearest a given percentile (so the caller can show
"what does the P5 downside case actually look like" with its full driver assumptions).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_PERCENTILES = (1, 5, 10, 25, 50, 75, 90, 95, 99)


@dataclass
class DistributionSummary:
    mean: float
    std: float
    min: float
    max: float
    percentiles: dict[int, float]  # e.g. {5: ..., 50: ..., 95: ...}

    def to_dict(self) -> dict:
        return {
            "mean": self.mean, "std": self.std, "min": self.min, "max": self.max,
            "percentiles": self.percentiles,
        }


def summarize(values: np.ndarray, percentiles: tuple[int, ...] = DEFAULT_PERCENTILES) -> DistributionSummary:
    clean = values[~np.isnan(values)]
    if len(clean) == 0:
        raise ValueError("No non-NaN values to summarize.")
    pct_values = np.percentile(clean, percentiles)
    return DistributionSummary(
        mean=float(clean.mean()), std=float(clean.std()),
        min=float(clean.min()), max=float(clean.max()),
        percentiles={p: float(v) for p, v in zip(percentiles, pct_values)},
    )


def probability_of_breach(values: np.ndarray, threshold: float, direction: str = "below") -> float:
    """Fraction of (non-NaN) scenarios where the metric breaches `threshold`.

    direction="below": fraction with value < threshold (e.g. "EBITDA falls below X").
    direction="above": fraction with value > threshold.
    """
    clean = values[~np.isnan(values)]
    if len(clean) == 0:
        raise ValueError("No non-NaN values to evaluate.")
    if direction == "below":
        return float(np.mean(clean < threshold))
    if direction == "above":
        return float(np.mean(clean > threshold))
    raise ValueError("direction must be 'below' or 'above'")


def nearest_scenario_to_percentile(values: np.ndarray, percentile: float) -> int:
    """Index of the scenario whose value is closest to the given percentile of `values`.
    Useful for surfacing a concrete "downside case" / "upside case" scenario rather than just
    a number — the caller can look up that index's full driver assumptions.
    """
    target = np.nanpercentile(values, percentile)
    valid = np.where(~np.isnan(values))[0]
    return int(valid[np.argmin(np.abs(values[valid] - target))])
