import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
import os

# .env reader for local development
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Connection — try Streamlit secrets first, then env, then local
try:
    supabase_url = st.secrets["SUPABASE_URL"]
except:
    supabase_url = os.getenv("SUPABASE_URL")

local_url = f'postgresql://postgres:{os.getenv("DB_PASSWORD")}@localhost/eve_market'
engine = create_engine(supabase_url if supabase_url else local_url)

# Page config
st.set_page_config(page_title="EVE Market Anomaly Detector", layout="wide",page_icon=":globe_with_meridians:")
st.title("⚔️ EVE Online Market Anomaly Detector")
st.markdown("Real-time market manipulation and anomaly detection for the Jita trade hub")

# Sidebar search
st.sidebar.header("🔍 Search Items")
search_term = st.sidebar.text_input("Item name", "Tritanium")

# Load all item names
@st.cache_data
def get_items():
    return pd.read_sql("SELECT type_id, name FROM item_names ORDER BY name", engine)

items_df = get_items()
filtered = items_df[items_df['name'].str.contains(search_term, case=False, na=False)]

if len(filtered) == 0:
    st.warning("No items found — try a different search term")
    st.stop()

selected_name = st.sidebar.selectbox("Select item", filtered['name'].tolist())
selected_id = int(filtered[filtered['name'] == selected_name]['type_id'].values[0])

# Item header with image
col1, col2 = st.columns([1, 8])
with col1:
    st.image(
        f"https://images.evetech.net/types/{selected_id}/icon",
        width=64
    )
with col2:
    st.subheader(selected_name)

# Load data
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

# Item overview stats
if len(history) > 0:
    latest = history.iloc[-1]
    prev = history.iloc[-2] if len(history) > 1 else latest

    price_change = ((latest['average'] - prev['average']) / prev['average']) * 100
    avg_30d = history.tail(30)['average'].mean()
    avg_volume_30d = history.tail(30)['volume'].mean()
    total_anomalies = len(anomalies)

    st.subheader("📋 Item Overview")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Latest Price",
            value=f"{latest['average']:,.2f} ISK",
            delta=f"{price_change:.2f}%"
        )
    with col2:
        st.metric(
            label="30-Day Avg Price",
            value=f"{avg_30d:,.2f} ISK"
        )
    with col3:
        st.metric(
            label="Latest Volume",
            value=f"{int(latest['volume']):,}"
        )
    with col4:
        st.metric(
            label="30-Day Avg Volume",
            value=f"{int(avg_volume_30d):,}"
        )
    with col5:
        st.metric(
            label="Anomalies Detected",
            value=total_anomalies
        )

# Price chart
st.subheader("📈 Price History")

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

if len(anomalies) > 0:
    anomaly_history = history[history['date'].isin(anomalies['date'])]
    fig.add_trace(go.Scatter(
        x=anomaly_history['date'],
        y=anomaly_history['average'],
        mode='markers',
        name='⚠️ Anomaly',
        marker=dict(color='yellow', size=10, symbol='star')
    ))

fig.update_layout(
    template='plotly_dark',
    xaxis_title='Date',
    yaxis_title='Price (ISK)',
    height=400,
    legend=dict(orientation='h', yanchor='bottom', y=1.02)
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

# Anomalies table for selected item
st.subheader("⚠️ Detected Anomalies for this Item")
if len(anomalies) > 0:
    st.dataframe(anomalies, use_container_width=True)
else:
    st.success("✅ No anomalies detected for this item")

# Top anomalies across all items
st.subheader("🔥 Top Anomalies Across All Items")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**By Price Change**")
    top_price = pd.read_sql("""
        SELECT name, date, average, price_change_pct, price_zscore
        FROM anomalies
        ORDER BY price_change_pct DESC
        LIMIT 25
    """, engine)
    st.dataframe(top_price, use_container_width=True)

with col2:
    st.markdown("**By Volume Change**")
    top_volume = pd.read_sql("""
        SELECT name, date, average, volume_change_pct, price_zscore
        FROM anomalies
        ORDER BY volume_change_pct DESC
        LIMIT 25
    """, engine)
    st.dataframe(top_volume, use_container_width=True)