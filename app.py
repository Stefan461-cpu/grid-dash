import streamlit as st
from datetime import date, timedelta
from components.ui import get_user_settings, render_chart_and_metrics, display_bot_results, plot_simulation_pattern  # FIXED TYPO HERE
from services.bitget_api import fetch_bitget_candles
from services.bot import calculate_grid_lines, simulate_grid_bot
from services.simulator import generate_simulated_data


# Seiteneinstellungen
st.set_page_config(page_title="Grid Bot Simulator", layout="wide")
st.title("📈 Grid Bot Simulator")

# Initialize session state
if 'prev_settings' not in st.session_state:
    st.session_state.prev_settings = None
if 'results' not in st.session_state:
    st.session_state.results = None

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
    interval = user_settings.get("simulation_interval", "1h")
    
    # Show pattern visualization
    st.subheader("Simulation Pattern Visualization")
    plot_simulation_pattern(df, user_settings["simulation_pattern"])  # FIXED FUNCTION NAME
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

# Store DataFrame
st.session_state["df"] = df

# Calculate grid lines for visualization
grid_lines = None
if user_settings["enable_bot"]:
    from services.bot import calculate_grid_lines
    bot_params = user_settings["bot_params"]
    grid_lines = calculate_grid_lines(
        bot_params["lower_price"],
        bot_params["upper_price"],
        bot_params["num_grids"],
        bot_params["grid_mode"]
    )

# Get trade log from previous run
trade_log = st.session_state.results.get("trade_log") if st.session_state.results else None

# Chart anzeigen
render_chart_and_metrics(df, symbol, interval, 
                         user_settings["chart_type"], 
                         user_settings["show_volume"],
                         grid_lines=grid_lines,
                         trade_log=trade_log)

# Settings change detection
current_settings = {k: v for k, v in user_settings.items() if k != "bot_run_triggered"}
if st.session_state.prev_settings != current_settings:
    st.session_state.prev_settings = current_settings
    st.session_state.results = None

# Vor dem simulate_grid_bot-Aufruf:
try:
    # Typkonvertierung sicherstellen
    bot_params = user_settings["bot_params"]
    results = simulate_grid_bot(
        df=df,
        total_investment=float(bot_params["total_investment"]),
        lower_price=float(bot_params["lower_price"]),
        upper_price=float(bot_params["upper_price"]),
        num_grids=int(bot_params["num_grids"]),
        grid_mode=str(bot_params["grid_mode"]),
        fee_rate=float(bot_params["fee_rate"])
    )
except (ValueError, KeyError) as e:
    st.error(f"Parameter-Fehler: {str(e)}")
    st.stop()

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
            st.session_state.results = results

# Display results if available
if st.session_state.results:
    display_bot_results(st.session_state.results, df)