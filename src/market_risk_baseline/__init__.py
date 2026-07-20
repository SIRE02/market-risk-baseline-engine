"""Market Risk Baseline Engine package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("market-risk-baseline-engine")
except PackageNotFoundError:
    # The fallback supports direct source-tree use before installation.
    __version__ = "0.2.0"

__all__ = ["__version__"]
