# %% Import libraries
import pandas as pd
import matplotlib.pyplot as plt
from lib import *
from execute import *
from gridsearch import *


# %% Load and prepare data
DATA_PATH = "data/qqq_2020_2022.csv"
df2 = load_data(DATA_PATH)


# %% Main execution

# Define a simple buy/sell condition and execute the strategy
buy_condition = {'delta': 0.3, 'dte': 30}
sell_condition = {'dte': 0}  # sell at expiration
result = execute_strategy(df2, buy_condition, sell_condition)
plot_strategy(df2, result)

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
buy_conditions = [{'delta': 0.2, 'dte': dte} for dte in [7, 14, 30, 45]]

# simulate 60 different starting dates, radomized, between 2021-02-10 and 2022-11-01
# start_dates = pd.date_range(start="2021-02-10", end="2022-11-01", freq='7D').to_pydatetime().tolist()
# start_dates = [d.strftime("%Y-%m-%d") for d in start_dates]
start_dates = ['2021-01-01']

# Run grid search and plot results
results = grid_search(df2, buy_conditions, sell_condition, start_dates)
plot_return_distribution(results, buy_conditions)
plot_mean_return_by_buy_condition(results, buy_conditions)

# save results to file
results_df = pd.DataFrame(results)
import os
if not os.path.exists("results"):
    os.makedirs("results")
results_df.to_csv("results/grid_search_results.csv", index=False)

# %%
