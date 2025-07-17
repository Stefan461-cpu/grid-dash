# bot.py - Version 18.2 (Verbesserte Grid-Initialisierung)
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class GridState:
    price: float
    side: Optional[str] = None  # 'buy' oder 'sell'
    coin_reserved: float = 0.0
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
        self.trade_log = []
        self.grids: Dict[float, GridState] = {}
        self.last_price = initial_price
        self.last_traded_price = None
        
        self._initialize_grids(total_investment, initial_price)

    def _validate_inputs(self, *args):
        total_investment, lower_price, upper_price, num_grids, fee_rate = args
        
        if not all(isinstance(x, (int, float)) for x in [total_investment, lower_price, upper_price, fee_rate]):
            raise ValueError("Alle Preise müssen numerisch sein")
        if lower_price >= upper_price:
            raise ValueError("Obere Preisgrenze muss > untere sein")
        if num_grids < 2:
            raise ValueError("Mindestens 2 Grid-Levels benötigt")
        if not 0 <= fee_rate < 0.1:
            raise ValueError("Gebühr muss zwischen 0% und 10% liegen")

    def _calculate_grid_lines(self, lower: float, upper: float, num: int, mode: str) -> List[float]:
        if mode == 'arithmetic':
            return sorted(np.linspace(lower, upper, num + 1).tolist())
        ratio = (upper / lower) ** (1 / num)
        return sorted([lower * (ratio ** i) for i in range(num + 1)])

    def _initialize_grids(self, total_investment: float, initial_price: Optional[float]):
        if initial_price is None:
            initial_price = self.grid_lines[len(self.grid_lines) // 2]
        
        # Calculate grid distribution based on initial price
        sell_grids = [p for p in self.grid_lines if p > initial_price]
        buy_grids = [p for p in self.grid_lines if p < initial_price]
        
        # Balanced allocation (50% for buys, 50% for sells)
        usdt_per_sell_grid = (total_investment * 0.5) / len(sell_grids) if sell_grids else 0
        usdt_per_buy_grid = (total_investment * 0.5) / len(buy_grids) if buy_grids else 0
        
        # Initialize coin position by buying at initial price
        if initial_price in self.grid_lines:
            buy_amount = (total_investment * 0.5) / (initial_price * (1 + self.fee_rate))
            self.position['usdt'] -= (buy_amount * initial_price) * (1 + self.fee_rate)
            self.position['coin'] += buy_amount
        
        # Initialize sell grids (above initial price)
        for price in sell_grids:
            coin_amount = usdt_per_sell_grid / (price * (1 + self.fee_rate))
            self.grids[price] = GridState(
                price=round(price, 4),
                coin_reserved=coin_amount
            )
        
        # Initialize buy grids (below initial price)
        for price in buy_grids:
            self.grids[price] = GridState(
                price=round(price, 4),
                coin_reserved=0.0  # No coin reserved for buy grids
            )
        
        # Handle the initial price grid if it exists in grid lines
        if initial_price in self.grid_lines:
            self.grids[initial_price] = GridState(
                price=round(initial_price, 4),
                coin_reserved=0.0  # Neutral grid at initial price
            )

    def process_candle(self, candle: pd.Series):
        try:
            current_price = float(candle['close'])
            prev_price = self.last_price if self.last_price is not None else float(candle['open'])
            
            for price in np.linspace(prev_price, current_price, 20):
                for grid in self.grids.values():
                    grid.side = 'sell' if price < grid.price else 'buy'
                    
                    if ((prev_price < grid.price < current_price and grid.side == 'sell') or
                       (prev_price > grid.price > current_price and grid.side == 'buy')):
                        if grid.price != getattr(self, 'last_traded_price', None):
                            self._execute_trade(grid, candle)
            
            self.last_price = current_price
        except Exception as e:
            raise RuntimeError(f"Candle-Verarbeitungsfehler: {str(e)}")

    def _execute_trade(self, grid: GridState, candle: pd.Series):
        try:
            trade_amount, fee, profit = 0.0, 0.0, 0.0
            current_price = float(candle['close'])
            
            if grid.side == 'sell':
                trade_amount = min(grid.coin_reserved, self.position['coin'])
                if trade_amount <= 1e-8:
                    return
                
                fee = trade_amount * grid.price * self.fee_rate
                self.position['coin'] -= trade_amount
                self.position['usdt'] += trade_amount * grid.price - fee
                grid.coin_reserved -= trade_amount
                
                buy_trades = [t for t in self.trade_log if t['type'] == 'BUY']
                if buy_trades:
                    total_cost = sum(t['price'] * t['amount'] for t in buy_trades)
                    total_amount = sum(t['amount'] for t in buy_trades)
                    cost_basis = total_cost / total_amount
                    profit = (grid.price - cost_basis) * trade_amount - fee
            else:
                available_usdt = self.position['usdt']
                trade_amount = available_usdt / (grid.price * (1 + self.fee_rate))
                if trade_amount <= 1e-8:
                    return
                
                fee = trade_amount * grid.price * self.fee_rate
                self.position['usdt'] -= (trade_amount * grid.price) + fee
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
            raise RuntimeError(f"Trade-Fehler bei {grid.price}: {str(e)}")

def simulate_grid_bot(df: pd.DataFrame,
                     total_investment: float,
                     lower_price: float,
                     upper_price: float,
                     num_grids: int = 20,
                     grid_mode: str = 'geometric',
                     fee_rate: float = 0.001) -> Dict:
    """
    Returns:
        {
            'initial_investment': float,
            'final_value': float,
            'profit_usdt': float,  # Summe aller Trade-Profits
            'profit_pct': float,   # Relativer Profit (vom Investment)
            'fees_paid': float,
            'num_trades': int,
            'trade_log': List[Dict],
            'grid_lines': List[float],
            'final_position': Dict,
            'initial_price': float,
            'final_price': float,
            'price_change_pct': float,  # Reine Kursänderung
            'error': Optional[str]
        }
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
            'initial_price': 0.0,
            'final_price': 0.0,
            'price_change_pct': 0.0,
            'error': str(e)
        }