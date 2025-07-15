# services/simulator.py
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_simulated_data(pattern='linear', days=7, initial_price=100000, volatility=5000):
    """
    Generate simulated price data for testing grid bot mechanics
    Returns DataFrame with same structure as real market data
    """
    # Generate timestamps (hourly intervals)
    timestamps = [datetime.now() - timedelta(days=days) + timedelta(hours=i) 
                 for i in range(days * 24)]
    
    # Pattern-specific price generation
    if pattern == 'linear_up':
        prices = [initial_price + (i * (volatility/10)) for i in range(len(timestamps))]
    elif pattern == 'linear_down':
        prices = [initial_price - (i * (volatility/10)) for i in range(len(timestamps))]
    elif pattern == 'sine':
        prices = [initial_price + volatility * np.sin(i/5) for i in range(len(timestamps))]
    elif pattern == 'range_bound':
        base = initial_price
        prices = [base + volatility * (0.5 - ((i % 20)/20)) for i in range(len(timestamps))]
    elif pattern == 'breakout':
        half = len(timestamps) // 2
        prices = [initial_price + (volatility * 0.2 * (i/half)) if i < half 
                 else initial_price + volatility * 0.2 + volatility * 0.8 * ((i-half)/(len(timestamps)-half))
                 for i in range(len(timestamps))]
    elif pattern == 'volatile':
        prices = [initial_price]
        for _ in range(1, len(timestamps)):
            change = np.random.choice([-1, 1]) * volatility * np.random.uniform(0.1, 0.5)
            prices.append(max(1000, prices[-1] + change))
    else:  # Default to random walk
        prices = [initial_price]
        for _ in range(1, len(timestamps)):
            prices.append(prices[-1] + np.random.uniform(-volatility/2, volatility/2))
    
    # Create realistic OHLCV data
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': [p + abs(np.random.normal(0, volatility/50)) for p in prices],
        'low': [p - abs(np.random.normal(0, volatility/50)) for p in prices],
        'close': prices,
        'volume': [abs(np.random.normal(100, 50)) for _ in prices]
    })
    
    # Add technical features expected by our bot
    df['price_change'] = df['close'].pct_change() * 100
    df['range'] = (df['high'] - df['low']) / df['low'] * 100
    
    return df