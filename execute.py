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
    

def set_backtest_range(data, date = None):
    
    if date is None:
        current_date = get_next_date(data, data["QUOTE_DATE"].min())
    else:
        current_date = get_next_date(data, pd.to_datetime(date))
    start_date = pd.to_datetime(current_date)

    # set end_date to max date in df
    end_date = pd.to_datetime(get_next_date(data, data["QUOTE_DATE"].max()))

    return start_date, end_date


def sell_at_expiration(data, quote_open, log=False):
    """Close the position at expiration. Returns (close_date, quote_close) or (None, None) if not found."""
    close_date = get_next_date(data, quote_open["EXPIRE_DATE"])
    quote_close = quote_at_strike(data, close_date, close_date, quote_open["STRIKE"])
    if log and quote_close is not None:
        print_short_put(quote_close)
    return close_date, quote_close


# Strategy execution engine with conditions
@profile
def execute_strategy(data, buy_condition, sell_condition, date = None, log = False):
    """Execute the short put strategy with the given buy and sell conditions."""    

    # backtest range
    start_date, end_date = set_backtest_range(data, date)

    # Execution loop
    current_date = start_date
    accrued_pl = 0.0
    max_capital = 0.0
    trades = []
    trade_records = []
    while True:

        # Execute next condition: sell put on next available date
        quote_open = quote_at(data, current_date, target_delta=buy_condition['delta'], target_dte=buy_condition['dte'], side="P")
        if quote_open is None:
            if log: print(f"  Skipping: no open quote found for {current_date}")
            current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=1))
            if current_date is None or pd.to_datetime(current_date) > end_date:
                break
            continue
        max_capital = max(max_capital, quote_open["STRIKE"] * 100)
        if log: print_short_put(quote_open)
        trades.append(f"Sell put on {current_date}")
        trade_records.append({
            "type": "open",
            "date": pd.to_datetime(current_date),
            "underlying": float(quote_open["UNDERLYING_LAST"]),
            "strike": float(quote_open["STRIKE"]),
        })

        # Execute next condition: sell on condition
        # implement other sell conditions (e.g. pct profit/loss)
        if sell_condition.get("pct_profit") is not None:
            # Walk forward day by day; close when profit >= pct_profit % of premium
            pct_profit = sell_condition["pct_profit"] / 100.0
            p_open = float(quote_open["P_LAST"])
            expire_date = get_next_date(data, quote_open["EXPIRE_DATE"])
            if expire_date is None:
                if log: print(f"  Stopping: expiration {quote_open['EXPIRE_DATE']} is outside the dataset — discarding last open trade")
                trade_records.pop()
                trades.pop()
                break
            sorted_dates = data.attrs.get("sorted_dates", np.sort(data.index.unique().values))
            start_idx = np.searchsorted(sorted_dates, pd.Timestamp(current_date).strftime("%Y-%m-%d")) + 1
            expire_idx = np.searchsorted(sorted_dates, pd.Timestamp(expire_date).strftime("%Y-%m-%d"), side="right")
            quote_close = None
            close_date = expire_date
            for scan_date in sorted_dates[start_idx:expire_idx]:
                q = quote_at_strike(data, scan_date, quote_open["EXPIRE_DATE"], quote_open["STRIKE"])
                if q is None:
                    continue
                p_current = float(q["P_LAST"])
                if p_open > 0 and (p_open - p_current) / p_open >= pct_profit:
                    quote_close = q
                    close_date = scan_date
                    break
            if quote_close is None:
                # target never reached — close at expiration
                close_date, quote_close = sell_at_expiration(data, quote_open, log=log)
            if quote_close is None:
                if log: print(f"  Skipping: no close quote found for {close_date}")
                current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=30))
                if current_date is None or pd.to_datetime(current_date) > end_date:
                    break
                continue
            if log: print_short_put(quote_close)

        # Sell at expiration if no other sell condition is met
        else:
            close_date, quote_close = sell_at_expiration(data, quote_open, log=log)
            if quote_close is None:
                if log: print(f"  Skipping: no close quote found for {close_date}")
                current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=30))
                if current_date is None or pd.to_datetime(current_date) > end_date:
                    break
                continue

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