
import streamlit as st
from datetime import date, timedelta
from components.ui import get_user_settings, render_chart_and_metrics, display_bot_results
from services.bitget_api import fetch_bitget_candles
from services.bot import simulate_grid_bot

st.set_page_config(page_title="📈 Live Grid Bot (Bitget)", layout="wide")

# Hole Nutzereinstellungen
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

# Kursdaten automatisch laden
symbol, df, error = fetch_bitget_candles(coin, interval, start_date, end_date, max_bars)
if error:
    st.error(error)
    st.stop()

# Speichere df im Session State
st.session_state["df"] = df

# Aktuellen Startkurs verwenden für Grenzen, wenn nicht manuell geändert
if enable_bot and "default_bounds_set" not in st.session_state:
    start_price = df.iloc[0]["close"]
    st.session_state["default_lower"] = round(start_price * 0.7, 4)
    st.session_state["default_upper"] = round(start_price * 1.3, 4)
    st.session_state["default_bounds_set"] = True

# Zeige Chart
render_chart_and_metrics(df, symbol, interval, chart_type, show_volume)

# Bot-Simulation starten
if enable_bot and bot_run_triggered:
    with st.spinner("Simulation läuft..."):
        results = simulate_grid_bot(
            df=df,
            total_investment=bot_params["total_investment"],
            lower_price=bot_params["lower_price"],
            upper_price=bot_params["upper_price"],
            num_grids=bot_params["num_grids"],
            grid_mode=bot_params["grid_mode"],
            reserved_amount=bot_params["reserved_amount"],
            fee_rate=bot_params["fee_rate"]
        )
        if results:
            display_bot_results(results)
