import os
import numpy as np
import pandas as pd

try:
    profile
except NameError:
    def profile(func):
        return func

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "qqq_2020_2022.csv")


def load_data_full(path=DATA_PATH):
    df = pd.read_csv(path, low_memory=False)
    df.columns = df.columns.str.strip().str.strip("[]")
    return df.dropna()

def get_data_section(data):
    df2 = data[['QUOTE_DATE', 'EXPIRE_DATE', 'DTE', 'STRIKE',
              'C_DELTA', 'C_LAST', 'P_DELTA', 'P_LAST', 'UNDERLYING_LAST']].copy()
    df2["QUOTE_DATE"]  = df2["QUOTE_DATE"].str.strip()
    df2["EXPIRE_DATE"] = df2["EXPIRE_DATE"].str.strip()
    df2["DTE"]             = pd.to_numeric(df2["DTE"], errors="coerce")
    df2["STRIKE"]          = pd.to_numeric(df2["STRIKE"], errors="coerce")
    df2["C_DELTA"]         = pd.to_numeric(df2["C_DELTA"], errors="coerce")
    df2["C_LAST"]          = pd.to_numeric(df2["C_LAST"], errors="coerce")
    df2["P_DELTA"]         = pd.to_numeric(df2["P_DELTA"], errors="coerce")
    df2["P_LAST"]          = pd.to_numeric(df2["P_LAST"], errors="coerce")
    df2["UNDERLYING_LAST"] = pd.to_numeric(df2["UNDERLYING_LAST"], errors="coerce")
    df2 = df2.dropna()
    df2 = df2.sort_values("QUOTE_DATE").set_index("QUOTE_DATE", drop=False)
    df2.attrs["sorted_dates"] = np.sort(df2.index.unique().values)
    return df2

def load_data(path=DATA_PATH):
    df = load_data_full(path)
    return get_data_section(df)

def get_next_date(data, date):
    """Return `date` if it exists in the dataset, otherwise the closest available QUOTE_DATE after it."""
    sorted_dates = data.attrs.get("sorted_dates") if hasattr(data, "attrs") else None
    if sorted_dates is None:
        sorted_dates = np.sort(data.index.unique().values)
    ts_str = pd.Timestamp(date).strftime("%Y-%m-%d")
    idx = np.searchsorted(sorted_dates, ts_str)
    if idx >= len(sorted_dates):
        return None
    return sorted_dates[idx]


def underlying_at(data, date):
    """Return the underlying price (UNDERLYING_LAST) at the given QUOTE_DATE."""
    if date not in data.index:
        return None
    rows = data.loc[date]
    if isinstance(rows, pd.Series):
        return float(rows["UNDERLYING_LAST"])
    return float(rows["UNDERLYING_LAST"].iloc[0])

@profile
def quote_at(data, date, target_delta, target_dte, side):
    """
    Return the option row closest to target_delta and target_dte on the given date.

    Parameters
    ----------
    date         : str  — QUOTE_DATE (YYYY-MM-DD)
    target_delta : float — absolute delta, e.g. 0.3
    target_dte   : int   — days to expiration, e.g. 30
    side         : 'P' for put, 'C' for call
    """
    if side not in ("P", "C"):
        raise ValueError(f"side must be 'P' or 'C', got {side!r}")
    if date not in data.index:
        return None
    delta_col = f"{side}_DELTA"
    chain = data.loc[date]
    if isinstance(chain, pd.Series):
        chain = chain.to_frame().T
    chain = chain.copy()
    chain["_score"] = (chain[delta_col].abs() - target_delta).abs() + (chain["DTE"] - target_dte).abs() * 0.01
    return chain.sort_values("_score").iloc[0]


def quote_at_strike(data, date, expiration, strike):
    """Return the option row for a specific strike and expiration on the given quote date."""
    if date not in data.index:
        return None
    day = data.loc[date]
    if isinstance(day, pd.Series):
        day = day.to_frame().T
    row = day[(day["EXPIRE_DATE"] == expiration) & (day["STRIKE"] == strike)]
    if row.empty:
        return None
    return row.iloc[0]


def print_short_put(quote):
    if quote is None:
        print("No quote available.")
        return
    premium          = float(quote["P_LAST"])
    capital_required = float(quote["STRIKE"]) * 100

    print(f"\nShort Put on {quote['QUOTE_DATE']}:")
    print(f"  Underlying: ${float(quote['UNDERLYING_LAST']):.2f}")
    print(f"  Delta:      {quote['P_DELTA']:.2f}")
    print(f"  DTE:        {quote['DTE']:.0f}")
    print(f"  Expiration: {quote['EXPIRE_DATE']}")
    print(f"  Strike:     ${quote['STRIKE']}")
    print(f"  Assignment: ${capital_required}")
    print(f"  Premium:    ${premium * 100:.0f}")


