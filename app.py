import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from dateutil import parser

# Titel
st.title("📈 Grid Bot Dashboard (Bitget Live Data)")

# Seitenleiste: Benutzer-Einstellungen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    coin = st.selectbox("Währung (COINUSDT)", ["BTC", "ETH", "SOL", "XRP", "LTC"])
    interval = st.radio("Intervall", ["15m", "30m", "1h", "4h", "1d"], horizontal=True)

    today = datetime.today()
    default_start = today - timedelta(days=30)
    start_date = st.date_input("Startdatum", default_start)
    end_date = st.date_input("Enddatum", today)

    max_bars = st.number_input("Max. Kerzen (bitget limit: 1000)", min_value=10, max_value=1000, value=500)

# API Keys aus Streamlit Secrets laden
api_key = st.secrets["BITGET_API_KEY"]
api_secret = st.secrets["BITGET_API_SECRET"]

# API-Parameter definieren
symbol = coin + "USDT"
resolution = interval
limit = max_bars

start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000)
end_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000)

# Bitget OHLCV API Endpoint
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={interval}&limit={limit}"

# Abfrage
st.write("API URL:", url)
response = requests.get(url)
data = response.json()

# Daten verarbeiten
if "data" in data and len(data["data"]) > 0:
    df = pd.DataFrame(data["data"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.sort_values(by="timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

    st.subheader(f"📊 Kursdaten: {symbol} [{interval}]")
    st.line_chart(df.set_index("timestamp")["close"], height=300)

    with st.expander("🧾 Rohdaten anzeigen"):
        st.dataframe(df, use_container_width=True)
else:
    st.warning("Keine Daten gefunden oder API-Antwort fehlerhaft.")

# Platzhalter: Hier folgt in Kürze die Grid Bot Simulation mit Visualisierung
st.info("💡 Die Grid-Bot-Logik wird hier integriert – inklusive Simulation und Handelsanzeige.")
