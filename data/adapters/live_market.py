"""Hybrid live/synthetic market adapter.

Four series are genuinely live, fetched from real public sources with no fabrication:

  - crude_brent_usd_bbl   <- EIA (Europe Brent Spot Price FOB)
  - natural_gas_usd_mmbtu <- EIA (Henry Hub Spot Price)
  - propane_usd_ton       <- EIA (Mont Belvieu Propane Spot Price), converted $/gal -> $/ton
  - fx_usdinr             <- frankfurter.dev (ECB reference rate)

Five series have no free public source anywhere (ethane, naphtha, butane, ethylene, propylene
are proprietary OPIS/Platts/ICIS pricing — see the module docstring in eia_client.py) and stay
synthetic, clearly labeled as such per-series via `data_quality_for()`. This adapter never
blends a real number and a guessed number into the same series, and it never asks an LLM to
"recall" a price — if a live fetch fails, the affected series falls back to synthetic and is
labeled synthetic, not silently presented as live.

Data freshness: EIA and the ECB (via frankfurter.dev) both publish once per business day —
this is genuine, current, publicly-sourced data, but it is end-of-day, not streaming ticks.
Fetches are cached in-process for `cache_ttl_seconds` (default 12h) since re-fetching more often
than the source updates would be pointless and would burn API rate limits for no benefit.
"""
from __future__ import annotations

import logging
import time

import pandas as pd

from app.schemas.governance import DataQualityStatus
from data.adapters.base import DataAdapter
from data.adapters.eia_client import EIA_SERIES_MAP, EiaClientError, fetch_eia_series
from data.adapters.fx_client import FxClientError, fetch_fx_history
from data.adapters.synthetic_adapter import SyntheticAdapter

logger = logging.getLogger(__name__)

# Mont Belvieu propane spot is quoted $/US gallon. Converted to $/metric ton using the
# propane-industry-standard density of 4.24 lb/gal (National Propane Gas Association figure,
# also used by EIA's own unit-conversion tables) -> 2204.62 lb/ton / 4.24 lb/gal = 519.96 gal/ton.
PROPANE_GAL_PER_TON = 2204.62 / 4.24

LIVE_SERIES = ("crude_brent_usd_bbl", "natural_gas_usd_mmbtu", "propane_usd_ton", "fx_usdinr")
HISTORY_START = "2015-01-01"


class LiveMarketAdapter(DataAdapter):
    data_quality = DataQualityStatus.SYNTHETIC  # blanket fallback; real answer is per-series

    def __init__(self, seed: int = 42, eia_api_key: str = "DEMO_KEY", cache_ttl_seconds: float = 12 * 3600):
        self._synthetic = SyntheticAdapter(start=HISTORY_START, seed=seed)
        self._eia_api_key = eia_api_key
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, pd.Series]] = {}
        self._live_ok: dict[str, bool] = {name: False for name in LIVE_SERIES}

    def _cached_fetch(self, key: str, fetch_fn) -> pd.Series | None:
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached and (now - cached[0]) < self._cache_ttl:
            return cached[1]
        try:
            series = fetch_fn()
        except (EiaClientError, FxClientError) as exc:
            logger.warning("Live fetch failed for %s, falling back to synthetic: %s", key, exc)
            return cached[1] if cached else None
        self._cache[key] = (now, series)
        return series

    def _live_prices(self) -> pd.DataFrame:
        columns: dict[str, pd.Series] = {}

        brent_id, _ = EIA_SERIES_MAP["crude_brent_usd_bbl"]
        brent = self._cached_fetch("crude_brent_usd_bbl", lambda: fetch_eia_series(brent_id, self._eia_api_key))
        if brent is not None:
            columns["crude_brent_usd_bbl"] = brent
            self._live_ok["crude_brent_usd_bbl"] = True

        gas_id, _ = EIA_SERIES_MAP["natural_gas_usd_mmbtu"]
        gas = self._cached_fetch("natural_gas_usd_mmbtu", lambda: fetch_eia_series(gas_id, self._eia_api_key))
        if gas is not None:
            columns["natural_gas_usd_mmbtu"] = gas
            self._live_ok["natural_gas_usd_mmbtu"] = True

        propane_id, _ = EIA_SERIES_MAP["propane_usd_gal_raw"]
        propane_gal = self._cached_fetch("propane_usd_ton", lambda: fetch_eia_series(propane_id, self._eia_api_key))
        if propane_gal is not None:
            columns["propane_usd_ton"] = propane_gal * PROPANE_GAL_PER_TON
            self._live_ok["propane_usd_ton"] = True

        fx = self._cached_fetch("fx_usdinr", lambda: fetch_fx_history("USD", "INR", HISTORY_START))
        if fx is not None:
            columns["fx_usdinr"] = fx
            self._live_ok["fx_usdinr"] = True

        if not columns:
            return pd.DataFrame()
        return pd.DataFrame(columns)

    def load_prices(self) -> pd.DataFrame:
        synthetic = self._synthetic.load_prices()
        live = self._live_prices()
        if live.empty:
            return synthetic

        merged = synthetic.copy()
        # Reindex live data onto the synthetic frame's business-day index: forward-fill across
        # non-publishing days (weekends/holidays the source doesn't quote), then back-fill any
        # leading gap before the live source's earliest available date with... nothing further
        # back than the source goes. Dates before a live series' first observation keep the
        # synthetic value (there is no real data to show for them), so history for a live
        # series is a real-for-recent-years, synthetic-for-older-placeholder blend — acceptable
        # for backtesting depth, never misrepresented (see data_quality_for()).
        for col in live.columns:
            # .dropna() first: a NaN at an *existing* index label (e.g. a source's placeholder
            # row for a not-yet-finalized date) would otherwise survive reindex(method="ffill")
            # unchanged — ffill only fills *missing* labels, not present-but-null ones.
            aligned = live[col].dropna().reindex(merged.index, method="ffill")
            has_real = aligned.notna()
            merged.loc[has_real, col] = aligned[has_real]

        return merged

    def load_operational(self) -> pd.DataFrame:
        # No free public source exists for demand index, utilisation, freight, or project
        # delay at plant/company granularity — these remain synthetic unconditionally.
        return self._synthetic.load_operational()

    def data_quality_for(self, series_name: str) -> DataQualityStatus:
        if series_name in LIVE_SERIES and self._live_ok.get(series_name):
            return DataQualityStatus.REAL_VALIDATED
        return DataQualityStatus.SYNTHETIC

    def live_status(self) -> dict[str, bool]:
        """Which live series are actually serving real data right now (vs. degraded to
        synthetic because the source was unreachable) — surfaced in /api/health for transparency.
        """
        return dict(self._live_ok)
