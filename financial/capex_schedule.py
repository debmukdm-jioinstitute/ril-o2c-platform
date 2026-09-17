"""Capex tracking and construction-period spend schedule.

`CapexStatus` holds the four capex-tracking figures the spec asks for (total, committed,
spent, remaining) plus physical construction progress, with the consistency checks a real capex
tracker needs — remaining is derived (never asked for as a separate input, since asking the
caller to keep it consistent with total/spent themselves is asking for drift), and a flag is
raised (not an error — this can legitimately happen) when spend-to-date and physical progress
diverge sharply, which is exactly the kind of thing a project controls team watches for.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# If |spent% - physical progress%| exceeds this, flag it — could mean front-loaded payment
# terms, or could mean cost overrun/underrun risk. Not an error; informational.
PROGRESS_DIVERGENCE_FLAG_PP = 15.0


@dataclass
class CapexStatus:
    total_capex_usd: float
    committed_capex_usd: float
    spent_capex_usd: float
    construction_progress_pct: float  # physical % complete, independent of cash spend

    def __post_init__(self) -> None:
        if self.total_capex_usd <= 0:
            raise ValueError("total_capex_usd must be > 0")
        if not 0 <= self.spent_capex_usd <= self.committed_capex_usd <= self.total_capex_usd:
            raise ValueError(
                "require 0 <= spent_capex_usd <= committed_capex_usd <= total_capex_usd "
                f"(got spent={self.spent_capex_usd}, committed={self.committed_capex_usd}, "
                f"total={self.total_capex_usd})"
            )
        if not 0 <= self.construction_progress_pct <= 100:
            raise ValueError("construction_progress_pct must be in [0, 100]")

    @property
    def remaining_capex_usd(self) -> float:
        return self.total_capex_usd - self.spent_capex_usd

    @property
    def uncommitted_capex_usd(self) -> float:
        return self.total_capex_usd - self.committed_capex_usd

    @property
    def spent_pct(self) -> float:
        return self.spent_capex_usd / self.total_capex_usd * 100

    @property
    def progress_divergence_flag(self) -> bool:
        return abs(self.spent_pct - self.construction_progress_pct) > PROGRESS_DIVERGENCE_FLAG_PP


def monthly_capex_outflow_schedule(remaining_capex_usd: float, months_to_commission: int) -> np.ndarray:
    """Even monthly spend of `remaining_capex_usd` across the months remaining until
    commissioning. If commissioning is already due (<=0 months remaining), the entire
    remaining balance is placed in month 0 — a schedule that's already at/past its
    commissioning date has no further runway to spread spend across.
    """
    if remaining_capex_usd < 0:
        raise ValueError("remaining_capex_usd must be >= 0")
    if months_to_commission <= 0:
        return np.array([remaining_capex_usd])
    return np.full(months_to_commission, remaining_capex_usd / months_to_commission)
