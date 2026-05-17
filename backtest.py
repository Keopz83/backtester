# %% Import libraries
import pandas as pd
import matplotlib.pyplot as plt
import importlib
import lib, execute, gridsearch
importlib.reload(lib)
importlib.reload(execute)
importlib.reload(gridsearch)
from gridsearch import *
from execute import *
from lib import *


# %% Load and prepare data
DATA_PATH = "data/qqq_2020_2022.csv"
df2 = load_data(DATA_PATH)


# %% Main execution

# Define a simple buy/sell condition and execute the strategy
#buy_condition = {'delta': 0.2, 'dte': 30}

# Define a set of buy conditions to test in the grid search
# buy_conditions = [
#     {'delta': 0.2, 'dte': 30},
#     {'delta': 0.3, 'dte': 30},
#     {'delta': 0.4, 'dte': 30},
#     {'delta': 0.3, 'dte': 45},
#     {'delta': 0.3, 'dte': 60},
# ]

# Define 10 buy conditions with fixed delta of 0.2 and dte from 7 to 70
#buy_conditions = [{'delta': 0.2, 'dte': dte} for dte in range(7, 71, 7)]
#buy_conditions = [{'delta': 0.2, 'dte': dte} for dte in [7, 30, 45, 90]]
buy_conditions = [{'delta': 0.2, 'dte': 90}]

#sell_condition = {'dte': 0, 'pct_profit': None, 'pct_loss': None}  # sell at expiration
sell_condition = {'dte': None, 'pct_profit': 50, 'pct_loss': None}  # sell at expiration

# simulate 60 different starting dates, radomized, between 2021-02-10 and 2022-11-01
start_dates = pd.date_range(start="2021-02-10", end="2022-11-01", freq='25D').to_pydatetime().tolist()
start_dates = [d.strftime("%Y-%m-%d") for d in start_dates]
# start_dates = ['2021-01-01']

# Run grid search and plot results
results = grid_search(df2, buy_conditions, sell_condition, start_dates, log = False)
plot_return_distribution(results, buy_conditions)
plot_mean_return_by_buy_condition(results, buy_conditions)

# %% save results to file
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

save_results(results, buy_conditions, sell_condition, start_dates)

# %%
