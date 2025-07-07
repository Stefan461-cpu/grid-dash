import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import numpy as np

st.set_page_config(page_title="Grid Bot Dashboard", layout="wide")
st.title("📈 Grid Bot Dashboard – Live Bitget Daten")

# Seitenleiste für Einstellungen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    coin = st.selectbox("Währung (COINUSDT)", ["BTC", "ETH", "SOL"])
    interval = st.radio("Intervall", ["1m", "5m", "15m", "1h", "4h", "1d"], horizontal=True)
    today = datetime.now(timezone.utc).date()
    start_date = st.date_input("Startdatum", today - timedelta(days=7))
    end_date = st.date_input("Enddatum", today)
    max_bars = st.slider("Max. Kerzen (10–1000)", 10, 1000, 500)
    
    # Add chart customization options
    st.subheader("📊 Chart-Optionen")
    chart_type = st.selectbox("Chart-Typ", ["Candlestick", "Linie", "Bereich"], index=0)
    show_volume = st.checkbox("Volumen anzeigen", True)
    show_moving_average = st.checkbox("Gleitenden Durchschnitt anzeigen", False)
    if show_moving_average:
        ma_period = st.slider("MA-Periode", 5, 50, 20)

# Bitget interval mapping
interval_mapping = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1day"
}
period = interval_mapping.get(interval)
if not period:
    st.error(f"Ungültiges Intervall: {interval}")
    st.stop()

# Convert dates to UTC timestamps
try:
    if start_date is None or end_date is None:
        st.error("Bitte gültige Start- und Enddaten auswählen")
        st.stop()
    
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc) - timedelta(seconds=1)
    now = datetime.now(timezone.utc)
    
    start_timestamp = int(start_dt.timestamp() * 1000)
    end_timestamp = min(int(end_dt.timestamp() * 1000), int(now.timestamp() * 1000))
    
    if start_timestamp >= end_timestamp:
        st.error("Startdatum muss vor Enddatum liegen und mindestens 1 Minute Unterschied haben")
        st.stop()
        
except Exception as e:
    st.error(f"Datumskonvertierungsfehler: {str(e)}")
    st.stop()

# Symbol format
symbol = f"{coin}USDT_SPBL"

# API request
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={period}&after={start_timestamp}&before={end_timestamp}&limit={max_bars}"
st.code(f"API URL: {url}", language="text")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
}

try:
    response = requests.get(url, headers=headers, timeout=15)
    data = response.json()
    
    if isinstance(data, dict) and data.get("code") != "00000":
        error_msg = data.get("msg", "Unbekannter API-Fehler")
        st.error(f"❌ Bitget API-Fehler: {error_msg} (Code: {data.get('code')})")
        with st.expander("🔍 Fehlerdetails anzeigen"):
            st.json(data)
        st.stop()
        
    response.raise_for_status()
        
except requests.exceptions.RequestException as e:
    st.error(f"❌ Netzwerkfehler: {str(e)}")
    st.stop()
except ValueError:
    st.error("❌ API-Antwort ist kein gültiges JSON.")
    st.stop()

# Process successful response
if isinstance(data, dict) and isinstance(data.get("data"), list):
    candles = data["data"]
    if not candles:
        st.warning("⚠️ Keine Daten im ausgewählten Zeitraum verfügbar. Tipp: Verkürze den Zeitraum oder wähle ein kleineres Intervall.")
        st.stop()
    
    # Create DataFrame
    df = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]
    )
    
    # Process data
    df = df.sort_values(by="timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    
    # Calculate additional metrics
    df["price_change"] = df["close"].pct_change() * 100
    df["range"] = (df["high"] - df["low"]) / df["low"] * 100
    
    if show_moving_average:
        df[f"MA_{ma_period}"] = df["close"].rolling(window=ma_period).mean()
    
    st.subheader(f"📊 {symbol} {interval} Chart")

    # Create figure with secondary y-axis for volume
    fig = go.Figure()
    
    # Add main price chart based on selected type
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Preis',
            increasing_line_color='#2ECC71',  # green
            decreasing_line_color='#E74C3C'   # red
        ))
    elif chart_type == "Linie":
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['close'],
            mode='lines',
            name='Schlusskurs',
            line=dict(color='#3498DB', width=2)
        ))
    else:  # Bereich
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['close'],
            fill='tozeroy',
            name='Preisbereich',
            fillcolor='rgba(52, 152, 219, 0.2)',
            line=dict(color='#3498DB', width=1)
        ))
    
    # Add moving average if enabled
    if show_moving_average:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df[f"MA_{ma_period}"],
            mode='lines',
            name=f'MA {ma_period}',
            line=dict(color='#F39C12', width=2, dash='dash')
        ))
    
    # Add volume if enabled
    if show_volume:
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volumen',
            marker_color='#7F8C8D',
            yaxis='y2'
        ))
    
    # Calculate dynamic range for y-axis
    price_range = df['high'].max() - df['low'].min()
    if price_range == 0:  # Handle flat markets
        price_range = df['close'].mean() * 0.01  # 1% range
    y_min = df['low'].min() - price_range * 0.1
    y_max = df['high'].max() + price_range * 0.1
    
    # Layout configuration
    fig.update_layout(
        height=600,
        title=f"{symbol} {interval} Chart",
        yaxis_title="Preis (USDT)",
        xaxis_title="Zeit",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        hovermode='x unified',
        yaxis=dict(
            range=[y_min, y_max],
            autorange=False,
            fixedrange=False
        ),
        yaxis2=dict(
            title="Volumen" if show_volume else "",
            overlaying='y',
            side='right',
            showgrid=False,
            visible=show_volume
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    # Add annotations for key metrics
    latest = df.iloc[-1]
    fig.add_annotation(
        x=latest['timestamp'],
        y=latest['close'],
        text=f"Letzter Preis: {latest['close']:.2f}",
        showarrow=True,
        arrowhead=1,
        ax=-50,
        ay=-40,
        bgcolor="black",
        bordercolor="white"
    )
    
    # Add technical indicators
    fig.add_hline(y=df['close'].mean(), line_dash="dot", 
                 annotation_text=f"Durchschnitt: {df['close'].mean():.2f}", 
                 annotation_position="bottom right")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Aktueller Preis", f"{latest['close']:.2f}", 
                 f"{df['price_change'].iloc[-1]:.2f}%")
    with col2:
        st.metric("Tageshöchst", f"{df['high'].max():.2f}")
    with col3:
        st.metric("Tagestief", f"{df['low'].min():.2f}")
    with col4:
        st.metric("Durchschnittsbereich", f"{df['range'].mean():.2f}%")
    
    # Data table
    with st.expander("📄 Vollständige Daten anzeigen"):
        st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume", "price_change"]], 
                    use_container_width=True)
else:
    st.error("❌ Ungültige API-Antwortstruktur")
    st.json(data)
