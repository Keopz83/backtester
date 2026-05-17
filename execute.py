# Import libraries
import pandas as pd
import matplotlib.pyplot as plt
from lib import *

#
try:
    profile
except NameError:
    def profile(func):
        return func


# Strategy execution engine with conditions
@profile
def execute_strategy(data, buy_condition, sell_condition, date = None):
    """Execute the short put strategy with the given buy and sell conditions."""
    # This function will implement the backtesting loop based on the specified conditions.
    
    # Execution loop
    # set current_date to min date in df
    if date is not None:
        current_date = get_next_date(data, pd.to_datetime(date))
    else:
        current_date = get_next_date(data, data["QUOTE_DATE"].min())
    start_date = pd.to_datetime(current_date)
    # set end_date to max date in df
    end_date = pd.to_datetime(get_next_date(data, data["QUOTE_DATE"].max()))

    #end_date = pd.to_datetime(df["QUOTE_DATE"].iloc[-1]) #pd.to_datetime("2021-12-31") 
    accrued_pl = 0.0
    max_capital = 0.0
    log = False
    trades = []
    trade_records = []
    while True:

        # Execute next condition: sell put on next available date
        quote_open = quote_at(data, current_date, target_delta=buy_condition['delta'], target_dte=buy_condition['dte'], side="P")
        max_capital = max(max_capital, quote_open["STRIKE"] * 100)
        if log: print_short_put(quote_open)
        trades.append(f"Sell put on {current_date}")
        trade_records.append({
            "type": "open",
            "date": pd.to_datetime(current_date),
            "underlying": float(quote_open["UNDERLYING_LAST"]),
            "strike": float(quote_open["STRIKE"]),
        })

        # Execute next condition: sell at expiration
        close_date = get_next_date(data, quote_open["EXPIRE_DATE"])
        quote_close = quote_at_strike(data, close_date, close_date, quote_open["STRIKE"])    
        if quote_close is None:
            if log: print(f"  Skipping: no close quote found for {close_date}")
            current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=30))
            if current_date is None or pd.to_datetime(current_date) > end_date:
                break
            continue
        if log: print_short_put(quote_close)

        # Compute trade results
        assigned, total_pl, premium_pl, valuation_pl = compute_trade(quote_open, quote_close)
        if log: print_trade(assigned, total_pl, premium_pl, valuation_pl)
        accrued_pl += total_pl
        if log: print(f"\n## Accrued P/L so far: ${accrued_pl:.2f}")
        trades.append(f"Buy to close put on {close_date} with P/L ${total_pl:.2f}")
        trade_records.append({
            "type": "close",
            "date": pd.to_datetime(close_date),
            "underlying": float(quote_close["UNDERLYING_LAST"]),
            "strike": float(quote_open["STRIKE"]),
            "pl": total_pl,
            "assigned": assigned,
        })

        # Execute next condition (simply repeat)
        # set current date to next buy date (e.g. next month) and repeat
        current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=30))
        if current_date is None or pd.to_datetime(current_date) > end_date:
            break

    if log: print(f"\nSummary: {start_date.date()} to {end_date.date()}")
    if log: print(f"  Total P/L:        ${accrued_pl:.2f}")
    if log: print(f"  Max capital req:  ${max_capital:.2f}")
    if log: print(f"  Return:           {accrued_pl / max_capital * 100:.2f}%")
    return {
        "start_date": start_date,
        "end_date": end_date,
        "accrued_pl": accrued_pl,
        "max_capital": max_capital,
        "trade_records": trade_records,
    }


# Plotting function to visualize strategy performance
def plot_strategy(df, result):
    """Plot underlying price over time with buy/sell points from execute_strategy result."""
    underlying = df["UNDERLYING_LAST"].groupby(level=0).first()
    underlying.index = pd.to_datetime(underlying.index)
    underlying = underlying.sort_index()
    underlying = underlying[
        (underlying.index >= result["start_date"]) &
        (underlying.index <= result["end_date"])
    ]

    opens             = [t for t in result["trade_records"] if t["type"] == "open"]
    unassigned_closes = [t for t in result["trade_records"] if t["type"] == "close" and not t["assigned"]]
    assigned_closes   = [t for t in result["trade_records"] if t["type"] == "close" and t["assigned"]]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(underlying.index, underlying.values, color="steelblue", linewidth=1, label="QQQ Underlying")

    if opens:
        ax.scatter([t["date"] for t in opens], [t["underlying"] for t in opens],
                   marker="^", color="green", s=80, zorder=5, label="Sell Put (Open)")
    if unassigned_closes:
        ax.scatter([t["date"] for t in unassigned_closes], [t["underlying"] for t in unassigned_closes],
                   marker="v", color="tomato", s=80, zorder=5, label="Close (Expired)")
    if assigned_closes:
        ax.scatter([t["date"] for t in assigned_closes], [t["underlying"] for t in assigned_closes],
                   marker="x", color="darkred", s=120, zorder=5, label="Close (Assigned)")

    ax.set_title(
        f"QQQ Short Put Strategy — {result['start_date'].date()} to {result['end_date'].date()}"
        f"  |  Return: {result['accrued_pl'] / result['max_capital'] * 100:.2f}%"
    )
    ax.set_ylabel("Underlying Price ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()