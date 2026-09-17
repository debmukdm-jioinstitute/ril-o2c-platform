"""Thin client for frankfurter.dev — a free, no-API-key FX rate service backed by the
European Central Bank's published reference rates. ECB publishes once per business day
(~16:00 CET), so like EIA this is genuine daily data, not tick-level streaming.
"""
from __future__ import annotations

import logging

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"


class FxClientError(RuntimeError):
    pass


def fetch_fx_history(base: str, quote: str, start_date: str, timeout: float = 15.0) -> pd.Series:
    """Fetch daily `base`/`quote` history from `start_date` to today. Raises FxClientError on
    any failure rather than fabricating a rate.
    """
    url = f"{FRANKFURTER_BASE_URL}/{start_date}.."
    try:
        resp = httpx.get(url, params={"from": base, "to": quote}, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FxClientError(f"FX fetch failed for {base}/{quote}: {exc}") from exc

    rates = payload.get("rates", {})
    if not rates:
        raise FxClientError(f"frankfurter.dev returned no rates for {base}/{quote}")

    dates = pd.to_datetime(list(rates.keys()))
    values = [v.get(quote) for v in rates.values()]
    series = pd.Series(values, index=dates, dtype=float).sort_index()
    series.index.name = None
    return series.dropna()
