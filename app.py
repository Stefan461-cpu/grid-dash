# app.py
import streamlit as st
from components.ui import get_user_settings, render_chart_and_metrics, display_bot_results
from services.bitget_api import fetch_bitget_candles
from services.bot import simulate_grid_bot  # New import

st.set_page_config(page_title="Grid Bot Dashboard", layout="wide")
st.title("Grid Bot Dashboard – Live Bitget Daten")

# Initialize session state
if 'bot_results' not in st.session_state:
    st.session_state.bot_results = None

# Get user settings
settings = get_user_settings()

# Fetch API data
symbol, df, error = fetch_bitget_candles(
    coin=settings["coin"],
    interval=settings["interval"],
    start_date=settings["start_date"],
    end_date=settings["end_date"],
    max_bars=settings["max_bars"]
)

if error:
    st.error(error)
elif df.empty:
    st.warning("Keine Daten verfügbar")
else:
    st.success(f"Erfolgreich {len(df)} Kerzen geladen")
    
    # Update grid bot price defaults if needed
    if settings["enable_bot"]:
        current_price = df.iloc[-1]['close']
        bot_params = settings["bot_params"]
        
        # Set default price bounds if not set
        if bot_params.get("lower_price", 0) <= 0.0001:
            bot_params["lower_price"] = current_price * 0.7
        if bot_params.get("upper_price", 0) <= 0.0001:
            bot_params["upper_price"] = current_price * 1.3
    
    # Run grid bot simulation if enabled
    grid_lines = None
    if settings["enable_bot"] and st.sidebar.button("Grid Bot simulieren", type="primary"):
        with st.spinner("Simuliere Grid Bot..."):
            st.session_state.bot_results = simulate_grid_bot(
                df=df,
                **settings["bot_params"]
            )
            # Add parameters to results for display
            st.session_state.bot_results.update(settings["bot_params"])
            grid_lines = st.session_state.bot_results["grid_lines"]
    
    # If we have previous results, use their grid lines
    elif settings["enable_bot"] and st.session_state.bot_results:
        grid_lines = st.session_state.bot_results["grid_lines"]
    
    # Render chart with grid lines
    render_chart_and_metrics(
        df, 
        symbol, 
        settings["interval"], 
        settings["chart_type"], 
        settings["show_volume"],
        grid_lines=grid_lines
    )
    
    # Display bot results if available
    if settings["enable_bot"] and st.session_state.bot_results:
        display_bot_results(st.session_state.bot_results)
