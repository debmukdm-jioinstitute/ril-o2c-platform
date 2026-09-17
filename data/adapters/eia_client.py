"""Thin client for the US EIA (Energy Information Administration) open data API v2.

EIA is the only free, no-subscription source for real commodity spot prices this platform
uses. It covers WTI/Brent crude, Henry Hub natural gas, and Mont Belvieu propane — see
data/adapters/live_market.py for which platform series map to which EIA series. It does NOT
cover ethane, butane, naphtha, ethylene, or propylene: those are proprietary OPIS/Platts/ICIS
data with no free tier, at any price point, anywhere. Don't add series here that aren't
genuinely published by EIA — see MODEL_CARD.md for why this line matters.

EIA data is end-of-day, typically posted with a 1-3 business day lag (it is *not* tick-level
real-time — no commodity data source that's genuinely real-time is free). "Live" in this
platform means "the freshest published real data, fetched on demand," not "streaming quotes."

Uses the `seriesid` bridge endpoint (`/v2/seriesid/{legacy_v1_series_id}`), which is the
simplest stable way to pull one series' full history through the v2 API. Falls back to the
shared `DEMO_KEY` (the api.data.gov convention EIA participates in) when no personal key is
configured — fine for light traffic, but rate-limited; see README for getting a free personal
key.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

EIA_BASE_URL = "https://api.eia.gov/v2/seriesid"

# Platform series name -> (EIA legacy v1 series id, source unit label).
# Every one of these is independently verifiable at eia.gov/opendata.
EIA_SERIES_MAP: dict[str, tuple[str, str]] = {
    "crude_brent_usd_bbl": ("PET.RBRTE.D", "$/bbl"),
    "natural_gas_usd_mmbtu": ("NG.RNGWHHD.D", "$/MMBtu"),
    # Mont Belvieu propane is published in $/gal; converted to $/ton by the caller.
    "propane_usd_gal_raw": ("PET.EER_EPLLPA_PF4_Y44MB_DPG.D", "$/gal"),
}


@dataclass
class EiaSeriesResult:
    series_name: str
    eia_series_id: str
    unit: str
    history: pd.Series  # date-indexed, sorted ascending
    source_url: str


class EiaClientError(RuntimeError):
    pass


def fetch_eia_series(eia_series_id: str, api_key: str, timeout: float = 15.0) -> pd.Series:
    """Fetch a full-history daily series from EIA. Raises EiaClientError on any failure —
    callers decide how to degrade (see live_market.py), this function never fabricates data.
    """
    url = f"{EIA_BASE_URL}/{eia_series_id}"
    try:
        resp = httpx.get(url, params={"api_key": api_key}, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise EiaClientError(f"EIA fetch failed for {eia_series_id}: {exc}") from exc

    rows = payload.get("response", {}).get("data", [])
    if not rows:
        raise EiaClientError(f"EIA returned no data for {eia_series_id}")

    df = pd.DataFrame(rows)
    if "period" not in df.columns or "value" not in df.columns:
        raise EiaClientError(f"Unexpected EIA response shape for {eia_series_id}: {list(df.columns)}")

    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).sort_values("period")
    series = df.set_index("period")["value"]
    series.index.name = None
    # Belt-and-suspenders: EIA occasionally includes a placeholder row for the most recent
    # date with a null value (not yet finalized) even after the coercion above — a NaN at an
    # *existing* index label defeats reindex(method="ffill") downstream, which only fills
    # *missing* labels, not present-but-null ones. Drop any that slipped through.
    return series.dropna()
