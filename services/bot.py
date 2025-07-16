# bot.py - Version 15.0 (Strict State Machine)
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Set

@dataclass
class GridState:
    price: float
    side: str  # 'buy' or 'sell'
    state: str = 'inactive'  # 'inactive'|'active'|'cooldown'
    cooldown: int = 0
    trade_count: int = 0

class StrictGridBot:
    def __init__(self, total_investment: float, lower_price: float, upper_price: float, 
                 num_grids: int, grid_mode: str, fee_rate: float):
        self.grid_lines = self._calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)
        self.fee_rate = fee_rate
        self.position = {'usdt': total_investment, 'coin': 0.0}
        self.trade_log = []
        self.trade_history: Set[float] = set()  # Track executed prices
        self.min_price_gap = upper_price * 0.0015  # 0.15% minimum spacing
        self._init_grids(total_investment)

    def _calculate_grid_lines(self, lower, upper, num, mode):
        if mode == "arithmetic":
            return np.linspace(lower, upper, num + 1).tolist()
        return [lower * ((upper/lower) ** (i/num)) for i in range(num + 1)]

    def _init_grids(self, total_investment):
        initial_price = self.grid_lines[len(self.grid_lines)//2]
        self.grids: Dict[float, GridState] = {}
        grid_usdt = total_investment * 0.98 / len(self.grid_lines)  # 2% fee reserve

        for price in sorted(self.grid_lines):
            side = 'sell' if price > initial_price else 'buy'
            g = GridState(price=round(price, 4), side=side)
            
            if side == 'sell':
                g.coin_reserved = grid_usdt / price
                self.position['usdt'] -= grid_usdt
                self.position['coin'] += g.coin_reserved
            
            self.grids[price] = g

    def process_candle(self, candle: pd.Series):
        current_price = candle['close']
        self._update_grid_states(current_price)
        
        for price, grid in self.grids.items():
            if grid.state != 'active' or price in self.trade_history:
                continue
                
            if self._validate_trade(grid, current_price):
                self._execute_trade(grid, candle)

    def _update_grid_states(self, current_price):
        active_grids = sorted(
            [g for g in self.grids.values() 
             if g.cooldown == 0 and g.price not in self.trade_history],
            key=lambda g: abs(g.price - current_price)
        
        for grid in active_grids[:2]:  # Activate nearest 2 grids
            grid.state = 'active'

        for grid in self.grids.values():
            if grid.cooldown > 0:
                grid.cooldown -= 1

    def _validate_trade(self, grid, current_price):
        price_diff = abs(grid.price - current_price) / current_price
        if grid.side == 'sell':
            return (current_price >= grid.price * 1.0015 and 
                    price_diff > 0.0005 and  # Minimum 0.05% movement
                    all(abs(grid.price - p) > self.min_price_gap 
                    for p in self.trade_history))
        else:
            return (current_price <= grid.price * 0.9985 and 
                    price_diff > 0.0005 and
                    all(abs(grid.price - p) > self.min_price_gap 
                    for p in self.trade_history))

    def _execute_trade(self, grid, candle):
        if grid.side == 'sell' and grid.coin_reserved > 0:
            trade_amount = min(grid.coin_reserved, self.position['coin'])
            trade_value = trade_amount * grid.price
            fee = trade_value * self.fee_rate
            
            self.position['coin'] -= trade_amount
            self.position['usdt'] += trade_value - fee
            grid.coin_reserved -= trade_amount
        else:
            trade_amount = min(self.position['usdt'] / (grid.price * (1 + self.fee_rate)), 
                              self.position['usdt'] * 0.1)  # Max 10% of USDT
            fee = trade_amount * grid.price * self.fee_rate
            
            self.position['usdt'] -= trade_amount * grid.price + fee
            self.position['coin'] += trade_amount
            if grid.side == 'buy':
                grid.coin_reserved += trade_amount

        self.trade_log.append({
            'timestamp': candle['timestamp'],
            'type': grid.side.upper(),
            'price': grid.price,
            'amount': trade_amount,
            'fee': fee,
            'profit': (grid.price - self._get_cost_basis()) * trade_amount - fee if grid.side == 'sell' else 0,
            'inventory_slots': len([g for g in self.grids.values() if g.coin_reserved > 0])
        })
        
        self.trade_history.add(grid.price)
        grid.state = 'cooldown'
        grid.cooldown = 3
        grid.trade_count += 1

    def _get_cost_basis(self):
        buy_trades = [t for t in self.trade_log if t['type'] == 'BUY']
        if not buy_trades:
            return 0
        total_cost = sum(t['price'] * t['amount'] for t in buy_trades)
        total_amount = sum(t['amount'] for t in buy_trades)
        return total_cost / total_amount if total_amount > 0 else 0

def simulate_grid_bot(df, total_investment, lower_price, upper_price, num_grids, grid_mode, fee_rate):
    bot = StrictGridBot(total_investment, lower_price, upper_price, num_grids, grid_mode, fee_rate)
    for _, candle in df.iterrows():
        bot.process_candle(candle)
    
    final_value = bot.position['usdt'] + bot.position['coin'] * df.iloc[-1]['close']
    
    return {
        'initial_investment': total_investment,
        'final_value': final_value,
        'profit_usdt': final_value - total_investment,
        'profit_pct': (final_value - total_investment) / total_investment * 100,
        'fees_paid': sum(t['fee'] for t in bot.trade_log),
        'grid_lines': bot.grid_lines,
        'trade_log': bot.trade_log,
        'final_position': dict(bot.position),
        'num_trades': len(bot.trade_log),
        'initial_price': df.iloc[0]['close'],
        'final_price': df.iloc[-1]['close'],
        'grid_mode': grid_mode,
        'bot_version': 'StrictGridBot v15'
    }