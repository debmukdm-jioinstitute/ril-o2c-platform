from unittest.mock import MagicMock, patch

import httpx
import pandas as pd
import pytest

from data.adapters.eia_client import EiaClientError, fetch_eia_series


def _fake_response(rows):
    resp = MagicMock()
    resp.json.return_value = {"response": {"data": rows}}
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_eia_series_parses_and_sorts():
    rows = [
        {"period": "2026-01-03", "value": "82.5"},
        {"period": "2026-01-01", "value": "80.1"},
        {"period": "2026-01-02", "value": "81.0"},
    ]
    with patch("data.adapters.eia_client.httpx.get", return_value=_fake_response(rows)):
        series = fetch_eia_series("PET.RBRTE.D", api_key="DEMO_KEY")
    assert list(series.index) == sorted(series.index)
    assert series.iloc[0] == pytest.approx(80.1)
    assert series.iloc[-1] == pytest.approx(82.5)
    assert isinstance(series.index, pd.DatetimeIndex)


def test_fetch_eia_series_raises_on_empty_data():
    with patch("data.adapters.eia_client.httpx.get", return_value=_fake_response([])):
        with pytest.raises(EiaClientError):
            fetch_eia_series("PET.RBRTE.D", api_key="DEMO_KEY")


def test_fetch_eia_series_raises_on_http_error():
    with patch("data.adapters.eia_client.httpx.get", side_effect=httpx.ConnectError("boom")):
        with pytest.raises(EiaClientError):
            fetch_eia_series("PET.RBRTE.D", api_key="DEMO_KEY")


def test_fetch_eia_series_drops_unparseable_values():
    rows = [
        {"period": "2026-01-01", "value": "80.1"},
        {"period": "2026-01-02", "value": "NA"},
        {"period": "2026-01-03", "value": "82.5"},
    ]
    with patch("data.adapters.eia_client.httpx.get", return_value=_fake_response(rows)):
        series = fetch_eia_series("PET.RBRTE.D", api_key="DEMO_KEY")
    assert len(series) == 2
