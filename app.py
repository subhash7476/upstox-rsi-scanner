# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import time
from rsi_v3_scanner import scan_stocks

st.set_page_config(page_title="Upstox RSI v3 Scanner", layout="wide")
st.title("Live RSI Signals (Upstox API v3)")

# Sidebar
with st.sidebar:
    st.header("v3 Settings")
    st.write(f"**Time:** {datetime.now().strftime('%I:%M %p IST')}")
    auto = st.checkbox("Auto-refresh (60s)", True)
    if st.button("Refresh Now"):
        st.cache_data.clear()

# Cache scan
@st.cache_data(ttl=60)
def get_signals():
    return scan_stocks()

# Run scan
with st.spinner("Fetching v3 historical candles..."):
    df = get_signals()

# Display
if not df.empty:
    st.success(f"Found {len(df)} signal(s)")
    st.dataframe(df, use_container_width=True)
else:
    st.info("No RSI signals right now.")

# Auto-refresh
if auto:
    time.sleep(60)
    st.rerun()
