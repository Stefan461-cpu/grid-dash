import streamlit as st
from datetime import date, timedelta
from components.ui import get_user_settings, render_chart_and_metrics, display_bot_results, plot_simulation_pattern
from services.bitget_api import fetch_bitget_candles
from services.bot import simulate_grid_bot
from services.simulator import generate_simulated_data

# Seiteneinstellungen
st.set_page_config(page_title="Grid Bot Simulator", layout="wide")
st.title("📈 Grid Bot Simulator")

# UI abrufen
user_settings = get_user_settings()

# Daten abrufen basierend auf Modus
if user_settings.get("use_simulated_data", False):
    # Generate simulated data
    df = generate_simulated_data(
        pattern=user_settings["simulation_pattern"],
        days=user_settings["simulation_days"],
        initial_price=user_settings["simulation_initial_price"],
        volatility=user_settings["simulation_volatility"]
    )
    symbol = "SIM/BTC"
    
    # Show pattern visualization
    st.subheader("Simulation Pattern Visualization")
    plot_simulation_pattern(df, user_settings["simulation_pattern"])
    
    # Set default interval for simulated data
    interval = "1h"  # Default interval for simulated data
    interval = user_settings.get("simulation_interval", "1h")  # Use selected interval
else:
    # Original data fetching
    coin = user_settings["coin"]
    interval = user_settings["interval"]
    start_date = user_settings["start_date"]
    end_date = user_settings["end_date"]
    max_bars = user_settings["max_bars"]
    
    symbol, df, error = fetch_bitget_candles(coin, interval, start_date, end_date, max_bars)
    if error:
        st.error(error)
        st.stop()

# DataFrame speichern
st.session_state["df"] = df

# Chart anzeigen
render_chart_and_metrics(df, symbol, interval, 
                        user_settings["chart_type"], 
                        user_settings["show_volume"])

# Grid Bot starten
if user_settings["enable_bot"] and user_settings.get("bot_run_triggered", False):
    with st.spinner("Simulation läuft..."):
        results = simulate_grid_bot(
            df=df,
            total_investment=user_settings["bot_params"]["total_investment"],
            lower_price=user_settings["bot_params"]["lower_price"],
            upper_price=user_settings["bot_params"]["upper_price"],
            num_grids=user_settings["bot_params"]["num_grids"],
            grid_mode=user_settings["bot_params"]["grid_mode"],
            fee_rate=user_settings["bot_params"]["fee_rate"]
        )
        if results:
            # Pass both results and df for verification
            display_bot_results(results, df)