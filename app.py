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
    
    st.subheader("📊 Chart-Optionen")
    chart_type = st.selectbox("Chart-Typ", ["Candlestick", "Linie"], index=0)
    show_volume = st.checkbox("Volumen anzeigen", True)

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
    
    # DEBUG: Show raw API response structure
    with st.expander("🔍 API-Rohdaten anzeigen"):
        st.write("Erster Eintrag:", candles[0] if candles else "Keine Daten")
        st.write("Typ des ersten Eintrags:", type(candles[0]) if candles else "N/A")
    
    # PROCESS THE NEW DICTIONARY FORMAT
    processed_data = []
    
    for candle in candles:
        try:
            # Extract values from dictionary
            ts = candle.get("ts")
            o = candle.get("open")
            h = candle.get("high")
            l = candle.get("low")
            c = candle.get("close")
            v = candle.get("usdtVol") or candle.get("baseVol") or candle.get("quoteVol") or "0"
            
            # Skip if essential data is missing
            if None in [ts, o, h, l, c]:
                continue
                
            # Add to processed data
            processed_data.append({
                "timestamp": ts,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v
            })
        except (KeyError, TypeError):
            continue
    
    # Check if we have any valid data
    if not processed_data:
        st.error("⚠️ Keine gültigen Daten nach der Konvertierung verfügbar. Die API hat ein unerwartetes Format zurückgegeben.")
        with st.expander("🔍 Erster API-Eintrag anzeigen"):
            st.write(candles[0] if candles else "Keine Daten")
        st.stop()
        
    # Create DataFrame from processed data
    df = pd.DataFrame(processed_data)
    
    # Convert data types
    try:
        # Convert timestamp
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True, errors="coerce")
        df["timestamp"] = df["timestamp"].dt.tz_convert(None)
        
        # Convert price columns
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors="coerce")
            
        # Convert volume
        df["volume"] = pd.to_numeric(df["volume"].astype(str).str.replace(',', '.'), errors="coerce")
        
    except Exception as e:
        st.error(f"Datenkonvertierungsfehler: {str(e)}")
        st.stop()
    
    # Remove any rows with invalid price data
    df = df.dropna(subset=["open", "high", "low", "close"])
    
    # Exit if no valid data remains
    if df.empty:
        st.error("⚠️ Keine gültigen Daten nach der Konvertierung verfügbar.")
        st.stop()
    
    # Sort by timestamp
    df = df.sort_values("timestamp")
    
    # Calculate additional metrics
    df["price_change"] = df["close"].pct_change() * 100
    df["range"] = (df["high"] - df["low"]) / df["low"].replace(0, np.nan) * 100
    
    # Display data info
    st.success(f"✅ Erfolgreich {len(df)} Kerzen geladen")
    
    st.subheader(f"📊 {symbol} {interval} Chart")

    # Create figure
    fig = go.Figure()
    
    # Add main price chart
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Preis',
            increasing_line_color='#2ECC71',
            decreasing_line_color='#E74C3C'
        ))
    else:  # Linie
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['close'],
            mode='lines',
            name='Schlusskurs',
            line=dict(color='#3498DB', width=2)
        ))
    
    # Add volume if enabled
    if show_volume and 'volume' in df.columns and not df['volume'].isnull().all():
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volumen',
            marker_color='#7F8C8D',
            yaxis='y2'
        ))
    
    # Layout configuration
    fig.update_layout(
        height=600,
        title=f"{symbol} {interval} Chart",
        yaxis_title="Preis (USDT)",
        xaxis_title="Zeit",
        template="plotly_dark",
        xaxis=dict(
            type='date',
            tickformat='%Y-%m-%d %H:%M',
            rangeslider_visible=False
        ),
        yaxis=dict(
            autorange=True
        ),
        yaxis2=dict(
            title="Volumen" if show_volume else "",
            overlaying='y',
            side='right',
            showgrid=False,
            visible=show_volume
        ),
        margin=dict(l=50, r=50, t=80, b=100),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display key metrics
    if not df.empty:
        latest = df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            change = df['price_change'].iloc[-1] if not pd.isnull(df['price_change'].iloc[-1]) else 0
            st.metric("Aktueller Preis", f"{latest['close']:.2f}", 
                     f"{change:.2f}%")
        with col2:
            st.metric("Tageshöchst", f"{df['high'].max():.2f}")
        with col3:
            st.metric("Tagestief", f"{df['low'].min():.2f}")
        with col4:
            avg_range = df['range'].mean() if not df['range'].isnull().all() else 0
            st.metric("Durchschnittsbereich", f"{avg_range:.2f}%")
    
    # Data table
    with st.expander("📄 Vollständige Daten anzeigen"):
        st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume"]], use_container_width=True)
else:
    st.error("❌ Ungültige API-Antwortstruktur")
    st.json(data)
