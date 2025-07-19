# ui.py Version 30

# components/ui.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import plotly.graph_objects as go
import numpy as np
from services.bitget_api import fetch_bitget_candles

def get_user_settings():
    with st.sidebar:
        #version_placeholder = st.sidebar.empty()

        st.subheader("Daten auswählen")
              
        # use_simulated = st.session_state.get("sim_toggle", False)
        # Synthetische Simulationsdaten sind aktuell deaktiviert - nicht mehr in der Sidebar
        # Da nicht klar, ob der Bot darauf funktioniert
        use_simulated = st.checkbox("Simulationsdaten verwenden", False, key="sim_toggle",disabled=True)
        
        # Callback zum automatischen Laden bei Eingabe der Währung
        def update_price_range():
            coin = st.session_state.get("coin_input", "BTC")
            symbol, df, error = fetch_bitget_candles(
                coin=coin,
                interval="1h",  # Default-Intervall für Erstabfrage
                start_date=date.today() - timedelta(days=5),
                end_date=date.today(),
                max_bars=50
            )
            if error or df is None or df.empty:
                st.session_state["close_price"] = 100000.0
            else:
                price = (df["close"].iloc[0] + df["close"].iloc[-1]) / 2
                st.session_state["close_price"] = price
                st.session_state["lower_price"] = round(price * 0.8, 2)
                st.session_state["upper_price"] = round(price * 1.2, 2)

 
                # price = df.iloc[0]["close"]
                # st.session_state["close_price"] = price
                # st.session_state["lower_price"] = round(price * 0.8, 2)
                # st.session_state["upper_price"] = round(price * 1.2, 2)

            # Initialwerte (wenn noch nicht gesetzt)
            if "lower_price" not in st.session_state:
                st.session_state["lower_price"] = 90000.0
            if "upper_price" not in st.session_state:
                st.session_state["upper_price"] = 130000.0
            if "close_price" not in st.session_state:
                st.session_state["close_price"] = 100000.0

            # # Eingabe der Währung (nur Anzeige hier)
            # coin_display = st.session_state.get("coin_input", "BTC")

            # # Preisbereichseingabe mit dynamischen Defaults
            # default_lower = st.session_state.get("lower_price", 90000.0)
            # default_upper = st.session_state.get("upper_price", 130000.0)

            # col1, col2 = st.columns(2)
            # with col1:
            #     bot_params["lower_price"] = st.number_input(
            #         "Unterer Preis", 0.0001, value=default_lower, format="%.4f"
            #     )
            # with col2:
            #     bot_params["upper_price"] = st.number_input(
            #         "Oberer Preis", 0.0001, value=default_upper, format="%.4f"
            #     )


            # Info-Label zum Kurs
            if "df" in st.session_state and not st.session_state["df"].empty:
                df = st.session_state["df"]
                avg_price = (df["close"].iloc[0] + df["close"].iloc[-1]) / 2
            else:
                avg_price = st.session_state.get("close_price", 100000.0)  # fallback

            price = st.session_state["df"]["close"].iloc[0]

