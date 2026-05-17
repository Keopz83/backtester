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
    return close_date, quote_close


def open_trade(data, buy_condition, current_date, max_capital, trade_records, log=False, side="P"):
    """Attempt to open a short put or call. Returns (quote_open, max_capital).
    On failure, quote_open is None and max_capital is unchanged."""
    quote_open = quote_at(data, current_date, target_delta=buy_condition['delta'], target_dte=buy_condition['dte'], side=side)
    if quote_open is None:
        if log: print(f"  Skipping: no open quote found for {current_date}")
        return None, max_capital
    max_capital = max(max_capital, quote_open["STRIKE"] * 100)
    position_id = len([r for r in trade_records if r["type"] == "open"]) + 1
    trade_id = len(trade_records) + 1
    if log: print(f"----------- OPEN TRADE pos=#{position_id} trade=#{trade_id} -----------")
    if log: (print_short_put if side == "P" else print_short_call)(quote_open)
    trade_records.append({
        "trade_id": trade_id,
        "position_id": position_id,
        "type": "open",
        "side": side,
        "date": pd.to_datetime(current_date),
        "underlying": float(quote_open["UNDERLYING_LAST"]),
        "strike": float(quote_open["STRIKE"]),
    })
    return quote_open, max_capital

def close_trade(data, sell_condition, quote_open, current_date, trade_records, log=False):
    """Find the close quote for an open short put or call.
    Returns quote_close on success, or None if no close quote was found.
    """
    pct_profit  = sell_condition.get("pct_profit")
    pct_loss    = sell_condition.get("pct_loss")
    position_id = trade_records[-1]["position_id"]
    side        = trade_records[-1].get("side", "P")
    premium_col = f"{side}_LAST"

    if pct_profit is not None or pct_loss is not None:
        pct_profit_ratio = pct_profit / 100.0 if pct_profit is not None else None
        pct_loss_ratio   = pct_loss   / 100.0 if pct_loss   is not None else None
        p_open = float(quote_open[premium_col])
        expire_date = get_next_date(data, quote_open["EXPIRE_DATE"])

        if expire_date is None:
            if log: print(f"  [pos=#{position_id}] Stopping: expiration {quote_open['EXPIRE_DATE']} is outside the dataset — discarding last open trade")
            return None

        sorted_dates = data.attrs.get("sorted_dates", np.sort(data.index.unique().values))
        start_idx = np.searchsorted(sorted_dates, pd.Timestamp(current_date).strftime("%Y-%m-%d")) + 1
        expire_idx = np.searchsorted(sorted_dates, pd.Timestamp(expire_date).strftime("%Y-%m-%d"), side="right")
        quote_close = None
        close_date = expire_date
        close_reason = "expiration"

        for scan_date in sorted_dates[start_idx:expire_idx]:
            q = quote_at_strike(data, scan_date, quote_open["EXPIRE_DATE"], quote_open["STRIKE"])
            if q is None:
                continue
            p_current = float(q[premium_col])
            hit_profit = pct_profit_ratio is not None and p_open > 0 and (p_open - p_current) / p_open >= pct_profit_ratio
            hit_loss   = pct_loss_ratio   is not None and p_open > 0 and (p_current - p_open) / p_open >= pct_loss_ratio
            if hit_profit or hit_loss:
                quote_close = q
                close_date = scan_date
                close_reason = "take_profit" if hit_profit else "stop_loss"
                break

        if quote_close is None:
            close_date, quote_close = sell_at_expiration(data, quote_open, log=log)
            close_reason = "expiration"

        if quote_close is None:
            if log: print(f"  [pos=#{position_id}] Skipping: no close quote found for {close_date}")
            return None

        if log: print(f"x---------- CLOSE TRADE pos=#{position_id} trade=#{len(trade_records) + 1} ----------x")
        if log: (print_short_put if side == "P" else print_short_call)(quote_close)
        assigned, total_pl, _, _ = compute_trade(quote_open, quote_close, side=side)
        trade_id = len(trade_records) + 1
        trade_records.append({
            "trade_id": trade_id,
            "position_id": position_id,
            "type": "close",
            "side": side,
            "close_reason": close_reason,
            "date": pd.to_datetime(quote_close["QUOTE_DATE"]),
            "underlying": float(quote_close["UNDERLYING_LAST"]),
            "strike": float(quote_open["STRIKE"]),
            "pl": total_pl,
            "assigned": assigned,
        })
        return quote_close

    else:
        close_date, quote_close = sell_at_expiration(data, quote_open, log=log)
        if quote_close is None:
            if log: print(f"  [pos=#{position_id}] Skipping: no close quote found for {close_date}")
            return None
        assigned, total_pl, _, _ = compute_trade(quote_open, quote_close, side=side)
        trade_id = len(trade_records) + 1
        if log: print(f"x---------- CLOSE TRADE pos=#{position_id} trade=#{trade_id} ----------x")
        if log: (print_short_put if side == "P" else print_short_call)(quote_close)
        trade_records.append({
            "trade_id": trade_id,
            "position_id": position_id,
            "type": "close",
            "side": side,
            "close_reason": "expiration",
            "date": pd.to_datetime(quote_close["QUOTE_DATE"]),
            "underlying": float(quote_close["UNDERLYING_LAST"]),
            "strike": float(quote_open["STRIKE"]),
            "pl": total_pl,
            "assigned": assigned,
        })
        return quote_close

    if pct_profit is not None or pct_loss is not None:
        pct_profit_ratio = pct_profit / 100.0 if pct_profit is not None else None
        pct_loss_ratio   = pct_loss   / 100.0 if pct_loss   is not None else None
        p_open = float(quote_open["P_LAST"])
        expire_date = get_next_date(data, quote_open["EXPIRE_DATE"])

        if expire_date is None:
            if log: print(f"  [pos=#{position_id}] Stopping: expiration {quote_open['EXPIRE_DATE']} is outside the dataset — discarding last open trade")
            return None

        sorted_dates = data.attrs.get("sorted_dates", np.sort(data.index.unique().values))
        start_idx = np.searchsorted(sorted_dates, pd.Timestamp(current_date).strftime("%Y-%m-%d")) + 1
        expire_idx = np.searchsorted(sorted_dates, pd.Timestamp(expire_date).strftime("%Y-%m-%d"), side="right")
        quote_close = None
        close_date = expire_date
        close_reason = "expiration"

        for scan_date in sorted_dates[start_idx:expire_idx]:
            q = quote_at_strike(data, scan_date, quote_open["EXPIRE_DATE"], quote_open["STRIKE"])
            if q is None:
                continue
            p_current = float(q["P_LAST"])
            hit_profit = pct_profit_ratio is not None and p_open > 0 and (p_open - p_current) / p_open >= pct_profit_ratio
            hit_loss   = pct_loss_ratio   is not None and p_open > 0 and (p_current - p_open) / p_open >= pct_loss_ratio
            if hit_profit or hit_loss:
                quote_close = q
                close_date = scan_date
                close_reason = "take_profit" if hit_profit else "stop_loss"
                break

        if quote_close is None:
            close_date, quote_close = sell_at_expiration(data, quote_open, log=log)
            close_reason = "expiration"

        if quote_close is None:
            if log: print(f"  [pos=#{position_id}] Skipping: no close quote found for {close_date}")
            return None

        if log: print(f"x---------- CLOSE TRADE pos=#{position_id} trade=#{len(trade_records) + 1} ----------x")
        if log: print_short_put(quote_close)
        assigned, total_pl, _, _ = compute_trade(quote_open, quote_close)
        trade_id = len(trade_records) + 1
        trade_records.append({
            "trade_id": trade_id,
            "position_id": position_id,
            "type": "close",
            "close_reason": close_reason,
            "date": pd.to_datetime(quote_close["QUOTE_DATE"]),
            "underlying": float(quote_close["UNDERLYING_LAST"]),
            "strike": float(quote_open["STRIKE"]),
            "pl": total_pl,
            "assigned": assigned,
        })
        return quote_close

    else:
        close_date, quote_close = sell_at_expiration(data, quote_open, log=log)
        position_id = trade_records[-1]["position_id"]
        if quote_close is None:
            if log: print(f"  [pos=#{position_id}] Skipping: no close quote found for {close_date}")
            return None
        assigned, total_pl, _, _ = compute_trade(quote_open, quote_close)
        trade_id = len(trade_records) + 1
        if log: print(f"x---------- CLOSE TRADE pos=#{position_id} trade=#{trade_id} ----------x")
        trade_records.append({
            "trade_id": trade_id,
            "position_id": position_id,
            "type": "close",
            "close_reason": "expiration",
            "date": pd.to_datetime(quote_close["QUOTE_DATE"]),
            "underlying": float(quote_close["UNDERLYING_LAST"]),
            "strike": float(quote_open["STRIKE"]),
            "pl": total_pl,
            "assigned": assigned,
        })
        return quote_close


