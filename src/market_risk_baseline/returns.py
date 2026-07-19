"""Vectorized simple-return and logarithmic-return calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _validate_prices(prices: pd.DataFrame) -> None:
    if prices.empty:
        raise ValueError("The price matrix is empty.")
    if (prices <= 0).any(axis=None):
        raise ValueError("All adjusted prices must be positive to calculate log returns.")


def calculate_simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate percentage changes and remove invalid observations."""
    _validate_prices(prices)
    returns = prices.pct_change(fill_method=None)
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if returns.empty:
        raise ValueError("The simple-return matrix is empty after cleaning.")
    return returns


def calculate_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate time-additive log returns and remove invalid observations."""
    _validate_prices(prices)
    returns = np.log(prices / prices.shift(1))
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if returns.empty:
        raise ValueError("The log-return matrix is empty after cleaning.")
    return returns


def summarize_returns(log_returns: pd.DataFrame) -> pd.DataFrame:
    """Return the requested compact descriptive-statistics table."""
    summary = log_returns.agg(["count", "mean", "std", "min", "max"]).T
    return summary.rename(
        columns={
            "count": "observation_count",
            "mean": "mean_daily_return",
            "std": "standard_deviation",
            "min": "minimum_return",
            "max": "maximum_return",
        }
    )