#             if st.session_state.get("close_price"):
#                 st.caption(
#                     f"💡 Voreingestellter Preisbereich (Unter-/Obergrenze) basiert auf einem Kurs von COIN +/- 20 % "
#                     f"({st.session_state['close_price']:,.2f} USDT)"
# #                    f"({st.session_state['close_price']:,.2f} USDT)"
#                 )
# #                 st.caption(
#                     f"💡 Voreingestellter Preisbereich (Unter-/Obergrenze) basiert auf dem Mittelwert aus Start- und Endkurs "
#                     f"({avg_price:,.2f} USDT)"
# )

        
        
        if use_simulated:
            st.subheader("Simulationsparameter")

            patterns = {
                "Linear ansteigend": "linear_up",
                "Linear fallend": "linear_down",
                "Sinuskurve": "sine",
                "Range Bound (Seitwärts)": "range_bound",
                "Ausbruch": "breakout",
                "Volatil": "volatile",
                "Mean Reverting": "mean_reverting"
            }
            label = st.selectbox("Kursverlauf", list(patterns.keys()), index=0)
            pattern = patterns[label]  # ← liefert intern z. B. "linear_up"

            init_price = st.number_input("Startkurs (USDT)", 
                                        value=100000.0, 
                                        step=1000.0,
                                        key="sim_init_price")
            sim_days = st.slider("Anzahl Tage", 1, 30, 7, key="sim_days")
            volatility = st.slider("Volatilität", 1000, 20000, 5000, key="sim_vol")
        else:
            # Original market data inputs
            st.subheader("Marktdaten")
            #coin = st.text_input("Währung (COIN in USDT)", value="BTC", placeholder="e. g. BTC or ETH")
            
            coin=st.selectbox(
                "Währung (COIN in USDT)",
                options=["BTC", "ETH", "SOL", "ADA", 
                "AVAX", "BNB", "DOGE", "DOT", "ICP", "LINK", 
                "LTC", "MATIC", "NEAR", "SHIB", "TON", "TRX", 
                "UNI", "WBTC", "XRP", "XLM"],
                index=0,
                placeholder="Gib ein Symbol ein…",
                key="coin_input",
                on_change=update_price_range
            )
   
            # coin = st.text_input(
            #     "Währung (COIN in USDT)", 
            #     value="BTC", 
            #     key="coin_input", 
            #     on_change=update_price_range
            # )
            interval = st.radio("Intervall", ["1m", "5m", "15m", "1h", "4h", "1d"], horizontal=True, index=3)
            today = date.today()
            start_date = st.date_input("Startdatum", today - timedelta(days=30))
            end_date = st.date_input("Enddatum", today)
            max_bars = st.slider("Anzahl Kerzen (10–1000)", 10, 1000, 1000)

        # Common settings (both simulated and real data)
        st.subheader("Chart Einstellungen")
        chart_type = st.selectbox("Chart Typ", ["Candlestick", "Linie"], index=0)
        show_volume = st.checkbox("Volumen anzeigen", True)
        show_grid_lines = st.checkbox("Gridbereich anzeigen", False)  # NEW: Grid toggle
        
        # Grid bot settings
        st.subheader("Grid Bot Parameter")
        enable_bot = st.checkbox("Grid Bot aktivieren", True)
        bot_params = {}
        bot_run_triggered = False

        if enable_bot:
            
            # Dynamische Preisgrenzen – immer sichtbar
            coin_display = st.session_state.get("coin_input", "BTC")
            default_lower = st.session_state.get("lower_price", 90000.0)
            default_upper = st.session_state.get("upper_price", 130000.0)

            col1, col2 = st.columns(2)
            with col1:
                bot_params["lower_price"] = st.number_input(
                    "Unterer Preis", 0.0001, value=default_lower, format="%.4f"
                )
            with col2:
                bot_params["upper_price"] = st.number_input(
                    "Oberer Preis", 0.0001, value=default_upper, format="%.4f"
                )

            if st.session_state.get("close_price"):
                st.caption(
                    f"💡 Voreingestellter Preisbereich basiert auf dem Kurs von COIN +/- 20 % "
                    f"({st.session_state['close_price']:,.2f} USDT)"
                )


            
            # # Default price setup
            # default_price = None
            # if "df" in st.session_state and not st.session_state["df"].empty:
            #     default_price = st.session_state["df"].iloc[0]["close"]
            # else:
            #     default_price = 100000.0

            # bot_params["total_investment"] = st.number_input("Investitionsbetrag (USDT)", 10.0, value=10000.0, step=100.0)
 
            # bot_params["num_grids"] = st.slider("Anzahl Grids", 2, 500, 20)

            # # Zwei Optionen anzeigen
            # slider_value = st.slider("Anzahl Grids - Wähle einen Wert", min_value=2, max_value=500, value=20)
            # number_value = st.number_input("Oder gib den Wert direkt ein", min_value=2, max_value=500, value=slider_value)

            # # Synchronisieren: wenn sich eines ändert, überschreibt es das andere
            # final_value = number_value if number_value != slider_value else slider_value
            # bot_params["num_grids"] = final_value

            #st.write(f"Verwendeter Wert: {final_value}")

            # Eingabe Anzahl Grids mit Slider und Number Input - bidirektionales Update

            # st.subheader("Anzahl Grids")
            # Initialwerte setzen (nur beim ersten Lauf)
            if "num_grids" not in st.session_state:
                st.session_state.num_grids = 20

            # Callback-Funktionen definieren
            def update_from_slider():
                st.session_state.num_grids = st.session_state.slider_value

            def update_from_number():
                st.session_state.num_grids = st.session_state.number_value

            # Slider mit Callback
            st.slider(
                "Anzahl Grids – wähle einen Wert",
                min_value=2, max_value=500,
                key="slider_value",
                value=st.session_state.num_grids,
                on_change=update_from_slider
            )

            # Number Input mit Callback
            st.number_input(
                "Oder gib den Wert direkt ein",
                min_value=2, max_value=500,
                key="number_value",
                value=st.session_state.num_grids,
                on_change=update_from_number
            )

            # Endgültiger Wert
            bot_params["num_grids"] = st.session_state.num_grids





            grid_modes = {
                "Arithmetisch (gleichmäßige Abstände)": "arithmetic",
                "Geometrisch (prozentuale Abstände)": "geometric"
            }

            grid_mode_label = st.radio("Grid Modus", list(grid_modes.keys()), index=0)
            bot_params["grid_mode"] = grid_modes[grid_mode_label]

            bot_params["fee_rate"] = st.number_input("Handelsgebühren (%)", 0.0, value=0.1, step=0.01) / 100.0

            reserve_pct = st.number_input("Betrag reserviert für Gebühren (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.5, key="reserve_pct") / 100.0
            bot_params["reserve_pct"] = reserve_pct
#            fee_rate = bot_params["fee_rate"]

            reserve_pct = bot_params.get("reserve_pct", 0.03)
            fee_rate = bot_params.get("fee_rate", 0.001)
            mode = bot_params.get("grid_mode", "arithmetic")
            lower_price = bot_params.get("lower_price", 0)
            upper_price = bot_params.get("upper_price", 0)
            num_grids = bot_params.get("num_grids", 1)

            grid_range = ""

            if lower_price > 0 and num_grids > 0 and upper_price > lower_price:
                if mode == "arithmetic":
                    grid_step = (upper_price - lower_price) / num_grids

                    # unterstes Grid
                    buy_low = lower_price
                    sell_low = lower_price + grid_step
                    raw_low = (sell_low - buy_low) / buy_low
                    net_low = (raw_low * (1 - reserve_pct) - 2 * fee_rate) * 100

                    # oberstes Grid
                    sell_high = upper_price
                    buy_high = upper_price - grid_step
                    raw_high = (sell_high - buy_high) / buy_high
                    net_high = (raw_high * (1 - reserve_pct) - 2 * fee_rate) * 100
                    st.session_state["net_grid_profit_pct"] = (net_high + net_low)/2

                    grid_range = f"{net_low:.2f} % – {net_high:.2f} %"
                elif mode == "geometric":
                    raw = (upper_price / lower_price) ** (1 / num_grids) - 1
                    net = (raw * (1 - reserve_pct) - 2 * fee_rate) * 100
                    st.session_state["net_grid_profit_pct"] = net

                    grid_range = f"{net:.2f} %"




            #reserve_pct = bot_params.get("reserve_pct", 0.03)

            # grid_profit_pct = 0
            # net_grid_profit_pct = 0

            # if bot_params["lower_price"] > 0 and bot_params["num_grids"] > 0:
            #     if bot_params["grid_mode"] == "arithmetic":
            #         raw_return = (bot_params["upper_price"] - bot_params["lower_price"]) / bot_params["num_grids"]
            #         raw_grid_pct = raw_return / bot_params["lower_price"]
            #     elif bot_params["grid_mode"] == "geometric":
            #         raw_grid_pct = (bot_params["upper_price"] / bot_params["lower_price"]) ** (1 / bot_params["num_grids"]) - 1

            #     # Bruttogewinn auf 100 % bezogen (ohne Fees)
            #     grid_profit_pct = raw_grid_pct * (1 - reserve_pct) * 100

            #     # Nettogewinn nach Trading-Fees (doppelt pro Grid)
            #     net_grid_profit_pct = (raw_grid_pct * (1 - reserve_pct) - 2 * fee_rate) * 100

            # st.sidebar.markdown(f"""
            # <div style='font-size: 0.875rem; line-height: 1.4; margin-top: 10px;'>
            # <b>📈 Gewinn pro Grid (nach Fees):</b> 
            # {grid_profit_pct:.2f} %
            # </div>
            # """, unsafe_allow_html=True)
 
            # Farb-/Symbol-Logik auf Basis der unteren Grenze
            value_for_rating = net_low if mode == "arithmetic" else net
            symbol = "⚠️"
            color = "orange"

            if value_for_rating >= 1.0:
                color = "#00FF66"
                symbol = "🔺"
            elif value_for_rating < 0.3:
                color = "#FF4D4D"
                symbol = "🔻"

            # Anzeige in der Sidebar
            st.sidebar.markdown(f"""
            <div style='font-size: 0.875rem; line-height: 1.4; margin-top: 10px; color: {color};'>
            <b>{symbol} Gewinn pro Grid (nach Fees):</b><br>
            {grid_range}
            </div>
            """, unsafe_allow_html=True)
 
 
 
            st.write("---")
             # Default price setup
            default_price = None
            if "df" in st.session_state and not st.session_state["df"].empty:
                default_price = st.session_state["df"].iloc[0]["close"]
            else:
                default_price = 100000.0

            bot_params["total_investment"] = st.number_input("Investitionsbetrag (USDT)", 10.0, value=10000.0, step=100.0)

 
           # Show fee reserves - neu
            reserve_usdt = bot_params["total_investment"] * (bot_params["reserve_pct"] * 1/3)
            reserve_coin_value = bot_params["total_investment"] * (bot_params["reserve_pct"] * 2/3)
            if st.button("Grid Bot starten"):
                bot_run_triggered = True

    # Return settings based on mode
    if use_simulated:
        return {
            "use_simulated_data": True,
            "simulation_pattern": pattern,
            "simulation_initial_price": init_price,
            "simulation_days": sim_days,
            "simulation_volatility": volatility,
            "chart_type": chart_type,
            "show_volume": show_volume,
            "show_grid_lines": show_grid_lines,  # NEW: Grid toggle state
            "enable_bot": enable_bot,
            "bot_params": bot_params,
            "bot_run_triggered": bot_run_triggered
        }
    else:
        return {
            "coin": coin,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "max_bars": max_bars,
            "chart_type": chart_type,
            "show_volume": show_volume,
            "show_grid_lines": show_grid_lines,  # NEW: Grid toggle state
            "enable_bot": enable_bot,
            "bot_params": bot_params,
            "bot_run_triggered": bot_run_triggered
        }


def calculate_annualized_volatility(df, interval):
    if "price_change" not in df or df["price_change"].isna().all():
        return None, None

    std_pct = df["price_change"].std()  # % pro Intervall

    interval_mapping = {
        "1h":  {"monthly": 720, "yearly": 8760},
        "4h":  {"monthly": 180, "yearly": 2190},
        "1d":  {"monthly": 30,  "yearly": 365}
    }

    if interval not in interval_mapping:
        return None, None

    factor_month = np.sqrt(interval_mapping[interval]["monthly"])
    factor_year = np.sqrt(interval_mapping[interval]["yearly"])

    vola_month = std_pct * factor_month
    vola_year = std_pct * factor_year

    return vola_month, vola_year


# # Render colored metric with custom HTML
# def render_colored_metric(col, label: str, value: float, unit: str = "%"):
#     """
#     Zeigt einen farbigen Metric-Wert im Stil von st.metric an – mit freier Farbe und exakt abgestimmtem Layout.

#     Parameters:
#         col:    Streamlit-Spalte (z. B. col4)
#         label:  Beschriftung (z. B. "Rendite im Sim-Intervall (%)")
#         value:  Zahlenwert (z. B. 73.9)
#         unit:   Einheit für Anzeige (default: "%")
#     """
#     farbe = "#00FF00" if value >= 0 else "red"

#     col.markdown(f"""
#     <div style="font-size: 0.875rem; line-height: 1.7; font-weight: 410; color: #ffffff;">
#         {label}
#     </div>
#     <div style="font-size: 2.25rem; line-height: 1.35; font-weight: 450; color: {farbe};">
#         {value:,.2f} {unit}
#     </div>
#     """, unsafe_allow_html=True)

def render_colored_metric(col, label: str, value: float, unit: str = "%", override_color: str = None, precision: int = 2, highlight_background: str = None):
    """
    Zeigt einen farbigen Metric-Wert im Stil von st.metric an – mit freier Farbe und exakt abgestimmtem Layout.

    Parameters:
        col:             Streamlit-Spalte (z. B. col4)
        label:           Beschriftung (z. B. "Rendite im Sim-Intervall (%)")
        value:           Zahlenwert (z. B. 73.9)
        unit:            Einheit für Anzeige (default: "%")
        override_color:  Optional: feste Farbe als CSS-Farbwert (z. B. "white", "#00FF00")
    """

    # Textfarbe + Hintergrund
    farbe = override_color if override_color else ("#00FF00" if value >= 0 else "red")
    background = f"background-color: {highlight_background}; padding: 4px 8px; border-radius: 6px;" if highlight_background else ""

    col.markdown(f"""
    <div style="font-size: 0.875rem; line-height: 1.7; font-weight: 410; color: #ffffff;">
        {label}
    </div>
    <div style="font-size: 2.25rem; line-height: 1.35; font-weight: 450; color: {farbe}; {background}">
        {value:,.{precision}f} {unit}
    </div>
    """, unsafe_allow_html=True)

 
def render_chart_and_metrics(df, symbol, interval, chart_type, show_volume, 
                           grid_lines=None, trade_log=None, show_grid_lines=False,
                           daily_values=None):  # NEW: show_grid_lines param
    if df.empty:
        st.warning("Keine Daten zum Anzeigen des Charts.")
        return
        
    st.subheader(f"{symbol} {interval} Chart")
    fig = go.Figure()
    
    # Plot main chart
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df['timestamp'], 
            open=df['open'], 
            high=df['high'], 
            low=df['low'], 
            close=df['close'],
            increasing_line_color='#2ECC71', 
            decreasing_line_color='#E74C3C', 
            name='Preis'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], 
            y=df['close'], 
            mode='lines', 
            name='Schlusskurs',
            line=dict(color='#3498DB', width=2)
        ))
    
    # Add volume if enabled
    if show_volume and 'volume' in df.columns:
        fig.add_trace(go.Bar(
            x=df['timestamp'], 
            y=df['volume'], 
            name='Volumen', 
            marker_color='#7F8C8D', 
            yaxis='y2'
        ))
    
    # # Neue Achse: Portfolio-Wert (y3)
    # if daily_values:
    #     daily_df = pd.DataFrame({
    #         "date": pd.to_datetime(list(daily_values.keys())),
    #         "value": list(daily_values.values())
    #     }).sort_values("date")

    #     fig.add_trace(go.Scatter(
    #         x=daily_df["date"],
    #         y=daily_df["value"],
    #         mode="lines+markers",
    #         name="Portfolio-Wert",
    #         line=dict(color="gold", width=2, dash="dot"),
    #         yaxis="y3"
    #     ))

    if daily_values and 'initial_investment' in st.session_state.results:
        initial_value = st.session_state.results['initial_investment']
        daily_df = pd.DataFrame({
            "date": pd.to_datetime(list(daily_values.keys())),
            "value": list(daily_values.values())
        }).sort_values("date")

        # Flags zur einmaligen Anzeige der Legenden
        legend_shown = {"blue": False, "red": False}

        for i in range(1, len(daily_df)):
            x_segment = [daily_df["date"].iloc[i-1], daily_df["date"].iloc[i]]
            y_segment = [daily_df["value"].iloc[i-1], daily_df["value"].iloc[i]]

            if all(v > initial_value for v in y_segment):
                color = "blue"
                name = "Portfolio über Initialwert"
                showlegend = not legend_shown[color]
                legend_shown[color] = True
            else:
                color = "red"
                if all(v <= initial_value for v in y_segment):
                    name = "Portfolio unter Initialwert"
                    showlegend = not legend_shown[color]
                    legend_shown[color] = True
                else:
                    name = None
                    showlegend = False  # gemischtes Segment → rot ohne Legende

            fig.add_trace(go.Scatter(
                x=x_segment,
                y=y_segment,
                mode="lines",
                line=dict(color=color, width=2),
                name=name,
                showlegend=showlegend,
                yaxis="y3"
            ))


    # if daily_values and 'initial_investment' in st.session_state.results:
    #     initial_value = st.session_state.results['initial_investment']
    #     daily_df = pd.DataFrame({
    #         "date": pd.to_datetime(list(daily_values.keys())),
    #         "value": list(daily_values.values())
    #     }).sort_values("date")

    #     for i in range(1, len(daily_df)):
    #         x_segment = [daily_df["date"].iloc[i-1], daily_df["date"].iloc[i]]
    #         y_segment = [daily_df["value"].iloc[i-1], daily_df["value"].iloc[i]]
    #         color = "blue" if all(v > initial_value for v in y_segment) else (
    #                 "red" if all(v <= initial_value for v in y_segment) else "red")

    #         fig.add_trace(go.Scatter(
    #             x=x_segment,
    #             y=y_segment,
    #             mode="lines",
    #             line=dict(color=color, width=2),
    #             name="Portfolio-Wert" if i == 1 else None,
    #             showlegend=(i == 1),
    #             yaxis="y3"
    #         ))



    # if daily_values and 'initial_investment' in st.session_state.results:
    #     initial_value = st.session_state.results['initial_investment']
    #     daily_df = pd.DataFrame({
    #         "date": pd.to_datetime(list(daily_values.keys())),
    #         "value": list(daily_values.values())
    #     }).sort_values("date")

    #     # Zwei Serien erstellen: über / unter initial_investment
    #     above = daily_df["value"] > initial_value
    #     below = ~above

    #     # Blau (über Initialwert)
    #     fig.add_trace(go.Scatter(
    #         x=daily_df["date"][above],
    #         y=daily_df["value"][above],
    #         mode="lines+markers",
    #         name="Portfolio über Initialwert",
    #         line=dict(color="blue", width=2),
    #         yaxis="y3"
    #     ))

    #     # Rot (unter Initialwert)
    #     fig.add_trace(go.Scatter(
    #         x=daily_df["date"][below],
    #         y=daily_df["value"][below],
    #         mode="lines+markers",
    #         name="Portfolio unter Initialwert",
    #         line=dict(color="red", width=2),
    #         yaxis="y3"
    #     ))



    # # Add grid lines if provided AND enabled
    # if show_grid_lines and grid_lines and not df.empty:  # NEW: check show_grid_lines
    #     for price in grid_lines:
    #         if df['low'].min() <= price <= df['high'].max():
    #             fig.add_hline(
    #                 y=price, 
    #                 line_dash="dot", 
    #                 line_width=1,
    #                 line_color="rgba(125,125,125,0.5)",
    #                 annotation_text=f"{price:.4f}",
    #                 annotation_position="right",
    #                 annotation_font_size=10
    #             )

    # if show_grid_lines and grid_lines and not df.empty:
    #     for price in grid_lines:
    #         if df['low'].min() <= price <= df['high'].max():
    #             formatted_price = f"{price/1000:.0f}k"
    #             fig.add_hline(
    #                 y=price,
    #                 line_dash="dot",
    #                 line_width=1,
    #                 line_color="rgba(125,125,125,0.5)",
    #                 annotation_text=formatted_price,
    #                 annotation_position="top right",  # keine Feinjustierung möglich
    #                 annotation_font_size=10
    #             )

    if show_grid_lines and grid_lines and not df.empty:
        lower = min(grid_lines)
        upper = max(grid_lines)

        fig.add_shape(
            type="rect",
            xref="paper",
            yref="y",
            x0=0,
            x1=1,
            y0=lower,
            y1=upper,
            fillcolor="rgba(100, 150, 255, 0.1)",
            line=dict(width=0),
            layer="below"
        )

        # Optional: Oberste und unterste Linie einzeln markieren
        fig.add_hline(y=lower, line_dash="dot", line_color="blue", line_width=1)
        fig.add_hline(y=upper, line_dash="dot", line_color="blue", line_width=1)

    
    # Add trade markers if trade log exists
    if trade_log and not df.empty:
        trades_df = pd.DataFrame(trade_log)
        buy_trades = trades_df[trades_df['type'] == 'BUY']
        sell_trades = trades_df[trades_df['type'] == 'SELL']
        
        if not buy_trades.empty:
            fig.add_trace(go.Scatter(
                x=buy_trades['timestamp'],
                y=buy_trades['price'],
                mode='markers',
                marker=dict(color='green', size=10, symbol='triangle-up'),
                name='BUY'
            ))
        if not sell_trades.empty:
            fig.add_trace(go.Scatter(
                x=sell_trades['timestamp'],
                y=sell_trades['price'],
                mode='markers',
                marker=dict(color='red', size=10, symbol='triangle-down'),
                name='SELL'
            ))
    
    # Configure layout
    fig.update_layout(
        height=600,
        title=f"{symbol} {interval} Chart",
        yaxis_title="Preis (USDT)",
        xaxis_title="Zeit",
        template="plotly_dark",
        xaxis=dict(type='date', tickformat='%d.%m', rangeslider_visible=False),
        yaxis=dict(autorange=True, side='right'),
        yaxis2=dict(overlaying='y', side='left', showgrid=False, visible=show_volume),
        yaxis3=dict(
            title="Portfolio (USDT)",
            anchor="x",
            overlaying="y",
            side="left",
            position=0.05,
            showgrid=False
        ),
        margin=dict(l=50, r=50, t=80, b=100),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True, key=f"{symbol}_{interval}")
    
    
    # Display market metrics
    if not df.empty:
        st.subheader("📊 Marktdaten")
        latest = df.iloc[-1]
        
        results = st.session_state.get("results")
        buy_hold_return = None
        bot_return = None
        fee_ratio = None

        if results and df is not None and not df.empty:
            initial = results.get('initial_price', df.iloc[0]['close'])
            final = results.get('final_price', df.iloc[-1]['close'])
            buy_hold_return = (final - initial) / initial * 100
            bot_return = results.get('profit_pct', 0)
            fee_ratio = results.get('fees_paid', 0) / results.get('initial_investment', 1) * 100
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Aktueller Preis (USDT)", f"{latest['close']:,.2f}", f"{df['price_change'].iloc[-1]:,.2f} %" if 'price_change' in df else "-")
        # col3.metric("Max Sim-Intervall (USDT)", f"{df['high'].max():,.2f}")
        # col3.metric("Min Sim-Intervall (USDT)", f"{df['low'].min():,.2f}")
        min_price = df["low"].min()
        max_price = df["high"].max()
        maxmin_perc = ((max_price - min_price) / min_price) * 100
        maxmin = ((max_price - min_price) ) 
        #col4.metric("Rendite Sim-Intervall (%)", f"{rendite:.2f} %")
        # Farbliche Anzeige über delta
        #farbe = "green" if rendite > 0 else "red"
 
        if buy_hold_return is not None:
            render_colored_metric(col2, "Buy & Hold P/L", buy_hold_return)
        if  maxmin is not None:
            render_colored_metric(col4, "Max-Min im Sim-Intervall (USDT)", maxmin, "", override_color="white")
        if maxmin_perc is not None:
            render_colored_metric(col4, "Max-Min im Sim-Intervall (%)", maxmin_perc, override_color="white")
        render_colored_metric(col3, "Max Sim-Intervall (USDT)", df['high'].max(), unit="", override_color="white")
        render_colored_metric(col3, "Min Sim-Intervall (USDT)", df['low'].min(), unit="", override_color="white")


        
        # col4.markdown(f"""
        # <div style="font-size: 0.875rem; line-height: 1.7; font-weight: 410; color: #ffffff;">
        #     Rendite im Sim-Intervall (%)
        # </div>
        # <div style="font-size: 2.25rem; line-height: 1.35; font-weight: 450; color: {farbe};">
        #     {rendite:.2f} %
        # </div>
        # """, unsafe_allow_html=True)



 #       col4.metric("Avg Range pro Kerze (%)", f"{df['range'].mean():,.2f} %" if 'range' in df else "-")
    st.write("")  # Trennlinie
    st.write("")  # Trennlinie

    if not df.empty:
        latest = df.iloc[-1]
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Avg Range pro Kerze (%)", f"{df['range'].mean():,.2f} %" if 'range' in df else "-")
        col2.metric("Avg % Rendite pro Kerze", f"{df['price_change'].mean():,.4f} %" if 'price_change' in df else "-")
        col3.metric("MAD % Rendite pro Kerze", f"{df['price_change'].abs().mean():,.4f} %" if 'price_change' in df else "-")
        col4.metric("Vola % Rendite pro Kerze", f"{df['price_change'].std():,.4f} %" if 'price_change' in df else "-")
        #col3.metric("Min Sim-Intervall", f"{df['low'].min():,.2f}")
        #col4.metric("Avg Range pro Kerze (%)", f"{df['range'].mean():,.2f} %" if 'range' in df else "-")
        #col5.metric("Avg Preisänderung pro Kerze (%)", f"{df['price_change'].mean():,.4f} %" if 'price_change' in df else "-")

    st.text(" ")  # eine Zeile Abstand
    st.text(" ")  # eine Zeile Abstand
    if not df.empty:
        if interval in ["1h", "4h", "1d"]:
            vola_month, vola_year = calculate_annualized_volatility(df, interval)
            if vola_month is not None:
                st.subheader("📈 Projizierte Volatilität (hist.)")
                col_vm, col_vm_coin, col_vy, col_vy_coin, col5 = st.columns(5)
                col_vm.metric("Monatliche Vola", f"{vola_month:,.2f} %")
                col_vm_coin.metric("Monatlich Std Coin (USDT)", f"{(vola_month / 100 * latest['close']):,.2f}")
                col_vy.metric("Jährliche Vola", f"{vola_year:,.2f} %")
                col_vy_coin.metric("Jährlich Std Coin (USDT)", f"{(vola_year / 100 * latest['close']):,.2f}")


    # col1, col2, col3, col4 = st.columns(4)

    # col1.markdown(f"""
    # <div style='font-size:12px'>
    #     <strong>Aktueller Preis</strong><br>
    #     {latest['close']:,.2f}<br>
    #     <span style='color:gray;'>{df['price_change'].iloc[-1]:,.2f}%</span>
    # </div>
    # """, unsafe_allow_html=True)

    # col2.markdown(f"""
    # <div style='font-size:12px'>
    #     <strong>Aktueller Preis</strong><br>
    #     {latest['close']:,.2f}<br>
    #     <span style='color:gray;'>{df['price_change'].iloc[-1]:,.2f}%</span>
    # </div>
    # """, unsafe_allow_html=True)
    
    # col3.markdown(f"""
    # <div style='font-size:12px'>
    #     <strong>Aktueller Preis</strong><br>
    #     {latest['close']:,.2f}<br>
    #     <span style='color:gray;'>{df['price_change'].iloc[-1]:,.2f}%</span>
    # </div>
    # """, unsafe_allow_html=True)
    
    # col4.markdown(f"""
    # <div style='font-size:12px'>
    #     <strong>Aktueller Preis</strong><br>
    #     {latest['close']:,.2f}<br>
    #     <span style='color:gray;'>{df['price_change'].iloc[-1]:,.2f}%</span>
    # </div>
    # """, unsafe_allow_html=True)


    # # Show full data
    # with st.expander("Vollständige Kursdaten anzeigen"):
    #     st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume", "range", "price_change"]], use_container_width=True)



