import streamlit as st
import plotly.graph_objects as go

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
    return {
        "coin": coin,
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "max_bars": max_bars,
        "chart_type": chart_type,
        "show_volume": show_volume
    }

def render_chart_and_metrics(df, symbol, interval, chart_type, show_volume):
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

