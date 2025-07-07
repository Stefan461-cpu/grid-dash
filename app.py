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

# Intervall-Mapping
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

# Zeitstempel berechnen
try:
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc) - timedelta(seconds=1)
    now = datetime.now(timezone.utc)

    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = min(int(end_dt.timestamp() * 1000), int(now.timestamp() * 1000))

    if start_ts >= end_ts:
        st.error("Startdatum muss vor Enddatum liegen.")
        st.stop()
except Exception as e:
    st.error(f"Fehler bei Datumskonvertierung: {e}")
    st.stop()

# Symbol
symbol = f"{coin}USDT_SPBL"
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={period}&after={start_ts}&before={end_ts}&limit={max_bars}"
st.code(f"API URL: {url}")

# API-Abfrage
try:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    st.error(f"❌ Netzwerk- oder JSON-Fehler: {e}")
    st.stop()

# Datenvalidierung
candles_raw = data.get("data")
if not isinstance(candles_raw, list):
    st.error("❌ Ungültige oder leere Antwort von Bitget.")
    st.json(data)
    st.stop()
if len(candles_raw) == 0:
    st.warning("⚠️ Keine Kursdaten im gewählten Zeitraum.")
    st.stop()

# DataFrame aufbauen
df = pd.DataFrame(
    candles_raw,
    columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]
)

# Umwandlungen
df["timestamp"] = pd.to_datetime(df["timestamp"].astype(np.int64), unit="ms", utc=True).dt.tz_convert(None)
for col in ["open", "high", "low", "close", "volume"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Zusatzspalten
df["price_change"] = df["close"].pct_change() * 100
df["range"] = (df["high"] - df["low"]) / df["low"] * 100

# Chart
st.subheader(f"📊 {symbol} – {interval}")
fig = go.Figure()

if chart_type == "Candlestick":
    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        increasing_line_color="green", decreasing_line_color="red"
    ))
else:
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["close"], mode="lines", name="Close", line=dict(color="blue")
    ))

if show_volume:
    fig.add_trace(go.Bar(
        x=df["timestamp"], y=df["volume"],
        name="Volumen", marker_color="gray", yaxis="y2"
    ))

fig.update_layout(
    height=600,
    yaxis_title="Preis (USDT)",
    xaxis_title="Zeit",
    template="plotly_dark",
    yaxis2=dict(
        overlaying="y",
        side="right",
        showgrid=False,
        visible=show_volume,
        title="Volumen"
    ),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# Metriken
latest = df.iloc[-1]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Letzter Preis", f"{latest['close']:.2f}")
col2.metric("Tageshoch", f"{df['high'].max():.2f}")
col3.metric("Tagestief", f"{df['low'].min():.2f}")
col4.metric("Ø Spanne", f"{df['range'].mean():.2f} %")

# Tabelle
with st.expander("📄 Daten anzeigen"):
    st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume", "price_change"]])