def render_entry(label, value, color="white", bold_label=True):
    label_style = "font-weight: bold;" if bold_label else ""
    return f"""
    <div style="display: flex; justify-content: space-between; line-height: 1.6;">
        <span style="{label_style}">{label}</span>
        <span style="color: {color};">{value}</span>
    </div>
    """


def display_bot_results(results, df=None):
    if not results:
        st.warning("No simulation results available")
        return
    
    st.text(" ")  # eine Zeile Abstand
    st.text(" ")  # eine Zeile Abstand        
    
    st.write("---")
    st.subheader("📐 Grid Bot Performance")

    if 'bot_version' in results:
        st.caption(results['bot_version'])    

    # Metrics - First Row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Investierter Betrag (USDT)", f"{results.get('initial_investment', 0):,.2f}")
    col2.metric("Endwert (USDT)", 
               f"{results.get('final_value', 0):,.2f}", 
               f"{results.get('profit_pct', 0):.2f}%")
    #col3.metric("Profit/Loss (USDT)", f"{results.get('profit_usdt', 0):,.2f}")
    render_colored_metric(col3, "Total Net P/L (USDT)", results.get("profit_usdt", 0), "")

    profit = results.get("profit_usdt", 0)
    capital = results.get("initial_capital", 1)  # Fallback 1 verhindert Division durch 0
    rendite_prozent = (profit / capital) / 100.0   # Rendite in Prozent

        # Simulation Verification
    if df is not None and not df.empty:
    #    st.subheader("Performance Comparison")
        
        # Calculate metrics
        initial = results.get('initial_price', df.iloc[0]['close'])
        final = results.get('final_price', df.iloc[-1]['close'])
        buy_hold_return = (final - initial) / initial * 100
        bot_return = results.get('profit_pct', 0)
        fee_ratio = results.get('fees_paid', 0) / results.get('initial_investment', 1) * 100

    render_colored_metric(col4, "Total Net P/L (%)", rendite_prozent)

    # Zeitstempel als datetime sicherstellen
    start_time = pd.to_datetime(df.iloc[0]['timestamp']) if 'timestamp' in df.columns else df.index[0]
    end_time = pd.to_datetime(df.iloc[-1]['timestamp']) if 'timestamp' in df.columns else df.index[-1]

    # Zeitraum in Jahren
    duration_years = (end_time - start_time).days / 365.25

    if duration_years > 0:
        cagr = ((1+rendite_prozent/100) ** (1 / duration_years) - 1)  # Annualized return in percentage
    else:
        cagr = 0

    # col5.metric("CAGR (%)", f"{cagr:,.2f} %")
    #render_colored_metric(col5, "CAGR", cagr * 100, unit="%", precision=2, override_color="blue")
    render_colored_metric(col5, "CAGR (%)", cagr * 100, unit="%", precision=2, override_color="#0B5E82", highlight_background="#BBBBBB")

    # Metrics - Second Row
    col6, col7, col8, col9, col10 = st.columns(5)
    #col6.metric("Number of Trades", results.get('num_trades', 0))
    
    # Handle average investment per grid with fallback
    render_colored_metric(col10, "Summe Trading Fees (USDT)", results.get("fees_paid", 0), unit="", override_color="white")

 
    reserve_pct = results.get('reserve_pct', 0.03)
    total_investment = results.get('initial_investment', 0)
    investierbares_kapital = total_investment * (1 - reserve_pct)

    grid_investment = results.get(
        'average_investment_per_grid',
        investierbares_kapital / len(results['grid_lines']) if 'grid_lines' in results else 0
    )
    col6.metric("Inv. Betrag pro Grid (USDT)", f"{grid_investment:,.2f}")


    sell_trades = sum(1 for t in results.get('trade_log', []) if t['type'] == 'SELL')
 
 
    col11, col12, col13,col14, col15 = st.columns(5)

    render_colored_metric(col15, "Fee Impact (%)", fee_ratio, unit="%", override_color="white")
    
    net_grid_profit_pct = st.session_state.get("net_grid_profit_pct", 0)
    render_colored_metric(col12, "(Avg.) Profit pro Grid (%)", net_grid_profit_pct, unit="%", override_color="white")
    grid_profit_amount = grid_investment * (net_grid_profit_pct / 100.0)
    render_colored_metric(col7, "(Avg.) Profit pro Grid (USDT)", grid_profit_amount, unit="USDT", override_color="white", precision=2)
    grid_profit_total = grid_profit_amount * sell_trades
    render_colored_metric(col8, "Grid Profit Total (USDT)", grid_profit_total, unit="")
    grid_profit_pct = grid_profit_total / total_investment*100 if total_investment > 0 else 0
    render_colored_metric(col9, "Grid Profit Total (%)", grid_profit_pct,precision=2)
    floating_profit_total = results.get("profit_usdt", 0)- grid_profit_total
    render_colored_metric(col13, "Floating Profit (USDT)", floating_profit_total,"")
    floating_profit_pct = (floating_profit_total / total_investment * 100) if total_investment > 0 else 0
    render_colored_metric(col14, "Floating Profit (%)", floating_profit_pct)
 

    bot_settings = results.get("bot_params", {})

    st.text(" ")  # eine Zeile Abstand
    st.text(" ")  # eine Zeile Abstand
    st.write("---")
    st.subheader("🔍 Grid Bot Details")
    # Zeige Spalten nur, wenn alle Schlüssel vorhanden sind

    # --- Reservierte Fees berechnen (sicher vorziehen) ---
    reserve_pct = results.get('reserve_pct', 0.03)
    initial_investment = results.get('initial_investment', 0)
    reserve_total = initial_investment * reserve_pct
    reserve_usdt = reserve_total * (1/3)
    reserve_coin_value = reserve_total * (2/3)
    initial_price = results.get('initial_price', df.iloc[0]['close'] if df is not None else 1)
    reserve_coin = reserve_coin_value / initial_price



    required_keys = ["grid_mode", "lower_price", "upper_price", "num_grids"]
    if all(k in bot_settings for k in required_keys):
        mode = bot_settings["grid_mode"].capitalize()
        lower = bot_settings["lower_price"]
        upper = bot_settings["upper_price"]
        num_grids = bot_settings["num_grids"]

        col1, spacer, col2, spacer, col3 = st.columns([1, 0.2, 1, 0.2, 1])  # Verhältnis: linke, Abstand, rechte Spalte

        with col1:
            st.markdown(render_entry("Modus", mode), unsafe_allow_html=True)
            st.markdown(render_entry("Preis Range", f"{lower:.4f} – {upper:.4f} USDT"), unsafe_allow_html=True)
            st.markdown(render_entry("Anzahl Grids", num_grids), unsafe_allow_html=True)
            st.markdown(render_entry("Profit pro Grid", f"{net_grid_profit_pct:.2f} %"), unsafe_allow_html=True)
            st.markdown(render_entry("Investierter Betrag", f"{results.get('initial_investment', 0):,.2f} USDT", color="white"), unsafe_allow_html=True)
 
        with col2:
            st.markdown(render_entry("Kurs COIN beim Start", f"{results.get('initial_price', 0):,.4f} USDT", color="white"), unsafe_allow_html=True)
            st.markdown(render_entry("Initialer Kauf COIN", f"{results.get('initial_coin', 0):.4f}", color="white"), unsafe_allow_html=True)
            st.markdown(render_entry("Kurs Initialkauf COIN", f"{results.get('initial_price', 0):,.4f} USDT", color="white"), unsafe_allow_html=True)
            st.markdown(render_entry(
                "Reservierte Fees",
                f"{reserve_usdt:,.2f} USDT + {reserve_coin:,.4f} COIN"
            ), unsafe_allow_html=True)
            st.markdown(render_entry(
                "Laufzeit",
                f"{(end_time - start_time).days:,.0f} Tage"
            ), unsafe_allow_html=True)

            # st.markdown(render_entry("Reservierte Fees", f"{lower:.4f} – {upper:.4f} USDT"), unsafe_allow_html=True)
            # st.markdown(render_entry("Anzahl Grids", num_grids), unsafe_allow_html=True)
 
        h_final = results.get("final_position", {})
        h_usdt = h_final.get("usdt", 0)
        h_coin = h_final.get("coin", 0)
        with col3:

            #st.markdown(render_entry("Finale Position", f"{h_usdt:,.2f} USDT + {h_coin:,.6f} COIN", color="white"), unsafe_allow_html=True)
            st.markdown(render_entry("Finale Position USDT", f"{h_usdt:,.2f} USDT", color="white"), unsafe_allow_html=True)
            st.markdown(render_entry("Finale Position COIN", f"{h_coin:,.4f} COIN", color="white"), unsafe_allow_html=True)

            st.markdown(render_entry("Anzahl Grid Trades", f"{results.get('num_trades', 0)}", color="white"), unsafe_allow_html=True)
            st.markdown(render_entry("Anzahl Arbitrage Trades (Fill/SELL)", f"{sell_trades-1}", color="white"), unsafe_allow_html=True)

