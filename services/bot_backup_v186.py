# bot.py - Version 18.6 (Fixed Consistent Trade Amounts)
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class GridState:
    price: float
    side: Optional[str] = None  # 'buy' or 'sell'
    coin_reserved: float = 0.0
    trade_amount: float = 0.0  # Fixed amount for this grid (in coin units)
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
        self.initial_coin = 0.0  # Stores initial coin purchase
        self.trade_log = []
        self.grids: Dict[float, GridState] = {}
        self.last_price = initial_price
        self.last_traded_price = None
        
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
        
        # 2. Initialize all grids with fixed trade amounts
        for price in self.grid_lines:
            if price > initial_price:  # Sell grid
                coin_amount = self.base_amount_usdt / (price * (1 + self.fee_rate))
                self.grids[price] = GridState(
                    price=round(price, 4),
                    coin_reserved=coin_amount,
                    trade_amount=coin_amount,
                    side='sell'
                )
            elif price < initial_price:  # Buy grid
                coin_amount = self.base_amount_usdt / (price * (1 + self.fee_rate))
                self.grids[price] = GridState(
                    price=round(price, 4),
                    coin_reserved=0.0,
                    trade_amount=coin_amount,
                    side='buy'
                )
            else:  # Neutral grid at initial price
                self.grids[price] = GridState(
                    price=round(price, 4),
                    coin_reserved=0.0,
                    trade_amount=0.0,
                    side=None
                )

    def process_candle(self, candle: pd.Series):
        try:
            current_price = float(candle['close'])
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
            fee, profit = 0.0, 0.0
            trade_amount = grid.trade_amount
            
            if grid.side == 'sell':
                # Verify we have enough coins to sell
                if self.position['coin'] < trade_amount or trade_amount <= 1e-8:
                    return
                
                fee = trade_amount * grid.price * self.fee_rate
                self.position['coin'] -= trade_amount
                self.position['usdt'] += trade_amount * grid.price - fee
                grid.coin_reserved -= trade_amount
                
                # Calculate profit based on average buy price
                buy_trades = [t for t in self.trade_log if t['type'] == 'BUY']
                if buy_trades:
                    total_cost = sum(t['price'] * t['amount'] for t in buy_trades)
                    total_amount = sum(t['amount'] for t in buy_trades)
                    cost_basis = total_cost / total_amount
                    profit = (grid.price - cost_basis) * trade_amount - fee
            else:  # buy
                # Verify we have enough USDT
                required_usdt = trade_amount * grid.price * (1 + self.fee_rate)
                if self.position['usdt'] < required_usdt or trade_amount <= 1e-8:
                    return
                
                fee = trade_amount * grid.price * self.fee_rate
                self.position['usdt'] -= required_usdt
                self.position['coin'] += trade_amount

            self.trade_log.append({
                'timestamp': candle['timestamp'],
                'type': grid.side.upper(),
                'price': float(grid.price),
                'amount': float(trade_amount),
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
    Simulates grid bot trading with consistent trade amounts per grid level.
    
    Returns:
        Dict with simulation results including:
        - initial_investment
        - final_value
        - profit metrics
        - trade log
        - position details
    """
    try:
        initial_price = float(df.iloc[0]['close'])
        bot = GridBot(total_investment, lower_price, upper_price, num_grids, grid_mode, fee_rate, initial_price)
        
        for _, candle in df.iterrows():
            bot.process_candle(candle)
        
        final_price = float(df.iloc[-1]['close'])
        final_value = bot.position['usdt'] + bot.position['coin'] * final_price
        
        total_profit = sum(t['profit'] for t in bot.trade_log)
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