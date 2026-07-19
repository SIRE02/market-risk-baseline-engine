"""Configuration loading and validation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from market_risk_baseline.config import AnalysisConfig, load_configuration


def test_json_configuration_is_normalized_and_overridden(tmp_path: Path) -> None:
    config_path = tmp_path / "analysis.json"
    config_path.write_text(
        json.dumps(
            {
                "provider": "yahoo",
                "tickers": [" spy ", "QQQ", "spy"],
                "start_date": "2023-01-01",
                "end_date": "2024-01-01",
                "rolling_window": 20,
            }
        ),
        encoding="utf-8",
    )
    config = load_configuration(config_path, {"rolling_window": 5})
    assert config.tickers == ("SPY", "QQQ")
    assert config.rolling_window == 5


def test_csv_configuration_requires_an_existing_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="CSV_PATH is required"):
        AnalysisConfig(provider="csv", tickers=("AAA", "BBB"))
    with pytest.raises(ValueError, match="readable file"):
        AnalysisConfig(
            provider="csv",
            csv_path=tmp_path / "missing.csv",
            tickers=("AAA", "BBB"),
        )


def test_unknown_options_and_invalid_core_values_fail_early(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.json"
    config_path.write_text('{"mystery": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown configuration"):
        load_configuration(config_path)
    with pytest.raises(ValueError, match="earlier"):
        AnalysisConfig(
            tickers=("AAA", "BBB"),
            start_date="2025-01-01",
            end_date="2024-01-01",
        )
    with pytest.raises(ValueError, match="TRADING_DAYS"):
        AnalysisConfig(tickers=("AAA", "BBB"), trading_days=0)
