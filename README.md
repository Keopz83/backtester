# Backtest Options

A study project for backtesting automated trading strategies on stocks and stock options using historical QQQ option chain data (2020–2022).

## Data

Source: [QQQ Daily Option Chains Q1 2020 – Q4 2022](https://www.kaggle.com/datasets/kylegraupe/qqq-daily-option-chains-q1-2020-to-q4-2022) (Kaggle)  
Place the CSV at `data/qqq_2020_2022.csv`.

## Structure

| File | Purpose |
|---|---|
| `lib.py` | Core helpers: data loading, date lookup, option chain queries, P&L computation |
| `backtest.py` | Strategy execution engine (`execute_strategy`) and profiling entry point |
| `read.py` | Exploratory analysis and data visualization |
| `test.py` | Unit tests for all helper functions |

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

## Strategy

The current implemented strategy is a **short put** (cash-secured put selling):
- Sell a put at a target delta and DTE each month
- Close at expiration
- Track premium P&L, assignment risk, and total return
