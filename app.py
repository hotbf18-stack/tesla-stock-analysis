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
period_option = st.sidebar.selectbox("Time Period", ["1 Year", "2 Years", "5 Years"], index=0)
horizon = st.sidebar.selectbox("Prediction Horizon (days)", [1, 5], index=0)

# Calculate dates based on selection (free tier safe: max 5 years recent)
years_back = {"1 Year": 1, "2 Years": 2, "5 Years": 5}[period_option]
from_date = (datetime.today() - timedelta(days=years_back * 365)).strftime("%Y-%m-%d")
to_date = datetime.today().strftime("%Y-%m-%d")

# Fetch data
@st.cache_data(ttl=3600)
def get_data():
    url = f"https://api.polygon.io/v2/aggs/ticker/TSLA/range/1/day/{from_date}/{to_date}?adjusted=true&sort=asc&limit=50000&apiKey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    if "results" not in data:
        error_msg = data.get("error", data.get("message", "Unknown error"))
        st.error(f"Polygon API error: {error_msg}. Check key, limits, or try shorter period.")
        return pd.DataFrame()
    
    df = pd.DataFrame(data["results"])
    df["Date"] = pd.to_datetime(df["t"], unit="ms")
    df = df.set_index("Date")
    df = df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
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

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Candlestick + Volume", "Moving Averages", "RSI", "MACD", "Bollinger Bands", "Prediction"])

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=plot_df["Date"], open=plot_df["Open"], high=plot_df["High"],
                                 low=plot_df["Low"], close=plot_df["Close"]))
    fig.add_trace(go.Bar(x=plot_df["Date"], y=plot_df["Volume"], name="Volume", yaxis="y2"))
    fig.update_layout(title="TSLA Candlestick + Volume", yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["SMA20"], name="SMA 20"))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["SMA50"], name="SMA 50"))
    fig.update_layout(title="Moving Averages")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    fig = go.Figure(go.Scatter(x=plot_df["Date"], y=plot_df["RSI"], name="RSI"))
    fig.add_hline(y=70, line_dash="dash", line_color="red")
    fig.add_hline(y=30, line_dash="dash", line_color="green")
    fig.update_layout(title="RSI (14)", yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["MACD"], name="MACD"))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["Signal"], name="Signal"))
    fig.add_trace(go.Bar(x=plot_df["Date"], y=plot_df["MACD_Hist"], name="Histogram"))
    fig.update_layout(title="MACD")
    st.plotly_chart(fig, use_container_width=True)

with tab5:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["BB_Upper"], name="Upper Band", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["BB_Middle"], name="Middle Band"))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["BB_Lower"], name="Lower Band", line=dict(dash="dash")))
    fig.update_layout(title="Bollinger Bands")
    st.plotly_chart(fig, use_container_width=True)

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
