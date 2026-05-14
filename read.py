# %% Import libraries
import pandas as pd
import matplotlib.pyplot as plt

# %% Load and clean data
DATA_PATH = "data/qqq_2020_2022.csv"

df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip().str.strip("[]")
df["QUOTE_DATE"]  = df["QUOTE_DATE"].str.strip()
df["EXPIRE_DATE"] = df["EXPIRE_DATE"].str.strip()
df["DTE"] = pd.to_numeric(df["DTE"], errors="coerce")

# %% Helper function to get the next available quote date
def get_next_date(date, data=df):
    """Return `date` if it exists in the dataset, otherwise the closest available QUOTE_DATE after it."""
    dates = pd.to_datetime(data["QUOTE_DATE"].unique())
    ts = pd.Timestamp(date)
    if ts in dates:
        return ts.strftime("%Y-%m-%d")
    later = dates[dates > ts]
    if later.empty:
        return None
    return later.min().strftime("%Y-%m-%d")

# example usage:
print(get_next_date("2021-03-01"))  # should return the next available quote

# %% Helper function to get the underlying price at a specific date
def underlying_at(date, data=df):
    """Return the underlying price (UNDERLYING_LAST) at the given QUOTE_DATE."""
    rows = data[data["QUOTE_DATE"] == date]["UNDERLYING_LAST"]
    if rows.empty:
        return None
    return float(rows.iloc[0])

# example usage:
print(underlying_at("2021-03-01"))  # should return the underlying price on that date


# %% Helper function to get the option quote closest to target delta and DTE on a specific date
def quote_at(date, target_delta, target_dte, side, data=df):
    """Return the option row closest to target_delta and target_dte on the given date.

    Parameters
    ----------
    date         : str  — QUOTE_DATE (YYYY-MM-DD)
    target_delta : float — absolute delta, e.g. 0.3
    target_dte   : int   — days to expiration, e.g. 30
    side         : 'P' for put, 'C' for call
    """
    if side not in ("P", "C"):
        raise ValueError(f"side must be 'P' or 'C', got {side!r}")
    delta_col = f"{side}_DELTA"
    last_col  = f"{side}_LAST"
    chain = data[data["QUOTE_DATE"] == date].copy()
    chain[delta_col] = pd.to_numeric(chain[delta_col], errors="coerce")
    chain["DTE"]     = pd.to_numeric(chain["DTE"], errors="coerce")
    chain = chain.dropna(subset=[delta_col, "DTE", last_col])
    if chain.empty:
        return None
    chain["_score"] = (chain[delta_col].abs() - target_delta).abs() + (chain["DTE"] - target_dte).abs() * 0.01
    return chain.sort_values("_score").iloc[0]

# example usage:
print(quote_at("2021-03-01", target_delta=0.3, target_dte=30, side="P"))  # should return the put option closest to delta 0.3 and DTE 30 on that date

# %% Helper function to get the option quote at a specific strike and expiration on a given date
def quote_at_strike(date, expiration, strike, data=df):
    """Return the option row for a specific strike and expiration on the given quote date."""
    row = data[
        (data["QUOTE_DATE"] == date) &
        (data["EXPIRE_DATE"] == expiration) &
        (data["STRIKE"] == strike)
    ]
    if row.empty:
        return None
    return row.iloc[0]

# example usage:
date_start = "2021-03-01"
quote = quote_at(date_start, target_delta=0.3, target_dte=30, side="P")
quote_strike = quote["STRIKE"]
expiration_date = quote["EXPIRE_DATE"]
days_passed = 10
current_date = get_next_date(pd.to_datetime(date_start) + pd.Timedelta(days=days_passed))
print(current_date)  # should return the next available quote date after 2021-
print(quote_at_strike(current_date, expiration=expiration_date, strike=quote_strike))  # should return the option with strike 300 expiring on 2021-03-31 on that date


# %% Display options chain for a specific date, DTE, and delta range
def display_chain(date, dte=None, delta_min=None, delta_max=None, data=df):
    chain = data[data["QUOTE_DATE"] == date].copy()
    chain["DTE"]     = pd.to_numeric(chain["DTE"], errors="coerce")
    chain["C_DELTA"] = pd.to_numeric(chain["C_DELTA"], errors="coerce")
    chain["P_DELTA"] = pd.to_numeric(chain["P_DELTA"], errors="coerce")

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

DATE = "2021-03-01"  # change this to the desired date (YYYY-MM-DD)
DTE = 30
DELTA_MIN = 0.3
DELTA_MAX = 0.5
chain = display_chain(DATE, dte=DTE, delta_min=DELTA_MIN, delta_max=DELTA_MAX)

# %% Display a smaller table with just strike, delta, and last price for calls and puts
small = chain[["STRIKE", "C_DELTA", "C_LAST"]].sort_values("STRIKE").reset_index(drop=True)
print(small.to_string(index=False))

