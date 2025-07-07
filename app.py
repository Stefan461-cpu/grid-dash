import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.title("📈 Grid Bot Dashboard – Live Bitget Daten")

# Seitenleiste für Einstellungen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    coin = st.selectbox("Währung (COINUSDT)", ["BTC", "ETH", "SOL"])
    interval = st.radio("Intervall", ["1m", "5m", "15m", "1h", "4h", "1d"], horizontal=True)
    today = datetime.today()
    start_date = st.date_input("Startdatum", today - timedelta(days=30))
    end_date = st.date_input("Enddatum", today)
    max_bars = st.slider("Max. Kerzen (1–1000)", 10, 1000, 500)

# Symbol zusammenbauen (Bitget erwartet z. B. BTCUSDT_SP)
symbol = f"{coin}USDT_SP"
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={interval}&limit={max_bars}"

# API-Abfrage
response = requests.get(url)
try:
    data = response.json()
except:
    st.error("❌ Antwort konnte nicht als JSON gelesen werden.")
    st.stop()

# Debug-Ausgabe der Rohdaten
st.subheader("🔍 API-Rohantwort")
st.write(data)

# Wenn Daten vorhanden, verarbeiten
if isinstance(data, dict) and "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
    df = pd.DataFrame(data["data"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.sort_values(by="timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

    st.subheader(f"📊 Kursverlauf {symbol} [{interval}]")
    st.line_chart(df.set_index("timestamp")["close"], height=300)
    with st.expander("📄 Tabelle anzeigen"):
        st.dataframe(df, use_container_width=True)
else:
    st.error("❌ Keine gültigen Kursdaten erhalten. Prüfe Symbol, Zeitraum und Intervall.")
