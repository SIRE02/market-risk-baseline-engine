"""Offline integration tests for the complete configured analysis workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from market_risk_baseline import cli
from market_risk_baseline.config import AnalysisConfig
from market_risk_baseline.data_loader import MarketDataError

EXPECTED_CSV_ARTIFACTS = {
    "adjusted_prices.csv",
    "simple_returns.csv",
    "log_returns.csv",
    "return_summary.csv",
    "volatility_summary.csv",
    "rolling_volatility.csv",
    "covariance_matrix.csv",
    "correlation_matrix.csv",
    "rolling_covariance.csv",
    "rolling_correlation.csv",
    "rolling_volatility.png",
    "correlation_heatmap.png",
    "data_quality_report.json",
    "run_manifest.json",
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


def _write_canonical_csv(prices: pd.DataFrame, path: Path) -> None:
    frame = prices.copy()
    frame.index.name = "date"
    frame.reset_index().melt(
        id_vars="date", var_name="ticker", value_name="adjusted_close"
    ).to_csv(path, index=False)


def test_complete_csv_analysis_writes_reports_and_source_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prices: pd.DataFrame
) -> None:
    csv_path = tmp_path / "prices.csv"
    output_dir = tmp_path / "outputs"
    _write_canonical_csv(prices, csv_path)
    config = AnalysisConfig(
        provider="csv",
        csv_path=csv_path,
        output_dir=output_dir,
        tickers=tuple(prices.columns),
        start_date="2024-01-01",
        end_date="2024-02-01",
        rolling_window=3,
    )
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

    cli.run_analysis(config)

    assert {path.name for path in output_dir.iterdir()} == EXPECTED_CSV_ARTIFACTS
    correlations = pd.read_csv(output_dir / "correlation_matrix.csv", index_col=0)
    assert list(correlations.columns) == list(prices.columns)
    manifest = json.loads((output_dir / "run_manifest.json").read_text())
    assert manifest["data_source"]["provider"] == "csv"
    assert manifest["data_source"]["source"] == str(csv_path.resolve())
    assert manifest["data_source"]["observation_count"] == len(prices)
    assert (
        manifest["estimation_conventions"]["sample_estimators"]["covariance_ddof"] == 1
    )
    assert (
        manifest["estimation_conventions"]["rolling"]["future_observations_used"]
        is False
    )
    distribution = manifest["estimation_conventions"]["return_distribution"]
    assert distribution["quantiles"] == [0.05, 0.25, 0.75, 0.95]
    assert distribution["quantile_method"] == "linear"
    assert distribution["downside_deviation"] == {
        "target": 0.0,
        "target_return_type": "daily_log_return",
        "denominator": "all_non_missing_observations",
        "formula": "sqrt(sum(min(return - target, 0)^2) / n)",
        "annualized": False,
    }
    summary = pd.read_csv(output_dir / "return_summary.csv", index_col=0)
    assert {
        "median_return",
        "quantile_0.05",
        "quantile_0.25",
        "quantile_0.75",
        "quantile_0.95",
        "sample_skewness",
        "sample_excess_kurtosis",
        "downside_deviation",
    }.issubset(summary.columns)
    assert "data_quality_report.json" in manifest["generated_artifacts"]


def test_cli_arguments_override_configuration_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "analysis.toml"
    config_path.write_text(
        """[analysis]
provider = "yahoo"
tickers = ["SPY", "QQQ"]
start_date = "2023-01-01"
end_date = "2024-01-01"
rolling_window = 10
""",
        encoding="utf-8",
    )
    captured: list[AnalysisConfig] = []
    monkeypatch.setattr(cli, "run_analysis", captured.append)

    cli.main(
        [
            "--config",
            str(config_path),
            "--tickers",
            "GLD,TLT",
            "--rolling-window",
            "5",
            "--rolling-min-observations",
            "3",
            "--observations-per-year",
            "260",
            "--quantiles",
            "0.1,0.5",
            "0.9",
            "--quantile-method",
            "nearest",
            "--downside-target",
            "-0.001",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert captured[0].tickers == ("GLD", "TLT")
    assert captured[0].rolling_window == 5
    assert captured[0].rolling_min_observations == 3
    assert captured[0].observations_per_year == 260
    assert captured[0].quantiles == (0.1, 0.5, 0.9)
    assert captured[0].quantile_method == "nearest"
    assert captured[0].downside_target == pytest.approx(-0.001)
    assert captured[0].start_date == "2023-01-01"


def test_cli_converts_expected_failures_to_exit_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_config: AnalysisConfig) -> None:
        raise MarketDataError("provider unavailable")

    monkeypatch.setattr(cli, "run_analysis", fail)

    with pytest.raises(SystemExit, match="Analysis failed: provider unavailable"):
        cli.main([])
