# rsi_scanner.py
import pandas as pd
from datetime import datetime
from upstox_client import ApiClient, Configuration, HistoricalDataApi
from ta.momentum import RSIIndicator
import streamlit as st

def get_upstox_client():
    cfg = st.secrets
    conf = Configuration()
    conf.api_key = cfg["upstox"]["api_key"]
    conf.api_secret = cfg["upstox"]["api_secret"]
    conf.access_token = cfg["upstox"]["access_token"]
    return HistoricalDataApi(ApiClient(conf))

def fetch(symbol):
    try:
        hist_api = get_upstox_client()
        end = datetime.now()
        start = end - pd.Timedelta(days=7)
        data = hist_api.get_historical_candle_data(
            instrument_key=f"NSE_EQ|{symbol.replace('.NS','')}",
            interval=st.secrets["scanner"]["interval"],
            from_date=start.strftime("%Y-%m-%d"),
            to_date=end.strftime("%Y-%m-%d")
        )
        df = pd.DataFrame(data["data"]["candles"],
                          columns=["timestamp","open","high","low","close","volume","oi"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df = df.astype(float).sort_index()
        return df.tail(int(st.secrets["scanner"]["lookback_bars"]))
    except Exception as e:
        st.error(f"[{symbol}] {e}")
        return pd.DataFrame()

def get_signal(df):
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
