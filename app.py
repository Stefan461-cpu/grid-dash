# app.py - Grid Bot Simulator
# Stabile Version

import streamlit as st
from datetime import date, timedelta
from components.ui import get_user_settings, render_chart_and_metrics, display_bot_results, plot_simulation_pattern
from services.bitget_api import fetch_bitget_candles
from services.bot import simulate_grid_bot  # Geändert: calculate_grid_lines entfernt
from services.simulator import generate_simulated_data

# Seiteneinstellungen
st.set_page_config(page_title="Grid Bot Simulator", layout="wide")
st.title("📈 Grid Bot Simulator (Spot)")

# Initialize session state
if 'prev_settings' not in st.session_state:
    st.session_state.prev_settings = None
if 'results' not in st.session_state:
    st.session_state.results = None

# UI abrufen
user_settings = get_user_settings()

# Daten abrufen basierend auf Modus
if user_settings.get("use_simulated_data", False):
    df = generate_simulated_data(
        pattern=user_settings["simulation_pattern"],
        days=user_settings["simulation_days"],
        initial_price=user_settings["simulation_initial_price"],
        volatility=user_settings["simulation_volatility"]
    )
    symbol = "SIM/BTC"
    interval = user_settings.get("simulation_interval", "1h")
    st.subheader("Simulationsmuster")
    plot_simulation_pattern(df, user_settings["simulation_pattern"])
else:
    coin = user_settings["coin"]
    interval = user_settings["interval"]
    start_date = user_settings["start_date"]
    end_date = user_settings["end_date"]
    max_bars = user_settings["max_bars"]
    
    symbol, df, error = fetch_bitget_candles(coin, interval, start_date, end_date, max_bars)
    if error:
        st.error(error)
        st.stop()

# Store DataFrame
st.session_state["df"] = df

# st.dataframe(df)  # interaktive Tabelle
# Initial price for grid calculations
# initial_price = df.iloc[0]["close"]

# Calculate grid lines for visualization (angepasst für bot.py v17)
grid_lines = None
if user_settings["enable_bot"]:
    bot_params = user_settings["bot_params"]
    try:
        # Temporäre Instanz zur Grid-Berechnung
        from services.bot import GridBot
        dummy_bot = GridBot(
            total_investment=10000,  # Dummy-Wert
            lower_price=float(bot_params["lower_price"]),
            upper_price=float(bot_params["upper_price"]),
            num_grids=int(bot_params["num_grids"]),
            grid_mode=str(bot_params["grid_mode"])
        )
        grid_lines = dummy_bot.grid_lines  # Zugriff auf berechnete Grid-Lines

    # except Exception as e:
    #     st.error(f"Grid-Berechnungsfehler: {str(e)}")
    except Exception as e:
        st.error(f"Grid-Berechnungsfehler → {e.__class__.__name__}: {e}")




# Settings change detection
current_settings = {k: v for k, v in user_settings.items() if k != "bot_run_triggered"}
if st.session_state.prev_settings != current_settings:
    st.session_state.prev_settings = current_settings
    st.session_state.results = None

# Grid Bot Simulation (angepasst für Error-Handling)
if user_settings["enable_bot"] and user_settings.get("bot_run_triggered", False):
    with st.spinner("Simulation läuft..."):
        try:
            bot_params = user_settings["bot_params"]
            results = simulate_grid_bot(
                df=df,
                total_investment=float(bot_params["total_investment"]),
                lower_price=float(bot_params["lower_price"]),
                upper_price=float(bot_params["upper_price"]),
                num_grids=int(bot_params["num_grids"]),
                grid_mode=str(bot_params["grid_mode"]),
                fee_rate=float(bot_params["fee_rate"]),
                reserve_pct=float(bot_params["reserve_pct"])
            )
            if results.get("error"):
                st.error(f"Simulationsfehler: {results['error']}")
            else:
                st.session_state.results = results
        except Exception as e:
            st.error(f"Kritischer Fehler: {str(e)}")


# Rest bleibt unverändert...
trade_log = st.session_state.results.get("trade_log") if st.session_state.results else None

# render_chart_and_metrics(df, symbol, interval, 
#                          user_settings["chart_type"], 
#                          user_settings["show_volume"],
#                          grid_lines=grid_lines,
#                          trade_log=trade_log)

# results = st.session_state.get("results")
# # Speichere Bot-Einstellungen mit ab
# results["bot_params"] = user_settings["bot_params"]
# st.session_state.results = results


results = st.session_state.get("results")

# Nur weitermachen, wenn Ergebnisse existieren
if results is not None:
    results["bot_params"] = user_settings.get("bot_params", {})
    st.session_state.results = results
#else:
 #   st.warning("⚠️ Simulationsergebnisse fehlen – keine bot_params gespeichert.")



daily_values = results.get("daily_values") if results else None

render_chart_and_metrics(
    df,
    symbol,
    interval,
    user_settings["chart_type"],
    user_settings["show_volume"],
    grid_lines=grid_lines,
    trade_log=trade_log,
    show_grid_lines=user_settings.get("show_grid_lines", False),
    daily_values=daily_values
)


if st.session_state.results:
    display_bot_results(st.session_state.results, df)

