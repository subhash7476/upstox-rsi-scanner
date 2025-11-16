# rsi_scanner.py
import streamlit as st
import pandas as pd
import requests
import urllib.parse
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator

# --- Instrument key mapping (add more as needed) ---
INSTRUMENT_MAP = {
    "TCS.NS": "NSE_EQ|INE467B01029",
    "RELIANCE.NS": "NSE_EQ|INE002A01018",
    "HDFCBANK.NS": "NSE_EQ|INE040A01034",
    "INFY.NS": "NSE_EQ|INE090A01021",
    # Add others here
}

def get_instrument_key(symbol: str) -> str:
    return INSTRUMENT_MAP.get(symbol, f"NSE_EQ|{symbol.replace('.NS', '')}")

def fetch(symbol: str):
    try:
        cfg = st.secrets
        token = cfg["upstox"]["access_token"]
        end = datetime.now().strftime("%Y-%m-%d")  # to_date
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")  # from_date

        key = urllib.parse.quote(get_instrument_key(symbol))
        unit = cfg["scanner"]["unit"]
        interval = cfg["scanner"]["interval"]

        # EXACT curl format from Upstox v3 docs
        url = f"https://api.upstox.com/v3/historical-candle/{key}/{unit}/{interval}/{end}/{start}"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            st.error(f"[{symbol}] API {resp.status_code}: {resp.text}")
            return pd.DataFrame()

        data = resp.json()
        if not data.get("data", {}).get("candles"):
            return pd.DataFrame()

        df = pd.DataFrame(
            data["data"]["candles"],
            columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float).sort_index()
        return df.tail(int(cfg["scanner"]["lookback_bars"]))
    except Exception as e:
        st.error(f"[{symbol}] Error: {e}")
        return pd.DataFrame()

def get_signal(df: pd.DataFrame):
    if df.empty or len(df) < int(st.secrets["scanner"]["rsi_period"]) + 1:
        return None
    rsi_val = RSIIndicator(close=df["close"], window=int(st.secrets["scanner"]["rsi_period"])).rsi().iloc[-1]
    price = df["close"].iloc[-1]
    if rsi_val < int(st.secrets["scanner"]["rsi_oversold"]):
        return "BUY", price, rsi_val
    if rsi_val > int(st.secrets["scanner"]["rsi_overbought"]):
        return "SELL", price, rsi_val
    return None

def scan_stocks():
    with open("stocks.txt") as f:
        symbols = [line.strip() for line in f if line.strip()]
    signals = []
    for sym in symbols:
        df = fetch(sym)
        sig = get_signal(df)
        if sig:
            action, price, rsi = sig
            signals.append({
                "Symbol": sym.replace(".NS", ""),
                "Action": action,
                "Price": f"₹{price:,.2f}",
                "RSI": f"{rsi:.1f}"
            })
    return pd.DataFrame(signals) if signals else pd.DataFrame()
