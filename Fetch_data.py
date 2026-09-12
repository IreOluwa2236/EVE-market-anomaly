import requests
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

conn = psycopg2.connect(
    host="localhost",
    database="eve_market",
    user="postgres",
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

def fetch_all_orders():
    page = 1
    all_orders = []
    
    while True:
        url = f"https://esi.evetech.net/latest/markets/10000002/orders/?order_type=all&page={page}"
        response = requests.get(url)
        
        if response.status_code != 200 or len(response.json()) == 0:
            break
            
        orders = response.json()
        all_orders.extend(orders)
        print(f"Fetched page {page} — {len(orders)} orders")
        page += 1
    
    return all_orders

orders = fetch_all_orders()

inserted = 0
for order in orders:
    cur.execute("""
        INSERT INTO market_orders 
        (order_id, type_id, price, volume_remain, is_buy_order, location_id, issued, duration)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (order_id) DO NOTHING
    """, (
        order['order_id'],
        order['type_id'],
        order['price'],
        order['volume_remain'],
        order['is_buy_order'],
        order['location_id'],
        order['issued'],
        order['duration']
    ))
    inserted += 1

conn.commit()
cur.close()
conn.close()

print(f"Done — inserted {inserted} total orders")