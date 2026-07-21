# Market-Risk-Baseline-Engine

A Python pipeline that validates adjusted daily prices from Yahoo Finance or a local CSV and produces return-distribution, volatility, covariance, and Pearson-correlation estimates using explicit statistical conventions.

## Project status and roadmap

Version `0.2.0` completes the installable asset-level quantitative foundation.
Phase 3 adds the explicit portfolio contract, valuation, cash, and exposure layer
without introducing VaR, forecasting models, or machine learning. The complete
scope, phase order, conventions, and exit gates are defined in the
[`market-risk-baseline-engine.md`](docs/market-risk-baseline-engine.md).

## What it produces

Running the installed `market-risk-baseline` command creates these files in `outputs/`:

- `adjusted_prices.csv`
- `simple_returns.csv`
- `log_returns.csv`
- `return_summary.csv`
- `volatility_summary.csv`
- `rolling_volatility.csv`
- `covariance_matrix.csv`
- `rolling_covariance.csv`
- `rolling_volatility.png`
- `correlation_matrix.csv`
- `rolling_correlation.csv`
- `correlation_heatmap.png`
- `data_quality_report.json`
- `run_manifest.json`

Yahoo runs also save the normalized, requested, in-range records to `acquired_adjusted_prices.csv` before complete-case alignment. The canonical CSV therefore preserves disclosed missing observations and can be selected explicitly in a later offline run. The engine never silently falls back from Yahoo to a local file or cache.

Every provider passes through the same normalization, date filtering, positive-price validation, and complete-case alignment pipeline. Dates with missing observations in any selected asset are dropped, and prices are never forward-filled. Until the Phase 3 market-calendar contract exists, a run fails if complete-case alignment would make two retained rows nonconsecutive within the provider's observed-date union; such a price relative must not be mislabeled as a daily return.

## Setup with Conda

The environment is named `market-risk-baseline-engine`:

```powershell
conda env create -f environment.yml
conda activate market-risk-baseline-engine
python -m pip install -e .
```

If the environment already exists, synchronize it with:

```powershell
conda env update -n market-risk-baseline-engine -f environment.yml --prune
python -m pip install -e .
```

## Configure and run

Version `0.2.0` accepts a TOML or JSON configuration file. Copy `config.example.toml`, edit it without changing application source, and run:

```powershell
conda run -n market-risk-baseline-engine market-risk-baseline --config config.example.toml
```

Command-line values override file values:

```powershell
conda run -n market-risk-baseline-engine market-risk-baseline `
  --config config.example.toml `
  --tickers SPY QQQ TLT GLD `
  --start-date 2021-01-01 `
  --end-date 2025-01-01 `
  --rolling-window 30 `
  --rolling-min-observations 20 `
  --observations-per-year 252 `
  --quantiles 0.05 0.25 0.75 0.95 `
  --quantile-method linear `
  --downside-target 0.0 `
  --output-dir outputs/alternate
```

Run `market-risk-baseline --help` for every option. Supported keys are `provider`, `tickers`, `start_date`, `end_date`, `rolling_window`, `rolling_min_observations`, `observations_per_year`, `quantiles`, `quantile_method`, `downside_target`, `output_dir`, and `csv_path`. TOML may put them under `[analysis]`; JSON uses a top-level object (or an `analysis` object). Command-line overrides have highest priority, followed by the file and built-in defaults.

Both providers treat `end_date` as exclusive. For example, `2025-01-01` includes observations before January 1, 2025, but not that date.

## Offline CSV input

CSV is a first-class provider. Select it explicitly; there is no automatic fallback:

```powershell
conda run -n market-risk-baseline-engine market-risk-baseline `
  --provider csv `
  --csv-path data/adjusted_prices.csv `
  --tickers SPY QQQ TLT GLD `
  --start-date 2021-01-01 `
  --end-date 2025-01-01
```

The canonical CSV is long-form and must have these required columns (additional columns are ignored):

