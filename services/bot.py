# bot.py - Version 17 (Stable)
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class GridState:
    """
    Repräsentiert den Zustand eines einzelnen Grid-Levels
    """
    price: float
    side: Optional[str] = None  # 'buy' oder 'sell', wird dynamisch gesetzt
    coin_reserved: float = 0.0  # Für Sell-Orders reservierte Coins
    trade_count: int = 0  # Anzahl der ausgeführten Trades

class GridBot:
    def __init__(self, 
                total_investment: float,
                lower_price: float,
                upper_price: float,
                num_grids: int,
                grid_mode: str = 'geometric',
                fee_rate: float = 0.001):
        """
        Initialisiert den Grid-Bot mit strenger Input-Validierung
        
        Args:
            total_investment: Gesamtinvestition in USDT
            lower_price: Untere Preisgrenze (muss > 0)
            upper_price: Obere Preisgrenze (muss > lower_price)
            num_grids: Anzahl der Grid-Levels (mind. 2)
            grid_mode: 'arithmetic' oder 'geometric'
            fee_rate: Handelsgebühr (z.B. 0.001 für 0.1%)
        """
        # Input-Validierung
        self._validate_inputs(total_investment, lower_price, upper_price, num_grids, fee_rate)
        
        self.grid_lines = self._calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)
        self.fee_rate = fee_rate
        self.position = {'usdt': float(total_investment), 'coin': 0.0}
        self.trade_log = []
        self.grids: Dict[float, GridState] = {}
        
        self._initialize_grids(total_investment)
        self.last_price = None  # Für Preisinterpolation

    def _validate_inputs(self, *args):
        """Wirft ValueError bei ungültigen Inputs"""
        total_investment, lower_price, upper_price, num_grids, fee_rate = args
        
        if not all(isinstance(x, (int, float)) for x in [total_investment, lower_price, upper_price, fee_rate]):
            raise ValueError("Alle Preise/Investitionen müssen numerisch sein")
        if num_grids < 2:
            raise ValueError("Mindestens 2 Grid-Levels erforderlich")
        if lower_price >= upper_price:
            raise ValueError("Obere Preisgrenze muss größer als untere sein")
        if fee_rate < 0 or fee_rate >= 0.1:
            raise ValueError("Gebühr muss zwischen 0 und 10% liegen")

    def _calculate_grid_lines(self, lower: float, upper: float, num: int, mode: str) -> List[float]:
        """Berechnet Grid-Preislevels"""
        if mode == 'arithmetic':
            return sorted(np.linspace(lower, upper, num + 1).tolist())
        ratio = (upper / lower) ** (1 / num)
        return sorted([lower * (ratio ** i) for i in range(num + 1)])

    def _initialize_grids(self, total_investment: float):
        """
        Initialisiert alle Grid-Levels mit:
        - Dynamischer Buy/Sell-Zuordnung
        - Korrekter Coin/USDT-Reservierung
        """
        start_price = self.grid_lines[len(self.grid_lines) // 2]
        usdt_per_grid = total_investment * 0.99 / len(self.grid_lines)  # 1% Fee-Reserve
        
        # Initiale Coin-Käufe für Sell-Grids
        sell_grids = [p for p in self.grid_lines if p > start_price]
        total_coin_needed = sum(usdt_per_grid / (p * (1 + self.fee_rate)) for p in sell_grids)
        
        # Position aktualisieren
        self.position['usdt'] -= usdt_per_grid * len(sell_grids)
        self.position['coin'] += total_coin_needed
        
        # Grids erstellen
        for price in self.grid_lines:
            self.grids[price] = GridState(
                price=round(price, 4),
                coin_reserved=usdt_per_grid / price if price > start_price else 0.0
            )

    def process_candle(self, candle: pd.Series):
        """
        Verarbeitet einen neuen Candlestick
        candle: pd.Series mit ['open','high','low','close','volume','timestamp']
        """
        try:
            current_price = float(candle['close'])
            prev_price = self.last_price if self.last_price is not None else float(candle['open'])
            
            # Lineare Preisinterpolation (20 Schritte zwischen Kerzen)
            price_steps = np.linspace(prev_price, current_price, 20)
            
            for price in price_steps:
                for grid in self.grids.values():
                    # Dynamische Side-Zuweisung
                    grid.side = 'sell' if price < grid.price else 'buy'
                    
                    # Trade-Logik
                    if (prev_price < grid.price < current_price and grid.side == 'sell') or \
                       (prev_price > grid.price > current_price and grid.side == 'buy'):
                        self._execute_trade(grid, candle)
            
            self.last_price = current_price
            
        except Exception as e:
            print(f"Fehler bei Candle-Verarbeitung: {str(e)}")
            raise

    def _execute_trade(self, grid: GridState, candle: pd.Series):
        """Führt einen Trade aus und aktualisiert die Position"""
        try:
            trade_amount, fee = 0.0, 0.0
            current_price = float(candle['close'])
            
            if grid.side == 'sell':
                trade_amount = min(grid.coin_reserved, self.position['coin'])
                if trade_amount <= 1e-8:  # Mindestgröße 0.00000001
                    return
                
                trade_value = trade_amount * grid.price
                fee = trade_value * self.fee_rate
                
                # Position aktualisieren
                self.position['coin'] -= trade_amount
                self.position['usdt'] += trade_value - fee
                grid.coin_reserved -= trade_amount
            else:
                available_usdt = self.position['usdt']
                trade_amount = available_usdt / (grid.price * (1 + self.fee_rate))
                if trade_amount <= 1e-8:
                    return
                
                fee = trade_amount * grid.price * self.fee_rate
                self.position['usdt'] -= (trade_amount * grid.price) + fee
                self.position['coin'] += trade_amount

            # Trade protokollieren
            self.trade_log.append({
                'timestamp': candle['timestamp'],
                'type': grid.side.upper(),
                'price': float(grid.price),
                'amount': float(trade_amount),
                'fee': float(fee),
                'inventory_slots': len([g for g in self.grids.values() if g.coin_reserved > 0])
            })
            
            grid.trade_count += 1
            
        except Exception as e:
            print(f"Trade-Fehler bei {grid.price}: {str(e)}")
            raise

def simulate_grid_bot(df: pd.DataFrame,
                     total_investment: float,
                     lower_price: float,
                     upper_price: float,
                     num_grids: int = 20,
                     grid_mode: str = 'geometric',
                     fee_rate: float = 0.001) -> Dict:
    """
    Führt eine vollständige Grid-Bot-Simulation durch
    
    Returns:
        {
            'initial_investment': float,
            'final_value': float,
            'profit_pct': float,
            'trade_log': List[Dict],
            'grid_lines': List[float],
            'final_position': Dict,
            'error': Optional[str]
        }
    """
    try:
        bot = GridBot(total_investment, lower_price, upper_price, num_grids, grid_mode, fee_rate)
        
        for _, candle in df.iterrows():
            bot.process_candle(candle)
        
        final_price = float(df.iloc[-1]['close'])
        final_value = bot.position['usdt'] + bot.position['coin'] * final_price
        
        return {
            'initial_investment': total_investment,
            'final_value': final_value,
            'profit_pct': (final_value - total_investment) / total_investment * 100,
            'trade_log': bot.trade_log,
            'grid_lines': bot.grid_lines,
            'final_position': dict(bot.position),
            'error': None
        }
        
    except Exception as e:
        return {
            'initial_investment': total_investment,
            'final_value': total_investment,
            'profit_pct': 0.0,
            'trade_log': [],
            'grid_lines': [],
            'final_position': {'usdt': total_investment, 'coin': 0.0},
            'error': str(e)
        }