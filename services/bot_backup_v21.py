# bot.py - Version 21.0 (Final Robust Implementation)
# Diese Version implementiert ein aufwendiges und überflüssiges und falsch implementiertes
# Buchungssystem für einzelnede Sell-Grids --> eliminiert 
# Gridstatus vor jedem Candle-Processing aktualisieren

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

BOT_VERSION = f"bot.py – Version 21.0 – Stand: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

from typing import Dict, List, Optional, Tuple

@dataclass
class GridState:
    price: float
    side: str  # 'buy' or 'sell'
    trade_amount: float  # Fixed coin amount for this grid
    coin_reserved: float = 0.0  # Only for sell grids
    trade_count: int = 0

class GridBot:
    def __init__(self, 
                total_investment: float,
                lower_price: float,
                upper_price: float,
                num_grids: int,
                grid_mode: str = 'geometric',
                fee_rate: float = 0.001,
                initial_price: Optional[float] = None):
        
        self._validate_inputs(total_investment, lower_price, upper_price, num_grids, fee_rate)
        
        self.grid_lines = self._calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)
        self.fee_rate = fee_rate
        self.position = {'usdt': float(total_investment), 'coin': 0.0}
        self.initial_coin = 0.0
        self.trade_log = []
        self.grids: Dict[float, GridState] = {}
        self.last_price = initial_price
        self.last_traded_price = None
        
        # FIFO inventory tracking (amount, buy_price, timestamp)
        self.coin_inventory: List[Tuple[float, float, pd.Timestamp]] = []
        
        # Calculate base USDT amount per grid (99% of total investment)
        self.base_amount_usdt = (total_investment * 0.99) / num_grids
        self._initialize_grids(total_investment, initial_price)

    def _validate_inputs(self, total_investment: float, lower_price: float,
                        upper_price: float, num_grids: int, fee_rate: float):
        if not all(isinstance(x, (int, float)) for x in [total_investment, lower_price, upper_price, fee_rate]):
            raise ValueError("All prices must be numeric")
        if lower_price >= upper_price:
            raise ValueError("Upper price must be > lower price")
        if num_grids < 2:
            raise ValueError("Minimum 2 grid levels required")
        if not 0 <= fee_rate < 0.1:
            raise ValueError("Fee must be between 0% and 10%")

    def _calculate_grid_lines(self, lower: float, upper: float, num: int, mode: str) -> List[float]:
        if mode == 'arithmetic':
            return sorted(np.linspace(lower, upper, num + 1).tolist())
        ratio = (upper / lower) ** (1 / num)
        return sorted([lower * (ratio ** i) for i in range(num + 1)])

    def _initialize_grids(self, total_investment: float, initial_price: Optional[float]):
        if initial_price is None:
            initial_price = self.grid_lines[len(self.grid_lines) // 2]
        
        # 1. Immediate coin purchase at initial price (50% of capital)
        initial_investment = total_investment * 0.5
        self.initial_coin = initial_investment / (initial_price * (1 + self.fee_rate))
        fee = self.initial_coin * initial_price * self.fee_rate
        
        self.position['usdt'] -= (self.initial_coin * initial_price) + fee
        self.position['coin'] += self.initial_coin
        self.coin_inventory.append((self.initial_coin, initial_price, pd.Timestamp.now()))
        
        # 2. Initialize all grids with fixed trade amounts
        for price in self.grid_lines:
            if price > initial_price:  # Sell grid
                coin_amount = self.base_amount_usdt / (price * (1 + self.fee_rate))
                self.grids[price] = GridState(
                    price=round(price, 4),
                    side='sell',
                    trade_amount=coin_amount,
                    coin_reserved=coin_amount
                )
            elif price < initial_price:  # Buy grid
                coin_amount = self.base_amount_usdt / (price * (1 + self.fee_rate))
                self.grids[price] = GridState(
                    price=round(price, 4),
                    side='buy',
                    trade_amount=coin_amount
                )

    def process_candle(self, candle: pd.Series):
        try:
            current_price = float(candle['close'])
            # --- Grid-Zustände vor jedem Candle-Processing aktualisieren ---
            for price in self.grid_lines:
                if price > current_price:
                    self.grids[price].side = 'sell'  # Neuer Zustand SELL
                elif price < current_price:
                    self.grids[price].side = 'buy'   # Neuer Zustand BUY
                else:
                    continue  # Keine Trades beim exakten Preis

                prev_price = self.last_price if self.last_price is not None else float(candle['open'])
                
                # Check price movements between grid levels
                for price in np.linspace(prev_price, current_price, 20):
                    for grid in self.grids.values():
                        if ((prev_price < grid.price < current_price and grid.side == 'sell') or
                           (prev_price > grid.price > current_price and grid.side == 'buy')):
                            if grid.price != getattr(self, 'last_traded_price', None):
                                self._execute_trade(grid, candle)
                
                self.last_price = current_price
        except Exception as e:
            raise RuntimeError(f"Candle processing error: {str(e)}")

    def _execute_trade(self, grid: GridState, candle: pd.Series):
        try:
            fee = 0.0
            profit = 0.0
            timestamp = candle['timestamp']
            
            if grid.side == 'sell':
                # FIFO implementation - sell oldest coins first
                remaining_amount = grid.trade_amount
                
                while remaining_amount > 0 and self.coin_inventory:
                    oldest_amount, oldest_price, oldest_time = self.coin_inventory[0]
                    sell_amount = min(oldest_amount, remaining_amount)
                    
                    # Calculate profit for this portion
                    profit += (grid.price - oldest_price) * sell_amount
                    
                    # Update inventory
                    if oldest_amount == sell_amount:
                        self.coin_inventory.pop(0)
                    else:
                        self.coin_inventory[0] = (oldest_amount - sell_amount, oldest_price, oldest_time)
                    
                    remaining_amount -= sell_amount
                
                if remaining_amount > 0:
                    return  # Not enough coins to complete trade
                
                # Apply fees and update position
                fee = grid.trade_amount * grid.price * self.fee_rate
                self.position['coin'] -= grid.trade_amount
                self.position['usdt'] += (grid.trade_amount * grid.price) - fee
                profit -= fee
                
                # Update grid reservation
                if grid.price in self.grids:
                    self.grids[grid.price].coin_reserved -= grid.trade_amount
            else:  # buy
                # Verify sufficient USDT
                required_usdt = grid.trade_amount * grid.price * (1 + self.fee_rate)
                if self.position['usdt'] < required_usdt:
                    return
                
                # Execute buy
                fee = grid.trade_amount * grid.price * self.fee_rate
                self.position['usdt'] -= required_usdt
                self.position['coin'] += grid.trade_amount
                self.coin_inventory.append((grid.trade_amount, grid.price, timestamp))

            # Log the trade
            self.trade_log.append({
                'timestamp': timestamp,
                'type': grid.side.upper(),
                'price': float(grid.price),
                'amount': float(grid.trade_amount),
                'fee': float(fee),
                'profit': float(profit),
                'inventory_slots': len([g for g in self.grids.values() if g.coin_reserved > 0])
            })
            
            self.last_traded_price = grid.price
            grid.trade_count += 1
            
        except Exception as e:
            raise RuntimeError(f"Trade error at {grid.price}: {str(e)}")

def simulate_grid_bot(df: pd.DataFrame,
                     total_investment: float,
                     lower_price: float,
                     upper_price: float,
                     num_grids: int = 20,
                     grid_mode: str = 'geometric',
                     fee_rate: float = 0.001) -> Dict:
    """
    Simulates grid bot trading with:
    - FIFO profit calculation
    - Consistent trade amounts
    - Exact fee accounting
    """
    try:
        initial_price = float(df.iloc[0]['close'])
        bot = GridBot(total_investment, lower_price, upper_price, num_grids, grid_mode, fee_rate, initial_price)
        
        for _, candle in df.iterrows():
            bot.process_candle(candle)
        
        final_price = float(df.iloc[-1]['close'])
        final_value = bot.position['usdt'] + bot.position['coin'] * final_price
        
        # Calculate total profit (including unrealized)
        total_profit = final_value - total_investment
        total_fees = sum(t['fee'] for t in bot.trade_log)
        
        return {
            'initial_investment': total_investment,
            'final_value': final_value,
            'profit_usdt': total_profit,
            'profit_pct': (total_profit / total_investment) * 100,
            'fees_paid': total_fees,
            'num_trades': len(bot.trade_log),
            'trade_log': bot.trade_log,
            'grid_lines': bot.grid_lines,
            'final_position': dict(bot.position),
            'initial_coin': bot.initial_coin,
            'reserved_coin': sum(g.coin_reserved for g in bot.grids.values()),
            'initial_price': initial_price,
            'final_price': final_price,
            'price_change_pct': ((final_price - initial_price) / initial_price) * 100,
            'error': None
        }
    except Exception as e:
        return {
            'initial_investment': total_investment,
            'final_value': total_investment,
            'profit_usdt': 0.0,
            'profit_pct': 0.0,
            'fees_paid': 0.0,
            'num_trades': 0,
            'trade_log': [],
            'grid_lines': [],
            'final_position': {'usdt': total_investment, 'coin': 0.0},
            'initial_coin': 0.0,
            'reserved_coin': 0.0,
            'initial_price': 0.0,
            'final_price': 0.0,
            'price_change_pct': 0.0,
            'error': str(e)
        }