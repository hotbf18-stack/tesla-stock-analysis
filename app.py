import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="TSLA Analysis", layout="wide")
st.title("🚗 Tesla (TSLA) Stock Technical Analysis")

# API key from secrets
if "POLYGON_API_KEY" not in st.secrets:
    st.error("Add your Polygon.io API key in app settings > Secrets.")
    st.stop()

API_KEY = st.secrets["POLYGON_API_KEY"]

# Sidebar
st.sidebar.header("Settings")
period = st.sidebar.selectbox("Time Period", ["1y", "2y", "max (2y free)"], index=0)

# Map to multiplier/timespan for daily bars
multiplier = 1
timespan = "day"
limit = 50000  # Max allowed, enough for years of daily

# Fetch data
@st.cache_data(ttl=3600)
def get_data():
    url = f"https://api.polygon.io/v2/aggs/ticker/TSLA/range/{multiplier}/{timespan}/{period}?adjusted=true&limit={limit}&apiKey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "results" not in data:
        st.error(f"Error: {data.get('error', 'No data or API issue')}. Check key or try shorter period.")
        return pd.DataFrame()
    
    df = pd.DataFrame(data["results"])
    df["date"] = pd.to_datetime(df["t"], unit="ms")
    df = df.set_index("date")
    df = df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df.sort_index()

df = get_data()
if df.empty:
    st.stop()

# Indicators
df["SMA20"] = df["Close"].rolling(20).mean()
df["SMA50"] = df["Close"].rolling(50).mean()

delta = df["Close"].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

ema12 = df["Close"].ewm(span=12, adjust=False).mean()
ema26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
df["MACD_Hist"] = df["MACD"] - df["Signal"]

df["BB_Middle"] = df["Close"].rolling(20).mean()
std = df["Close"].rolling(20).std()
df["BB_Upper"] = df["BB_Middle"] + 2 * std
df["BB_Lower"] = df["BB_Middle"] - 2 * std

plot_df = df.dropna().reset_index()

# Tabs (same layout)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Candlestick + Volume", "Moving Averages", "RSI", "MACD", "Bollinger Bands", "Prediction"])

# (Same chart code as previous yfinance version — copy from my last yfinance message if needed, using plot_df["date"] as x)

# Prediction tab (same as before)

with tab6:
    st.subheader("Simple Buy/Sell Signal")
    latest = df.iloc[-1]
    signals = []
    if latest["RSI"] < 30: signals.append("Buy")
    elif latest["RSI"] > 70: signals.append("Sell")
    signals.append("Buy" if latest["MACD"] > latest["Signal"] else "Sell")
    signals.append("Buy" if latest["Close"] > latest["SMA20"] else "Sell")
    
    buy = signals.count("Buy")
    sell = signals.count("Sell")
    signal = "🟢 BUY" if buy > sell else "🔴 SELL" if sell > buy else "🟡 HOLD"
    
    st.markdown(f"### Next {horizon} day(s): **{signal}**")
    st.write(f"Close: ${latest['Close']:.2f} | RSI: {latest['RSI']:.1f}")
    st.caption("Educational only.")

# Paste the full chart code from my previous yfinance message for the tabs — it's identical.

### `requirements.txt`
