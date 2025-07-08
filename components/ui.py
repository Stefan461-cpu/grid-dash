import streamlit as st
import plotly.graph_objects as go
import pandas as pd

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
            # Initialize with safe defaults
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

def render_chart_and_metrics(df, symbol, interval, chart_type, show_volume, grid_lines=None):
    st.subheader(f"{symbol} {interval} Chart")

    fig = go.Figure()
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C', name='Preis'))
    else:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['close'], mode='lines', name='Schlusskurs',
                                 line=dict(color='#3498DB', width=2)))

    if show_volume and 'volume' in df.columns:
        fig.add_trace(go.Bar(x=df['timestamp'], y=df['volume'], name='Volumen', marker_color='#7F8C8D', yaxis='y2'))
    
    # Add grid lines if provided
    if grid_lines and not df.empty:
        price_range = [df['low'].min(), df['high'].max()]
        for price in grid_lines:
            if price_range[0] <= price <= price_range[1]:
                fig.add_hline(
                    y=price, 
                    line_dash="dot", 
                    line_width=1, 
                    line_color="rgba(125, 125, 125, 0.5)",
                    annotation_text=f" {price:.4f}",
                    annotation_position="right",
                    annotation_font_size=10
                )

    fig.update_layout(
        height=600,
        title=f"{symbol} {interval} Chart",
        yaxis_title="Preis (USDT)",
        xaxis_title="Zeit",
        template="plotly_dark",
        xaxis=dict(type='date', tickformat='%Y-%m-%d %H:%M', rangeslider_visible=False),
        yaxis=dict(autorange=True),
        yaxis2=dict(overlaying='y', side='right', showgrid=False, visible=show_volume),
        margin=dict(l=50, r=50, t=80, b=100),
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    if not df.empty:
        latest = df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Aktueller Preis", f"{latest['close']:.2f}", f"{df['price_change'].iloc[-1]:.2f}%")
        col2.metric("Tageshöchst", f"{df['high'].max():.2f}")
        col3.metric("Tagestief", f"{df['low'].min():.2f}")
        col4.metric("Durchschnittsbereich", f"{df['range'].mean():.2f}%")

    with st.expander("Vollständige Daten anzeigen"):
        st.dataframe(df[["timestamp", "open", "high", "low", "close", "volume"]], use_container_width=True)

def display_bot_results(results):
    """Display grid bot simulation results"""
    st.subheader("Grid Bot Performance")
    
    # Key metrics - Row 1
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Initialinvestition", f"{results['initial_investment']:,.2f} USDT")
    col2.metric("Endwert", f"{results['final_value']:,.2f} USDT", 
               f"{results['profit_pct']:.2f}%")
    col3.metric("Gewinn/Verlust", f"{results['profit_usdt']:,.2f} USDT")
    col4.metric("Gebühren gesamt", f"{results['fees_paid']:,.4f} USDT")
    
    # Key metrics - Row 2
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Anzahl Trades", results['num_trades'])
    col6.metric("Durchschn. Invest/Grid", f"{results['average_investment_per_grid']:,.2f} USDT")
    col7.metric("Finales USDT", f"{results['final_position']['usdt']:,.2f}")
    col8.metric("Finale Coins", f"{results['final_position']['coin']:,.6f}")
    
    # Position details
    st.write(f"**Endposition:** {results['final_position']['coin']:,.6f} Coins + "
             f"{results['final_position']['usdt']:,.2f} USDT (Wert: {results['final_value']:,.2f} USDT)")
    
    # Grid details expander
    with st.expander("Grid Konfiguration"):
        st.write(f"**Grid Modus:** {results.get('grid_mode', 'arithmetic').capitalize()}")
        st.write(f"**Anzahl Grids:** {results.get('num_grids', 0)}")
        st.write(f"**Preisspanne:** {results.get('lower_price', 0):.4f} - {results.get('upper_price', 0):.4f}")
        st.dataframe(
            pd.DataFrame({
                "Grid Level": range(1, len(results['grid_lines']) + 1),
                "Preis": results['grid_lines']
            }),
            hide_index=True
        )
    
    # Trade log expander
    if results.get('trade_log'):
        with st.expander(f"Handelsprotokoll ({len(results['trade_log'])} Trades)"):
            trade_df = pd.DataFrame(results['trade_log'])
            trade_df['timestamp'] = trade_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(trade_df, hide_index=True)