def compute_trade_results(quote_open, quote_close, accrued_pl, trade_records, log=False):
    """Compute P&L for a closed trade, log results, and return updated accrued_pl."""
    side = trade_records[-1].get("side", "P")
    assigned, total_pl, premium_pl, valuation_pl = compute_trade(quote_open, quote_close, side=side)
    if log: print_trade(assigned, total_pl, premium_pl, valuation_pl)
    accrued_pl += total_pl
    if log: print(f"\n## [pos=#{trade_records[-1]['position_id']} trade=#{trade_records[-1]['trade_id']}] Accrued P/L so far: ${accrued_pl:.2f}")
    return accrued_pl


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

    put_opens         = [t for t in result["trade_records"] if t["type"] == "open"  and t.get("side", "P") == "P"]
    call_opens        = [t for t in result["trade_records"] if t["type"] == "open"  and t.get("side", "P") == "C"]
    put_closes_u      = [t for t in result["trade_records"] if t["type"] == "close" and t.get("side", "P") == "P" and not t["assigned"]]
    put_closes_a      = [t for t in result["trade_records"] if t["type"] == "close" and t.get("side", "P") == "P" and     t["assigned"]]
    call_closes_u     = [t for t in result["trade_records"] if t["type"] == "close" and t.get("side", "P") == "C" and not t["assigned"]]
    call_closes_a     = [t for t in result["trade_records"] if t["type"] == "close" and t.get("side", "P") == "C" and     t["assigned"]]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(underlying.index, underlying.values, color="steelblue", linewidth=1, label="QQQ Underlying")

    _label_style = dict(
        textcoords="offset points", fontsize=7, color="black",
        ha="center", va="bottom",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.6, edgecolor="none"),
    )
    _reason_map = {"take_profit": "TAKE PROFIT", "stop_loss": "STOP LOSS", "expiration": "EXPIRATION"}

    def _scatter_open(records, color, label):
        if not records: return
        ax.scatter([t["date"] for t in records], [t["underlying"] for t in records],
                   marker="^", color=color, s=80, zorder=5, label=label)
        for t in records:
            ax.annotate(f"#{t['position_id']} {t['date'].strftime('%m/%d/%y')}",
                        xy=(t["date"], t["underlying"]), xytext=(0, 10), **_label_style)

    def _scatter_close(records, color, marker, label):
        if not records: return
        ax.scatter([t["date"] for t in records], [t["underlying"] for t in records],
                   marker=marker, color=color, s=80 if marker == "v" else 120, zorder=5, label=label)
        for t in records:
            reason = _reason_map.get(t.get("close_reason"), "")
            ax.annotate(f"#{t['position_id']} {t['date'].strftime('%m/%d/%y')}\n{reason}",
                        xy=(t["date"], t["underlying"]), xytext=(0, 10), **_label_style)

    _scatter_open(put_opens,    color="green",      label="Short Put (Open)")
    _scatter_open(call_opens,   color="royalblue",  label="Covered Call (Open)")
    _scatter_close(put_closes_u,  color="tomato",   marker="v", label="Put Close")
    _scatter_close(put_closes_a,  color="darkred",  marker="x", label="Put Assigned")
    _scatter_close(call_closes_u, color="deepskyblue", marker="v", label="Call Close")
    _scatter_close(call_closes_a, color="navy",     marker="x", label="Called Away")

    ax.set_title(
        f"QQQ Options Strategy — {result['start_date'].date()} to {result['end_date'].date()}"
        f"  |  Return: {result['accrued_pl'] / result['max_capital'] * 100:.2f}%"
        if result['max_capital'] else
        f"QQQ Options Strategy — {result['start_date'].date()} to {result['end_date'].date()}  |  Return: N/A"
    )
    ax.set_ylabel("Underlying Price ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# Short put execution engine
@profile
def _execute_short_put(data, strategy, date=None, log=False):
    """Execute the recurrent short put strategy."""

    # backtest range
    start_date, end_date = set_backtest_range(data, date)

    # Execution loop
    current_date = get_next_date(data, start_date)
    accrued_pl = 0.0
    max_capital = 0.0
    trade_records = []
    while True:

        # OPEN TRADE: sell put on next available date
        quote_open, max_capital = open_trade(data, strategy['buy_condition'], current_date, max_capital, trade_records, log=log)
        if quote_open is None:
            break

        # ADVANCE DATE
        current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=1))
        if current_date is None or pd.to_datetime(current_date) > end_date:
            # undo trade
            if log: print(f"  [pos=#{trade_records[-1]['position_id']}] Stopping: no more data available after advancing date — discarding last open trade")
            trade_records.pop()
            break

        # CLOSE TRADE: sell on condition
        quote_close = close_trade(data, strategy['sell_condition'], quote_open, current_date, trade_records, log=log)
        if quote_close is None:
            # undo trade
            if log: print(f"  [pos=#{trade_records[-1]['position_id']}] Stopping: no close quote found — discarding last open trade")
            trade_records.pop()
            break
        current_date = quote_close["QUOTE_DATE"]

        # Compute trade results
        accrued_pl = compute_trade_results(quote_open, quote_close, accrued_pl, trade_records, log=log)

        # ADVANCE DATE
        current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=1))
        if current_date is None or pd.to_datetime(current_date) > end_date:
            break



    if log: print(f"\nSummary: {start_date.date()} to {end_date.date()}")
    if log: print(f"  Total P/L:        ${accrued_pl:.2f}")
    if log: print(f"  Max capital req:  ${max_capital:.2f}")
    if log: print(f"  Return:           {accrued_pl / max_capital * 100:.2f}%" if max_capital else "  Return:           N/A (no trades)")
    return {
        "start_date": start_date,
        "end_date": end_date,
        "accrued_pl": accrued_pl,
        "max_capital": max_capital,
        "trade_records": trade_records,
    }


