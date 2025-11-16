# rsi_scanner.py
import streamlit as st
import pandas as pd
import requests
import urllib.parse
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator
import os

# -------------------------------------------------
# 1. SECRETS – work locally (secrets.toml) OR Cloud (env vars)
# -------------------------------------------------
def get_secret(key: str, default=None):
    """Read from st.secrets first, then os.environ."""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)

UPSTOX = {
    "api_key": get_secret("upstox.api_key"),
    "api_secret": get_secret("upstox.api_secret"),
    "access_token": get_secret("upstox.access_token")
}
SCANNER = {
    "unit": get_secret("scanner.unit", "minutes"),
    "interval": get_secret("scanner.interval", "1"),
    "lookback_bars": int(get_secret("scanner.lookback_bars", "100")),
    "rsi_period": int(get_secret("scanner.rsi_period", "14")),
    "rsi_oversold": int(get_secret("scanner.rsi_oversold", "30")),
    "rsi_overbought": int(get_secret("scanner.rsi_overbought", "70"))
}

# -------------------------------------------------
# 2. Instrument key mapping (add more as needed)
# -------------------------------------------------
INSTRUMENT_MAP = {
    "TCS.NS": "NSE_EQ|INE467B01029",
    "RELIANCE.NS": "NSE_EQ|INE002A01018",
    "HDFCBANK.NS": "NSE_EQ|INE040A01034",
    "INFY.NS": "NSE_EQ|INE090A01021",
}

def get_instrument_key(symbol: str) -> str:
    return INSTRUMENT_MAP.get(symbol, f"NSE_EQ|{symbol.replace('.NS', '')}")

# -------------------------------------------------
# 3. Fetch using exact v3 curl format
# -------------------------------------------------
def fetch(symbol: str):
    try:
        token = UPSTOX["access_token"]
        if not token:
            st.error("Missing access_token – add to secrets.toml or Cloud UI")
            return pd.DataFrame()

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        key = urllib.parse.quote(get_instrument_key(symbol))
        unit = SCANNER["unit"]
        interval = SCANNER["interval"]

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
        return df.tail(SCANNER["lookback_bars"])
    except Exception as e:
        st.error(f"[{symbol}] Error: {e}")
        return pd.DataFrame()

# -------------------------------------------------
# 4. RSI signal
# -------------------------------------------------
def get_signal(df: pd.DataFrame):
    if df.empty or len(df) < SCANNER["rsi_period"] + 1:
        return None
    rsi_val = RSIIndicator(close=df["close"], window=SCANNER["rsi_period"]).rsi().iloc[-1]
    price = df["close"].iloc[-1]
    if rsi_val < SCANNER["rsi_oversold"]:
        return "BUY", price, rsi_val
    if rsi_val > SCANNER["rsi_overbought"]:
        return "SELL", price, rsi_val
    return None

# -------------------------------------------------
# 5. Scan all stocks
# -------------------------------------------------
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
