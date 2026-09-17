import numpy as np
import pytest

from financial.capex_schedule import CapexStatus, monthly_capex_outflow_schedule


def test_remaining_and_uncommitted():
    status = CapexStatus(total_capex_usd=1000, committed_capex_usd=800, spent_capex_usd=300, construction_progress_pct=25)
    assert status.remaining_capex_usd == 700
    assert status.uncommitted_capex_usd == 200
    assert status.spent_pct == pytest.approx(30.0)


def test_rejects_inconsistent_ordering():
    with pytest.raises(ValueError):
        CapexStatus(total_capex_usd=1000, committed_capex_usd=800, spent_capex_usd=900, construction_progress_pct=25)
    with pytest.raises(ValueError):
        CapexStatus(total_capex_usd=1000, committed_capex_usd=1200, spent_capex_usd=100, construction_progress_pct=25)


def test_rejects_bad_progress_pct():
    with pytest.raises(ValueError):
        CapexStatus(total_capex_usd=1000, committed_capex_usd=800, spent_capex_usd=300, construction_progress_pct=150)


def test_progress_divergence_flag():
    aligned = CapexStatus(total_capex_usd=1000, committed_capex_usd=800, spent_capex_usd=300, construction_progress_pct=30)
    assert not aligned.progress_divergence_flag
    diverged = CapexStatus(total_capex_usd=1000, committed_capex_usd=800, spent_capex_usd=300, construction_progress_pct=80)
    assert diverged.progress_divergence_flag


def test_monthly_capex_outflow_even_split():
    schedule = monthly_capex_outflow_schedule(1200, 12)
    assert len(schedule) == 12
    np.testing.assert_allclose(schedule, 100.0)
    assert schedule.sum() == pytest.approx(1200)


def test_monthly_capex_outflow_zero_months():
    schedule = monthly_capex_outflow_schedule(500, 0)
    assert list(schedule) == [500]


def test_monthly_capex_outflow_rejects_negative():
    with pytest.raises(ValueError):
        monthly_capex_outflow_schedule(-100, 12)
