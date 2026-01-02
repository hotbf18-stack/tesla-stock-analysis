import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="TSLA Analysis", layout="wide")
st.title("🚗 Tesla (TSLA) Stock Technical Analysis")

# Sidebar
st.sidebar.header("Settings")
period = st.sidebar.selectbox("Time Period", ["1y", "2y", "5y", "max"], index=0)
horizon = st.sidebar.selectbox("Prediction Horizon (days)", [1, 5], index=0)

# Fetch data with caching and error handling
@st.cache_data(ttl=3600, show_spinner="Fetching TSLA data from Yahoo Finance...")
def get_data():
    try:
        df = yf.download("TSLA", period=period, progress=False)
        if df.empty:
            raise ValueError("No data returned.")
        return df
    except Exception as e:
        if "Rate Limit" in str(e) or "Too Many Requests" in str(e):
            st.error("Yahoo Finance rate limit reached (common on shared servers). Wait 30-60 minutes and rerun the app. It works locally and temporarily here.")
        else:
            st.error(f"Error fetching data: {str(e)}. Try again later or a shorter period.")
        return pd.DataFrame()

df = get_data()
if df.empty:
    st.stop()

# Indicators with pure pandas
df["SMA20"] = df["Close"].rolling(window=20).mean()
df["SMA50"] = df["Close"].rolling(window=50).mean()

delta = df["Close"].diff()
gain = delta.where(delta > 0, 0).rolling(window=14).mean()
loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

ema12 = df["Close"].ewm(span=12, adjust=False).mean()
ema26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
df["MACD_Hist"] = df["MACD"] - df["Signal"]

df["BB_Middle"] = df["Close"].rolling(window=20).mean()
bb_std = df["Close"].rolling(window=20).std()
df["BB_Upper"] = df["BB_Middle"] + (bb_std * 2)
df["BB_Lower"] = df["BB_Middle"] - (bb_std * 2)

plot_df = df.dropna().reset_index()

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Candlestick + Volume", "Moving Averages", "RSI", "MACD", "Bollinger Bands", "Prediction"])

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=plot_df["Date"], open=plot_df["Open"], high=plot_df["High"],
                                 low=plot_df["Low"], close=plot_df["Close"], name="Price"))
    fig.add_trace(go.Bar(x=plot_df["Date"], y=plot_df["Volume"], name="Volume", yaxis="y2"))
    fig.update_layout(title="TSLA Candlestick + Volume", yaxis2=dict(title="Volume", overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["SMA20"], name="SMA 20"))
    fig.add_trace(go.Scatter(x=plot_df["Date"], y=plot_df["SMA50"], name="SMA 50"))
    fig.update_layout(title="Moving Averages (20 & 50)")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    fig = go.Figure(go.Scatter(x=plot_df["Date"], y=plot_df["RSI"], name="RSI"))
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
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
    fig.update_layout(title="Bollinger Bands (20, 2)")
    st.plotly_chart(fig, use_container_width=True)

with tab6:
    st.subheader("Simple Buy/Sell Signal Prediction")
    latest = df.iloc[-1]
    signals = []
    if latest["RSI"] < 30: signals.append("Buy")
    elif latest["RSI"] > 70: signals.append("Sell")
    signals.append("Buy" if latest["MACD"] > latest["Signal"] else "Sell")
    signals.append("Buy" if latest["Close"] > latest["SMA20"] else "Sell")
    
    buy_count = signals.count("Buy")
    sell_count = signals.count("Sell")
    overall = "🟢 Buy" if buy_count > sell_count else "🔴 Sell" if sell_count > buy_count else "🟡 Hold"
    
    st.markdown(f"### For next {horizon} day(s): **{overall}**")
    st.write(f"Latest Close: ${latest['Close']:.2f} | RSI: {latest['RSI']:.1f}")
    st.caption("Simple rule-based model for educational purposes. Not financial advice.")