def print_trade(assigned, total_pl, premium_pl, valuation_pl):
    print(f"\nCurrent trade result:")
    print(f"  Assigned: {'Yes' if assigned else 'No'}")
    print(f"  Total P/L: ${total_pl:.2f}")
    print(f"    Premium P/L: ${premium_pl:.2f}")
    print(f"    Valuation P/L: ${valuation_pl:.2f}")


def compute_trade(quote_open, quote_close):
    """Return (total_pl, premium_pl, valuation_pl) for a short put between two quotes.

    - premium_pl  : change in extrinsic (time) value captured  = (extrinsic_open - extrinsic_close) * 100
    - valuation_pl: change in intrinsic value (assignment risk) = (intrinsic_open - intrinsic_close) * 100
    - total_pl    : premium_pl + valuation_pl  (= option_open - option_close) * 100
    """
    strike         = float(quote_open["STRIKE"])
    p_open         = float(quote_open["P_LAST"])
    p_close        = float(quote_close["P_LAST"])
    ul_open        = float(quote_open["UNDERLYING_LAST"])
    ul_close       = float(quote_close["UNDERLYING_LAST"])

    intrinsic_close = ul_close - strike
    assigned = quote_close["QUOTE_DATE"] == quote_open["EXPIRE_DATE"] and intrinsic_close < 0

    premium_pl   = (p_open - p_close)  * 100
    valuation_pl = (intrinsic_close if intrinsic_close < 0 else 0) * 100
    total_pl     = (p_open * 100 + valuation_pl) if assigned else premium_pl

    return assigned, total_pl, premium_pl, valuation_pl


def display_chain(data, date, dte=None, delta_min=None, delta_max=None):
    if date not in data.index:
        print(f"No data found for {date}"
              + (f"  DTE={dte}" if dte is not None else "")
              + (f"  delta=[{delta_min}, {delta_max}]" if delta_min is not None or delta_max is not None else ""))
        return
    chain = data.loc[date]
    if isinstance(chain, pd.Series):
        chain = chain.to_frame().T
    chain = chain.copy()

    if dte is not None:
        chain = chain[chain["DTE"].round().eq(dte)]

    if delta_min is not None or delta_max is not None:
        lo, hi = (delta_min or 0.0), (delta_max or 1.0)
        chain = chain[chain["C_DELTA"].abs().between(lo, hi) | chain["P_DELTA"].abs().between(lo, hi)]

    if chain.empty:
        print(f"No data found for {date}"
              + (f"  DTE={dte}" if dte is not None else "")
              + (f"  delta=[{delta_min}, {delta_max}]" if delta_min is not None or delta_max is not None else ""))
        return

    cols = [
        "EXPIRE_DATE", "DTE", "STRIKE", "UNDERLYING_LAST",
        "C_BID", "C_ASK", "C_LAST", "C_IV", "C_DELTA", "C_VOLUME",
        "P_BID", "P_ASK", "P_LAST", "P_IV", "P_DELTA", "P_VOLUME",
    ]
    dte_info   = f"  DTE={dte}" if dte is not None else ""
    delta_info = f"  delta=[{delta_min}, {delta_max}]" if delta_min is not None or delta_max is not None else ""
    print(f"QQQ Option Chain — {date}{dte_info}{delta_info}  (underlying: {chain['UNDERLYING_LAST'].iloc[0]})")
    print(chain[cols].sort_values(["EXPIRE_DATE", "STRIKE"]).to_string(index=False))
    return chain

def save_results(results, buy_conditions, sell_condition, start_dates):
    results_df = pd.DataFrame(results)
    import os, json
    from datetime import datetime
    if not os.path.exists("results"):
        os.makedirs("results")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pct_profit = sell_condition.get("pct_profit")
    pct_loss   = sell_condition.get("pct_loss")
    sell_tag   = f"tp{pct_profit}" if pct_profit else f"dte{sell_condition.get('dte', 0)}"
    if pct_loss:
        sell_tag += f"_sl{pct_loss}"
    deltas = "_".join(str(c["delta"]) for c in buy_conditions)
    dtes   = "_".join(str(c["dte"])   for c in buy_conditions)
    strategy_tag = f"d{deltas}_dte{dtes}_{sell_tag}"
    base = f"results/grid_search_{strategy_tag}_{timestamp}"
    results_df.to_csv(f"{base}.csv", index=False)
    strategy_info = {
        "timestamp": timestamp,
        "buy_conditions": buy_conditions,
        "sell_condition": sell_condition,
        "start_dates": start_dates,
    }
    with open(f"{base}.json", "w") as f:
        json.dump(strategy_info, f, indent=2, default=str)
