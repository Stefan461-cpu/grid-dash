import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Grid Bot Dashboard", layout="wide")
st.title("📈 Grid Bot Dashboard – Live Bitget Daten")

# Seitenleiste für Einstellungen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    coin = st.selectbox("Währung (COINUSDT)", ["BTC", "ETH", "SOL"])
    interval = st.radio("Intervall", ["1m", "5m", "15m", "1h", "4h", "1d"], horizontal=True)
    today = datetime.utcnow().date()
    start_date = st.date_input("Startdatum", today - timedelta(days=30))
    end_date = st.date_input("Enddatum", today)
    max_bars = st.slider("Max. Kerzen (10–1000)", 10, 1000, 500)

# Symbol korrekt setzen (Bitget erwartet SP-Suffix)
symbol = f"{coin}USDT_SP"
url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={interval}&limit={max_bars}"

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
    df = pd.DataFrame(data["data"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.sort_values(by="timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

    st.subheader(f"📊 Kursverlauf {symbol} [{interval}]")
    st.line_chart(df.set_index("timestamp")["close"], height=300)

    with st.expander("📄 Tabelle anzeigen"):
        st.dataframe(df, use_container_width=True)
else:
    error_msg = data.get("msg", "Unbekannter Fehler")
    st.error(f"❌ API-Antwort ungültig: {error_msg}")
