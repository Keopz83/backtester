# %% Read
import pandas as pd

# %%
DATA_PATH = "data/qqq_2020_2022.csv"

df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip().str.strip("[]")
df["QUOTE_DATE"] = df["QUOTE_DATE"].str.strip()
df["DTE"] = pd.to_numeric(df["DTE"], errors="coerce")

# %%
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

# %%
