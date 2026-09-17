import pytest

from models.feedstock import CrackerEconomicsInputs, compare_feedstocks, compute_cracker_economics


def make_inputs(feedstock: str, feedstock_price: float) -> CrackerEconomicsInputs:
    return CrackerEconomicsInputs(
        feedstock=feedstock,
        feedstock_price=feedstock_price,
        throughput_tons_day=3000,
        ethylene_price_usd_ton=950,
        propylene_price_usd_ton=900,
        byproduct_price_usd_ton=500,
        conversion_cost_usd_ton_feedstock=60,
        logistics_cost_usd_ton_feedstock=15,
        fx_usdinr=83.5,
        operating_days=330,
    )


def test_unknown_feedstock_raises():
    with pytest.raises(ValueError):
        compute_cracker_economics(make_inputs("coal", 100))


def test_yields_sum_to_one_reflected_in_tonnage():
    from models.feedstock.yields import YIELD_PROFILES
    r = compute_cracker_economics(make_inputs("naphtha", 640))
    profile = YIELD_PROFILES["naphtha"]
    total_tpd = r.ethylene_tons_day + r.propylene_tons_day + r.byproduct_tons_day
    assert total_tpd == pytest.approx(3000 * (profile.ethylene_yield_pct + profile.propylene_yield_pct + profile.other_byproduct_pct))


def test_higher_feedstock_price_lowers_margin():
    cheap = compute_cracker_economics(make_inputs("naphtha", 500))
    expensive = compute_cracker_economics(make_inputs("naphtha", 800))
    assert cheap.contribution_margin_usd_day > expensive.contribution_margin_usd_day


def test_ethane_mmbtu_pricing_converted_to_tons():
    r = compute_cracker_economics(make_inputs("ethane", 8.5))
    # 8.5 usd/mmbtu * 45.5 mmbtu/ton = ~386.75 usd/ton feedstock cost basis
    expected_cost_per_ton = 8.5 * 45.5
    assert r.feedstock_cost_usd_day == pytest.approx(expected_cost_per_ton * 3000, rel=1e-6)


def test_compare_feedstocks_ranks_by_margin_no_bias():
    scenarios = {
        "ethane_base": make_inputs("ethane", 8.5),
        "naphtha_base": make_inputs("naphtha", 640),
        "propane_base": make_inputs("propane", 520),
        "butane_base": make_inputs("butane", 540),
    }
    df = compare_feedstocks(scenarios)
    assert list(df["rank"]) == [1, 2, 3, 4]
    # Ranking must be monotonic in the computed CM metric — not hard-coded to any feedstock.
    assert df["cm_usd_per_ton_ethylene"].is_monotonic_decreasing

    # Flip the price advantage: make naphtha artificially cheap and ethane artificially expensive.
    # The ranking must respond — this is the "no static superiority" guarantee under test.
    flipped = {
        "ethane_expensive": make_inputs("ethane", 40.0),
        "naphtha_cheap": make_inputs("naphtha", 200),
    }
    df2 = compare_feedstocks(flipped)
    assert df2.iloc[0]["scenario"] == "naphtha_cheap"
