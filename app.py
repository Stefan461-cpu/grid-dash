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
    start_date = st.date_input("Startdatum", today - timedelta(days=7))  # Reduced default to 7 days
    end_date = st.date_input("Enddatum", today)
    max_bars = st.slider("Max. Kerzen (10–1000)", 10, 1000, 500)

# Interval mapping for Bitget API - CORRECTED
interval_mapping = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D"
}
period = interval_mapping.get(interval)
if not period:
    st.error(f"Ungültiges Intervall: {interval}")
    st.stop()

# Convert dates to UTC timestamps (in milliseconds) - FIXED
try:
    # Validate date inputs
    if start_date is None or end_date is None:
        st.error("Bitte gültige Start- und Enddaten auswählen")
        st.stop()
    
    # Ensure timezone-aware datetime objects
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    now = datetime.now(timezone.utc)
    
    # Convert to timestamps with fallback to current time
    start_timestamp = int(start_dt.timestamp() * 1000)
    end_timestamp = min(
        int(end_dt.timestamp() * 1000),
        int(now.timestamp() * 1000)  # Ensure we don't request future data
    )
    
    if start_timestamp >= end_timestamp:
        st.error("Startdatum muss vor Enddatum liegen")
        st.stop()
        
except Exception as e:
    st.error(f"Datumskonvertierungsfehler: {str(e)}")
    st.stop()

# Symbol korrekt setzen (Bitget erwartet SP-Suffix)
symbol = f"{coin}USDT_SP"

# API URL with CORRECTED parameters - using Bitget's expected format
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&granularity={period}&startTime={start_timestamp}&endTime={end_timestamp}&limit={max_bars}"

# Zeige URL zur Kontrolle
st.code(f"API URL: {url}", language="text")

# Daten abrufen with IMPROVED error handling
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    # Capture API error responses
    if isinstance(data, dict) and data.get("code") != "00000":
        error_msg = data.get("msg", "Unbekannter API-Fehler")
        st.error(f"❌ Bitget API-Fehler: {error_msg} (Code: {data.get('code')})")
        st.stop()
        
except requests.exceptions.RequestException as e:
    # Show detailed error message
    error_msg = str(e)
    if hasattr(e, 'response') and e.response is not None:
        try:
            error_body = e.response.json()
            error_msg += f"\nAPI-Antwort: {error_body}"
        except:
            error_msg += f"\nAntworttext: {e.response.text[:200]}..."
    st.error(f"❌ Netzwerkfehler bei API-Anfrage: {error_msg}")
    st.stop()
except ValueError:
    st.error("❌ API-Antwort ist kein gültiges JSON.")
    st.stop()

# Validierung der API-Antwortstruktur
if isinstance(data, dict) and isinstance(data.get("data"), list):
    candles = data["data"]
    if not candles:
        st.warning("⚠️ Keine Daten im ausgewählten Zeitraum verfügbar")
        st.stop()
    
    # Create DataFrame - FIXED column names
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
    st.error(f"❌ Ungültige API-Antwortstruktur: {type(data)}")
    st.json(data)
