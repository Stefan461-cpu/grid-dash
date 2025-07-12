# bot.py – Version 8.0 – Proper Initial Allocation
import numpy as np
import pandas as pd
from collections import deque

def calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode):
    if grid_mode == "arithmetic":
        return np.linspace(lower_price, upper_price, num_grids + 1).tolist()
    else:  # geometric
        ratio = (upper_price / lower_price) ** (1 / num_grids)
        return [lower_price * (ratio ** i) for i in range(num_grids + 1)]

def simulate_grid_bot(df, total_investment, lower_price, upper_price, num_grids,
                      grid_mode, fee_rate):
    if df.empty:
        return None

    initial_price = df.iloc[0]['close']
    grid_lines = calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)
    
    # Calculate reserves (3% of capital)
    reserved_usdt = total_investment * 0.01
    reserved_coin = (total_investment * 0.02) / initial_price
    
    # Count grids above/below initial price
    n_below = sum(1 for price in grid_lines if price < initial_price)
    n_above = sum(1 for price in grid_lines if price > initial_price)
    total_grids = n_below + n_above
    
    # Calculate proportional allocation
    total_trading_capital = total_investment * 0.97  # 97% for trading
    usdt_portion = n_below / total_grids
    coin_portion = n_above / total_grids
    
    # Convert USDT to coins for the "sell" portion
    initial_coin_purchase = (total_trading_capital * coin_portion) / initial_price
    initial_usdt = total_trading_capital * usdt_portion
    
    # Apply fee to initial conversion
    conversion_fee = (total_trading_capital * coin_portion) * fee_rate
    initial_coin_net = initial_coin_purchase * (1 - fee_rate)
    
    # Initialize position
    position = {
        "usdt": initial_usdt,
        "coin": initial_coin_net + reserved_coin
    }
    fees_paid = conversion_fee
    trade_log = []
    buy_queue = deque()
    
    # Per-grid values
    usdt_per_buy_grid = initial_usdt / n_below if n_below > 0 else 0
    coin_per_sell_grid = initial_coin_net / n_above if n_above > 0 else 0

    # Initialize grid states
    grid_state = {}
    for price in grid_lines:
        if price < initial_price:
            grid_state[price] = {"active": True, "side": "BUY", "last": None}
        elif price > initial_price:
            grid_state[price] = {"active": True, "side": "SELL", "last": None}
        else:
            grid_state[price] = {"active": False, "side": None, "last": None}

    for idx in range(1, len(df)):
        prev_price = df.iloc[idx - 1]['close']
        current_price = df.iloc[idx]['close']
        timestamp = df.iloc[idx]['timestamp']
        
        # Skip micro-fluctuations
        if abs(current_price - prev_price) < initial_price * 0.0015:
            continue
            
        # Process grids in price movement direction
        direction = "UP" if current_price > prev_price else "DOWN"
        grid_sequence = sorted(grid_lines) if direction == "UP" else sorted(grid_lines, reverse=True)

        for grid_price in grid_sequence:
            state = grid_state.get(grid_price)
            if not state or not state["active"]:
                continue
                
            # SELL execution
            if state["side"] == "SELL" and prev_price < grid_price <= current_price:
                if position["coin"] >= coin_per_sell_grid:
                    trade_value = coin_per_sell_grid * grid_price
                    fee = trade_value * fee_rate
                    profit = 0.0
                    
                    # Profit calculation
                    if buy_queue:
                        buy_price = buy_queue.popleft()
                        profit = (grid_price - buy_price) * coin_per_sell_grid - fee
                    
                    position["usdt"] += trade_value - fee
                    position["coin"] -= coin_per_sell_grid
                    fees_paid += fee
                    
                    trade_log.append({
                        "timestamp": timestamp,
                        "type": "SELL",
                        "price": grid_price,
                        "amount": coin_per_sell_grid,
                        "fee": fee,
                        "profit": profit
                    })
                    state["active"] = False
                    
                    # Activate next lower grid
                    lower_grids = [p for p in grid_lines if p < grid_price]
                    if lower_grids:
                        next_lower = max(lower_grids)
                        if grid_state.get(next_lower):
                            grid_state[next_lower]["active"] = True
                            grid_state[next_lower]["side"] = "BUY"

            # BUY execution
            elif state["side"] == "BUY" and prev_price > grid_price >= current_price:
                if position["usdt"] >= usdt_per_buy_grid:
                    coin_amount = usdt_per_buy_grid / grid_price
                    fee = usdt_per_buy_grid * fee_rate
                    net_coin = coin_amount * (1 - fee_rate)
                    
                    position["usdt"] -= usdt_per_buy_grid
                    position["coin"] += net_coin
                    fees_paid += fee
                    buy_queue.append(grid_price)
                    
                    trade_log.append({
                        "timestamp": timestamp,
                        "type": "BUY",
                        "price": grid_price,
                        "amount": net_coin,
                        "fee": fee,
                        "profit": 0.0
                    })
                    state["active"] = False
                    
                    # Activate next higher grid
                    higher_grids = [p for p in grid_lines if p > grid_price]
                    if higher_grids:
                        next_higher = min(higher_grids)
                        if grid_state.get(next_higher):
                            grid_state[next_higher]["active"] = True
                            grid_state[next_higher]["side"] = "SELL"

    # Final valuation
    final_price = df.iloc[-1]['close']
    final_usdt = position["usdt"] + reserved_usdt
    final_coin_value = position["coin"] * final_price
    final_value = final_usdt + final_coin_value
    profit_usdt = final_value - total_investment
    profit_pct = (profit_usdt / total_investment) * 100

    return {
        "initial_investment": total_investment,
        "final_value": final_value,
        "profit_usdt": profit_usdt,
        "profit_pct": profit_pct,
        "fees_paid": fees_paid,
        "grid_lines": grid_lines,
        "trade_log": trade_log,
        "final_position": {
            "usdt": final_usdt,
            "coin": position["coin"]
        },
        "num_trades": len(trade_log),
        "average_investment_per_grid": usdt_per_buy_grid,
        "reserved_amount": reserved_usdt,
        "grid_mode": grid_mode,
        "lower_price": lower_price,
        "upper_price": upper_price,
        "bot_version": "bot.py v8.0 (Corrected Allocation)"
    }