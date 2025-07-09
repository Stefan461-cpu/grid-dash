# data.py v1.0 – 2025-07-10

import pandas as pd
import requests
from datetime import datetime, timedelta

def load_klines(symbol, interval, start_date, end_date, max_bars=1000):
    url = "https://api.bitget.com/api/v2/spot/market/candles"

    interval_map = {
        "1m": "1min", "5m": "5min", "15m": "15min",
        "1h": "1H", "4h": "4H", "1d": "1D"
    }

    if interval not in interval_map:
        return pd.DataFrame()

    start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_date + timedelta(days=1)).timestamp() * 1000)

    params = {
        "symbol": symbol,
        "granularity": interval_map[interval],
        "startTime": start_ts,
        "endTime": end_ts,
        "limit": max_bars
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        raw = response.json().get("data", [])
        df = pd.DataFrame(raw, columns=[
            "timestamp", "open", "high", "low", "close", "volume", "quoteVolume"
        ])
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    except Exception as e:
        print("Error fetching data:", e)
        return pd.DataFrame()

