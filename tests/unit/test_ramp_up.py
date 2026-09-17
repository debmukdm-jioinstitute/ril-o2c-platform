import pytest

from financial.ramp_up import default_ramp_curve, validate_ramp_curve


def test_default_ramp_curve_endpoints():
    curve = default_ramp_curve(12, start_utilisation_pct=30, end_utilisation_pct=100)
    assert len(curve) == 12
    assert curve[0] == pytest.approx(0.30)
    assert curve[-1] == pytest.approx(1.00)


def test_default_ramp_curve_monotonic():
    curve = default_ramp_curve(6, start_utilisation_pct=20, end_utilisation_pct=95)
    assert all(b >= a for a, b in zip(curve, curve[1:]))


def test_default_ramp_curve_single_month():
    curve = default_ramp_curve(1, start_utilisation_pct=30, end_utilisation_pct=100)
    assert curve == [1.0]


def test_default_ramp_curve_rejects_bad_bounds():
    with pytest.raises(ValueError):
        default_ramp_curve(6, start_utilisation_pct=100, end_utilisation_pct=30)
    with pytest.raises(ValueError):
        default_ramp_curve(0)


def test_validate_ramp_curve_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_ramp_curve([0.5, 1.2])
    with pytest.raises(ValueError):
        validate_ramp_curve([])
    validate_ramp_curve([0.3, 0.6, 1.0])  # should not raise
