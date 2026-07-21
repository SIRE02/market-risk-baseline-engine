"""Run-lineage manifest generation."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from market_risk_baseline import __version__
from market_risk_baseline.config import AnalysisConfig
from market_risk_baseline.data_loader import MarketDataResult
from market_risk_baseline.estimation import estimation_conventions


def _dependency_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for dependency in ("numpy", "pandas", "matplotlib", "seaborn", "yfinance"):
        try:
            result[dependency] = version(dependency)
        except PackageNotFoundError:
            result[dependency] = "not-installed"
    return result


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def build_run_manifest(
    config: AnalysisConfig,
    market_data: MarketDataResult,
    artifacts: list[str],
) -> dict[str, Any]:
    """Build the reproducibility and source-lineage record for a completed run."""
    quality = market_data.quality_report
    rolling_minimum = config.rolling_min_observations
    # AnalysisConfig resolves this during validation.
    assert rolling_minimum is not None
    return {
        "project": "market-risk-baseline-engine",
        "project_version": __version__,
        "git_commit": _git_commit(),
        "execution_timestamp": datetime.now(UTC).isoformat(),
        "configuration": config.to_dict(),
        "estimation_conventions": estimation_conventions(
            config.observations_per_year,
            config.rolling_window,
            rolling_minimum,
            config.quantiles,
            config.quantile_method,
            config.downside_target,
        ),
        "data_source": {
            "provider": market_data.payload.provider,
            "source": market_data.payload.source,
            "acquired_at": market_data.payload.acquired_at,
            "provider_metadata": market_data.payload.metadata,
            "actual_start_date": quality["first_common_date"],
            "actual_end_date": quality["last_common_date"],
            "observation_count": quality["common_date_count_after_alignment"],
            "instruments": list(market_data.prices.columns),
            "canonical_record_stage": (
                "normalized_requested_in_range_pre_complete_case_alignment"
            ),
        },
        "dependency_versions": _dependency_versions(),
        "generated_artifacts": sorted(artifacts),
    }


def persist_run_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Write a deterministic, human-readable JSON manifest."""
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
