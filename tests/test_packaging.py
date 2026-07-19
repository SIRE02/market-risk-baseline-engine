"""Build and clean-target installation checks for the distributable package."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_wheel_builds_and_imports_outside_the_source_tree(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    project_copy = tmp_path / "project"
    wheel_directory = tmp_path / "wheel"
    install_directory = tmp_path / "installed"
    wheel_directory.mkdir()
    project_copy.mkdir()
    for filename in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(repository_root / filename, project_copy / filename)
    shutil.copytree(
        repository_root / "src",
        project_copy / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(project_copy),
            "--no-deps",
            "--no-build-isolation",
            "--no-cache-dir",
            "--wheel-dir",
            str(wheel_directory),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(wheel_directory.glob("market_risk_baseline_engine-0.1.3-*.whl"))
    assert len(wheels) == 1

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            str(wheels[0]),
            "--no-deps",
            "--no-cache-dir",
            "--target",
            str(install_directory),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(install_directory)
    import_result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from importlib.metadata import distribution; "
                "import market_risk_baseline; "
                "dist = distribution('market-risk-baseline-engine'); "
                "entry_point = next(ep for ep in dist.entry_points "
                "if ep.group == 'console_scripts' and ep.name == 'market-risk-baseline'); "
                "assert market_risk_baseline.__version__ == dist.version == '0.1.3'; "
                "assert callable(entry_point.load())"
            ),
        ],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert import_result.returncode == 0, import_result.stderr

    installed_tests = tmp_path / "installed_tests"
    nested_pytest_temp = tmp_path / "nested_pytest_temp"
    installed_tests.mkdir()
    for filename in (
        "test_config.py",
        "test_data_loader.py",
        "test_dependence.py",
        "test_metrics.py",
        "test_providers.py",
        "test_cli.py",
    ):
        shutil.copy2(repository_root / "tests" / filename, installed_tests / filename)
    test_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(nested_pytest_temp),
            str(installed_tests),
        ],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert test_result.returncode == 0, test_result.stdout + test_result.stderr
