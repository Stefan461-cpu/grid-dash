# app.py – Version 1.1 – Stand: 2025-07-09 20:15
import streamlit as st
from datetime import date, timedelta
from components.ui import get_user_settings, render_chart_and_metrics, display_bot_results
from services.bitget_api import fetch_bitget_candles
from services.bot import simulate_grid_bot

# Seiteneinstellungen
st.set_page_config(page_title="Live Grid Bot (Bitget)", layout="wide")
st.title("📈 Live Grid Bot (Bitget)")

# UI abrufen
user_settings = get_user_settings()
coin = user_settings["coin"]
interval = user_settings["interval"]
start_date = user_settings["start_date"]
end_date = user_settings["end_date"]
max_bars = user_settings["max_bars"]
chart_type = user_settings["chart_type"]
show_volume = user_settings["show_volume"]
enable_bot = user_settings["enable_bot"]
bot_params = user_settings["bot_params"]
bot_run_triggered = user_settings.get("bot_run_triggered", False)

# Kursdaten abrufen
symbol, df, error = fetch_bitget_candles(coin, interval, start_date, end_date, max_bars)
if error:
    st.error(error)
    st.stop()

# DataFrame speichern
st.session_state["df"] = df

# Chart anzeigen
render_chart_and_metrics(df, symbol, interval, chart_type, show_volume)

# Grid Bot starten
if enable_bot and bot_run_triggered:
    with st.spinner("Simulation läuft..."):
        results = simulate_grid_bot(
            df=df,
            total_investment=bot_params["total_investment"],
            lower_price=bot_params["lower_price"],
            upper_price=bot_params["upper_price"],
            num_grids=bot_params["num_grids"],
            grid_mode=bot_params["grid_mode"],
            fee_rate=bot_params["fee_rate"]
        )
        if results:
            display_bot_results(results)
