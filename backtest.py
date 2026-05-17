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

# %% Define strategy
strategy_puts1 = {
    'type': 'short_put',
    'buy_condition': {'delta': 0.2, 'dte': 90},
    'sell_condition': {'dte': None, 'pct_profit': 80, 'pct_loss': None},
}

strategy_puts2 = {
    'type': 'short_put',
    'buy_condition': {'delta': 0.2, 'dte': 30},
    'sell_condition': {'dte': None, 'pct_profit': 80, 'pct_loss': 50},
}

strategy_puts3 = {
    'type': 'short_put',
    'buy_condition': {'delta': 0.2, 'dte': 90},
    'sell_condition': {'dte': None, 'pct_profit': 50, 'pct_loss': 20},
}

strategy_wheel = {
    'type': 'wheel',
    'put_condition':  {'delta': 0.2, 'dte': 90},
    'call_condition': {'delta': 0.2, 'dte': 90},
    'sell_condition': {'pct_profit': 80, 'pct_loss': None},
}

strategy = strategy_wheel


# Run strategy once with the first buy condition and starting date, to verify it works
start_date = "2021-01-01"
result = execute_strategy(df2, strategy, date=start_date, log = True)
print(result)
plot_strategy(df2, result)

# %% Run grid search and plot results

# simulate 60 different starting dates, radomized, between 2021-02-10 and 2022-11-01
start_dates = pd.date_range(start="2021-02-10", end="2022-11-01", freq='25D').to_pydatetime().tolist()
start_dates = [d.strftime("%Y-%m-%d") for d in start_dates]
# start_dates = ['2021-01-01']

buy_conditions = [strategy['buy_condition']]
sell_condition = strategy['sell_condition']
results = grid_search(df2, buy_conditions, sell_condition, start_dates, log = False)
plot_return_distribution(results, buy_conditions)
plot_mean_return_by_buy_condition(results, buy_conditions)

# %% save results to file
save_results(results, buy_conditions, sell_condition, start_dates)

# %%
