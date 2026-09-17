"""Illustrative steam-cracker yield structures by feedstock. These are publicly documented
order-of-magnitude figures used across petrochemical industry literature (not RIL-specific
plant data) — swap in real yield curves when confidential data is available. Yields are mass
fraction of feedstock cracked, and do not sum to 100% alone; `other_byproduct_pct` captures
fuel gas, pygas, C4 co-products, etc. so each row sums to 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedstockYieldProfile:
    feedstock: str
    ethylene_yield_pct: float
    propylene_yield_pct: float
    other_byproduct_pct: float
    # Feedstock consumption per ton of ethylene produced (mass basis) — inverse of ethylene yield,
    # kept explicit for readability in the economics engine.
    price_unit: str  # "usd_ton" or "usd_mmbtu"
    mmbtu_per_ton: float | None = None  # conversion factor when priced per mmbtu (ethane/gas)

    def consumption_ton_per_ton_ethylene(self) -> float:
        return 1.0 / self.ethylene_yield_pct


YIELD_PROFILES: dict[str, FeedstockYieldProfile] = {
    "ethane": FeedstockYieldProfile(
        feedstock="ethane", ethylene_yield_pct=0.80, propylene_yield_pct=0.02,
        other_byproduct_pct=0.18, price_unit="usd_mmbtu", mmbtu_per_ton=45.5,
    ),
    "propane": FeedstockYieldProfile(
        feedstock="propane", ethylene_yield_pct=0.45, propylene_yield_pct=0.16,
        other_byproduct_pct=0.39, price_unit="usd_ton",
    ),
    "butane": FeedstockYieldProfile(
        feedstock="butane", ethylene_yield_pct=0.38, propylene_yield_pct=0.17,
        other_byproduct_pct=0.45, price_unit="usd_ton",
    ),
    "naphtha": FeedstockYieldProfile(
        feedstock="naphtha", ethylene_yield_pct=0.31, propylene_yield_pct=0.16,
        other_byproduct_pct=0.53, price_unit="usd_ton",
    ),
}
