# bot.py - Version 13.0 (Exchange-Accurate Grid Bot)
import numpy as np
import pandas as pd
from collections import defaultdict

def calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode):
    """Calculate grid lines based on selected mode (unchanged)"""
    if grid_mode == "arithmetic":
        return np.linspace(lower_price, upper_price, num_grids + 1).tolist()
    else:  # geometric
        ratio = (upper_price / lower_price) ** (1 / num_grids)
        return [lower_price * (ratio ** i) for i in range(num_grids + 1)]

def simulate_grid_bot(df, total_investment, lower_price, upper_price, num_grids,
                     grid_mode, fee_rate):
    """Exchange-accurate grid bot simulation with Bitget-style initialization"""
    if df.empty:
        return None

    # Initialize core variables
    initial_price = df.iloc[0]['close']
    final_price = df.iloc[-1]['close']
    grid_lines = sorted(calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode))
    fees_paid = 0.0
    trade_log = []
    
    # Validate price range
    if not (lower_price <= initial_price <= upper_price):
        raise ValueError("Initial price must be within grid range")

    # Calculate grid-specific parameters
    def get_grid_size(price):
        """Calculate coin amount per grid (price-sensitive for geometric grids)"""
        if grid_mode == "arithmetic":
            return (total_investment * 0.98) / (num_grids * price)  # 2% fee reserve
        else:
            base_size = (total_investment * 0.98) / (num_grids * initial_price)
            grid_idx = grid_lines.index(price)
            return base_size * (1.0 if grid_idx == 0 else (grid_lines[1]/grid_lines[0]) ** (grid_idx - 1))

    # 1. Initial Coin Acquisition (Bitget-style bulk purchase)
    upper_grids = [p for p in grid_lines if p > initial_price]
    total_sell_coins = sum(get_grid_size(p) for p in upper_grids)
    
    # Deduct with fees (emulate exchange behavior)
    buy_value = total_sell_coins * initial_price
    buy_fee = buy_value * fee_rate
    fees_paid += buy_fee
    
    # Initialize position with reserves
    position = {
        "usdt": total_investment - buy_value - buy_fee,
        "coin": total_sell_coins,
        "reserved_coin": total_sell_coins  # For upper grids
    }
    
    # Log initial purchase
    trade_log.append({
        "timestamp": df.iloc[0]['timestamp'],
        "type": "BUY",
        "price": initial_price,
        "amount": total_sell_coins,
        "fee": buy_fee,
        "profit": 0.0,
        "inventory_slots": len(upper_grids)
    })

    # 2. Grid State Initialization
    grids = {}
    for price in grid_lines:
        is_upper = price > initial_price
        grids[price] = {
            "side": "sell" if is_upper else "buy",
            "coin_reserved": get_grid_size(price) if is_upper else 0,
            "state": "active",
            "cooldown": 0,
            "traded": False
        }

    # 3. Main Simulation Loop
    for idx in range(1, len(df)):
        current = df.iloc[idx]
        previous = df.iloc[idx-1]
        
        # Update grid cooldowns
        for grid in grids.values():
            if grid["cooldown"] > 0:
                grid["cooldown"] -= 1
                if grid["cooldown"] == 0:
                    grid["state"] = "active"
        
        # Check each grid level
        for price, grid in grids.items():
            if grid["state"] != "active":
                continue
                
            crossed_up = previous['close'] < price <= current['close']
            crossed_down = previous['close'] > price >= current['close']
            
            # SELL Execution (upper grids)
            if crossed_up and grid["side"] == "sell":
                if grid["coin_reserved"] > 1e-10:  # Prevent floating point errors
                    sell_amount = grid["coin_reserved"]
                    sell_value = sell_amount * price
                    sell_fee = sell_value * fee_rate
                    profit = (price - initial_price) * sell_amount - sell_fee
                    
                    position["usdt"] += sell_value - sell_fee
                    position["coin"] -= sell_amount
                    position["reserved_coin"] -= sell_amount
                    fees_paid += sell_fee
                    grid["coin_reserved"] = 0
                    grid["traded"] = True
                    
                    trade_log.append({
                        "timestamp": current['timestamp'],
                        "type": "SELL",
                        "price": price,
                        "amount": sell_amount,
                        "fee": sell_fee,
                        "profit": profit,
                        "inventory_slots": sum(1 for g in grids.values() if g["coin_reserved"] > 0)
                    })
                    
                    grid["state"] = "cooldown"
                    grid["cooldown"] = 3
            
            # BUY Execution (lower grids)
            elif crossed_down and grid["side"] == "buy":
                buy_amount = get_grid_size(price)
                buy_cost = buy_amount * price
                buy_fee = buy_cost * fee_rate
                
                if position["usdt"] >= buy_cost + buy_fee:
                    position["usdt"] -= buy_cost + buy_fee
                    position["coin"] += buy_amount
                    fees_paid += buy_fee
                    
                    trade_log.append({
                        "timestamp": current['timestamp'],
                        "type": "BUY",
                        "price": price,
                        "amount": buy_amount,
                        "fee": buy_fee,
                        "profit": 0.0,
                        "inventory_slots": sum(1 for g in grids.values() if g["coin_reserved"] > 0)
                    })
                    
                    grid["state"] = "cooldown"
                    grid["cooldown"] = 3

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
        "initial_price": initial_price,
        "final_price": final_price,
        "grid_mode": grid_mode,
        "bot_version": "bot.py v13.0 (Exchange-Accurate)"
    }