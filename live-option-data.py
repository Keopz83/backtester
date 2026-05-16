# %%
import yfinance as yf
import datetime

# %% Get the last price of the QQQ put option with a strike price of 710 and DTE of 30 days
# Get today's date
today = datetime.date.today()
# Get the option chain for QQQ
qqq = yf.Ticker("QQQ")
# Get the expiration dates for QQQ options
expiration_dates = qqq.options
# Find the expiration date that is closest to 30 days from today
target_date = today + datetime.timedelta(days=30)
closest_expiration = min(expiration_dates, key=lambda d: abs(datetime.datetime.strptime(d, "%Y-%m-%d").date() - target_date))
# Get the option chain for the closest expiration date
option_chain = qqq.option_chain(closest_expiration)
# Find the put option with a strike price of 710
put_option = option_chain.puts[option_chain.puts['strike'] == 710]
# Get the last price of the put option
if not put_option.empty:
    last_price = put_option['lastPrice'].values[0]
    print(f"The last price of the QQQ put option with a strike price of 710 and expiration date {closest_expiration} is: ${last_price}")
else:
    print(f"No put option found for QQQ with a strike price of 710 and expiration date {closest_expiration}.")



# %%
