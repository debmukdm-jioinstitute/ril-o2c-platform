"""A tiny generic in-process TTL cache, used to avoid recomputing expensive model runs
(forecasts) on every request when the underlying data hasn't changed. Underlying market data
updates at most once per business day (see data/adapters/live_market.py) and synthetic data is
static within a process, so recomputing a forecast on every single page load is wasted CPU —
which matters a lot on a constrained host (see the forecasting endpoint for why this exists).

Deliberately minimal: no eviction policy beyond TTL expiry, no size cap. This cache holds at
most (series × model × horizon) combinations, which is small and bounded by what the UI/API
actually expose — not a general-purpose cache for arbitrary unbounded keys.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Hashable, TypeVar

T = TypeVar("T")


class TTLCache:
    def __init__(self):
        self._store: dict[Hashable, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get_or_compute(self, key: Hashable, ttl_seconds: float, compute_fn: Callable[[], T]) -> T:
        now = time.monotonic()
        with self._lock:
            cached = self._store.get(key)
            if cached and (now - cached[0]) < ttl_seconds:
                return cached[1]  # type: ignore[return-value]
        # Compute outside the lock — model fitting can take seconds, and we don't want to
        # block other keys' cache reads/writes while one is being computed.
        value = compute_fn()
        with self._lock:
            self._store[key] = (now, value)
        return value
