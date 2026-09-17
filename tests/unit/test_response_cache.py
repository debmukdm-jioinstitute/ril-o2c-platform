import time

from app.services.response_cache import TTLCache


def test_returns_cached_value_within_ttl():
    cache = TTLCache()
    calls = []

    def compute():
        calls.append(1)
        return "value"

    assert cache.get_or_compute("k", 60, compute) == "value"
    assert cache.get_or_compute("k", 60, compute) == "value"
    assert len(calls) == 1  # second call served from cache, compute() not re-invoked


def test_recomputes_after_ttl_expires():
    cache = TTLCache()
    calls = []

    def compute():
        calls.append(1)
        return len(calls)

    assert cache.get_or_compute("k", 0.05, compute) == 1
    time.sleep(0.1)
    assert cache.get_or_compute("k", 0.05, compute) == 2


def test_different_keys_cached_independently():
    cache = TTLCache()
    assert cache.get_or_compute("a", 60, lambda: "A") == "A"
    assert cache.get_or_compute("b", 60, lambda: "B") == "B"
    assert cache.get_or_compute("a", 60, lambda: "changed") == "A"
