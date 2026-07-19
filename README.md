# Market-Risk-Baseline-Engine

A Python pipeline that downloads adjusted daily prices and produces simple returns, log returns, daily and annualized volatility, rolling volatility, and multi-asset Pearson correlations.

## What it produces

Running `main.py` creates these files in `outputs/`:

- `adjusted_prices.csv`
- `simple_returns.csv`
- `log_returns.csv`
- `return_summary.csv`
- `volatility_summary.csv`
- `rolling_volatility.csv`
- `rolling_volatility.png`
- `correlation_matrix.csv`
- `correlation_heatmap.png`

Prices come from Yahoo Finance through `yfinance`. The loader explicitly requests `Adj Close`; it does not silently substitute raw closing prices. Dates with missing observations in any selected asset are dropped, and prices are never forward-filled.

## Setup with Conda

The environment is named `market-risk-baseline-engine`:

```powershell
conda env create -f environment.yml
conda activate market-risk-baseline-engine
```

If the environment already exists, synchronize it with:

```powershell
conda env update -n market-risk-baseline-engine -f environment.yml --prune
```

## Configure and run

Edit the configuration block at the top of `main.py`:

```python
TICKERS = ["SPY", "QQQ", "TLT", "GLD"]
START_DATE = "2020-01-01"
END_DATE = "2025-01-01"
ROLLING_WINDOW = 21
TRADING_DAYS = 252
```

Then run the single entry point:

```powershell
conda run -n market-risk-baseline-engine python main.py
```

Yahoo Finance treats `END_DATE` as exclusive. For example, `2025-01-01` requests observations strictly before January 1, 2025.

## Tests

The automated tests use deterministic synthetic prices and do not require network access:

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

The program reports invalid date ranges, invalid rolling windows, missing adjusted-price fields, empty provider responses, temporary download failures, invalid tickers, insufficient common history, and empty return matrices with readable messages.

Potential future additions include cumulative returns, drawdowns, rolling pairwise correlation, a small interface, and additional risk metrics. Forecasting, VaR, portfolio optimization, machine learning, live feeds, automated trading, and complex infrastructure remain intentionally out of scope for version one.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
