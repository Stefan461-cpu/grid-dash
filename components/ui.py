# components/ui.py
def get_user_settings():
    with st.sidebar:
        st.header("Einstellungen")
        coin = st.selectbox("Währung (COINUSDT)", ["BTC", "ETH", "SOL"])
        interval = st.radio("Intervall", ["1m", "5m", "15m", "1h", "4h", "1d"], horizontal=True)
        start_date = st.date_input("Startdatum")
        end_date = st.date_input("Enddatum")
        max_bars = st.slider("Max. Kerzen (10–1000)", 10, 1000, 500)
        st.subheader("Chart-Optionen")
        chart_type = st.selectbox("Chart-Typ", ["Candlestick", "Linie"], index=0)
        show_volume = st.checkbox("Volumen anzeigen", True)
        
        # Grid Bot Settings
        st.subheader("Grid Bot Parameter")
        enable_bot = st.checkbox("Grid Bot aktivieren", True)
        bot_params = {}
        if enable_bot:
            # Get current price from data if available
            try:
                # Default values if no data
                default_lower = 10000 * 0.7  # BTC example
                default_upper = 10000 * 1.3
            except:
                default_lower = 100
                default_upper = 200
            
            bot_params["total_investment"] = st.number_input("Gesamtinvestition (USDT)", 
                                                           min_value=10.0, 
                                                           value=1000.0,
                                                           step=100.0)
            
            col1, col2 = st.columns(2)
            with col1:
                bot_params["lower_price"] = st.number_input("Unterer Preis", 
                                                          min_value=0.0001, 
                                                          value=default_lower,
                                                          format="%.4f")
            with col2:
                bot_params["upper_price"] = st.number_input("Oberer Preis", 
                                                          min_value=0.0001, 
                                                          value=default_upper,
                                                          format="%.4f")
            
            bot_params["num_grids"] = st.slider("Anzahl Grids", 2, 100, 20)
            bot_params["grid_mode"] = st.radio("Grid Modus", ["arithmetic", "geometric"], index=0)
            bot_params["reserved_amount"] = st.number_input("Reserviertes Kapital (USDT)", 
                                                          min_value=0.0, 
                                                          value=100.0,
                                                          step=10.0)
            bot_params["fee_rate"] = st.number_input("Gebühren (%)", 
                                                   min_value=0.0, 
                                                   value=0.1,
                                                   step=0.01) / 100.0
    
    return {
        "coin": coin,
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "max_bars": max_bars,
        "chart_type": chart_type,
        "show_volume": show_volume,
        "enable_bot": enable_bot,
        "bot_params": bot_params
    }
