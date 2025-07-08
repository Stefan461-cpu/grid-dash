
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta

def get_user_settings():
    with st.sidebar:
        st.header("Einstellungen")
        coin = st.selectbox("Währung (COINUSDT)", ["BTC", "ETH", "SOL"], key="coin")
        interval = st.radio("Intervall", ["1m", "5m", "15m", "1h", "4h", "1d"], horizontal=True, index=3)
        today = date.today()
        start_date = st.date_input("Startdatum", today - timedelta(days=30))
        end_date = st.date_input("Enddatum", today)
        max_bars = st.slider("Max. Kerzen (10–1000)", 10, 1000, 500)
        chart_type = st.selectbox("Chart-Typ", ["Candlestick", "Linie"], index=0)
        show_volume = st.checkbox("Volumen anzeigen", True)

        st.subheader("Grid Bot Parameter")
        enable_bot = st.checkbox("Grid Bot aktivieren", True)
        bot_params = {}
        bot_run_triggered = False

        if enable_bot:
            default_lower = st.session_state.get("default_lower", 100.0)
            default_upper = st.session_state.get("default_upper", 200.0)

            bot_params["total_investment"] = st.number_input("Gesamtinvestition (USDT)", 10.0, value=1000.0, step=100.0)
            col1, col2 = st.columns(2)
            with col1:
                bot_params["lower_price"] = st.number_input("Unterer Preis", 0.0001, value=default_lower, format="%.4f")
            with col2:
                bot_params["upper_price"] = st.number_input("Oberer Preis", 0.0001, value=default_upper, format="%.4f")
            bot_params["num_grids"] = st.slider("Anzahl Grids", 2, 100, 20)
            bot_params["grid_mode"] = st.radio("Grid Modus", ["arithmetic", "geometric"], index=0)
            bot_params["reserved_amount"] = st.number_input("Reserviertes Kapital (USDT)", 0.0, value=100.0, step=10.0)
            bot_params["fee_rate"] = st.number_input("Gebühren (%)", 0.0, value=0.1, step=0.01) / 100.0

            if st.button("Grid Bot starten"):
                bot_run_triggered = True

    return {
        "coin": coin,
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "max_bars": max_bars,
        "chart_type": chart_type,
        "show_volume": show_volume,
        "enable_bot": enable_bot,
        "bot_params": bot_params,
        "bot_run_triggered": bot_run_triggered
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

    if grid_lines and not df.empty:
        for price in grid_lines:
            if df['low'].min() <= price <= df['high'].max():
                fig.add_hline(y=price, line_dash="dot", line_width=1,
                              line_color="rgba(125,125,125,0.5)",
                              annotation_text=f"{price:.4f}",
                              annotation_position="right",
                              annotation_font_size=10)

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

    st.plotly_chart(fig, use_container_width=True, key=f"{symbol}_{interval}")

def display_bot_results(results):
    st.subheader("Grid Bot Performance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Initialinvestition", f"{results['initial_investment']:,.2f} USDT")
    col2.metric("Endwert", f"{results['final_value']:,.2f} USDT", f"{results['profit_pct']:.2f}%")
    col3.metric("Gewinn/Verlust", f"{results['profit_usdt']:,.2f} USDT")
    col4.metric("Gebühren gesamt", f"{results['fees_paid']:,.4f} USDT")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Anzahl Trades", results['num_trades'])
    col6.metric("Durchschn. Invest/Grid", f"{results['average_investment_per_grid']:,.2f} USDT")
    col7.metric("Finales USDT", f"{results['final_position']['usdt']:,.2f}")
    col8.metric("Finale Coins", f"{results['final_position']['coin']:,.6f}")