#            st.markdown(render_entry("Anzahl Trades", f"{results.get('initial_price', 0):,.4f} USDT", color="white"), unsafe_allow_html=True)
 #           st.markdown(render_entry("Anzahl Arbitrage (Fill/SELL)", f"{results.get('initial_price', 0):,.4f} USDT", color="white"), unsafe_allow_html=True)


 
    # # Add to display_bot_results()
    # st.write(f"**Initial Coin Purchase:** {results.get('initial_coin', 0):.6f}")
    # st.write(f"**Initial Coin Investment:** {results.get('initial_investment', 0):.6f}")
    # st.write(f"**Reserved for Sell Grids:** {results.get('reserved_coin', 0):.6f}")

    # Price Information Section
    st.write("---")
    # price_info = [
    #     ("Initial Price", results.get('initial_price', df.iloc[0]['close'] if df is not None else 'N/A')),
    #     ("Final Price", results.get('final_price', df.iloc[-1]['close'] if df is not None else 'N/A')),
    #     ("Price Change", f"{((results.get('final_price', 0) - results.get('initial_price', 0)))/max(results.get('initial_price', 1),1)*100:.2f}%")
    # ]
    # for label, value in price_info:
    #     st.write(f"**{label}:** {value}")

    # # Position Summary
    # st.write("---")
    # final_coin = results.get('final_position', {}).get('coin', 0)
    # final_usdt = results.get('final_position', {}).get('usdt', 0)
    # st.write(f"**Final Position:** {final_coin:,.6f} Coins + {final_usdt:,.2f} USDT = {results.get('final_value', 0):,.2f} USDT")

     # Show full data
    with st.expander("Vollständige Kursdaten"):
        st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume", "range", "price_change"]], use_container_width=True)
 
    # Grid Configuration
    with st.expander("Grid Konfiguration"):
        if 'grid_mode' in results:
            st.write(f"**Grid Mode:** {results['grid_mode'].capitalize()}")
        if 'lower_price' in results and 'upper_price' in results:
            st.write(f"**Price Range:** {results['lower_price']:.4f} - {results['upper_price']:.4f}")
        if 'grid_lines' in results:
            st.dataframe(pd.DataFrame({
                "Grid Level": range(1, len(results['grid_lines']) + 1),
                "Price": results['grid_lines']
            }), hide_index=True)

    # Trade Log
    if results.get('trade_log'):
        with st.expander(f"Trade Log ({len(results['trade_log'])} Trades)"):
            trade_df = pd.DataFrame(results['trade_log'])
            
            # Format numeric columns
            styled_df = trade_df.style.format({
                'cprice': '{:,.2f}',
                'price': '{:,.2f}',
                'amount': '{:.8f}',
                'fee': '{:.4f}',
                'profit': '{:.2f}' if 'profit' in trade_df.columns else None
            })
            
            # Apply profit coloring
            if 'profit' in trade_df.columns:
                def color_profit(val):
                    if val > 0: return 'color: green; font-weight: bold;'
                    elif val < 0: return 'color: red; font-weight: bold;'
                    return ''
                styled_df = styled_df.applymap(color_profit, subset=['profit'])
            
            st.dataframe(styled_df, hide_index=True, 
                         column_config={
                             "timestamp": "Time",
                             "type": "Type",
                             "cprice": st.column_config.NumberColumn("Trigger Price"),
                             "price": st.column_config.NumberColumn("Grid Price"),
                             "amount": st.column_config.NumberColumn("Amount", format="%.8f"),
                             "fee": st.column_config.NumberColumn("Fee", format="%.4f"),
                             "profit": st.column_config.NumberColumn("Profit", format="%.2f"),
                             "queue_size": "Inventory Slots"
                         })

    #     test_total_fee = trade_df['fee'].sum() if 'fee' in trade_df.columns else 0.0
    #     test_total_profit = trade_df['profit'].sum() if 'profit' in trade_df.columns else 0.0

    # st.markdown(f"""
    # ### 🧾 Gesamtübersicht
    # - **Summe Gebühren:** {test_total_fee:,.4f} USDT  
    # - **Summe Profit:** {test_total_profit:,.2f} USDT
    # """)


    # # Simulation Verification
    # if df is not None and not df.empty:
    #     st.subheader("Performance Comparison")
        
    #     # Calculate metrics
    #     initial = results.get('initial_price', df.iloc[0]['close'])
    #     final = results.get('final_price', df.iloc[-1]['close'])
    #     buy_hold_return = (final - initial) / initial * 100
    #     bot_return = results.get('profit_pct', 0)
    #     fee_ratio = results.get('fees_paid', 0) / results.get('initial_investment', 1) * 100
        
    #     # Display metrics
    #     col1, col2, col3 = st.columns(3)
    #     col1.metric("Buy & Hold P/L", f"{buy_hold_return:.2f}%")
    #     col2.metric("Bot Return", f"{bot_return:.2f}%", 
    #                 f"{(bot_return - buy_hold_return):.2f}%", 
    #                 delta_color="inverse" if (bot_return - buy_hold_return) < 0 else "normal")
    #     col3.metric("Fee Impact", f"{fee_ratio:.2f}%")
        
    #     # Visual comparison
    #     st.write("---")
    #     st.subheader("Return Comparison")
    #     fig = go.Figure()
    #     fig.add_trace(go.Indicator(
    #         mode="number+gauge", 
    #         value=bot_return,
    #         title={"text": "Bot Return"},
    #         domain={'x': [0.25, 0.5], 'y': [0.7, 1]},
    #         gauge={
    #             'shape': "bullet",
    #             'axis': {'range': [min(bot_return, buy_hold_return)-5, max(bot_return, buy_hold_return)+5]},
    #             'bar': {'color': "darkblue"}
    #         }
    #     ))
    #     fig.add_trace(go.Indicator(
    #         mode="number+gauge", 
    #         value=buy_hold_return,
    #         title={"text": "Buy & Hold"},
    #         domain={'x': [0.5, 0.75], 'y': [0.7, 1]},
    #         gauge={
    #             'shape': "bullet",
    #             'axis': {'range': [min(bot_return, buy_hold_return)-5, max(bot_return, buy_hold_return)+5]},
    #             'bar': {'color': "darkgreen"}
    #         }
    #     ))
    #     fig.update_layout(
    #         height=200,
    #         margin=dict(t=30, b=10)
    #     )
    #     st.plotly_chart(fig, use_container_width=True)

    # st.write("---")
    
    # reserve_pct = results.get('reserve_pct', 0.03)
    # reserve_total = results.get('initial_investment', 0) * reserve_pct
    # reserve_usdt = reserve_total * (1/3)
    # reserve_coin_value = reserve_total * (2/3)
    # initial_price = results.get('initial_price', df.iloc[0]['close'] if df is not None else 1)
    # reserve_coin = reserve_coin_value / initial_price

 




    # Debug Information
    if 'debug' in results:
        with st.expander("Debug Information"):
            st.write("Buy Prices:", results['debug'].get('buy_prices', []))
            st.write("Coin Amounts:", results['debug'].get('coin_amounts', []))
            st.write("Initial Price:", results['debug'].get('initial_price', 'N/A'))
            st.write("Final Price:", results['debug'].get('final_price', 'N/A'))

    
    st.markdown("""
    <hr style='margin-top: 50px; margin-bottom: 10px;'>

    <div style='font-size: 0.75rem; color: gray;'>
    
    Limitationen: <br>
    Dieses Dashboard ist ein Prototyp. Alle Angaben ohne Gewähr. DYOR.<br>
    Aktuell kann nur eine History von 1000 Kerzen angezeigt werden (Beschänkung Bitget-API). <br>
                Die Auswertung der Kerzen erfolgt nur zum Close-Kurs der Kerze. Das bedeutet, 
                dass Grid-Auslöser innerhalb einer Kerze nicht berücksichtigt werden. In der Regel spielt
                dies bei einem ausreichend kleinen Intervall (z. B. 1h) keine grosse Rolle. 
                Tendenziell wird der Gridgewinn dadurch unterschätzt. Mit den aktuell verfügbaren Kerzen
                und dem 1h-Intervall kann ein Backtesting für einen Monat in die Vergangenheit durchgeführt
                werden. Das ist in der Regel ausreichend. <br>
    Mögliche Erweiterungen: <br>
    Umgehen der Beschränkung der Bitget-API durch "Time-based Pagination".<br>
    Abarbeiten einer Trade-Queue (open-low-high-close), um auch Grid-Auslöser innerhalb einer Kerze zu berücksichtigen.<br>
    
    
    </div>
    """, unsafe_allow_html=True)
    
    jetzt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if 'bot_version' in results:
        full_status = f"{results['bot_version']} | ui.py v30, {jetzt}"
        st.caption(full_status)



