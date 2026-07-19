"""Offline integration tests for the complete Phase 1 analysis workflow."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from market_risk_baseline import cli
from market_risk_baseline.data_loader import MarketDataError


EXPECTED_ARTIFACTS = {
    "adjusted_prices.csv",
    "simple_returns.csv",
    "log_returns.csv",
    "return_summary.csv",
    "volatility_summary.csv",
    "rolling_volatility.csv",
    "correlation_matrix.csv",
    "rolling_volatility.png",
    "correlation_heatmap.png",
}


@pytest.fixture
def prices() -> pd.DataFrame:
    index = pd.date_range("2024-01-02", periods=8, freq="B")
    return pd.DataFrame(
        {
            "SPY": [100, 102, 101, 104, 106, 105, 108, 110],
            "QQQ": [50, 49, 51, 52, 51, 53, 54, 55],
            "TLT": [80, 81, 82, 81, 83, 84, 86, 85],
            "GLD": [120, 121, 119, 122, 123, 125, 124, 127],
        },
        index=index,
    )


def test_complete_analysis_writes_phase_1_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prices: pd.DataFrame
) -> None:
    output_dir = tmp_path / "outputs"
    monkeypatch.setattr(cli, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(cli, "ROLLING_WINDOW", 3)
    monkeypatch.setattr(cli, "download_adjusted_prices", lambda *_args: prices)
    monkeypatch.setattr(
        cli,
        "plot_rolling_volatility",
        lambda _data, path, _window: path.write_bytes(b"test chart"),
    )
    monkeypatch.setattr(
        cli,
        "plot_correlation_heatmap",
        lambda _data, path: path.write_bytes(b"test chart"),
    )

    cli.run_analysis()

    assert {path.name for path in output_dir.iterdir()} == EXPECTED_ARTIFACTS
    correlations = pd.read_csv(output_dir / "correlation_matrix.csv", index_col=0)
    assert list(correlations.columns) == list(prices.columns)


def test_cli_converts_expected_failures_to_exit_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> None:
        raise MarketDataError("provider unavailable")

    monkeypatch.setattr(cli, "run_analysis", fail)

    with pytest.raises(SystemExit, match="Analysis failed: provider unavailable"):
        cli.main()
