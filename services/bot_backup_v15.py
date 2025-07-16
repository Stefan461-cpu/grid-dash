# bot.py - Version 16 (Fixed Grid Logic)
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List

def calculate_grid_lines(lower_price: float, upper_price: float, 
                       num_grids: int, grid_mode: str) -> List[float]:
    """Calculate grid lines (arithmetic or geometric)"""
    if grid_mode == "arithmetic":
        return np.linspace(lower_price, upper_price, num_grids + 1).tolist()
    ratio = (upper_price / lower_price) ** (1 / num_grids)
    return [lower_price * (ratio ** i) for i in range(num_grids + 1)]

@dataclass
class GridState:
    price: float
    side: str  # 'buy' or 'sell'
    state: str = 'inactive'
    cooldown: int = 0
    trade_count: int = 0
    coin_reserved: float = 0.0

class StrictGridBot:
    def __init__(self, 
                total_investment: float, 
                lower_price: float,
                upper_price: float,
                num_grids: int,
                grid_mode: str,
                fee_rate: float):
        
        # Input validation
        assert num_grids >= 2, "num_grids must be ≥ 2"
        assert grid_mode in ('arithmetic', 'geometric'), "Invalid grid_mode"
        assert 0 <= fee_rate < 0.1, "fee_rate must be 0 ≤ rate < 0.1"
        
        self.grid_lines = sorted(calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode))
        self.fee_rate = fee_rate
        self.position = {'usdt': float(total_investment), 'coin': 0.0}
        self.trade_log = []
        self.min_price_gap = (upper_price - lower_price) * 0.005  # 0.5% of range
        self.grids = {}  # ✅ HIER Initialisierung
        self._init_grids(float(total_investment))

    def _init_grids(self, total_investment: float):
        """Initialize grids with proper buy/sell classification"""
        mid_price = self.grid_lines[len(self.grid_lines)//2]
        grid_usdt = total_investment * 0.98 / len(self.grid_lines)  # 2% fee reserve
        
        for price in self.grid_lines:
            side = 'buy' if price < mid_price else 'sell'
            coin_reserved = grid_usdt / price if side == 'sell' else 0.0
            
            self.grids[price] = GridState(
                price=round(price, 4),
                side=side,
                coin_reserved=coin_reserved
            )
            
            if side == 'sell':
                self.position['usdt'] -= grid_usdt
                self.position['coin'] += coin_reserved

    def process_candle(self, candle: pd.Series):
        """Process new candle data"""
        current_price = candle['close']
        
        # Skip if price outside grid range
        if not (self.grid_lines[0] <= current_price <= self.grid_lines[-1]):
            return
            
        self._update_grid_states(current_price)
        
        # Process active grids
        for price, grid in self.grids.items():
            if self._should_execute(grid, current_price):
                self._execute_trade(grid, candle)

    def _update_grid_states(self, current_price: float):
        """Activate grids in current price zone"""
        price_range = current_price * 0.02  # 2% activation zone
        
        for grid in self.grids.values():
            # Reset cooldown if applicable
            if grid.cooldown > 0:
                grid.cooldown -= 1
                
            # Activate grids in range
            if (abs(grid.price - current_price) <= price_range
                and grid.cooldown == 0):
                grid.state = 'active'
            else:
                grid.state = 'inactive'

    def _should_execute(self, grid: GridState, current_price: float) -> bool:
        """Check trade execution conditions"""
        if grid.state != 'active':
            return False
            
        # Simple directional logic
        if grid.side == 'sell':
            return current_price >= grid.price
        else:
            return current_price <= grid.price

    def _execute_trade(self, grid: GridState, candle: pd.Series):
        """Execute trade and update state"""
        current_price = candle['close']
        
        if grid.side == 'sell':
            # Sell logic
            trade_amount = min(grid.coin_reserved, self.position['coin'])
            if trade_amount <= 0:
                return
                
            trade_value = trade_amount * grid.price
            fee = trade_value * self.fee_rate
            
            self.position['coin'] -= trade_amount
            self.position['usdt'] += trade_value - fee
            grid.coin_reserved -= trade_amount
        else:
            # Buy logic
            available_usdt = self.position['usdt'] * 0.1  # 10% of balance
            trade_amount = available_usdt / (grid.price * (1 + self.fee_rate))
            
            if trade_amount <= 0:
                return
                
            fee = trade_amount * grid.price * self.fee_rate
            self.position['usdt'] -= (trade_amount * grid.price) + fee
            self.position['coin'] += trade_amount
            grid.coin_reserved += trade_amount

        # Log trade
        self.trade_log.append({
            'timestamp': candle['timestamp'],
            'type': grid.side.upper(),
            'price': grid.price,
            'amount': trade_amount,
            'fee': fee,
            'profit': (grid.price - self._get_cost_basis()) * trade_amount - fee if grid.side == 'sell' else 0,
            'inventory_slots': len([g for g in self.grids.values() if g.coin_reserved > 0])
        })
        
        # Update grid state
        grid.state = 'cooldown'
        grid.cooldown = 1  # Minimal cooldown
        grid.trade_count += 1

    def _get_cost_basis(self) -> float:
        """Calculate average coin purchase price"""
        buy_trades = [t for t in self.trade_log if t['type'] == 'BUY']
        if not buy_trades:
            return 0.0
        total_cost = sum(t['price'] * t['amount'] for t in buy_trades)
        total_amount = sum(t['amount'] for t in buy_trades)
        return total_cost / total_amount if total_amount > 0 else 0.0

def simulate_grid_bot(df, total_investment, lower_price, upper_price, num_grids, grid_mode, fee_rate):
    """Run simulation with the improved bot"""
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
        'bot_version': 'StrictGridBot v16 (Fixed)'
    }