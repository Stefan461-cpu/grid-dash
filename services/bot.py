# bot.py – Version 10.6 (FIFO Fix)
# Last Updated: 2025-07-16 12:00 UTC
# Lines: 253 (matches original)
# Changes:
# 1. Fixed FIFO inventory depletion
# 2. Added buy trade logging
# 3. Strict inventory validation
# All other logic unchanged

import numpy as np
import pandas as pd
from collections import deque

def calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode):
    """Calculate grid lines based on selected mode"""
    if grid_mode == "arithmetic":
        return np.linspace(lower_price, upper_price, num_grids + 1).tolist()
    else:  # geometric
        ratio = (upper_price / lower_price) ** (1 / num_grids)
        return [lower_price * (ratio ** i) for i in range(num_grids + 1)]

def simulate_grid_bot(df, total_investment, lower_price, upper_price, num_grids,
                     grid_mode, fee_rate):
    """Main grid bot simulation with FIFO fixes"""
    if df.empty:
        return None

    # Initialize core variables
    initial_price = df.iloc[0]['close']
    final_price = df.iloc[-1]['close']
    grid_lines = calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)
    fees_paid = 0.0
    trade_log = []
    
    # FIFO tracking system (2 separate queues)
    buy_price_queue = deque()      # Tracks purchase prices
    coin_inventory = deque()       # Tracks coin amounts at each price
    
    # Capital allocation (3% reserves)
    reserved_usdt = total_investment * 0.01
    reserved_coin = (total_investment * 0.02) / initial_price
    trading_capital = total_investment - reserved_usdt - (reserved_coin * initial_price)
    
    # PROPORTIONAL ALLOCATION BY GRID COUNT
    n_below = sum(1 for p in grid_lines if p < initial_price)
    n_above = sum(1 for p in grid_lines if p > initial_price)
    total_active_grids = max(n_below + n_above, 1)
    
    usdt_portion = trading_capital * n_below / total_active_grids
    coin_portion = trading_capital * n_above / total_active_grids
    
    # Initialize position
    position = {
        "usdt": usdt_portion + reserved_usdt,
        "coin": (coin_portion / initial_price) + reserved_coin
    }
    
    # Calculate per-grid amounts
    usdt_per_buy_grid = usdt_portion / n_below if n_below > 0 else 0
    coin_per_sell_grid = (coin_portion / initial_price) / n_above if n_above > 0 else 0

    # Initial grid setup
    grid_state = {}
    for price in grid_lines:
        grid_state[price] = {
            "active": (price > initial_price),
            "side": "SELL" if price > initial_price else "BUY"
        }

    # SEED INITIAL INVENTORY (CRITICAL FIX)
    if n_above > 0:
        initial_coins = coin_portion / initial_price
        coins_per_grid = initial_coins / n_above
        for _ in range(n_above):
            buy_price_queue.append(initial_price)
            coin_inventory.append(coins_per_grid)
        
        # Log initial allocation
        trade_log.append({
            "timestamp": df.iloc[0]['timestamp'],
            "type": "INIT",
            "price": initial_price,
            "amount": initial_coins,
            "fee": 0.0,
            "profit": 0.0,
            "queue_size": len(buy_price_queue)
        })

    # Execute initial BUY if price below lowest grid
    if initial_price < grid_lines[0] and n_below > 0:
        buy_price = grid_lines[0]
        fee = usdt_per_buy_grid * fee_rate
        coins_bought = (usdt_per_buy_grid - fee) / buy_price
        
        position["usdt"] -= usdt_per_buy_grid
        position["coin"] += coins_bought
        fees_paid += fee
        
        buy_price_queue.append(buy_price)
        coin_inventory.append(coins_bought)
        
        trade_log.append({
            "timestamp": df.iloc[0]['timestamp'],
            "type": "BUY",
            "price": buy_price,
            "amount": coins_bought,
            "fee": fee,
            "profit": 0.0,
            "queue_size": len(buy_price_queue)
        })

    # Main simulation loop with FIXED FIFO DEPLETION
    for idx in range(1, len(df)):
        current = df.iloc[idx]
        previous = df.iloc[idx-1]
        
        for grid_price in grid_lines:
            state = grid_state.get(grid_price, {})
            if not state.get("active"):
                continue
                
            # Detect price crossing
            crossed_up = previous['close'] < grid_price <= current['close']
            crossed_down = previous['close'] > grid_price >= current['close']
            
            # SAFE SELL EXECUTION (FIXED)
            if crossed_up and state["side"] == "SELL":
                if (position["coin"] >= coin_per_sell_grid and 
                    coin_per_sell_grid > 0 and 
                    len(buy_price_queue) > 0 and 
                    len(coin_inventory) > 0):
                    
                    remaining_sell_amount = coin_per_sell_grid
                    total_fee = 0.0
                    total_profit = 0.0
                    
                    # Process FIFO inventory
                    while remaining_sell_amount > 1e-8 and coin_inventory:
                        available_coins = coin_inventory[0]
                        sell_amount = min(available_coins, remaining_sell_amount)
                        
                        if sell_amount <= 0:
                            break
                            
                        buy_price = buy_price_queue[0]
                        trade_value = sell_amount * grid_price
                        fee = trade_value * fee_rate
                        profit = (grid_price - buy_price) * sell_amount - fee
                        
                        # Update tracking
                        position["usdt"] += trade_value - fee
                        position["coin"] -= sell_amount
                        fees_paid += fee
                        total_fee += fee
                        total_profit += profit
                        
                        # Update inventory
                        coin_inventory[0] -= sell_amount
                        if coin_inventory[0] <= 1e-8:
                            buy_price_queue.popleft()
                            coin_inventory.popleft()
                            
                        remaining_sell_amount -= sell_amount
                    
                    if remaining_sell_amount > 1e-8:
                        print(f"Warning: Couldn't sell full amount at {grid_price}")
                    
                    # Log composite sell
                    trade_log.append({
                        "timestamp": current['timestamp'],
                        "type": "SELL",
                        "price": grid_price,
                        "amount": coin_per_sell_grid - remaining_sell_amount,
                        "fee": total_fee,
                        "profit": total_profit,
                        "queue_size": len(buy_price_queue)
                    })
                    
                    # Activate next grid
                    next_grid = next((p for p in grid_lines if p < grid_price), None)
                    if next_grid:
                        grid_state[next_grid]["active"] = True
            
            # BUY EXECUTION (UNCHANGED)
            elif crossed_down and state["side"] == "BUY":
                if position["usdt"] >= usdt_per_buy_grid and usdt_per_buy_grid > 0:
                    fee = usdt_per_buy_grid * fee_rate
                    coins_bought = (usdt_per_buy_grid - fee) / grid_price
                    
                    position["usdt"] -= usdt_per_buy_grid
                    position["coin"] += coins_bought
                    fees_paid += fee
                    
                    buy_price_queue.append(grid_price)
                    coin_inventory.append(coins_bought)
                    
                    trade_log.append({
                        "timestamp": current['timestamp'],
                        "type": "BUY",
                        "price": grid_price,
                        "amount": coins_bought,
                        "fee": fee,
                        "profit": 0.0,
                        "queue_size": len(buy_price_queue)
                    })
                    
                    # Activate next grid
                    next_grid = next((p for p in grid_lines if p > grid_price), None)
                    if next_grid:
                        grid_state[next_grid]["active"] = True

    # Final valuation
    final_usdt = position["usdt"]
    final_coin_value = position["coin"] * final_price
    final_value = final_usdt + final_coin_value
    
    # Inventory validation
    inventory_diff = sum(coin_inventory) - (position["coin"] - reserved_coin)
    if abs(inventory_diff) > 1e-8:
        print(f"Inventory mismatch: {inventory_diff:.8f}")

    return {
        # Core metrics
        "initial_investment": total_investment,
        "final_value": final_value,
        "profit_usdt": final_value - total_investment,
        "profit_pct": (final_value - total_investment) / total_investment * 100,
        "fees_paid": fees_paid,
        "grid_lines": grid_lines,
        "trade_log": [t for t in trade_log if t["type"] in ("BUY", "SELL")],  # Filter INIT
        "final_position": {
            "usdt": final_usdt,
            "coin": position["coin"]
        },
        "num_trades": len([t for t in trade_log if t["type"] in ("BUY", "SELL")]),
        "average_investment_per_grid": usdt_per_buy_grid,
        "initial_price": initial_price,
        "final_price": final_price,
        "reserved_amount": reserved_usdt,
        "grid_mode": grid_mode,
        "lower_price": lower_price,
        "upper_price": upper_price,
        "avg_cost_basis": (sum(buy_price_queue)/len(buy_price_queue)) if buy_price_queue else initial_price,
        "debug": {
            "fifo_status": {
                "remaining_prices": len(buy_price_queue),
                "remaining_coins": sum(coin_inventory),
                "expected_coins": position["coin"] - reserved_coin,
                "discrepancy": inventory_diff
            },
            "allocation": {
                "usdt_portion": usdt_portion,
                "coin_portion": coin_portion,
                "n_below": n_below,
                "n_above": n_above
            }
        },
        "bot_version": "bot.py v10.6 (FIFO Fixed)"
    }