| Column | Requirement |
| --- | --- |
| `date` | A parseable date; selected rows satisfy `start_date <= date < end_date`. |
| `ticker` | Instrument symbol, normalized to trimmed uppercase. |
| `adjusted_close` | Numeric split- and distribution-adjusted close greater than zero. |

```csv
date,ticker,adjusted_close
2024-01-02,SPY,472.318
2024-01-02,QQQ,401.992
2024-01-03,SPY,476.131
2024-01-03,QQQ,405.274
```

Adjusted prices are used so stock splits and cash distributions do not appear as ordinary market gains or losses in the return series. Do not put raw closes in `adjusted_close`: the engine cannot infer or reconstruct split/dividend adjustments and deliberately refuses Yahoo responses without `Adj Close`. The exact adjustment remains provider-defined.

Duplicate date/ticker rows keep the last source row and are disclosed. Missing, nonnumeric, zero, and negative prices are never filled; invalid observations are removed before complete-case alignment. In particular, forward-filling would invent a stale price observation, suppress that asset's measured return, and potentially distort cross-asset dependence. If an interior missing observation would make the aligned matrix span another provider observation date, the run fails instead of treating the resulting multi-observation price relative as daily. A run needs at least `rolling_min_observations + 1` common adjusted-price observations so the price series yields the configured minimum number of returns.

`outputs/acquired_adjusted_prices.csv` from a successful Yahoo run follows this schema and preserves the normalized pre-alignment records. It can be passed later with `--provider csv --csv-path ...`.

## Data quality and lineage

`data_quality_report.json` records requested and returned instruments, actual first and last common dates, per-instrument observation counts, duplicate date/instrument rows, invalid prices, and the reduction caused by common-history alignment. `missing_adjusted_close_values` is scoped to requested, in-range, deduplicated records; `source_missing_adjusted_close_values` separately records missing values in the provider-normalized source before scope filters.

`run_manifest.json` records the package version, Git commit when available, execution timestamp, complete effective configuration, actual provider and source, acquisition/read time, actual input range, instruments, dependency versions, generated artifacts, and machine-readable estimation conventions. A CSV run records the resolved source path and file modification time. These files describe the data actually analyzed, not merely what was requested.

## Yahoo and yfinance limitations

The Yahoo adapter pins `yfinance` and explicitly requests `Adj Close` with `auto_adjust=False`. Adjusted values are vendor-supplied; their adjustment methodology, correction timing, completeness, and corporate-action treatment are not independently reconstructed or guaranteed here. Provider availability, response shape, rate limits, and historical values can change, so reproducible work should retain the emitted canonical acquisition and manifest.

