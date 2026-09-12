import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import create_engine
import os

# Manual .env reader
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

# Connect to database
password = os.getenv("DB_PASSWORD")
engine = create_engine(f'postgresql://postgres:{password}@localhost/eve_market')

# Pull price history into a dataframe
query = """
    SELECT 
        type_id,
        date,
        average,
        highest,
        lowest,
        volume,
        order_count
    FROM price_history
    ORDER BY type_id, date
"""

print("Loading data from database...")
df = pd.read_sql(query, engine)
print(f"Loaded {len(df)} rows for {df['type_id'].nunique()} items")
print(df.head())
print(df.columns)

# Engineer features
def engineer_features(group):
    group = group.copy()
    group = group.sort_values('date')
    group['price_change_pct'] = group['average'].pct_change() * 100
    group['volume_change_pct'] = group['volume'].pct_change() * 100
    group['price_rolling_mean'] = group['average'].rolling(7).mean()
    group['price_rolling_std'] = group['average'].rolling(7).std()
    group['price_zscore'] = (group['average'] - group['price_rolling_mean']) / group['price_rolling_std']
    group['spread'] = group['highest'] - group['lowest']
    group['spread_pct'] = (group['spread'] / group['average']) * 100
    return group

print("Engineering features...")
df = df.groupby('type_id', group_keys=True).apply(engineer_features).reset_index(level=0)
print(df.columns.tolist())
df = df.dropna()
print(f"After feature engineering: {len(df)} rows")

# Run Isolation Forest
features = ['price_change_pct', 'volume_change_pct', 'price_zscore', 'spread_pct']
X = df[features]

print("Running Isolation Forest...")
iso_forest = IsolationForest(
    contamination=0.02,
    random_state=42,
    n_estimators=100
)

df['anomaly_score'] = iso_forest.fit_predict(X)
df['anomaly'] = df['anomaly_score'] == -1

anomalies = df[df['anomaly'] == True]
print(f"Found {len(anomalies)} anomalies out of {len(df)} data points")


""""
print("\nTop 20 most suspicious price movements:")
top_anomalies = anomalies.nlargest(20, 'price_zscore')[
    ['type_id', 'date', 'average', 'price_change_pct',
     'volume_change_pct', 'price_zscore']
]
print(top_anomalies.to_string()) 
""" 

# Load item names
names_df = pd.read_sql("SELECT type_id, name FROM item_names", engine)

# Merge anomalies with names
anomalies = anomalies.merge(names_df, on='type_id', how='left')

print("\nTop 20 by price change:")
top_price = anomalies.nlargest(20, 'price_change_pct')[
    ['name', 'type_id', 'date', 'average', 'price_change_pct', 
     'volume_change_pct', 'price_zscore']
]
print(top_price.to_string())

print("\nTop 20 by volume change:")
top_volume = anomalies.nlargest(20, 'volume_change_pct')[
    ['name', 'type_id', 'date', 'average', 'price_change_pct',
     'volume_change_pct', 'price_zscore']
]
print(top_volume.to_string()) 




# Save anomalies to database
print("\nSaving anomalies to database...")

from sqlalchemy import text

with engine.connect() as conn_sa:
    conn_sa.execute(text("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id SERIAL PRIMARY KEY,
            type_id INTEGER,
            name VARCHAR(255),
            date DATE,
            average NUMERIC,
            price_change_pct NUMERIC,
            volume_change_pct NUMERIC,
            price_zscore NUMERIC,
            detected_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn_sa.execute(text("DELETE FROM anomalies"))
    conn_sa.commit()

anomalies_to_save = anomalies[['type_id', 'name', 'date', 'average', 
                                'price_change_pct', 'volume_change_pct', 
                                'price_zscore']].copy()

anomalies_to_save.to_sql('anomalies', engine, if_exists='append', index=False)
print(f"Saved {len(anomalies_to_save)} anomalies to database")