def plot_simulation_pattern(df, pattern):
    """Generate explanation visualization for each pattern"""
    fig = go.Figure()
    title = pattern.replace("_", " ").title() + " Pattern"
    
    # Add price trace for all patterns
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], name='Price', line=dict(width=2)))
    
    # Pattern-specific annotations
    if pattern == 'linear_up':
        fig.update_layout(
            title=title,
            annotations=[dict(
                x=0.5, y=0.9, xref="paper", yref="paper",
                text="✅ Bot should place BUYs at start and SELLs during rise",
                showarrow=False, font=dict(size=14))
            ])
    
    elif pattern == 'linear_down':
        fig.add_annotation(
            x=df['timestamp'].iloc[-1], y=df['close'].iloc[-1],
            text="✅ Expected: BUYs during decline, fewer SELLs",
            showarrow=True, arrowhead=4, ax=0, ay=-40)
        fig.update_layout(title=title)
    
    elif pattern == 'sine':
        # Add horizontal lines showing expected buy/sell zones
        mid_price = (df['close'].max() + df['close'].min()) / 2
        amplitude = (df['close'].max() - df['close'].min()) / 2
        
        fig.add_hline(y=mid_price + amplitude*0.7, line_dash="dot", 
                     annotation_text="SELL Zone", annotation_position="right top")
        fig.add_hline(y=mid_price - amplitude*0.7, line_dash="dot", 
                     annotation_text="BUY Zone", annotation_position="right bottom")
        fig.update_layout(
            title=title,
            annotations=[dict(
                x=0.5, y=0.05, xref="paper", yref="paper",
                text="✅ Bot should BUY in valleys and SELL at peaks",
                showarrow=False, font=dict(size=14))
            ])
    
    elif pattern == 'range_bound':
        fig.add_hline(y=df['close'].max(), line_dash="dot", annotation_text="Upper Range")
        fig.add_hline(y=df['close'].min(), line_dash="dot", annotation_text="Lower Range")
        fig.update_layout(
            title=title,
            annotations=[dict(
                x=0.5, y=0.9, xref="paper", yref="paper",
                text="✅ Bot should profit from multiple BUY/SELL cycles",
                showarrow=False, font=dict(size=14))
            ])
    
    elif pattern == 'breakout':
        # Add vertical line at breakout point
        midpoint = len(df) // 2
        fig.add_vline(x=df['timestamp'].iloc[midpoint], line_dash="dash", 
                     annotation_text="Breakout Point", annotation_position="top")
        
        # Add trend lines
        fig.add_trace(go.Scatter(
            x=[df['timestamp'].iloc[0], df['timestamp'].iloc[midpoint]],
            y=[df['close'].iloc[0], df['close'].iloc[midpoint]],
            mode='lines', line=dict(dash='dash', color='gray'),
            name='Pre-Breakout'
        ))
        fig.add_trace(go.Scatter(
            x=[df['timestamp'].iloc[midpoint], df['timestamp'].iloc[-1]],
            y=[df['close'].iloc[midpoint], df['close'].iloc[-1]],
            mode='lines', line=dict(dash='dash', color='orange'),
            name='Post-Breakout'
        ))
        fig.update_layout(
            title=title,
            annotations=[dict(
                x=0.5, y=0.9, xref="paper", yref="paper",
                text="✅ Bot should capture gains after breakout",
                showarrow=False, font=dict(size=14))
            ])
    
    elif pattern == 'volatile':
        # Add volatility bands
        rolling_high = df['high'].rolling(5).max().fillna(method='bfill')
        rolling_low = df['low'].rolling(5).min().fillna(method='bfill')
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=rolling_high,
            line=dict(color='rgba(255,0,0,0.2)'), 
            name='Volatility High'
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=rolling_low,
            line=dict(color='rgba(0,255,0,0.2)'), 
            fill='tonexty', name='Volatility Low'
        ))
        fig.update_layout(
            title=title,
            annotations=[dict(
                x=0.5, y=0.9, xref="paper", yref="paper",
                text="✅ Bot should capture large price swings",
                showarrow=False, font=dict(size=14))
            ])
            
    elif pattern == 'mean_reverting':
        # Add mean line
        mean_price = df['close'].mean()
        fig.add_hline(y=mean_price, line_dash="dash", line_color="purple", 
                     annotation_text="Mean Price", annotation_position="right")
        
        # Add reversion arrows
        for i in range(1, len(df)-1, 5):
            if abs(df['close'].iloc[i] - mean_price) > 0.1 * mean_price:
                fig.add_annotation(
                    x=df['timestamp'].iloc[i],
                    y=df['close'].iloc[i],
                    text="↕️",
                    showarrow=False,
                    font=dict(size=20)
                )
        
        fig.update_layout(
            title=title,
            annotations=[dict(
                x=0.5, y=0.9, xref="paper", yref="paper",
                text="✅ Bot should profit from price oscillations around mean",
                showarrow=False, font=dict(size=14))
            ])
    
    else:  # Default case
        fig.update_layout(title=title)
    
    # Common layout settings
    fig.update_layout(
        height=400,
        template="plotly_dark",
        xaxis_title="Time",
        yaxis_title="Price",
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)