from unittest.mock import MagicMock, patch

import httpx
import pytest

from data.adapters.fx_client import FxClientError, fetch_fx_history


def _fake_response(rates: dict):
    resp = MagicMock()
    resp.json.return_value = {"rates": rates}
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_fx_history_parses():
    rates = {"2026-01-01": {"INR": 83.1}, "2026-01-02": {"INR": 83.4}}
    with patch("data.adapters.fx_client.httpx.get", return_value=_fake_response(rates)):
        series = fetch_fx_history("USD", "INR", "2026-01-01")
    assert len(series) == 2
    assert series.iloc[0] == pytest.approx(83.1)


def test_fetch_fx_history_raises_on_empty():
    with patch("data.adapters.fx_client.httpx.get", return_value=_fake_response({})):
        with pytest.raises(FxClientError):
            fetch_fx_history("USD", "INR", "2026-01-01")


def test_fetch_fx_history_raises_on_error():
    with patch("data.adapters.fx_client.httpx.get", side_effect=httpx.ConnectError("boom")):
        with pytest.raises(FxClientError):
            fetch_fx_history("USD", "INR", "2026-01-01")
