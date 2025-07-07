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
    start_date = st.date_input("Startdatum", today - timedelta(days=7))
    end_date = st.date_input("Enddatum", today)
    max_bars = st.slider("Max. Kerzen (10–1000)", 10, 1000, 500)

# CORRECTED Bitget interval mapping
interval_mapping = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D"  # Must be uppercase 'D'
}
period = interval_mapping.get(interval)
if not period:
    st.error(f"Ungültiges Intervall: {interval}")
    st.stop()

# Convert dates to UTC timestamps (in milliseconds)
try:
    if start_date is None or end_date is None:
        st.error("Bitte gültige Start- und Enddaten auswählen")
        st.stop()
    
    # Use 00:00 UTC for start, and 23:59:59 for end
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc) - timedelta(seconds=1)
    now = datetime.now(timezone.utc)
    
    start_timestamp = int(start_dt.timestamp() * 1000)
    end_timestamp = min(int(end_dt.timestamp() * 1000), int(now.timestamp() * 1000))
    
    # Ensure valid time range (at least 1 minute difference)
    if start_timestamp >= end_timestamp:
        st.error("Startdatum muss vor Enddatum liegen und mindestens 1 Minute Unterschied haben")
        st.stop()
        
    # Verify time range doesn't exceed Bitget limits
    max_range_days = 90  # Bitget's max range for minute data
    if (end_dt - start_dt) > timedelta(days=max_range_days):
        st.error(f"Zeitraum zu lang! Maximal {max_range_days} Tage für minütliche Daten.")
        st.stop()
        
except Exception as e:
    st.error(f"Datumskonvertierungsfehler: {str(e)}")
    st.stop()

# Symbol must use correct case (BTCUSDT_SP)
symbol = f"{coin}USDT_SP".upper()

# CORRECTED API parameters (Bitget uses 'period', 'after', 'before')
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={period}&after={start_timestamp}&before={end_timestamp}&limit={max_bars}"

st.code(f"API URL: {url}", language="text")

# Add API headers to avoid rate limiting
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json"
}

try:
    response = requests.get(url, headers=headers, timeout=15)
    
    # Handle 400 errors with detailed diagnostics
    if response.status_code == 400:
        try:
            error_data = response.json()
            st.error(f"❌ Bitget API-Fehler (Code {error_data.get('code')}): {error_data.get('msg')}")
            
            # Suggest common fixes
            if "period" in error_data.get("msg", "").lower():
                st.warning("⚠️ Mögliche Lösung: Überprüfe das Intervall-Format (1min, 1H, 1D)")
            if "symbol" in error_data.get("msg", "").lower():
                st.warning("⚠️ Mögliche Lösung: Symbolformat sollte 'COINUSDT_SP' sein (z.B. BTCUSDT_SP)")
            if "time" in error_data.get("msg", "").lower():
                st.warning("⚠️ Mögliche Lösung: Verkürze den Zeitraum oder wähle ein größeres Intervall")
                
            st.stop()
        except:
            st.error(f"❌ Unbekannter Bitget-Fehler: {response.text[:200]}")
            st.stop()
    
    response.raise_for_status()
    data = response.json()
    
    # Handle Bitget's success code
    if isinstance(data, dict) and data.get("code") != "00000":
        error_msg = data.get("msg", "Unbekannter API-Fehler")
        st.error(f"❌ Bitget API-Fehler: {error_msg} (Code: {data.get('code')})")
        st.stop()
        
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
    
    st.subheader(f"📊 Kursverlauf {symbol} [{interval}]")
    st.line_chart(df.set_index("timestamp")["close"], height=300)

    with st.expander("📄 Tabelle anzeigen"):
        st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume"]], use_container_width=True)
else:
    st.error("❌ Ungültige API-Antwortstruktur")
    st.json(data)