# %% Simulate a short put trade with on 2021-03-31, delta ~0.3, and DTE ~30 days
trade_date = "2021-03-31"
quote_start = quote_at(trade_date, target_delta=0.3, target_dte=30, side="P")
# print the total premium and capital at risk for the trade
def print_trade(t):
    if t is None:
        print("No quote available.")
        return
    premium          = float(t["P_LAST"])
    capital_required = float(t["STRIKE"]) * 100
    unrealized_pnl   = (premium - max(0, float(t["STRIKE"]) - float(t["UNDERLYING_LAST"]))) * 100
    print(f"Simulated trade: Short 1 QQQ put")
    print(f"  Underlying: ${float(t['UNDERLYING_LAST']):>8.2f}")
    print(f"  Delta:      {t['P_DELTA']:.2f}")
    print(f"  DTE:        {t['DTE']:.0f}")
    print(f"  Expiration: {t['EXPIRE_DATE']}")
    print(f"  Strike:     ${t['STRIKE']}")
    print(f"  Assignment: ${capital_required:>8.2f}")
    print(f"  Premium:    ${premium * 100:>8.2f}")
    print(f"  P&L:        ${unrealized_pnl:>8.2f}")

print_trade(quote_start)

# %% Print the selected strike option value for the 10 days after the trade date
dates_after = sorted([
    d for d in df["QUOTE_DATE"].unique()
    if d >= trade_date
])[:11]  # trade date + 10 after

rows = []
for d in dates_after:
    q = quote_at_strike(d, expiration=quote_start["EXPIRE_DATE"], strike=quote_start["STRIKE"])
    if q is not None:
        rows.append({"QUOTE_DATE": d, "UNDERLYING_LAST": float(q["UNDERLYING_LAST"]), "P_LAST": float(q["P_LAST"])})

option_values = pd.DataFrame(rows)
option_values["QUOTE_DATE"] = pd.to_datetime(option_values["QUOTE_DATE"])
option_values["Premium P/L"] = (float(quote_start["P_LAST"]) - option_values["P_LAST"]) * 100
print(option_values.to_string(index=False))

# %% Plot
fig, ax1 = plt.subplots(figsize=(10, 5))

ax1.plot(option_values["QUOTE_DATE"], option_values["UNDERLYING_LAST"], color="steelblue", marker="o", label="Underlying")
ax1.set_ylabel("Underlying Price", color="steelblue")
ax1.tick_params(axis="y", labelcolor="steelblue")
ax1.axvline(pd.Timestamp(trade_date), color="gray", linestyle="--", linewidth=0.8, label="Trade date")

ax2 = ax1.twinx()
ax2.plot(option_values["QUOTE_DATE"], option_values["Premium P/L"], color="seagreen", marker="s", label="Premium P/L")
ax2.axhline(0, color="seagreen", linestyle=":", linewidth=0.8)
ax2.set_ylabel("Premium P/L ($)", color="seagreen")
ax2.tick_params(axis="y", labelcolor="seagreen")

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

plt.title(f"QQQ Short Put — Strike ${float(quote_start['STRIKE']):.0f}  Exp {quote_start['EXPIRE_DATE']}")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# %% Simulate trade

# Place trade
date_start = get_next_date("2021-03-01")
print(f"Simulating trade on {date_start}...")
quote_start = quote_at(date_start, target_delta=0.3, target_dte=30, side="P")
expiration_date = quote_start["EXPIRE_DATE"]
quote_strike    = quote_start["STRIKE"]
print_trade(quote_start)

# Check trade P/L after X days
days_passed = 10
current_date = get_next_date(pd.to_datetime(date_start) + pd.Timedelta(days=days_passed))
print(f"\nChecking trade after {days_passed} days on {current_date}...")
quote_current = quote_at_strike(current_date, expiration=expiration_date, strike=quote_strike)
print_trade(quote_current)

# Check trade P/L at expiration
print(f"\nChecking trade at expiration on {expiration_date}...")
quote_expiration = quote_at_strike(expiration_date, expiration=expiration_date, strike=quote_strike)
print_trade(quote_expiration)

# Premium P/L at expiration
premium_pl = (float(quote_start["P_LAST"]) - max(0, float(quote_strike) - float(quote_expiration["UNDERLYING_LAST"]))) * 100
print(f"\nPremium P/L at expiration: ${premium_pl:.2f}")

# Underlying change from trade date to expiration
underlying_change = float(quote_start["UNDERLYING_LAST"]) - float(quote_expiration["UNDERLYING_LAST"])
print(f"Underlying G/L: ${underlying_change:.2f}")

# Underlying difference to strike at expiration
underlying_to_strike = float(quote_expiration["UNDERLYING_LAST"]) - float(quote_strike)
print(f"Underlying to Strike: ${underlying_to_strike:.2f}")

# Assignment cost at expiration
assignment_cost = max(0, -underlying_to_strike * 100)
print(f"Assignment cost at expiration: ${assignment_cost:.2f}")

# Print underlying at start, underlying at expiration, premium at start, and premium at expiration
print(f"\nSummary:")
print(f"  Underlying start: ${float(quote_start['UNDERLYING_LAST']):.2f}")
print(f"  Underlying exp: ${float(quote_expiration['UNDERLYING_LAST']):.2f}")
print(f"  Premium at start: ${float(quote_start['P_LAST']) * 100:.2f}")
print(f"  Premium at exp: ${float(quote_expiration['P_LAST']) * 100:.2f}")

# Total P/L at expiration
total_pl = premium_pl - assignment_cost
print(f"Total P/L at expiration: ${total_pl:.2f}")


# %%
