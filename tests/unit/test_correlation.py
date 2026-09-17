import numpy as np
import pandas as pd
import pytest

from data.common.correlation import draw_correlated_standard_normals, nearest_psd_cholesky


def test_cholesky_of_identity_is_identity():
    corr = np.eye(3)
    chol = nearest_psd_cholesky(corr)
    np.testing.assert_allclose(chol, np.eye(3), atol=1e-10)


def test_cholesky_reconstructs_correlation():
    corr = np.array([[1.0, 0.5], [0.5, 1.0]])
    chol = nearest_psd_cholesky(corr)
    np.testing.assert_allclose(chol @ chol.T, corr, atol=1e-10)


def test_draw_correlated_standard_normals_shape_and_marginals():
    corr = pd.DataFrame([[1.0, 0.0], [0.0, 1.0]], index=["a", "b"], columns=["a", "b"])
    draws = draw_correlated_standard_normals(50_000, corr, seed=1)
    assert draws.shape == (50_000, 2)
    assert abs(draws["a"].mean()) < 0.02
    assert abs(draws["a"].std() - 1.0) < 0.02


def test_draw_correlated_standard_normals_matches_target_correlation():
    corr = pd.DataFrame([[1.0, 0.7], [0.7, 1.0]], index=["a", "b"], columns=["a", "b"])
    draws = draw_correlated_standard_normals(100_000, corr, seed=1)
    empirical = draws["a"].corr(draws["b"])
    assert empirical == pytest.approx(0.7, abs=0.02)


def test_reproducible_given_seed():
    corr = pd.DataFrame([[1.0, 0.3], [0.3, 1.0]], index=["a", "b"], columns=["a", "b"])
    d1 = draw_correlated_standard_normals(1000, corr, seed=7)
    d2 = draw_correlated_standard_normals(1000, corr, seed=7)
    pd.testing.assert_frame_equal(d1, d2)


def test_mismatched_index_columns_raises():
    corr = pd.DataFrame([[1.0, 0.3], [0.3, 1.0]], index=["a", "b"], columns=["a", "c"])
    with pytest.raises(ValueError):
        draw_correlated_standard_normals(10, corr, seed=1)
