# %% Import libraries
import pandas as pd
import matplotlib.pyplot as plt
import time
from lib import *

try:
    profile
except NameError:
    def profile(func):
        return func

# %% Strategy execution engine with conditions
@profile
def execute_strategy(df, buy_condition, sell_condition):
    """Execute the short put strategy with the given buy and sell conditions."""
    # This function will implement the backtesting loop based on the specified conditions.
    
    # Execution loop
    # set current_date to min date in df
    current_date = get_next_date(df2, df["QUOTE_DATE"].min())
    start_date = pd.to_datetime(current_date)
    # set end_date to max date in df
    end_date = pd.to_datetime(get_next_date(df2, df["QUOTE_DATE"].max()))

    #end_date = pd.to_datetime(df["QUOTE_DATE"].iloc[-1]) #pd.to_datetime("2021-12-31") 
    accrued_pl = 0.0
    max_capital = 0.0
    log = False
    trades = []
    while True:

        # Execute next condition: sell put on next available date
        quote_open = quote_at(df2, current_date, target_delta=buy_condition['delta'], target_dte=buy_condition['dte'], side="P")
        max_capital = max(max_capital, quote_open["STRIKE"] * 100)
        if log: print_short_put(quote_open)
        trades.append(f"Sell put on {current_date}")

        # Execute next condition: sell at expiration
        close_date = get_next_date(df2, quote_open["EXPIRE_DATE"])
        quote_close = quote_at_strike(df2, close_date, close_date, quote_open["STRIKE"])    
        if quote_close is None:
            if log: print(f"  Skipping: no close quote found for {close_date}")
            current_date = get_next_date(df2, pd.to_datetime(current_date) + pd.Timedelta(days=30))
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

        # Execute next condition (simply repeat)
        # set current date to next buy date (e.g. next month) and repeat
        current_date = get_next_date(df2, pd.to_datetime(current_date) + pd.Timedelta(days=30))
        if current_date is None or pd.to_datetime(current_date) > end_date:
            break

    print(f"\nSummary: {start_date.date()} to {end_date.date()}")
    print(f"  Total P/L:        ${accrued_pl:.2f}")
    print(f"  Max capital req:  ${max_capital:.2f}")
    print(f"  Return:           {accrued_pl / max_capital * 100:.2f}%")



if __name__ == "__main__":

    # example usage:
    DATA_PATH = "data/qqq_2020_2022.csv"
    df2 = load_data(DATA_PATH)

    buy_condition = {'delta': 0.3, 'dte': 30}
    sell_condition = {'dte': 0} # sell at expiration
    execute_strategy(df2, buy_condition, sell_condition)

# %%
