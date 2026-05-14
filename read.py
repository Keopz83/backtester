# %% Import libraries
import pandas as pd
import matplotlib.pyplot as plt

# %% Load and clean data
DATA_PATH = "data/qqq_2020_2022.csv"

df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip().str.strip("[]")
df["QUOTE_DATE"] = df["QUOTE_DATE"].str.strip()
df["DTE"] = pd.to_numeric(df["DTE"], errors="coerce")

# %% Display options chain for a specific date, DTE, and delta range
DATE = "2021-03-01"  # change this to the desired date (YYYY-MM-DD)
DTE = 30            # filter by DTE (e.g. 30); set to None to show all expirations
DELTA_MIN = 0.3    # min absolute delta, e.g. 0.20 — applies to both calls and puts
DELTA_MAX = 0.5    # max absolute delta, e.g. 0.50

chain = df[df["QUOTE_DATE"] == DATE].copy()

if DTE is not None:
    chain = chain[chain["DTE"].round().eq(DTE)]

if DELTA_MIN is not None or DELTA_MAX is not None:
    chain["C_DELTA"] = pd.to_numeric(chain["C_DELTA"], errors="coerce")
    chain["P_DELTA"] = pd.to_numeric(chain["P_DELTA"], errors="coerce")
    lo, hi = (DELTA_MIN or 0.0), (DELTA_MAX or 1.0)
    call_mask = chain["C_DELTA"].abs().between(lo, hi)
    put_mask  = chain["P_DELTA"].abs().between(lo, hi)
    chain = chain[call_mask | put_mask]

if chain.empty:
    print(f"No data found for {DATE}"
          + (f"  DTE={DTE}" if DTE is not None else "")
          + (f"  delta=[{DELTA_MIN}, {DELTA_MAX}]" if DELTA_MIN is not None or DELTA_MAX is not None else ""))
else:
    cols = [
        "EXPIRE_DATE", "DTE", "STRIKE", "UNDERLYING_LAST",
        "C_BID", "C_ASK", "C_LAST", "C_IV", "C_DELTA", "C_VOLUME",
        "P_BID", "P_ASK", "P_LAST", "P_IV", "P_DELTA", "P_VOLUME",
    ]
    dte_info   = f"  DTE={DTE}" if DTE is not None else ""
    delta_info = f"  delta=[{DELTA_MIN}, {DELTA_MAX}]" if DELTA_MIN is not None or DELTA_MAX is not None else ""
    print(f"QQQ Option Chain — {DATE}{dte_info}{delta_info}  (underlying: {chain['UNDERLYING_LAST'].iloc[0]})")
    print(chain[cols].sort_values(["EXPIRE_DATE", "STRIKE"]).to_string(index=False))

# %% Compact view
small = chain[["STRIKE", "C_DELTA", "C_LAST"]].sort_values("STRIKE").reset_index(drop=True)
print(small.to_string(index=False))

# %% Simulate a short put trade with on 2021-03-31, delta ~0.3, and DTE ~30 days
trade_date = "2021-03-31"
trade_chain = df[df["QUOTE_DATE"] == trade_date].copy()
trade_chain["P_DELTA"] = pd.to_numeric(trade_chain["P_DELTA"], errors="coerce")
trade_chain["DTE"] = pd.to_numeric(trade_chain["DTE"], errors="coerce")
trade_chain = trade_chain[trade_chain["DTE"].round().eq(30)]
trade_chain["delta_diff"] = (trade_chain["P_DELTA"].abs() - 0.3).abs()
trade = trade_chain.sort_values("delta_diff").iloc[0]
# print the total premium and capital at risk for the trade
def print_trade(t):
    premium          = float(t["P_LAST"])
    capital_required = float(t["STRIKE"]) * 100
    unrealized_pnl   = (premium - max(0, float(t["STRIKE"]) - float(t["UNDERLYING_LAST"]))) * 100
    print(f"Simulated trade: Short 1 QQQ put")
    print(f"  Delta:      {t['P_DELTA']:.2f}")
    print(f"  DTE:        {t['DTE']:.0f}")
    print(f"  Expiration: {t['EXPIRE_DATE']}")
    print(f"  Strike:     ${t['STRIKE']}")
    print(f"  Assignment: ${capital_required:>8.2f}")
    print(f"  Premium:    ${premium * 100:>8.2f}")
    print(f"  P&L:        ${unrealized_pnl:>8.2f}")

print_trade(trade)

# %% Print the selected strike option value for the 10 days after the trade date
expiration = trade["EXPIRE_DATE"]
option_values = df[(df["EXPIRE_DATE"] == expiration) & (df["STRIKE"] == trade["STRIKE"])][["QUOTE_DATE", "UNDERLYING_LAST", "P_LAST"]].copy()
option_values["QUOTE_DATE"] = pd.to_datetime(option_values["QUOTE_DATE"])
after  = option_values[option_values["QUOTE_DATE"] > pd.Timestamp(trade_date)].sort_values("QUOTE_DATE").head(10)
on_date = option_values[option_values["QUOTE_DATE"] == pd.Timestamp(trade_date)]
option_values = pd.concat([on_date, after]).reset_index(drop=True)
option_values["P_LAST"] = pd.to_numeric(option_values["P_LAST"], errors="coerce")
option_values["Premium P/L"] = (float(trade["P_LAST"]) - option_values["P_LAST"]) * 100
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

plt.title(f"QQQ Short Put — Strike ${float(trade['STRIKE']):.0f}  Exp {trade['EXPIRE_DATE']}")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# %%
