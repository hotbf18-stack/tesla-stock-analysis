import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas_ta as ta
from sklearn.linear_model import LinearRegression

# App title
st.title("Tesla (TSLA) Stock Technical Analysis & Simple Prediction")

# Sidebar inputs
st.sidebar.header("Settings")
end_date = st.sidebar.date_input("End Date", datetime.today())
start_date = st.sidebar.date_input("Start Date", end_date - timedelta(days=365))

if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")
    st.stop()

horizon = st.sidebar.selectbox("Prediction Horizon (days)", [1, 5])

# Cache data fetching
@st.cache_data(show_spinner="Fetching TSLA data...")
def fetch_data(start, end):
    try:
        data = yf.download("TSLA", start=start, end=end + timedelta(days=1))
        if data.empty:
            st.error("No data returned. Try a different date range.")
            return None
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

data = fetch_data(start_date, end_date)
if data is None:
    st.stop()

# Cache indicator calculation
@st.cache_data(show_spinner="Calculating indicators...")
def calculate_indicators(df):
    df = df.copy()
    df["SMA_20"] = ta.sma(df["Close"], length=20)
    df["SMA_50"] = ta.sma(df["Close"], length=50)
    df["RSI"] = ta.rsi(df["Close"], length=14)

    macd_df = ta.macd(df["Close"])
    df = pd.concat([df, macd_df], axis=1)

    bb_df = ta.bbands(df["Close"], length=20, std=2)
    df = pd.concat([df, bb_df], axis=1)

    return df

data_with_ind = calculate_indicators(data)

# FIXED: Use plain string list for subset (no variables that could be interpreted as NaN)
plot_df = data_with_ind.dropna(subset=["SMA_20", "SMA_50", "RSI", "MACD_12_26_9", "BBU_20_2.0"])

if plot_df.empty:
    st.error("Not enough data to calculate indicators. Try a longer date range (at least 1-2 years).")
    st.stop()

df_plot = plot_df.reset_index()

# Chart selection
chart_type = st.selectbox("Select Chart Type", [
    "Candlestick", "Moving Averages", "RSI", "MACD",
    "Bollinger Bands", "Volume"
])

# Create figure
fig = go.Figure()

if chart_type == "Candlestick":
    fig.add_trace(go.Candlestick(x=df_plot["Date"],
                                 open=df_plot["Open"],
                                 high=df_plot["High"],
                                 low=df_plot["Low"],
                                 close=df_plot["Close"]))
    fig.update_layout(title="TSLA Candlestick Chart")

elif chart_type == "Moving Averages":
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["SMA_20"], name="SMA 20"))
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["SMA_50"], name="SMA 50"))
    fig.update_layout(title="Moving Averages (20 & 50)")

elif chart_type == "RSI":
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["RSI"], name="RSI"))
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
    fig.update_layout(title="RSI (14)", yaxis_range=[0, 100])

elif chart_type == "MACD":
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["MACD_12_26_9"], name="MACD"))
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["MACDs_12_26_9"], name="Signal"))
    hist = df_plot["MACDh_12_26_9"].fillna(0)
    fig.add_trace(go.Bar(x=df_plot["Date"], y=hist, name="Histogram"))
    fig.update_layout(title="MACD")

elif chart_type == "Bollinger Bands":
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["Close"], name="Close"))
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["BBU_20_2.0"], name="Upper Band", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["BBM_20_2.0"], name="Middle Band"))
    fig.add_trace(go.Scatter(x=df_plot["Date"], y=df_plot["BBL_20_2.0"], name="Lower Band", line=dict(dash="dash")))
    fig.update_layout(title="Bollinger Bands (20, 2)")

elif chart_type == "Volume":
    fig.add_trace(go.Bar(x=df_plot["Date"], y=df_plot["Volume"]))
    fig.update_layout(title="Trading Volume")

fig.update_layout(xaxis_title="Date", yaxis_title="Value", height=600)
st.plotly_chart(fig, use_container_width=True)

# Prediction section - also fixed dropna
st.header(f"Simple Buy/Sell Signal Prediction (Next {horizon} Day{'s' if horizon > 1 else ''})")

def predict_signal(df_full, horizon_days):
    df = df_full.dropna(subset=["Close", "RSI", "MACD_12_26_9", "MACDs_12_26_9"])
    if df.empty:
        return "Insufficient Data", []

    df = df.copy()
    df["DayNum"] = np.arange(len(df))

    model = LinearRegression()
    model.fit(df[["DayNum"]], df["Close"])
    future_days = np.arange(len(df), len(df) + horizon_days).reshape(-1, 1)
    pred_prices = model.predict(future_days)
    avg_pred = np.mean(pred_prices)
    current_price = df["Close"].iloc[-1]

    trend = "Buy" if avg_pred > current_price * 1.005 else "Sell" if avg_pred < current_price * 0.995 else "Hold"
    rsi = df["RSI"].iloc[-1]
    rsi_sig = "Buy" if rsi < 30 else "Sell" if rsi > 70 else "Hold"
    macd_sig = "Buy" if df["MACD_12_26_9"].iloc[-1] > df["MACDs_12_26_9"].iloc[-1] else "Sell" if df["MACD_12_26_9"].iloc[-1] < df["MACDs_12_26_9"].iloc[-1] else "Hold"

    votes = [trend, rsi_sig, macd_sig]
    if votes.count("Buy") >= 2:
        overall = "🟢 Buy"
    elif votes.count("Sell") >= 2:
        overall = "🔴 Sell"
    else:
        overall = "🟡 Hold"

    return overall, pred_prices.round(2).tolist()

signal, pred_prices = predict_signal(data_with_ind, horizon)
st.markdown(f"### Overall Signal: **{signal}**")
if pred_prices:
    st.write(f"Predicted closing prices for next {horizon} day(s): {pred_prices}")
else:
    st.write("Not enough data for prediction.")
st.caption("Note: This is a simple educational model using technical indicators and linear trend. Not financial advice.")
