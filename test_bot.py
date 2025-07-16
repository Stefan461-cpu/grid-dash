# test_bot.py
import sys
import os
import pandas as pd
import numpy as np

# Fix import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.bot import simulate_grid_bot

def create_test_data():
    return pd.DataFrame({
        'timestamp': pd.date_range(start="2023-01-01", periods=100, freq="H"),
        'close': np.linspace(50000, 70000, 100),
        'open': np.linspace(50000, 70000, 100),
        'high': np.linspace(50500, 70500, 100),
        'low': np.linspace(49500, 69500, 100),
        'volume': np.random.uniform(100, 500, 100)
    })

def test_arithmetic_grid():
    print("\n=== Testing Arithmetic Grid ===")
    results = simulate_grid_bot(
        df=create_test_data(),
        total_investment=10000,
        lower_price=50000,
        upper_price=70000,
        num_grids=20,
        grid_mode="arithmetic",
        fee_rate=0.001
    )
    assert len(results['trade_log']) > 0
    print("✓ Test passed - Arithmetic grid executed successfully")

def test_geometric_grid():
    print("\n=== Testing Geometric Grid ===")
    results = simulate_grid_bot(
        df=create_test_data(),
        total_investment=10000,
        lower_price=50000,
        upper_price=70000,
        num_grids=20,
        grid_mode="geometric",
        fee_rate=0.001
    )
    assert len(results['trade_log']) > 0
    print("✓ Test passed - Geometric grid executed successfully")

if __name__ == "__main__":
    test_arithmetic_grid()
    test_geometric_grid()
    print("\nAll tests completed!")