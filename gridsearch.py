# Import libraries
import pandas as pd
import matplotlib.pyplot as plt
from execute import *

# Grid search over buy condition and start date
def grid_search(data, buy_conditions, sell_condition, start_dates, log = False):
    """Run grid search over buy conditions and start dates, returning a list of results."""

    # Implement grid search over buy conditions and start dates
    total = len(buy_conditions) * len(start_dates)
    done = 0
    results = []
    for buy_cond in buy_conditions:
        for start_date in start_dates:
            done += 1
            print(f"\r  {done}/{total}  delta={buy_cond['delta']} dte={buy_cond['dte']} start={start_date}", end="", flush=True)
            result = execute_strategy(data, buy_cond, sell_condition, date=start_date, log = log)
            result["buy_condition"] = buy_cond
            result["start_date"] = start_date
            results.append(result)
    print()
    return results


# Plot 2D bubble chart where x is delta, y is dte, bubble size is return, and color is start date
def plot_grid_search_results(results):
    import matplotlib.dates as mdates
    fig, ax = plt.subplots(figsize=(10, 6))
    for res in results:
        buy_cond = res["buy_condition"]
        start_date = pd.to_datetime(res["start_date"])
        ret = res["accrued_pl"] / res["max_capital"] * 100 if res["max_capital"] > 0 else 0
        ax.scatter(buy_cond['delta'], buy_cond['dte'], s=abs(ret)*10, color=plt.cm.viridis(mdates.date2num(start_date) / mdates.date2num(pd.to_datetime("2022-12-31"))), alpha=0.6) 
    ax.set_xlabel("Target Delta")
    ax.set_ylabel("Target DTE")
    ax.set_title("Grid Search Results: Return by Buy Condition and Start Date")
    ax.grid(True, alpha=0.3)
    sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis, norm=plt.Normalize(vmin=mdates.date2num(pd.to_datetime("2021-01-01")), vmax=mdates.date2num(pd.to_datetime("2022-12-31"))))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label("Start Date")
    plt.show()

# Plot return distribution as histogram for each of the 5 buy conditions
def plot_return_distribution(results, buy_conditions):
    fig, axes = plt.subplots(len(buy_conditions), 1, figsize=(10, 4 * len(buy_conditions)), sharex=True, squeeze=False)
    axes = axes[:, 0]
    for ax, buy_cond in zip(axes, buy_conditions):
        cond_results = [res for res in results if res["buy_condition"] == buy_cond]
        returns = [res["accrued_pl"] / res["max_capital"] * 100 if res["max_capital"] > 0 else 0 for res in cond_results]
        mean_val = np.mean(returns) if returns else 0
        ax.hist(returns, bins=20, label=f"Mean: {mean_val:.2f}%")
        ax.set_title(f"Delta={buy_cond['delta']}, DTE={buy_cond['dte']}")
        ax.set_ylabel("Count")
        ax.legend()
    axes[-1].set_xlabel("Return (%)")
    fig.suptitle("Return Distribution by Buy Condition")
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.show()

# Plot mean by buy condition
def plot_mean_return_by_buy_condition(results, buy_conditions):
    mean_returns = []
    for buy_cond in buy_conditions:
        cond_results = [res for res in results if res["buy_condition"] == buy_cond]
        returns = [res["accrued_pl"] / res["max_capital"] * 100 if res["max_capital"] > 0 else 0 for res in cond_results]
        mean_val = np.mean(returns) if returns else 0
        mean_returns.append(mean_val)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(range(len(buy_conditions)), mean_returns, color="steelblue")
    ax.set_xticks(range(len(buy_conditions)))
    ax.set_xticklabels([f"Δ={bc['delta']}, DTE={bc['dte']}" for bc in buy_conditions], rotation=45)
    ax.set_ylabel("Mean Return (%)")
    ax.set_title("Mean Return by Buy Condition")
    plt.tight_layout()
    plt.show()