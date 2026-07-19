# Market-Risk-Baseline-Engine

A Python pipeline that validates adjusted daily prices from Yahoo Finance or a local CSV and produces return-distribution, volatility, covariance, and Pearson-correlation estimates using explicit statistical conventions.

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

Yahoo runs also save `acquired_adjusted_prices.csv` in the canonical CSV schema so it can be selected explicitly in a later offline run. The engine never silently falls back from Yahoo to a local file or cache.

Every provider passes through the same normalization, date filtering, positive-price validation, and complete-case alignment pipeline. Dates with missing observations in any selected asset are dropped, and prices are never forward-filled.

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

Version `0.1.4` accepts a TOML or JSON configuration file. Copy `config.example.toml`, edit it without changing application source, and run:

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

Do not put raw closes in `adjusted_close`. The engine cannot infer or reconstruct split/dividend adjustments and deliberately refuses Yahoo responses without `Adj Close`. Duplicate date/ticker rows keep the last source row and are disclosed. Missing, nonnumeric, zero, and negative prices are never filled; invalid observations are removed before complete-case alignment. A run needs at least `rolling_min_observations + 1` common adjusted-price observations so the price series yields the configured minimum number of returns.

`outputs/acquired_adjusted_prices.csv` from a successful Yahoo run follows this schema and can be passed later with `--provider csv --csv-path ...`.

## Data quality and lineage

`data_quality_report.json` records requested and returned instruments, actual first and last common dates, per-instrument observation counts, missing values, duplicate date/instrument rows, invalid prices, and the reduction caused by common-history alignment.

`run_manifest.json` records the package version, Git commit when available, execution timestamp, complete effective configuration, actual provider and source, acquisition/read time, actual input range, instruments, dependency versions, generated artifacts, and machine-readable estimation conventions. A CSV run records the resolved source path and file modification time. These files describe the data actually analyzed, not merely what was requested.

## Yahoo and yfinance limitations

The Yahoo adapter pins `yfinance` and explicitly requests `Adj Close` with `auto_adjust=False`. Adjusted values are vendor-supplied; their adjustment methodology, correction timing, completeness, and corporate-action treatment are not independently reconstructed or guaranteed here. Provider availability, response shape, rate limits, and historical values can change, so reproducible work should retain the emitted canonical acquisition and manifest.

`yfinance` is an independent open-source project and is not affiliated with, endorsed by, or vetted by Yahoo. Its project page describes the tool as intended for research/education and Yahoo Finance access as personal-use oriented. Users remain responsible for determining whether downloading, storing, and redistributing data is permitted for their use case under the [yfinance project notice](https://pypi.org/project/yfinance/) and [Yahoo API terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html). The software and downloaded market data have separate licensing considerations.

## Tests

The automated tests use deterministic synthetic prices and saved provider-shaped responses; they do not require network access. They include Yahoo/CSV equivalence, hand-calculated covariance, symmetry and positive-semidefinite checks, rolling boundary and no-look-ahead checks, constant-series behavior, quality-report checks, a wheel build, isolated-target installation, package import, entry-point check, and an offline complete-analysis test:

```powershell
conda run -n market-risk-baseline-engine python -m pytest -q
```

They verify hand-calculated median, quantile, skewness, excess-kurtosis, and downside-deviation fixtures; return and dependence invariants; rolling no-look-ahead behavior; complete-case alignment; and clear failures for invalid configuration or insufficient samples.

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

Rolling windows are backward-looking, include the current observation, and never use future rows. `rolling_min_observations` defaults to `rolling_window`, which leaves the first `window - 1` estimates as `NaN`. If the configured minimum is smaller than the window, estimates begin at that minimum using an incomplete trailing window. At least two observations are required, the minimum cannot exceed the window, and a sample shorter than the minimum fails explicitly.

Cross-asset covariance and correlation use complete-case alignment. Rolling covariance and correlation CSVs use `(date, ticker)` row keys and one column per paired ticker. The quantile probabilities and method, skewness and kurtosis bias conventions, and complete downside-deviation definition are repeated in every `run_manifest.json`. Correlation describes linear comovement, does not establish causation, and can change across sample periods. All return-distribution and dependence outputs are historical sample descriptions rather than forecasts.

## Error handling

The program reports invalid configuration, date ranges, output/source paths, rolling windows and minimum observations, annualization settings, quantile probabilities or methods, downside targets, CSV schemas, missing adjusted-price fields, empty provider responses, temporary download failures, invalid tickers, insufficient common history, and insufficient return samples with readable messages.

Potential future additions include cumulative returns, drawdowns, a small interface, and additional risk metrics. Forecasting, VaR, portfolio optimization, machine learning, live feeds, automated trading, and complex infrastructure remain intentionally out of scope for version one.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
