# bot.py - Version 12.0 (Grid State Management)
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
    """Main grid bot simulation with grid state management"""
    if df.empty:
        return None

    # Initialize core variables
    initial_price = df.iloc[0]['close']
    final_price = df.iloc[-1]['close']
    grid_lines = sorted(calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode))
    fees_paid = 0.0
    trade_log = []
    
    # FIFO tracking system
    inventory_queue = deque()
    
    # Capital allocation (3% reserves)
    reserved_usdt = total_investment * 0.01
    reserved_coin = (total_investment * 0.02) / initial_price
    trading_capital = total_investment - reserved_usdt - (reserved_coin * initial_price)
    
    # Proportional allocation
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

    # Initial coin allocation for upper grids
    if n_above > 0:
        initial_coins = coin_portion / initial_price
        coins_per_grid = initial_coins / n_above
        for i in range(n_above):
            trade_log.append({
                "timestamp": df.iloc[0]['timestamp'],
                "type": "BUY",
                "price": initial_price,
                "amount": coins_per_grid,
                "fee": 0.0,
                "profit": 0.0,
                "queue_size": i + 1
            })
            inventory_queue.append((initial_price, coins_per_grid))

    # Grid state initialization with cooldown
    grid_state = {
        price: {
            "active": False,
            "side": "SELL" if price > initial_price else "BUY",
            "cooldown": 0  # Cooldown counter
        } for price in grid_lines
    }
    
    # Activate adjacent grids
    for i, price in enumerate(grid_lines):
        if price <= initial_price and i < len(grid_lines)-1 and grid_lines[i+1] > initial_price:
            grid_state[grid_lines[i+1]]["active"] = True
            if i > 0:
                grid_state[grid_lines[i]]["active"] = True
            break

    # Main simulation loop
    for idx in range(1, len(df)):
        current = df.iloc[idx]
        previous = df.iloc[idx-1]
        
        # Update grid cooldowns
        for grid_price in grid_lines:
            state = grid_state[grid_price]
            if state["cooldown"] > 0:
                state["cooldown"] -= 1
                if state["cooldown"] == 0:
                    state["active"] = True
        
        for grid_price in grid_lines:
            state = grid_state[grid_price]
            if not state["active"]:
                continue
                
            # Detect price crossing
            crossed_up = previous['close'] < grid_price <= current['close']
            crossed_down = previous['close'] > grid_price >= current['close']
            
            # SELL execution
            if crossed_up and state["side"] == "SELL":
                if position["coin"] > 1e-8 and inventory_queue:
                    sell_amount = min(position["coin"], coin_per_sell_grid)
                    remaining_sell = sell_amount
                    total_fee = 0
                    total_profit = 0
                    
                    while remaining_sell > 1e-8 and inventory_queue:
                        buy_price, coin_amount = inventory_queue[0]
                        sell_lot = min(coin_amount, remaining_sell)
                        
                        trade_value = sell_lot * grid_price
                        fee = trade_value * fee_rate
                        profit = (grid_price - buy_price) * sell_lot - fee
                        
                        position["usdt"] += trade_value - fee
                        position["coin"] -= sell_lot
                        fees_paid += fee
                        total_fee += fee
                        total_profit += profit
                        
                        new_amount = coin_amount - sell_lot
                        if new_amount <= 1e-8:
                            inventory_queue.popleft()
                        else:
                            inventory_queue[0] = (buy_price, new_amount)
                        
                        remaining_sell -= sell_lot
                    
                    if total_profit != 0:
                        trade_log.append({
                            "timestamp": current['timestamp'],
                            "type": "SELL",
                            "price": grid_price,
                            "amount": sell_amount - remaining_sell,
                            "fee": total_fee,
                            "profit": total_profit,
                            "queue_size": len(inventory_queue)
                        })
                    
                    # Deactivate and cooldown
                    state["active"] = False
                    state["cooldown"] = 3  # 3 candle cooldown
                    
                    # Activate next grid
                    current_idx = grid_lines.index(grid_price)
                    if current_idx < len(grid_lines) - 1:
                        next_grid = grid_lines[current_idx + 1]
                        grid_state[next_grid]["active"] = True
            
            # BUY execution
            elif crossed_down and state["side"] == "BUY":
                if position["usdt"] >= usdt_per_buy_grid:
                    fee = usdt_per_buy_grid * fee_rate
                    coins_bought = (usdt_per_buy_grid - fee) / grid_price
                    
                    position["usdt"] -= usdt_per_buy_grid
                    position["coin"] += coins_bought
                    fees_paid += fee
                    
                    inventory_queue.append((grid_price, coins_bought))
                    
                    trade_log.append({
                        "timestamp": current['timestamp'],
                        "type": "BUY",
                        "price": grid_price,
                        "amount": coins_bought,
                        "fee": fee,
                        "profit": 0.0,
                        "queue_size": len(inventory_queue)
                    })
                    
                    # Deactivate and cooldown
                    state["active"] = False
                    state["cooldown"] = 3  # 3 candle cooldown
                    
                    # Activate next grid
                    current_idx = grid_lines.index(grid_price)
                    if current_idx > 0:
                        next_grid = grid_lines[current_idx - 1]
                        grid_state[next_grid]["active"] = True

    # Final valuation
    final_usdt = position["usdt"]
    final_coin_value = position["coin"] * final_price
    final_value = final_usdt + final_coin_value
    
    return {
        "initial_investment": total_investment,
        "final_value": final_value,
        "profit_usdt": final_value - total_investment,
        "profit_pct": (final_value - total_investment) / total_investment * 100,
        "fees_paid": fees_paid,
        "grid_lines": grid_lines,
        "trade_log": trade_log,
        "final_position": {
            "usdt": final_usdt,
            "coin": position["coin"]
        },
        "num_trades": len(trade_log),
        "average_investment_per_grid": usdt_per_buy_grid,
        "initial_price": initial_price,
        "final_price": final_price,
        "grid_mode": grid_mode,
        "lower_price": lower_price,
        "upper_price": upper_price,
        "bot_version": "bot.py v12.0 (Grid State)"
    }