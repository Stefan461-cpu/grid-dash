import streamlit as st
from datetime import date, timedelta
from components.ui import get_user_settings, render_chart_and_metrics, display_bot_results
from services.bitget_api import fetch_bitget_candles
from services.bot import simulate_grid_bot

st.set_page_config(page_title="📈 Live Grid Bot (Bitget)", layout="wide")

# 1. Erste UI-Eingabe (ohne Grid-Grenzen) zur Auswahl von Coin, Intervall, Zeitspanne etc.
st.markdown("## 🛠 Einstellungen laden")
temp_settings = get_user_settings(key_prefix="phase1")

# 2. API-Daten laden (basierend auf erster UI)
symbol, df, error = fetch_bitget_candles(
    temp_settings["coin"],
    temp_settings["interval"],
    temp_settings["start_date"],
    temp_settings["end_date"],
    temp_settings["max_bars"]
)

if error:
    st.error(error)
    st.stop()

st.session_state["df"] = df

# 3. Grid-Grenzen aus erstem Kurs berechnen
if not df.empty:
    start_price = df.iloc[0]["close"]
    default_lower = round(start_price * 0.7, 4)
    default_upper = round(start_price * 1.3, 4)
else:
    default_lower = 100.0
    default_upper = 200.0

# 4. Vollständige UI mit Grid-Bot-Parametern (und richtigen Grenzen)
user_settings = get_user_settings(default_lower=default_lower, default_upper=default_upper, key_prefix="phase2")

# 5. Chart anzeigen
render_chart_and_metrics(df, symbol, user_settings["interval"], user_settings["chart_type"], user_settings["show_volume"])

# 6. Simulation starten (falls aktiviert und getriggert)
if user_settings["enable_bot"] and user_settings.get("bot_run_triggered"):
    with st.spinner("Simulation läuft..."):
        results = simulate_grid_bot(
            df=df,
            total_investment=user_settings["bot_params"]["total_investment"],
            lower_price=user_settings["bot_params"]["lower_price"],
            upper_price=user_settings["bot_params"]["upper_price"],
            num_grids=user_settings["bot_params"]["num_grids"],
            grid_mode=user_settings["bot_params"]["grid_mode"],
            reserved_amount=user_settings["bot_params"]["reserved_amount"],
            fee_rate=user_settings["bot_params"]["fee_rate"]
        )
        if results:
            display_bot_results(results)