# Wheel execution engine (short put → covered call → repeat)
def _execute_wheel(data, strategy, date=None, log=False):
    """Execute the wheel strategy: sell puts until assigned, then sell covered calls
    until called away, then repeat.

    strategy dict keys:
      - 'put_condition':  {'delta': float, 'dte': int}  — entry condition for the put leg
      - 'call_condition': {'delta': float, 'dte': int}  — entry condition for the call leg
                          (falls back to put_condition if omitted)
      - 'sell_condition': {'pct_profit': float, 'pct_loss': float}  — exit for both legs
    """
    start_date, end_date = set_backtest_range(data, date)
    current_date = get_next_date(data, start_date)
    accrued_pl = 0.0
    max_capital = 0.0
    trade_records = []
    phase = "put"   # 'put' | 'call'

    while True:
        if phase == "put":
            buy_condition = strategy.get("put_condition", strategy.get("buy_condition"))
            side = "P"
        else:
            buy_condition = strategy.get("call_condition", strategy.get("put_condition", strategy.get("buy_condition")))
            side = "C"

        if log: print(f"\n{'='*10} {'SHORT PUT' if phase == 'put' else 'COVERED CALL'} {'='*10}")

        # OPEN TRADE
        quote_open, max_capital = open_trade(data, buy_condition, current_date, max_capital, trade_records, log=log, side=side)
        if quote_open is None:
            break

        # ADVANCE DATE
        current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=1))
        if current_date is None or pd.to_datetime(current_date) > end_date:
            if log: print(f"  [pos=#{trade_records[-1]['position_id']}] Stopping: no more data — discarding last open trade")
            trade_records.pop()
            break

        # CLOSE TRADE
        quote_close = close_trade(data, strategy['sell_condition'], quote_open, current_date, trade_records, log=log)
        if quote_close is None:
            if log: print(f"  [pos=#{trade_records[-1]['position_id']}] Stopping: no close quote — discarding last open trade")
            trade_records.pop()
            break
        current_date = quote_close["QUOTE_DATE"]

        # Compute results
        accrued_pl = compute_trade_results(quote_open, quote_close, accrued_pl, trade_records, log=log)

        # Phase transition on assignment
        last_close = trade_records[-1]
        if phase == "put" and last_close["assigned"]:
            phase = "call"
            if log: print(f"  [pos=#{last_close['position_id']}] Assigned — transitioning to covered call phase")
        elif phase == "call" and last_close["assigned"]:
            phase = "put"
            if log: print(f"  [pos=#{last_close['position_id']}] Called away — transitioning back to short put phase")

        # ADVANCE DATE
        current_date = get_next_date(data, pd.to_datetime(current_date) + pd.Timedelta(days=1))
        if current_date is None or pd.to_datetime(current_date) > end_date:
            break

    if log: print(f"\nSummary: {start_date.date()} to {end_date.date()}")
    if log: print(f"  Total P/L:        ${accrued_pl:.2f}")
    if log: print(f"  Max capital req:  ${max_capital:.2f}")
    if log: print(f"  Return:           {accrued_pl / max_capital * 100:.2f}%" if max_capital else "  Return:           N/A (no trades)")
    return {
        "start_date": start_date,
        "end_date": end_date,
        "accrued_pl": accrued_pl,
        "max_capital": max_capital,
        "trade_records": trade_records,
    }


# Strategy dispatcher — routes to the correct engine based on strategy['type']
_STRATEGY_ENGINES = {
    "short_put": _execute_short_put,
    "wheel":     _execute_wheel,
}

@profile
def execute_strategy(data, strategy, date=None, log=False):
    """Dispatch to the correct execution engine based on strategy['type'].

    strategy dict must contain:
      - 'type':           'short_put' | 'wheel'
      - 'buy_condition':  dict with 'delta' and 'dte'
      - 'sell_condition': dict with optional 'pct_profit', 'pct_loss'
    """
    strategy_type = strategy.get("type", "short_put")
    engine = _STRATEGY_ENGINES.get(strategy_type)
    if engine is None:
        raise ValueError(f"Unknown strategy type '{strategy_type}'. Valid types: {list(_STRATEGY_ENGINES)}")
    return engine(data, strategy, date=date, log=log)