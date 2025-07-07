import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Grid Bot Dashboard", layout="wide")
st.title("📈 Grid Bot Dashboard – Live Bitget Daten")

# Seitenleiste für Einstellungen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    coin = st.selectbox("Währung (COINUSDT)", ["BTC", "ETH", "SOL"])
    interval = st.radio("Intervall", ["1m", "5m", "15m", "1h", "4h", "1d"], horizontal=True)
    today = datetime.now(timezone.utc).date()
    start_date = st.date_input("Startdatum", today - timedelta(days=30))
    end_date = st.date_input("Enddatum", today)
    max_bars = st.slider("Max. Kerzen (10–1000)", 10, 1000, 500)

# Interval mapping for Bitget API
interval_mapping = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1H",
    "4h": "4H",
    "1d": "1day"
}
period = interval_mapping.get(interval)
if not period:
    st.error(f"Ungültiges Intervall: {interval}")
    st.stop()

# Convert dates to UTC timestamps (in milliseconds)
try:
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    now = datetime.now(timezone.utc)
    
    start_timestamp = int(start_dt.timestamp() * 1000)
    end_timestamp = min(int(end_dt.timestamp() * 1000), int(now.timestamp() * 1000))
    
    if start_timestamp >= end_timestamp:
        st.error("Startdatum muss vor Enddatum liegen")
        st.stop()
        
except Exception as e:
    st.error(f"Datumskonvertierungsfehler: {e}")
    st.stop()

# Symbol korrekt setzen (Bitget erwartet SP-Suffix)
symbol = f"{coin}USDT_SP"
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={period}&after={start_timestamp}&before={end_timestamp}&limit={max_bars}"

# Zeige URL zur Kontrolle
st.code(f"API URL: {url}", language="text")

# Daten abrufen
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException as e:
    st.error(f"❌ Netzwerkfehler bei API-Anfrage: {e}")
    st.stop()
except ValueError:
    st.error("❌ API-Antwort ist kein gültiges JSON.")
    st.stop()

# Ausgabe roher JSON-Antwort
st.subheader("🧾 Bitget API-Rohantwort")
st.json(data)

# Validierung der API-Antwortstruktur
if isinstance(data, dict) and data.get("code") == "00000" and isinstance(data.get("data"), list):
    # Create DataFrame from candle data
    candles = data["data"]
    if not candles:
        st.warning("Keine Daten im ausgewählten Zeitraum verfügbar")
        st.stop()
    
    df = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume", "quote_volume"]
    )
    
    # Process data
    df = df.sort_values(by="timestamp")  # Sort chronologically
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    
    st.subheader(f"📊 Kursverlauf {symbol} [{interval}]")
    st.line_chart(df.set_index("timestamp")["close"], height=300)

    with st.expander("📄 Tabelle anzeigen"):
        st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume"]], use_container_width=True)
else:
    error_msg = data.get("msg", "Unbekannter Fehler")
    st.error(f"❌ API-Fehler: {error_msg} (Code: {data.get('code')})")
