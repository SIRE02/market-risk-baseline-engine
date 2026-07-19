"""Central statistical conventions shared by analytical estimators."""

from __future__ import annotations

from typing import Any


DEFAULT_OBSERVATIONS_PER_YEAR = 252
DEFAULT_ROLLING_WINDOW = 21
SAMPLE_DDOF = 1
MINIMUM_SAMPLE_OBSERVATIONS = SAMPLE_DDOF + 1


def validate_positive_integer(value: object, name: str) -> int:
    """Return a validated positive integer parameter."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def resolve_rolling_min_observations(
    rolling_window: int,
    rolling_min_observations: int | None,
) -> int:
    """Validate a trailing window and resolve its minimum sample size."""
    window = validate_positive_integer(rolling_window, "ROLLING_WINDOW")
    minimum = window if rolling_min_observations is None else rolling_min_observations
    validate_positive_integer(minimum, "ROLLING_MIN_OBSERVATIONS")
    if minimum < MINIMUM_SAMPLE_OBSERVATIONS:
        raise ValueError(
            "ROLLING_MIN_OBSERVATIONS must be at least 2 for sample estimators."
        )
    if minimum > window:
        raise ValueError(
            "ROLLING_MIN_OBSERVATIONS must not exceed ROLLING_WINDOW."
        )
    return minimum


def validate_rolling_sample(
    sample_size: int,
    rolling_window: int,
    rolling_min_observations: int | None,
) -> int:
    """Validate rolling parameters and ensure the sample can meet the minimum."""
    minimum = resolve_rolling_min_observations(
        rolling_window, rolling_min_observations
    )
    if sample_size < minimum:
        raise ValueError(
            "Insufficient return observations for rolling estimation: "
            f"need at least {minimum}, but received {sample_size}."
        )
    return minimum


def estimation_conventions(
    observations_per_year: int,
    rolling_window: int,
    rolling_min_observations: int,
) -> dict[str, Any]:
    """Return machine-readable conventions for run manifests."""
    return {
        "return_input": {
            "simple_returns": "reported as a separate output only",
            "log_returns": [
                "return_summary",
                "volatility",
                "covariance",
                "pearson_correlation",
            ],
        },
        "sample_estimators": {
            "standard_deviation_ddof": SAMPLE_DDOF,
            "covariance_ddof": SAMPLE_DDOF,
            "pearson_correlation": "sample-centered; undefined for constant series",
        },
        "annualization": {
            "observations_per_year": observations_per_year,
            "volatility_scaling": "square_root_of_time",
            "covariance_output": "daily_not_annualized",
        },
        "rolling": {
            "orientation": "trailing_including_current_observation",
            "window": rolling_window,
            "minimum_observations": rolling_min_observations,
            "initial_values": (
                "NaN until minimum_observations; partial trailing windows are "
                "estimated thereafter when minimum_observations < window"
            ),
            "future_observations_used": False,
        },
        "missing_data": "complete_case_for_cross_asset_dependence",
    }
