import numpy as np
import pytest

from simulation.financial_mc import ProjectFinanceAssumptions, compute_irr, compute_npv


def test_npv_zero_ebitda_equals_negative_capex():
    assumptions = ProjectFinanceAssumptions(capex_usd=1000.0, project_life_years=10, wacc=0.10)
    npv = compute_npv(np.array([0.0]), np.array([0.0]), assumptions)
    assert npv[0] == pytest.approx(-1000.0)


def test_npv_decreases_with_delay():
    assumptions = ProjectFinanceAssumptions(capex_usd=1000.0, project_life_years=10, wacc=0.10)
    ebitda = np.array([500.0, 500.0])
    npv = compute_npv(ebitda, np.array([0.0, 180.0]), assumptions)
    assert npv[1] < npv[0]


def test_irr_recovers_known_rate():
    # Construct a cash flow stream with a known IRR: capex=1000, flat FCF=200/yr for 10 years
    # at exactly the rate that zeroes NPV, then verify compute_irr finds that rate and
    # compute_npv confirms NPV ≈ 0 at it.
    assumptions = ProjectFinanceAssumptions(capex_usd=1000.0, project_life_years=10, wacc=0.10)
    ebitda = np.array([200.0])
    irr = compute_irr(ebitda, np.array([0.0]), assumptions)
    assert not np.isnan(irr[0])

    check_assumptions = ProjectFinanceAssumptions(capex_usd=1000.0, project_life_years=10, wacc=irr[0])
    npv_at_irr = compute_npv(ebitda, np.array([0.0]), check_assumptions)
    assert npv_at_irr[0] == pytest.approx(0.0, abs=1e-2)


def test_irr_nan_when_project_never_recoups():
    assumptions = ProjectFinanceAssumptions(capex_usd=1_000_000.0, project_life_years=5, wacc=0.10)
    irr = compute_irr(np.array([10.0]), np.array([0.0]), assumptions)
    assert np.isnan(irr[0])


def test_npv_vectorized_shape():
    assumptions = ProjectFinanceAssumptions(capex_usd=1000.0, project_life_years=10, wacc=0.10)
    ebitda = np.linspace(100, 500, 50)
    delay = np.zeros(50)
    npv = compute_npv(ebitda, delay, assumptions)
    assert npv.shape == (50,)
    assert np.all(np.diff(npv) > 0)  # monotonic in EBITDA
