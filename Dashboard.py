import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
import os

# .env reader
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            os.environ[key.strip()] = value.strip()

password = os.getenv("DB_PASSWORD")
engine = create_engine(f'postgresql://postgres:{password}@localhost/eve_market')

st.set_page_config(page_title="EVE Market Anomaly Detector", layout="wide")
st.title("🚀 EVE Online Market Anomaly Detector")
st.markdown("Real-time market manipulation and anomaly detection for Jita trade hub")

# Sidebar
st.sidebar.header("Search")
search_term = st.sidebar.text_input("Search item name", "Tritanium")

# Load matching items
@st.cache_data
def get_items():
    return pd.read_sql("SELECT type_id, name FROM item_names ORDER BY name", engine)

items_df = get_items()
filtered = items_df[items_df['name'].str.contains(search_term, case=False, na=False)]

if len(filtered) == 0:
    st.warning("No items found")
    st.stop()

selected_name = st.sidebar.selectbox("Select item", filtered['name'].tolist())
selected_id = filtered[filtered['name'] == selected_name]['type_id'].values[0]

# Load price history for selected item
@st.cache_data
def get_history(type_id):
    return pd.read_sql(f"""
        SELECT date, average, highest, lowest, volume, order_count
        FROM price_history
        WHERE type_id = {type_id}
        ORDER BY date
    """, engine)

@st.cache_data
def get_item_anomalies(type_id):
    return pd.read_sql(f"""
        SELECT date, average, price_change_pct, volume_change_pct, price_zscore
        FROM anomalies
        WHERE type_id = {type_id}
        ORDER BY date
    """, engine)

history = get_history(selected_id)
anomalies = get_item_anomalies(selected_id)

# Price chart
st.subheader(f"📈 Price History — {selected_name}")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=history['date'],
    y=history['average'],
    mode='lines',
    name='Average Price',
    line=dict(color='cyan', width=2)
))

fig.add_trace(go.Scatter(
    x=history['date'],
    y=history['highest'],
    mode='lines',
    name='Highest',
    line=dict(color='green', width=1, dash='dot')
))

fig.add_trace(go.Scatter(
    x=history['date'],
    y=history['lowest'],
    mode='lines',
    name='Lowest',
    line=dict(color='red', width=1, dash='dot')
))

# Highlight anomalies
if len(anomalies) > 0:
    anomaly_history = history[history['date'].isin(anomalies['date'])]
    fig.add_trace(go.Scatter(
        x=anomaly_history['date'],
        y=anomaly_history['average'],
        mode='markers',
        name='Anomaly Detected',
        marker=dict(color='yellow', size=10, symbol='star')
    ))

fig.update_layout(
    template='plotly_dark',
    xaxis_title='Date',
    yaxis_title='Price (ISK)',
    height=400
)

st.plotly_chart(fig, use_container_width=True)

# Volume chart
st.subheader("📊 Volume History")

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=history['date'],
    y=history['volume'],
    name='Volume',
    marker_color='steelblue'
))

fig2.update_layout(
    template='plotly_dark',
    xaxis_title='Date',
    yaxis_title='Volume',
    height=300
)

st.plotly_chart(fig2, use_container_width=True)

# Anomalies table
st.subheader("⚠️ Detected Anomalies for this Item")
if len(anomalies) > 0:
    st.dataframe(anomalies.style.highlight_max(axis=0), use_container_width=True)
else:
    st.success("No anomalies detected for this item")

# Top anomalies across all items
st.subheader("🔥 Top Anomalies Across All Items")
top_anomalies = pd.read_sql("""
    SELECT name, date, average, price_change_pct, volume_change_pct, price_zscore
    FROM anomalies
    ORDER BY volume_change_pct DESC
    LIMIT 50
""", engine)

st.dataframe(top_anomalies, use_container_width=True)