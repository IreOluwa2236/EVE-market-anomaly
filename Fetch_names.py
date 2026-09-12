import requests
import psycopg2
import os

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

conn = psycopg2.connect(
    host="localhost",
    database="eve_market",
    user="postgres",
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

# Get all unique type_ids we have data for
cur.execute("SELECT DISTINCT type_id FROM price_history")
type_ids = [row[0] for row in cur.fetchall()]

print(f"Fetching names for {len(type_ids)} items...")

success = 0
for i, type_id in enumerate(type_ids):
    try:
        url = f"https://esi.evetech.net/latest/universe/types/{type_id}/"
        response = requests.get(url)
        
        if response.status_code != 200:
            continue
            
        data = response.json()
        name = data.get('name', 'Unknown')
        
        cur.execute("""
            INSERT INTO item_names (type_id, name)
            VALUES (%s, %s)
            ON CONFLICT (type_id) DO NOTHING
        """, (type_id, name))
        
        success += 1
        
        if i % 100 == 0:
            conn.commit()
            print(f"Progress: {i}/{len(type_ids)} — {success} names fetched")
            
    except Exception:
        continue

conn.commit()
cur.close()
conn.close()

print(f"Done — {success} item names fetched")