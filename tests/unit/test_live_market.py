from unittest.mock import patch

import pandas as pd
import pytest

from app.schemas.governance import DataQualityStatus
from data.adapters.eia_client import EiaClientError
from data.adapters.fx_client import FxClientError
from data.adapters.live_market import LIVE_SERIES, LiveMarketAdapter


def _fake_series(value: float, start="2020-01-01", end="2026-09-17") -> pd.Series:
    idx = pd.bdate_range(start=start, end=end)
    return pd.Series(value, index=idx)


@pytest.fixture
def mocked_fetches():
    with patch("data.adapters.live_market.fetch_eia_series") as eia_mock, \
         patch("data.adapters.live_market.fetch_fx_history") as fx_mock:
        eia_mock.side_effect = lambda series_id, api_key: {
            "PET.RBRTE.D": _fake_series(90.0),
            "NG.RNGWHHD.D": _fake_series(3.0),
            "PET.EER_EPLLPA_PF4_Y44MB_DPG.D": _fake_series(1.0),  # $/gal
        }[series_id]
        fx_mock.return_value = _fake_series(84.0)
        yield eia_mock, fx_mock


def test_live_series_marked_real_validated(mocked_fetches):
    adapter = LiveMarketAdapter(seed=1)
    prices = adapter.load_prices()
    for series_name in LIVE_SERIES:
        assert adapter.data_quality_for(series_name) == DataQualityStatus.REAL_VALIDATED
    assert prices["crude_brent_usd_bbl"].iloc[-1] == pytest.approx(90.0)
    assert prices["natural_gas_usd_mmbtu"].iloc[-1] == pytest.approx(3.0)


def test_synthetic_only_series_stay_synthetic(mocked_fetches):
    adapter = LiveMarketAdapter(seed=1)
    adapter.load_prices()
    for series_name in ["ethane_usd_mmbtu", "naphtha_usd_ton", "butane_usd_ton", "ethylene_usd_ton", "propylene_usd_ton"]:
        assert adapter.data_quality_for(series_name) == DataQualityStatus.SYNTHETIC


def test_propane_gal_to_ton_conversion(mocked_fetches):
    from data.adapters.live_market import PROPANE_GAL_PER_TON
    adapter = LiveMarketAdapter(seed=1)
    prices = adapter.load_prices()
    assert prices["propane_usd_ton"].iloc[-1] == pytest.approx(1.0 * PROPANE_GAL_PER_TON)


def test_operational_data_always_synthetic(mocked_fetches):
    adapter = LiveMarketAdapter(seed=1)
    op = adapter.load_operational()
    assert "demand_index" in op.columns


def test_fetch_failure_falls_back_to_synthetic_and_is_labeled_synthetic():
    with patch("data.adapters.live_market.fetch_eia_series", side_effect=EiaClientError("down")), \
         patch("data.adapters.live_market.fetch_fx_history", side_effect=FxClientError("down")):
        adapter = LiveMarketAdapter(seed=1)
        prices = adapter.load_prices()
        # Falls back to the synthetic generator's own values for these columns.
        synthetic_only = adapter._synthetic.load_prices()
        pd.testing.assert_series_equal(prices["crude_brent_usd_bbl"], synthetic_only["crude_brent_usd_bbl"])
        for series_name in LIVE_SERIES:
            assert adapter.data_quality_for(series_name) == DataQualityStatus.SYNTHETIC
        assert adapter.live_status() == {name: False for name in LIVE_SERIES}


def test_cache_avoids_refetching_within_ttl(mocked_fetches):
    eia_mock, fx_mock = mocked_fetches
    adapter = LiveMarketAdapter(seed=1, cache_ttl_seconds=3600)
    adapter.load_prices()
    first_call_count = eia_mock.call_count
    adapter.load_prices()
    assert eia_mock.call_count == first_call_count  # no new calls, served from cache


def test_live_status_reports_per_series_health(mocked_fetches):
    adapter = LiveMarketAdapter(seed=1)
    adapter.load_prices()
    status = adapter.live_status()
    assert all(status.values())
    assert set(status.keys()) == set(LIVE_SERIES)


def test_trailing_placeholder_nan_does_not_defeat_ffill():
    """Regression test: a real EIA response occasionally includes a row for the most recent
    date with a null value (not yet finalized) — that's a NaN at an *existing* index label,
    which reindex(method='ffill') alone won't fill (ffill only fills *missing* labels). The
    merge in load_prices() must still carry the last real value forward for that date.
    """
    good = _fake_series(90.0, end="2026-09-15")
    with_trailing_nan = pd.concat([good, pd.Series([float("nan")], index=[pd.Timestamp("2026-09-16")])])

    with patch("data.adapters.live_market.fetch_eia_series") as eia_mock, \
         patch("data.adapters.live_market.fetch_fx_history") as fx_mock:
        eia_mock.side_effect = lambda series_id, api_key: {
            "PET.RBRTE.D": with_trailing_nan,
            "NG.RNGWHHD.D": _fake_series(3.0),
            "PET.EER_EPLLPA_PF4_Y44MB_DPG.D": _fake_series(1.0),
        }[series_id]
        fx_mock.return_value = _fake_series(84.0)

        adapter = LiveMarketAdapter(seed=1)
        prices = adapter.load_prices()

    # 2026-09-16 has no real value yet, but the day before does — must forward-fill to 90.0,
    # not silently keep whatever the synthetic generator produced for that date.
    assert prices.loc["2026-09-16", "crude_brent_usd_bbl"] == pytest.approx(90.0)
