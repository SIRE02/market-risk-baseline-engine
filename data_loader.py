"""Download and clean adjusted daily market prices."""

from __future__ import annotations
from collections.abc import Sequence
from datetime import date
import pandas as pd
import yfinance as yf


class MarketDataError(RuntimeError):
    """Raised when usable adjusted-price data cannot be obtained."""


def validate_configuration(
    tickers: Sequence[str],
    start_date: str,
    end_date: str,
    rolling_window: int,
) -> list[str]:
    """Validate user inputs and return normalized, unique ticker symbols."""
    if isinstance(tickers, (str, bytes)):
        raise ValueError("TICKERS must be a sequence containing at least two symbols.")

    normalized = list(dict.fromkeys(str(ticker).strip().upper() for ticker in tickers))
    normalized = [ticker for ticker in normalized if ticker]

    if len(normalized) < 2:
        raise ValueError("At least two unique ticker symbols are required.")

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("START_DATE and END_DATE must use YYYY-MM-DD format.") from exc

    if start >= end:
        raise ValueError("START_DATE must be earlier than END_DATE.")
    if isinstance(rolling_window, bool) or not isinstance(rolling_window, int):
        raise ValueError("ROLLING_WINDOW must be a positive integer.")
    if rolling_window <= 0:
        raise ValueError("ROLLING_WINDOW must be a positive integer.")
    return normalized


def _extract_adjusted_close(raw: pd.DataFrame, tickers: Sequence[str]) -> pd.DataFrame:
    """Extract only the vendor's adjusted-close field from a yfinance response."""
    if raw.empty:
        raise MarketDataError("The market-data provider returned an empty response.")

    if isinstance(raw.columns, pd.MultiIndex):
        for level in range(raw.columns.nlevels):
            values = raw.columns.get_level_values(level)
            if "Adj Close" in values:
                adjusted = raw.xs("Adj Close", axis=1, level=level, drop_level=True)
                break
        else:
            raise MarketDataError(
                "Adjusted Close is unavailable. Raw Close will not be used as a fallback."
            )
    else:
        if "Adj Close" not in raw.columns:
            raise MarketDataError(
                "Adjusted Close is unavailable. Raw Close will not be used as a fallback."
            )
        adjusted = raw.loc[:, ["Adj Close"]].copy()
        if len(tickers) != 1:
            raise MarketDataError("The provider response did not identify every requested ticker.")
        adjusted.columns = [tickers[0]]

    if isinstance(adjusted, pd.Series):
        adjusted = adjusted.to_frame(name=tickers[0])
    adjusted.columns = [str(column).upper() for column in adjusted.columns]
    return adjusted.reindex(columns=list(tickers))


def clean_adjusted_prices(
    adjusted_prices: pd.DataFrame,
    tickers: Sequence[str],
    rolling_window: int,
) -> pd.DataFrame:
    """Normalize, align, and validate adjusted prices without forward filling."""
    prices = adjusted_prices.copy()
    prices.index = pd.to_datetime(prices.index, errors="coerce")
    prices = prices.loc[~prices.index.isna()]
    prices = prices.loc[~prices.index.duplicated(keep="last")].sort_index()
    prices = prices.apply(pd.to_numeric, errors="coerce")

    missing_tickers = [ticker for ticker in tickers if ticker not in prices.columns]
    empty_tickers = [ticker for ticker in tickers if ticker in prices and prices[ticker].dropna().empty]
    unusable = missing_tickers + empty_tickers
    if unusable:
        symbols = ", ".join(dict.fromkeys(unusable))
        raise MarketDataError(f"No usable adjusted-price data was returned for: {symbols}.")

    prices = prices.loc[:, list(tickers)]
    # Complete-case alignment is explicit: missing dates are removed, never filled.
    prices = prices.dropna(how="any")
    prices = prices.where(prices > 0).dropna(how="any")
    minimum_prices = rolling_window + 2
    if len(prices) < minimum_prices:
        raise MarketDataError(
            "Insufficient common price history: "
            f"need at least {minimum_prices} aligned prices for a {rolling_window}-day "
            f"window, but received {len(prices)}."
        )
    return prices


def download_adjusted_prices(
    tickers: Sequence[str],
    start_date: str,
    end_date: str,
    rolling_window: int,
) -> pd.DataFrame:
    """Download adjusted closes and return a clean, common-date price matrix."""
    symbols = validate_configuration(tickers, start_date, end_date, rolling_window)
    try:
        raw = yf.download(
            tickers=symbols,
            start=start_date,
            end=end_date,
            auto_adjust=False,
            actions=False,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception as exc:  # yfinance exposes several backend-specific errors
        raise MarketDataError(f"Market-data download failed: {exc}") from exc

    adjusted = _extract_adjusted_close(raw, symbols)
    return clean_adjusted_prices(adjusted, symbols, rolling_window)
