# Market-Risk-Baseline-Engine

A Python pipeline that validates adjusted daily prices from Yahoo Finance or a local CSV and produces simple returns, log returns, daily and annualized volatility, rolling volatility, and multi-asset Pearson correlations.

## What it produces

Running the installed `market-risk-baseline` command creates these files in `outputs/`:

- `adjusted_prices.csv`
- `simple_returns.csv`
- `log_returns.csv`
- `return_summary.csv`
- `volatility_summary.csv`
- `rolling_volatility.csv`
- `rolling_volatility.png`
- `correlation_matrix.csv`
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

Version `0.1.2` accepts a TOML or JSON configuration file. Copy `config.example.toml`, edit it without changing application source, and run:

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
  --output-dir outputs/alternate
```

Run `market-risk-baseline --help` for every option. Supported keys are `provider`, `tickers`, `start_date`, `end_date`, `rolling_window`, `trading_days`, `output_dir`, and `csv_path`. TOML may put them under `[analysis]`; JSON uses a top-level object (or an `analysis` object). Command-line overrides have highest priority, followed by the file and built-in defaults.

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

Do not put raw closes in `adjusted_close`. The engine cannot infer or reconstruct split/dividend adjustments and deliberately refuses Yahoo responses without `Adj Close`. Duplicate date/ticker rows keep the last source row and are disclosed. Missing, nonnumeric, zero, and negative prices are never filled; invalid observations are removed before complete-case alignment. A run needs at least `rolling_window + 2` common adjusted-price observations.

`outputs/acquired_adjusted_prices.csv` from a successful Yahoo run follows this schema and can be passed later with `--provider csv --csv-path ...`.

## Data quality and lineage

`data_quality_report.json` records requested and returned instruments, actual first and last common dates, per-instrument observation counts, missing values, duplicate date/instrument rows, invalid prices, and the reduction caused by common-history alignment.

`run_manifest.json` records the package version, Git commit when available, execution timestamp, complete effective configuration, actual provider and source, acquisition/read time, actual input range, instruments, dependency versions, and generated artifacts. A CSV run records the resolved source path and file modification time. These files describe the data actually analyzed, not merely what was requested.

## Yahoo and yfinance limitations

The Yahoo adapter pins `yfinance` and explicitly requests `Adj Close` with `auto_adjust=False`. Adjusted values are vendor-supplied; their adjustment methodology, correction timing, completeness, and corporate-action treatment are not independently reconstructed or guaranteed here. Provider availability, response shape, rate limits, and historical values can change, so reproducible work should retain the emitted canonical acquisition and manifest.

`yfinance` is an independent open-source project and is not affiliated with, endorsed by, or vetted by Yahoo. Its project page describes the tool as intended for research/education and Yahoo Finance access as personal-use oriented. Users remain responsible for determining whether downloading, storing, and redistributing data is permitted for their use case under the [yfinance project notice](https://pypi.org/project/yfinance/) and [Yahoo API terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html). The software and downloaded market data have separate licensing considerations.

## Tests

The automated tests use deterministic synthetic prices and saved provider-shaped responses; they do not require network access. They include Yahoo/CSV equivalence, quality-report checks, a wheel build, isolated-target installation, package import, entry-point check, and an offline complete-analysis test:

```powershell
conda run -n market-risk-baseline-engine python -m pytest -q
```

They verify that returns have fewer rows than prices, contain no infinities, volatility is non-negative, correlations stay in `[-1, 1]`, correlation diagonals equal one, complete-case aligned returns contain no missing data, and invalid rolling windows fail clearly.

## Calculation notes

- Simple return: `P(t) / P(t-1) - 1`
- Log return: `log(P(t) / P(t-1))`
- Daily volatility: sample standard deviation of daily log returns with `ddof=1`
- Annualized volatility: daily volatility multiplied by `sqrt(252)`
- Rolling volatility: rolling sample standard deviation multiplied by `sqrt(252)`
- Correlation: Pearson correlation of complete-case aligned log returns

The 252-day convention and square-root-of-time scaling are standard baseline approximations. Correlation describes linear comovement, does not establish causation, and can change across sample periods. Returns are usually more suitable than prices for statistical analysis, but are not guaranteed to be stationary.

## Error handling

The program reports invalid configuration, date ranges, output/source paths, rolling windows, CSV schemas, missing adjusted-price fields, empty provider responses, temporary download failures, invalid tickers, insufficient common history, and empty return matrices with readable messages.

Potential future additions include cumulative returns, drawdowns, rolling pairwise correlation, a small interface, and additional risk metrics. Forecasting, VaR, portfolio optimization, machine learning, live feeds, automated trading, and complex infrastructure remain intentionally out of scope for version one.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
