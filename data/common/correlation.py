"""Shared correlated-random-draw utilities. Used by both the synthetic daily-series generator
(data/synthetic/generator.py) and the Monte Carlo scenario engine (simulation/) so the two
never drift into different techniques for the same underlying problem: turning a correlation
matrix into correlated draws via Cholesky factorization.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def nearest_psd_cholesky(corr: np.ndarray) -> np.ndarray:
    """Cholesky factor of a correlation matrix, nudging toward the nearest positive
    semi-definite matrix first if numerical noise (e.g. from hand-authored matrices) makes it
    not quite PSD.
    """
    try:
        return np.linalg.cholesky(corr)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(corr)
        eigvals_clipped = np.clip(eigvals, 1e-8, None)
        corr_psd = eigvecs @ np.diag(eigvals_clipped) @ eigvecs.T
        d = np.sqrt(np.diag(corr_psd))
        corr_psd = corr_psd / np.outer(d, d)
        return np.linalg.cholesky(corr_psd)


def draw_correlated_standard_normals(
    n_draws: int,
    correlation: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    """Draw `n_draws` rows of correlated standard-normal variates, one column per variable in
    `correlation`'s index/columns (which must match). Each column has mean 0, std 1 marginally;
    the correlation structure between columns matches `correlation` (subject to Cholesky/PSD
    approximation). Deterministic given `seed`.
    """
    if list(correlation.index) != list(correlation.columns):
        raise ValueError("correlation matrix must have matching index and columns")
    names = list(correlation.index)
    rng = np.random.default_rng(seed)
    chol = nearest_psd_cholesky(correlation.to_numpy())
    independent = rng.standard_normal(size=(n_draws, len(names)))
    correlated = independent @ chol.T
    return pd.DataFrame(correlated, columns=names)
