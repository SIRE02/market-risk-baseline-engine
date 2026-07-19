"""Complete-case Pearson correlation calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def align_returns(log_returns: pd.DataFrame) -> pd.DataFrame:
    """Keep dates that contain a valid log return for every selected asset."""
    if log_returns.shape[1] < 2:
        raise ValueError("At least two assets are required for correlation analysis.")
    aligned = log_returns.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if aligned.empty:
        raise ValueError("The aligned return matrix is empty after cleaning.")
    return aligned


def correlation_matrix(log_returns: pd.DataFrame) -> pd.DataFrame:
    """Calculate a Pearson correlation matrix from aligned log returns."""
    return align_returns(log_returns).corr(method="pearson")


def extreme_correlation_pairs(
    correlations: pd.DataFrame,
) -> tuple[tuple[str, str, float], tuple[str, str, float]]:
    """Return the highest and lowest unique off-diagonal asset pairs."""
    if correlations.shape[0] < 2 or correlations.shape[0] != correlations.shape[1]:
        raise ValueError("A square correlation matrix with at least two assets is required.")
    mask = np.triu(np.ones(correlations.shape, dtype=bool), k=1)
    pairs = correlations.where(mask).stack()
    if pairs.empty:
        raise ValueError("No off-diagonal correlation pairs are available.")
    highest_pair = pairs.idxmax()
    lowest_pair = pairs.idxmin()
    highest = (str(highest_pair[0]), str(highest_pair[1]), float(pairs.loc[highest_pair]))
    lowest = (str(lowest_pair[0]), str(lowest_pair[1]), float(pairs.loc[lowest_pair]))
    return highest, lowest

