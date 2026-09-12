import requests
import psycopg2
import time
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host="localhost",
    database="eve_market",
    user="postgres",
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

cur.execute("SELECT DISTINCT type_id FROM market_orders")
type_ids = [row[0] for row in cur.fetchall()]

print(f"Fetching history for {len(type_ids)} items...")

success = 0
failed = 0

for i, type_id in enumerate(type_ids):
    try:
        url = f"https://esi.evetech.net/latest/markets/10000002/history/?type_id={type_id}"
        response = requests.get(url)
        
        if response.status_code != 200:
            failed += 1
            continue
            
        history = response.json()
        
        for entry in history:
            cur.execute("""
                INSERT INTO price_history 
                (type_id, date, average, highest, lowest, order_count, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (type_id, date) DO NOTHING
            """, (
                type_id,
                entry['date'],
                entry['average'],
                entry['highest'],
                entry['lowest'],
                entry['order_count'],
                entry['volume']
            ))
        
        success += 1
        
        if i % 100 == 0:
            conn.commit()
            print(f"Progress: {i}/{len(type_ids)} items — {success} success, {failed} failed")
        
        time.sleep(0.1)
        
    except Exception as e:
        failed += 1
        continue

conn.commit()
cur.close()
conn.close()

print(f"Done — {success} items fetched, {failed} failed")