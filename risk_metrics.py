"""Daily, annualized, and rolling volatility calculations."""

from __future__ import annotations
import numpy as np
import pandas as pd


def _validate_trading_days(trading_days: int) -> None:
    if isinstance(trading_days, bool) or not isinstance(trading_days, int) or trading_days <= 0:
        raise ValueError("TRADING_DAYS must be a positive integer.")


def volatility_summary(log_returns: pd.DataFrame, trading_days: int = 252) -> pd.DataFrame:
    """Calculate sample daily volatility and square-root-of-time annualization."""
    if log_returns.empty:
        raise ValueError("Log returns are required for volatility calculations.")
    _validate_trading_days(trading_days)
    daily = log_returns.std(ddof=1)
    annualized = daily * np.sqrt(trading_days)
    return pd.DataFrame(
        {"daily_volatility": daily, "annualized_volatility": annualized}
    ).rename_axis("ticker")


def rolling_volatility(
    log_returns: pd.DataFrame,
    rolling_window: int = 21,
    trading_days: int = 252,
) -> pd.DataFrame:
    """Calculate annualized rolling sample volatility for each asset."""
    _validate_trading_days(trading_days)
    if isinstance(rolling_window, bool) or not isinstance(rolling_window, int):
        raise ValueError("ROLLING_WINDOW must be a positive integer.")
    if rolling_window <= 0:
        raise ValueError("ROLLING_WINDOW must be a positive integer.")
    if rolling_window >= len(log_returns):
        raise ValueError(
            f"ROLLING_WINDOW ({rolling_window}) must be smaller than the available "
            f"return sample ({len(log_returns)})."
        )
    rolling = log_returns.rolling(window=rolling_window).std(ddof=1)
    return rolling * np.sqrt(trading_days)

