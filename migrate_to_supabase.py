import pandas as pd
from sqlalchemy import create_engine, text
import os

# .env reader
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))
print("SUPABASE_URL:", os.getenv("SUPABASE_URL"))

# Local database
local_engine = create_engine(f'postgresql://postgres:{os.getenv("DB_PASSWORD")}@localhost/eve_market')

# Supabase database
supabase_engine = create_engine(os.getenv("SUPABASE_URL"))

# Drop and recreate tables cleanly
print("Dropping and recreating tables...")
with supabase_engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS anomalies"))
    conn.execute(text("DROP TABLE IF EXISTS price_history"))
    conn.execute(text("DROP TABLE IF EXISTS item_names"))
    conn.execute(text("""
        CREATE TABLE item_names (
            type_id INTEGER PRIMARY KEY,
            name VARCHAR(255)
        )
    """))
    conn.execute(text("""
        CREATE TABLE price_history (
            id SERIAL PRIMARY KEY,
            type_id INTEGER,
            date DATE,
            average NUMERIC,
            highest NUMERIC,
            lowest NUMERIC,
            order_count BIGINT,
            volume BIGINT,
            fetched_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE TABLE anomalies (
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
    conn.commit()
print("Tables recreated cleanly")

# Migrate item_names
print("Migrating item names...")
names_df = pd.read_sql("SELECT * FROM item_names", local_engine)
names_df.to_sql('item_names', supabase_engine, if_exists='append', index=False, chunksize=1000)
print(f"Migrated {len(names_df)} item names")

# Migrate anomalies
print("Migrating anomalies...")
anomalies_df = pd.read_sql("""
    SELECT type_id, name, date, average, price_change_pct, volume_change_pct, price_zscore 
    FROM anomalies
""", local_engine)
anomalies_df.to_sql('anomalies', supabase_engine, if_exists='append', index=False, chunksize=1000)
print(f"Migrated {len(anomalies_df)} anomalies")

# Migrate price history in chunks
print("Migrating price history (this will take a while)...")
chunk_size = 10000
offset = 0
total = 0

while True:
    chunk = pd.read_sql(f"""
        SELECT type_id, date, average, highest, lowest, order_count, volume
        FROM price_history
        LIMIT {chunk_size} OFFSET {offset}
    """, local_engine)
    
    if len(chunk) == 0:
        break
        
    chunk.to_sql('price_history', supabase_engine, if_exists='append', index=False, chunksize=1000)
    total += len(chunk)
    offset += chunk_size
    print(f"Migrated {total} price history rows...")

print(f"Done — migrated {total} total price history rows")