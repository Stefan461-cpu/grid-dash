import streamlit as st
from components.ui import get_user_settings, render_chart_and_metrics
from services.bitget_api import fetch_bitget_candles

st.set_page_config(page_title="Grid Bot Dashboard", layout="wide")
st.title("\ud83d\udcc8 Grid Bot Dashboard – Live Bitget Daten")

# Einstellungen abfragen
settings = get_user_settings()

# API-Daten abrufen
symbol, df, error = fetch_bitget_candles(**settings)

if error:
    st.error(error)
else:
    st.success(f"✅ Erfolgreich {len(df)} Kerzen geladen")
    render_chart_and_metrics(df, symbol, settings["interval"], settings["chart_type"], settings["show_volume"])