`yfinance` is an independent open-source project and is not affiliated with, endorsed by, or vetted by Yahoo. Its project page describes the tool as intended for research/education and Yahoo Finance access as personal-use oriented. Users remain responsible for determining whether downloading, storing, and redistributing data is permitted for their use case under the [yfinance project notice](https://pypi.org/project/yfinance/) and [Yahoo API terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html). The software and downloaded market data have separate licensing considerations.

## Tests

The automated tests use deterministic synthetic prices and saved provider-shaped responses; they do not require network access. Calculation tests call the return, dependence, and risk estimators without providers or file output, while provider and reporting tests exercise I/O separately. The suite includes Yahoo/CSV equivalence, hand-calculated covariance, symmetry and positive-semidefinite checks, rolling boundary and no-look-ahead checks, constant-series behavior, quality-report checks, a wheel build, isolated-target installation, installed-CLI execution, package import, entry-point checks, and an offline complete-analysis test:

```powershell
conda run -n market-risk-baseline-engine python -m pytest -q
```

They verify hand-calculated median, quantile, skewness, excess-kurtosis, and downside-deviation fixtures; return and dependence invariants; rolling no-look-ahead behavior; complete-case alignment; and clear failures for invalid configuration or insufficient samples.

Install the development tools and run the same checks enforced by CI with:

```powershell
python -m pip install -e ".[dev]"
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m pytest -q
python -m build
```

## Estimation conventions

| Output or metric | Return input | Estimator and scaling |
| --- | --- | --- |
| `simple_returns.csv` | Adjusted prices | `P(t) / P(t-1) - 1`; reported as a separate transformation, not used by the current estimators. |
| Log returns and basic return summary | Adjusted prices / daily log returns | `log(P(t) / P(t-1))`; mean uses the available sample, median is the middle order statistic, and standard deviation is sample-based with `ddof=1`. |
| Empirical quantiles | Daily log returns | Configurable probabilities, defaulting to 5%, 25%, 75%, and 95%; `linear` interpolation by default. `lower`, `higher`, `midpoint`, and `nearest` are also supported. |
| Skewness | Daily log returns | Bias-corrected Fisher-Pearson sample skewness, requiring at least three observations. |
| Excess kurtosis | Daily log returns | Bias-corrected Fisher excess kurtosis, where a normal distribution has value zero, requiring at least four observations. |
| Downside deviation | Daily log returns | `sqrt(sum(min(r - target, 0)^2) / n)`, where `n` counts all non-missing returns. The daily log-return target defaults to zero; the result is daily and is not annualized. |
| Daily volatility | Log returns | Sample standard deviation with `ddof=1`. |
| Annualized volatility | Log returns | Daily sample volatility multiplied by `sqrt(observations_per_year)`. |
| Covariance matrix | Complete-case log returns | Daily sample covariance with `ddof=1`; it is not annualized. |
| Pearson correlation | Complete-case log returns | Sample-centered Pearson correlation. It is undefined (`NaN`) for a constant series. |
| Rolling volatility/covariance/correlation | Log returns | The same estimator as its full-sample counterpart over a trailing window. |

No standard-deviation or covariance output uses a population estimator (`ddof=0`). Downside deviation deliberately uses all non-missing observations in its denominator, not only observations below the target. `observations_per_year` defaults to 252 and is configurable; it affects volatility annualization only. Square-root-of-time annualization is a baseline approximation, not a universal law.

Because every return summary includes both skewness and excess kurtosis, the summary fails explicitly unless every instrument has at least four non-missing log-return observations; it never emits silent insufficient-sample `NaN` values for those fields. The run manifest records this combined-summary minimum separately from the mathematically correct per-estimator minima of three observations for skewness and four for excess kurtosis.

Rolling windows are backward-looking, include the current observation, and never use future rows. `rolling_min_observations` defaults to `rolling_window`, which leaves the first `window - 1` estimates as `NaN`. If the configured minimum is smaller than the window, estimates begin at that minimum using an incomplete trailing window. At least two observations are required, the minimum cannot exceed the window, and a sample shorter than the minimum fails explicitly.

Cross-asset covariance and correlation use complete-case alignment: a date is retained only when every selected asset has a valid price. Retained rows must also be consecutive within the union of provider observation dates, preventing an interior missing observation from creating a multi-observation return labeled daily. This provides one consistent sample for every pair, but it can shorten the history and create selection effects when missingness is systematic; the quality report discloses the reduction. Rolling covariance and correlation CSVs use `(date, ticker)` row keys and one column per paired ticker. The quantile probabilities and method, skewness and kurtosis bias conventions, and complete downside-deviation definition are repeated in every `run_manifest.json`. Correlation describes linear comovement, does not establish causation, and can change across sample periods. All return-distribution and dependence outputs are historical sample descriptions rather than forecasts.

## Error handling

The program reports invalid configuration, date ranges, output/source paths, rolling windows and minimum observations, annualization settings, quantile probabilities or methods, downside targets, CSV schemas, missing adjusted-price fields, empty provider responses, temporary download failures, invalid tickers, gap-spanning aligned intervals, insufficient common history, and insufficient return samples with readable messages.

The next releases extend the baseline into explicit portfolio valuation,
historical portfolio P&L, simple-return covariance aggregation, transparent
historical and normal VaR/Expected Shortfall, deterministic stress testing, and
baseline risk-model validation. Conditional forecasting models, expected-return
or price prediction, portfolio optimization, machine learning, deep learning,
live feeds, and automated trading remain outside this repository.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
