import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="TSLA Analysis", layout="wide")
st.title("🚗 Tesla (TSLA) Stock Technical Analysis")

# Sidebar
st.sidebar.header("Settings")
period_option = st.sidebar.selectbox("Time Period", ["1 Year", "2 Years", "5 Years", "7+ Years"], index=0)
horizon = st.sidebar.selectbox("Prediction Horizon (days)", [1, 5], index=0)

# Map to years back
years_back = {"1 Year": 1, "2 Years": 2, "5 Years": 5, "7+ Years": 7}[period_option]
from_date = (datetime.today() - timedelta(days=years_back * 365 + 100)).strftime("%Y-%m-%d")  # Extra buffer
to_date = datetime.today().strftime("%Y-%m-%d")

# Fetch data from StockData.org (free, no key)
@st.cache_data(ttl=3600)
def get_data():
    url = f"https://api.stockdata.org/v1/data/eod?symbols=TSLA&from_date={from_date}&to_date={to_date}&api_token=demo"  # "demo" works for free access
    response = requests.get(url)
    data = response.json()
    
    if "data" not in data or not data["data"]:
        st.error("No data returned from StockData.org. Try a shorter period or rerun later.")
        return pd.DataFrame()
    
    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df.sort_index()

df = get_data()
if df.empty:
    st.stop()

# Indicators (pure pandas)
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

# Tabs (same as before)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Candlestick + Volume", "Moving Averages", "RSI", "MACD", "Bollinger Bands", "Prediction"])

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=plot_df["date"], open=plot_df["Open"], high=plot_df["High"],
                                 low=plot_df["Low"], close=plot_df["Close"]))
    fig.add_trace(go.Bar(x=plot_df["date"], y=plot_df["Volume"], name="Volume", yaxis="y2"))
    fig.update_layout(title="TSLA Candlestick + Volume", yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

# (Add the other tabs from previous code - Moving Averages, RSI, MACD, Bollinger Bands - same as before)

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
    st.caption("Educational only — not financial advice.")

# Full tabs code is the same as my last yfinance version — just replace "Date" with "date" if needed.

### `requirements.txt`
