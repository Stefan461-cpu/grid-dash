# bot.py – Version 1.5 – Stand: 2025-07-09 22:45
import numpy as np
import pandas as pd

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
    reserved_amount = total_investment * 0.01  # 1 % USDT Reserve
    grid_lines = calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)

    # Initialisiere Grid-Zustände
    grid_state = {}
    for price in grid_lines:
        if price < initial_price:
            grid_state[price] = {"active_side": "BUY", "last_trade": None}
        elif price > initial_price:
            grid_state[price] = {"active_side": "SELL", "last_trade": None}
        else:
            grid_state[price] = {"active_side": None, "last_trade": None}

    position = {"usdt": total_investment - reserved_amount, "coin": 0.0}
    fees_paid = 0.0
    trade_log = []
    investment_per_grid = (total_investment - reserved_amount) / num_grids

    for idx in range(1, len(df)):
        prev_price = df.iloc[idx - 1]['close']
        current_price = df.iloc[idx]['close']
        timestamp = df.iloc[idx]['timestamp']

        # Richtung erkennen (für sinnvolle Grid-Sequenz)
        grid_sequence = sorted(grid_lines) if current_price > prev_price else sorted(grid_lines, reverse=True)

        for grid_price in grid_sequence:
            state = grid_state[grid_price]
            active_side = state["active_side"]

            # SELL (nur wenn aktiv und korrekt von unten überquert)
            if active_side == "SELL" and prev_price < grid_price <= current_price:
                coin_to_sell = investment_per_grid / grid_price
                if position["coin"] >= coin_to_sell:
                    trade_value = coin_to_sell * grid_price
                    fee = trade_value * fee_rate
                    position["usdt"] += trade_value - fee
                    position["coin"] -= coin_to_sell
                    fees_paid += fee
                    trade_log.append({
                        "timestamp": timestamp,
                        "type": "SELL",
                        "price": grid_price,
                        "amount": coin_to_sell,
                        "fee": fee
                    })
                    grid_state[grid_price]["active_side"] = None
                    grid_state[grid_price]["last_trade"] = "SELL"

            # BUY (nur wenn aktiv und korrekt von oben überquert)
            elif active_side == "BUY" and prev_price > grid_price >= current_price:
                if position["usdt"] >= investment_per_grid:
                    amount_net = investment_per_grid * (1 - fee_rate)
                    coins_bought = amount_net / grid_price
                    fee = investment_per_grid * fee_rate
                    position["usdt"] -= investment_per_grid
                    position["coin"] += coins_bought
                    fees_paid += fee
                    trade_log.append({
                        "timestamp": timestamp,
                        "type": "BUY",
                        "price": grid_price,
                        "amount": coins_bought,
                        "fee": fee
                    })
                    grid_state[grid_price]["active_side"] = None
                    grid_state[grid_price]["last_trade"] = "BUY"

            # Reaktivierung: Grid verlassen → neue Richtung erlauben
            elif state["active_side"] is None:
                last_trade = state["last_trade"]
                # Preis oberhalb + letzter Trade BUY → neuer SELL möglich
                if last_trade == "BUY" and current_price > grid_price and prev_price > grid_price:
                    grid_state[grid_price]["active_side"] = "SELL"
                # Preis unterhalb + letzter Trade SELL → neuer BUY möglich
                elif last_trade == "SELL" and current_price < grid_price and prev_price < grid_price:
                    grid_state[grid_price]["active_side"] = "BUY"

    final_usdt = position["usdt"]
    final_coin = position["coin"]
    final_value = final_usdt + final_coin * df.iloc[-1]['close']
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
        "final_position": position,
        "num_trades": len(trade_log),
        "average_investment_per_grid": investment_per_grid,
        "num_grids": num_grids,
        "reserved_amount": reserved_amount,
        "grid_mode": grid_mode,
        "lower_price": lower_price,
        "upper_price": upper_price,
        "bot_version": "bot.py v1.5 (2025-07-09 22:45)"
    }
