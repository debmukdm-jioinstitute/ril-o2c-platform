"""API integration tests. No live Postgres required — audit logging degrades gracefully
(see app.services.audit.log_model_run) when the configured database is unreachable, so these
exercise the full request/response path against the synthetic data adapter only.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data_source_mode"] == "synthetic"


def test_list_series(client):
    resp = client.get("/api/forecasting/series")
    assert resp.status_code == 200
    body = resp.json()
    assert "crude_brent_usd_bbl" in body["series"]
    assert "ensemble" in body["models"]


def test_prices_endpoint(client):
    resp = client.get("/api/data/prices", params={"series": ["crude_brent_usd_bbl"], "tail_days": 30})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_quality"] == "synthetic"
    assert len(body["dates"]) == 30
    assert len(body["series"]["crude_brent_usd_bbl"]) == 30


def test_prices_endpoint_unknown_series(client):
    resp = client.get("/api/data/prices", params={"series": ["unobtanium"]})
    assert resp.status_code == 400


def test_forecast_naive(client):
    resp = client.post("/api/forecasting/forecast", json={
        "series_name": "crude_brent_usd_bbl", "model": "naive", "horizon_days": 10,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["point_forecast"]) == 10
    assert body["governance"]["data_quality"] == "synthetic"
    assert body["governance"]["model_name"] == "naive_random_walk"


def test_forecast_unknown_model(client):
    resp = client.post("/api/forecasting/forecast", json={
        "series_name": "crude_brent_usd_bbl", "model": "not_a_model", "horizon_days": 10,
    })
    assert resp.status_code == 400


def test_feedstock_economics(client):
    resp = client.post("/api/feedstock/economics", json={
        "feedstock": "naphtha", "feedstock_price": 640, "throughput_tons_day": 3000,
        "ethylene_price_usd_ton": 950, "propylene_price_usd_ton": 900,
        "byproduct_price_usd_ton": 500, "conversion_cost_usd_ton_feedstock": 60,
        "logistics_cost_usd_ton_feedstock": 15,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["ethylene_tons_day"] > 0
    assert body["feedstock"] == "naphtha"


def test_feedstock_switch_point(client):
    scenario = {
        "feedstock": "ethane", "feedstock_price": 8.5, "throughput_tons_day": 3000,
        "ethylene_price_usd_ton": 950, "propylene_price_usd_ton": 900,
        "byproduct_price_usd_ton": 500, "conversion_cost_usd_ton_feedstock": 60,
        "logistics_cost_usd_ton_feedstock": 15,
    }
    scenario_b = {**scenario, "feedstock": "naphtha", "feedstock_price": 640}
    resp = client.post("/api/feedstock/switch-point", json={
        "scenario_a": scenario, "scenario_b": scenario_b,
        "price_min_a": 5, "price_max_a": 15, "price_min_b": 400, "price_max_b": 900,
        "grid_points": 5,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["grid"]) == 25
