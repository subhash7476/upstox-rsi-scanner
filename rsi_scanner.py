# rsi_v3_scanner.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from upstox_client import ApiClient, Configuration, HistoricalDataApi, InstrumentsApi
from ta.momentum import RSIIndicator
import requests  # For raw v3 call if SDK fallback needed

def get_upstox_client():
    cfg = st.secrets["upstox"]
    conf = Configuration()
    conf.api_key = cfg["api_key"]
    conf.api_secret = cfg["api_secret"]
    conf.access_token = cfg["access_token"]
    return ApiClient(conf)

def get_instrument_key(client: ApiClient, symbol: str) -> str:
    """Fetch full NSE_EQ|INE... key via Instruments API."""
    try:
        inst_api = InstrumentsApi(client)
        # Query by symbol (e.g., "RELIANCE")
        resp = inst_api.get_instrument_by_symbol(exchange_segment="NSE_EQ", symbol=symbol.replace(".NS", ""))
        if resp.data and len(resp.data) > 0:
            return resp.data[0].instrument_key
        st.warning(f"No key found for {symbol}; using fallback.")
    except Exception as e:
        st.warning(f"Instruments API error for {symbol}: {e}")
    # Fallback: Manual NSE_EQ|SYMBOL
    return f"NSE_EQ|{symbol.replace('.NS', '')}"

def fetch_v3(symbol: str):
    try:
        client = get_upstox_client()
        hist_api = HistoricalDataApi(client)
        cfg = st.secrets["scanner"]
        
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")  # v3 limit: 1 year for 5-min
        
        instrument_key = get_instrument_key(client, symbol)
        unit = cfg["unit"]  # e.g., "minutes"
        interval = cfg["interval"]  # e.g., "5" (number)
        
        # v3 SDK call (maps to /v3/historical-candle/{key}/{unit}/{interval}/{to}/{from})
        data = hist_api.get_historical_candle_data(
            instrument_key=instrument_key,
            unit=unit,  # New v3 param
            interval=interval,  # Numeric string
            from_date=start,  # YYYY-MM-DD
            to_date=end
        )
        
        if not data.data or not data.data.candles:
            # Fallback: Raw curl equivalent (if SDK buggy)
            headers = {
                "Authorization": f"Bearer {st.secrets['upstox']['access_token']}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            url = f"https://api.upstox.com/v3/historical-candle/{instrument_key}/{unit}/{interval}/{end}/{start}"
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                st.error(f"v3 Raw API error {resp.status_code}: {resp.text}")
                return pd.DataFrame()
            data = resp.json()
        
        df = pd.DataFrame(
            data["data"]["candles"],
            columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float).sort_index()
        return df.tail(int(cfg["lookback_bars"]))
    except Exception as e:
        st.error(f"v3 Fetch error for {symbol}: {e}")
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
        df = fetch_v3(sym)
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
