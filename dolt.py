# %% """Quick test: read option_chain table from Dolt SQL server running in WSL."""
import pandas as pd
import sqlalchemy

# Dolt sql-server uses the MySQL protocol.
# From Windows, WSL2 is reachable via localhost on the same port.
DOLT_URL = "mysql+pymysql://root@localhost:3306/options"

engine = sqlalchemy.create_engine(DOLT_URL)

with engine.connect() as conn:
    df = pd.read_sql("SELECT * FROM option_chain LIMIT 10", conn)

print(df.shape)
print(df.head())

# %% Print min max dates
with engine.connect() as conn:
    min_date = pd.read_sql("SELECT MIN(date) AS min_date FROM option_chain", conn)["min_date"][0]
    max_date = pd.read_sql("SELECT MAX(date) AS max_date FROM option_chain", conn)["max_date"][0]
print(f"Data date range: {min_date} to {max_date}")

# %% Print unique act_symbol values
with engine.connect() as conn:
    act_symbols = pd.read_sql("SELECT DISTINCT act_symbol FROM option_chain", conn)["act_symbol"].tolist()
print(f"Unique act_symbol values: {act_symbols}")
n_symbols = len(act_symbols)
print(f"Number of unique act_symbol values: {n_symbols}")

# %% Print size of option_chain table. Format number with commas.
with engine.connect() as conn:
    row_count = pd.read_sql("SELECT COUNT(*) AS row_count FROM option_chain", conn)["row_count"][0]
print(f"Number of rows in option_chain table: {row_count:,}")

# %% Print 10 first values for act_symbol NVDA
with engine.connect() as conn:
    nvda_df = pd.read_sql("SELECT * FROM option_chain WHERE act_symbol = 'NVDA' LIMIT 10", conn)
print(nvda_df)

# %% Summray information
print(f"Data date range: {min_date} to {max_date}")
print(f"Number of unique act_symbol values: {n_symbols}")
print(f"Number of rows in option_chain table: {row_count:,}")
print(nvda_df)

# %% Print the db size in MB via sql query
with engine.connect() as conn:
    db_size_mb = pd.read_sql("SELECT SUM(data_length + index_length) / 1024 / 1024 AS size_mb FROM information_schema.tables WHERE table_schema = 'options'", conn)["size_mb"][0]
print(f"Size of options database: {db_size_mb:.2f} MB")
# %%
