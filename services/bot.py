# services/bot.py
import numpy as np
import pandas as pd

def calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode):
    """Calculate grid price levels based on selected mode"""
    if grid_mode == "arithmetic":
        return np.linspace(lower_price, upper_price, num_grids + 1).tolist()
    else:  # geometric
        ratio = (upper_price / lower_price) ** (1/num_grids)
        return [lower_price * (ratio ** i) for i in range(num_grids + 1)]

def simulate_grid_bot(df, total_investment, lower_price, upper_price, num_grids, 
                      grid_mode, reserved_amount, fee_rate):
    """Run grid bot simulation on historical data"""
    # Initial setup
    if df.empty:
        return None
        
    initial_price = df.iloc[0]['close']
    grid_lines = calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)
    active_grids = set(range(len(grid_lines)))
    position = {"usdt": total_investment - reserved_amount, "coin": 0.0}
    fees_paid = 0.0
    trade_log = []
    
    # Calculate grid step amounts
    investment_per_grid = (total_investment - reserved_amount) / num_grids
    coin_per_grid = investment_per_grid / initial_price
    
    for idx, row in df.iterrows():
        current_price = row['close']
        
        # Skip first row as we don't have previous price
        if idx == 0:
            prev_price = current_price
            continue
        else:
            prev_price = df.iloc[idx-1]['close']
        
        # Check which grid lines were crossed
        grids_crossed = []
        for i in active_grids:
            grid_price = grid_lines[i]
            
            # Check if price crossed this grid line
            if (prev_price < grid_price <= current_price) or (prev_price > grid_price >= current_price):
                grids_crossed.append(i)
        
        # Process crossed grids in price order
        if current_price > prev_price:  # Price rising
            grids_crossed.sort()  # Process lowest first
        else:  # Price falling
            grids_crossed.sort(reverse=True)  # Process highest first
        
        for grid_index in grids_crossed:
            grid_price = grid_lines[grid_index]
            
            if current_price >= grid_price:  # Sell territory
                if position["coin"] >= coin_per_grid:
                    # Execute sell
                    trade_value = coin_per_grid * grid_price
                    fee = trade_value * fee_rate
                    position["usdt"] += trade_value - fee
                    position["coin"] -= coin_per_grid
                    fees_paid += fee
                    trade_log.append({
                        "timestamp": row['timestamp'],
                        "type": "SELL",
                        "price": grid_price,
                        "amount": coin_per_grid,
                        "fee": fee
                    })
                    active_grids.remove(grid_index)
            
            else:  # Buy territory
                if position["usdt"] >= investment_per_grid:
                    # Execute buy
                    coins_bought = investment_per_grid / grid_price
                    fee = investment_per_grid * fee_rate
                    position["usdt"] -= investment_per_grid
                    position["coin"] += coins_bought
                    fees_paid += fee
                    trade_log.append({
                        "timestamp": row['timestamp'],
                        "type": "BUY",
                        "price": grid_price,
                        "amount": coins_bought,
                        "fee": fee
                    })
                    active_grids.remove(grid_index)
    
    # Calculate final results
    final_value = position["usdt"] + position["coin"] * df.iloc[-1]['close']
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
        "final_position": position
    }
