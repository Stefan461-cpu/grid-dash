import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone

def fetch_bitget_candles(coin, interval, start_date, end_date, max_bars, **kwargs):
    interval_mapping = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1day"
    }
    period = interval_mapping.get(interval)
    if not period:
        return None, None, f"Ungültiges Intervall: {interval}"

    try:
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = min(int(end_dt.timestamp() * 1000), int(now.timestamp() * 1000))

        if start_ts >= end_ts:
            return None, None, "Startdatum muss vor Enddatum liegen."
    except Exception as e:
        return None, None, f"Datumskonvertierungsfehler: {str(e)}"

    symbol = f"{coin}USDT_SPBL"
    url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={symbol}&period={period}&after={start_ts}&before={end_ts}&limit={max_bars}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()

        if data.get("code") != "00000":
            return None, None, f"Bitget API-Fehler: {data.get('msg', 'Unbekannt')} (Code: {data.get('code')})"
    except Exception as e:
        return None, None, f"API-Fehler: {str(e)}"

    candles = data.get("data", [])
    if not candles:
        return None, None, "Keine Daten im gewählten Zeitraum."

    processed = []
    for c in candles:
        try:
            ts = c.get("ts")
            o = c.get("open")
            h = c.get("high")
            l = c.get("low")
            c_ = c.get("close")
            v = c.get("usdtVol") or c.get("baseVol") or c.get("quoteVol") or "0"
            if None in [ts, o, h, l, c_]: continue
            processed.append({"timestamp": ts, "open": o, "high": h, "low": l, "close": c_, "volume": v})
        except:
            continue

    df = pd.DataFrame(processed)
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True).dt.tz_convert(None)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")

    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
    df = df.sort_values("timestamp")
    df["price_change"] = df["close"].pct_change() * 100
    df["range"] = (df["high"] - df["low"]) / df["low"].replace(0, np.nan) * 100

    return symbol, df, None

