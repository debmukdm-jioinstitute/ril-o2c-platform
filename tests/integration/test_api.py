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


def test_monte_carlo(client):
    resp = client.post("/api/simulation/monte-carlo", json={
        "feedstock": "ethane", "throughput_tons_day": 3000, "byproduct_price_usd_ton": 500,
        "conversion_cost_usd_ton_feedstock": 60, "logistics_cost_usd_ton_feedstock": 15,
        "capex_usd": 2_000_000_000, "project_life_years": 15, "wacc": 0.11,
        "n_scenarios": 10000, "seed": 42, "ebitda_threshold_usd_year": 100_000_000,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_scenarios"] == 10000
    assert body["ebitda_usd_year"]["percentiles"]["5"] <= body["ebitda_usd_year"]["percentiles"]["95"]
    assert 0.0 <= body["probability_ebitda_breach"] <= 1.0
    assert body["governance"]["model_name"] == "monte_carlo_scenario_engine"
    assert "crude" in body["downside_case"]


def test_monte_carlo_rejects_too_few_scenarios(client):
    resp = client.post("/api/simulation/monte-carlo", json={
        "feedstock": "ethane", "throughput_tons_day": 3000, "byproduct_price_usd_ton": 500,
        "conversion_cost_usd_ton_feedstock": 60, "logistics_cost_usd_ton_feedstock": 15,
        "capex_usd": 2_000_000_000, "project_life_years": 15, "wacc": 0.11,
        "n_scenarios": 100, "seed": 42,
    })
    assert resp.status_code == 422  # Pydantic ge=MIN_SCENARIOS rejects it before the handler runs


def test_monte_carlo_unknown_feedstock(client):
    resp = client.post("/api/simulation/monte-carlo", json={
        "feedstock": "propane", "throughput_tons_day": 3000, "byproduct_price_usd_ton": 500,
        "conversion_cost_usd_ton_feedstock": 60, "logistics_cost_usd_ton_feedstock": 15,
        "capex_usd": 2_000_000_000, "project_life_years": 15, "wacc": 0.11,
        "n_scenarios": 10000, "seed": 42,
    })
    assert resp.status_code == 400


def _financial_project_payload(**overrides):
    payload = {
        "capex": {
            "total_capex_usd": 2_000_000_000, "committed_capex_usd": 1_500_000_000,
            "spent_capex_usd": 500_000_000, "construction_progress_pct": 25,
        },
        "operating": {
            "feedstock": "ethane", "nameplate_throughput_tons_day": 3000, "feedstock_price": 8.5,
            "ethylene_price_usd_ton": 950, "propylene_price_usd_ton": 900,
            "byproduct_price_usd_ton": 500, "conversion_cost_usd_ton_feedstock": 60,
            "logistics_cost_usd_ton_feedstock": 15, "fx_usdinr": 83.5,
        },
        "wacc": 0.11, "valuation_date": "2026-01-01", "planned_commissioning_date": "2027-01-01",
        "ramp_up_months": 6, "ramp_start_utilisation_pct": 30, "post_ramp_operating_life_years": 15,
    }
    payload.update(overrides)
    return payload


def test_financial_project(client):
    resp = client.post("/api/financial/project", json=_financial_project_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["months_to_commission"] > 0
    assert body["payback_months"] is not None
    assert len(body["schedule"]) > 0
    assert body["governance"]["model_name"] == "capacity_expansion_financial_model"


def test_financial_project_unknown_feedstock(client):
    payload = _financial_project_payload()
    payload["operating"]["feedstock"] = "coal"
    resp = client.post("/api/financial/project", json=payload)
    assert resp.status_code == 400


def test_financial_project_rejects_bad_capex_ordering(client):
    payload = _financial_project_payload()
    payload["capex"]["spent_capex_usd"] = 9_999_999_999
    resp = client.post("/api/financial/project", json=payload)
    assert resp.status_code == 422  # Pydantic model_validator rejects it


def test_financial_scenarios(client):
    resp = client.post("/api/financial/scenarios", json=_financial_project_payload(
        acceleration_days=60, acceleration_cost_usd=80_000_000,
    ))
    assert resp.status_code == 200
    body = resp.json()
    assert "base_case" in body["scenarios"]
    assert "delay_1_month" in body["scenarios"]
    assert "delay_3_month" in body["scenarios"]
    assert "delay_6_month" in body["scenarios"]
    assert "accelerated" in body["scenarios"]
    assert body["scenarios"]["delay_6_month"]["npv_delta_vs_base_usd"] < body["scenarios"]["delay_1_month"]["npv_delta_vs_base_usd"]
