"""Single entry point for the Quantitative Market Baseline Engine."""

from __future__ import annotations
from pathlib import Path
from correlation import correlation_matrix, extreme_correlation_pairs
from data_loader import MarketDataError, download_adjusted_prices
from returns import calculate_log_returns, calculate_simple_returns, summarize_returns
from risk_metrics import rolling_volatility, volatility_summary
from visualizations import plot_correlation_heatmap, plot_rolling_volatility

# Change the entire analysis universe and horizon in this one configuration section.
TICKERS = ["SPY", "QQQ", "TLT", "GLD"]
START_DATE = "2020-01-01"
END_DATE = "2025-01-01"
ROLLING_WINDOW = 21
TRADING_DAYS = 252
OUTPUT_DIR = Path("outputs")


def run_analysis() -> None:
    """Run the complete baseline analysis and save all required outputs."""
    print(f"Downloading adjusted prices for {', '.join(TICKERS)}...")
    prices = download_adjusted_prices(TICKERS, START_DATE, END_DATE, ROLLING_WINDOW)
    simple_returns = calculate_simple_returns(prices)
    log_returns = calculate_log_returns(prices)
    return_summary = summarize_returns(log_returns)
    vol_summary = volatility_summary(log_returns, TRADING_DAYS)
    rolling = rolling_volatility(log_returns, ROLLING_WINDOW, TRADING_DAYS)
    correlations = correlation_matrix(log_returns)
    highest, lowest = extreme_correlation_pairs(correlations)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prices.to_csv(OUTPUT_DIR / "adjusted_prices.csv", index_label="date")
    simple_returns.to_csv(OUTPUT_DIR / "simple_returns.csv", index_label="date")
    log_returns.to_csv(OUTPUT_DIR / "log_returns.csv", index_label="date")
    return_summary.to_csv(OUTPUT_DIR / "return_summary.csv")
    vol_summary.to_csv(OUTPUT_DIR / "volatility_summary.csv")
    rolling.to_csv(OUTPUT_DIR / "rolling_volatility.csv", index_label="date")
    correlations.to_csv(OUTPUT_DIR / "correlation_matrix.csv")
    plot_rolling_volatility(
        rolling, OUTPUT_DIR / "rolling_volatility.png", ROLLING_WINDOW
    )
    plot_correlation_heatmap(correlations, OUTPUT_DIR / "correlation_heatmap.png")

    print("\nDaily and annualized volatility:")
    print(vol_summary.to_string(float_format=lambda value: f"{value:.4f}"))
    print("\nPearson correlation matrix:")
    print(correlations.to_string(float_format=lambda value: f"{value:.3f}"))
    print(f"\nHighest pair: {highest[0]} / {highest[1]} ({highest[2]:.3f})")
    print(f"Lowest pair:  {lowest[0]} / {lowest[1]} ({lowest[2]:.3f})")
    print(f"\nSaved tables and charts to: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    try:
        run_analysis()
    except (MarketDataError, ValueError) as exc:
        raise SystemExit(f"Analysis failed: {exc}") from exc