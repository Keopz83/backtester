# Stock Options Backtester

A Python backtesting framework for systematic options strategies on QQQ (2020–2022). The engine supports configurable entry and exit conditions, grid search over delta/DTE parameter spaces, and a suite of visualisations for analysing return distributions and strategy performance across different market regimes.


## Currently implemented strategies

Following are the currently implemented strategies.

#### 1. Recurrent Short Put

The current implemented strategy is a **short put** (cash-secured put selling):
- Sell a put at a target delta and DTE each month
- Close at expiration
- Track premium P&L, assignment risk, and total return


## Roadmap

Planned features to extend the framework beyond the current short put strategy:

1. **Stop-loss / take-profit exit conditions** — close the short put early when the position has gained or lost a target percentage of the premium collected (e.g. close at 50% profit or 200% loss)
2. **Underlying technicals as entry/exit filters** — gate trades on momentum indicators (SMA crossovers, rate-of-change) or mean-reversion signals (RSI overbought/oversold) derived from the underlying price
3. **Short covered call** — after taking assignment on a short put, sell an OTM call against the acquired shares to collect additional premium while waiting for the stock to recover
4. **Wheel strategy** — combine the short put and covered call into a continuous cycle: sell puts until assigned, then sell covered calls until called away, then repeat



## Data

Source: [QQQ Daily Option Chains Q1 2020 – Q4 2022](https://www.kaggle.com/datasets/kylegraupe/qqq-daily-option-chains-q1-2020-to-q4-2022) (Kaggle)  
Place the CSV at `data/qqq_2020_2022.csv`.

## Grid Search

`grid_search()` in `backtest.py` sweeps over a list of buy conditions (delta / DTE combinations) and a list of start dates, running `execute_strategy` for every combination.  Results are collected as a list of result dicts and can be visualised with:

- `plot_grid_search_results()` — 2-D bubble chart (x = delta, y = DTE, bubble size ∝ |return|, colour = start date)
- `plot_return_distribution()` — stacked histograms of return (%) per buy condition, each with its mean annotated

Example: sweep 10 DTE values (7–70 days) at fixed delta 0.2 across ~90 weekly start dates (2021-02-10 → 2022-11-01).  Progress is printed to the console as `done/total  delta=… dte=… start=…`.

## Sample screenshots

![Return Distribution by Condition](screenshots/screenshot_gridsearch_return_dist_by_condition.png)
![Mean Return by Condition](screenshots/screenshot_gridsearch_mean_return_by_condition.png)


## Structure

| File | Purpose |
|---|---|
| `lib.py` | Core library: data loading & cleaning, date helpers, option chain queries (`quote_at`, `quote_at_strike`), P&L computation (`compute_trade`), display utilities |
| `backtest.py` | Strategy engine: `execute_strategy`, `grid_search`, plotting functions (`plot_strategy`, `plot_grid_search_results`, `plot_return_distribution`) |
| `live-option-data.py` | Fetches live option chain data for experimentation |
| `test.py` | Unit tests for all `lib.py` helper functions |
| `data/` | Historical QQQ daily option chain data (not tracked in git) |
| `results/` | Output files from backtests and grid searches (not tracked in git) |


## Usage

Run a backtest:
```bash
python backtest.py
```

Profile performance:
```bash
kernprof -l -v backtest.py
```

Run tests:
```bash
python -m unittest -v test
```