# bot.py - Version 20.0 (Finale stabile Version)
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass
class GridState:
    price: float
    side: str  # 'buy' oder 'sell'
    trade_amount: float  # Fixe Coin-Menge für dieses Grid
    coin_reserved: float = 0.0  # Nur für Verkaufs-Grids
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
        
        # FIFO Inventarverfolgung (Menge, Kaufpreis, Zeitstempel)
        self.coin_inventory: List[Tuple[float, float, pd.Timestamp]] = []
        
        # Basis-Coin-Menge berechnen (99% des Kapitals)
        self.base_coin_amount = self._calculate_base_coin_amount(total_investment, num_grids, initial_price)
        self._initialize_grids(total_investment, initial_price)

    def _validate_inputs(self, total_investment: float, lower_price: float,
                        upper_price: float, num_grids: int, fee_rate: float):
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

    def _calculate_base_coin_amount(self, total_investment: float, num_grids: int, initial_price: float) -> float:
        """Berechnet die konsistente Coin-Menge pro Grid-Level"""
        grid_investment = (total_investment * 0.99) / num_grids
        return round(grid_investment / initial_price, 8)  # Auf 8 Dezimalstellen gerundet

    def _initialize_grids(self, total_investment: float, initial_price: float):
        # 1. Sofortiger Coin-Kauf zum Startpreis (50% des Kapitals)
        initial_investment = total_investment * 0.5
        self.initial_coin = round(initial_investment / (initial_price * (1 + self.fee_rate)), 8)
        fee = round(self.initial_coin * initial_price * self.fee_rate, 8)
        
        self.position['usdt'] -= round((self.initial_coin * initial_price) + fee, 8)
        self.position['coin'] += self.initial_coin
        self.coin_inventory.append((self.initial_coin, initial_price, pd.Timestamp.now()))
        
        # 2. Grids initialisieren mit festen Trade-Mengen
        for price in self.grid_lines:
            if price > initial_price:  # Verkaufs-Grid
                self.grids[price] = GridState(
                    price=round(price, 4),
                    side='sell',
                    trade_amount=self.base_coin_amount,
                    coin_reserved=self.base_coin_amount
                )
            elif price < initial_price:  # Kauf-Grid
                self.grids[price] = GridState(
                    price=round(price, 4),
                    side='buy',
                    trade_amount=self.base_coin_amount
                )

    def process_candle(self, candle: pd.Series):
        try:
            current_price = float(candle['close'])
            prev_price = self.last_price if self.last_price is not None else float(candle['open'])
            
            # Preisbewegungen zwischen Grid-Levels prüfen
            for price in np.linspace(prev_price, current_price, 20):
                for grid in self.grids.values():
                    if ((prev_price < grid.price < current_price and grid.side == 'sell') or
                       (prev_price > grid.price > current_price and grid.side == 'buy')):
                        if grid.price != getattr(self, 'last_traded_price', None):
                            self._execute_trade(grid, candle)
            
            self.last_price = current_price
        except Exception as e:
            raise RuntimeError(f"Candle-Verarbeitungsfehler: {str(e)}")

    def _execute_trade(self, grid: GridState, candle: pd.Series):
        try:
            timestamp = candle['timestamp']
            fee = 0.0
            profit = 0.0
            
            if grid.side == 'sell':
                # FIFO Verkauf - älteste Coins zuerst
                remaining = grid.trade_amount
                temp_inventory = []
                
                while remaining > 0 and self.coin_inventory:
                    amount, buy_price, buy_time = self.coin_inventory.pop(0)
                    sell_amount = min(amount, remaining)
                    
                    if sell_amount < amount:
                        temp_inventory.append((amount - sell_amount, buy_price, buy_time))
                    
                    profit += (grid.price - buy_price) * sell_amount
                    remaining -= sell_amount
                
                # Nicht verkaufte Coins zurück ins Inventar
                self.coin_inventory = temp_inventory + self.coin_inventory
                
                if remaining > 0:
                    return  # Nicht genug Coins
                
                # Gebühren und Position aktualisieren
                fee = round(grid.trade_amount * grid.price * self.fee_rate, 8)
                self.position['coin'] -= grid.trade_amount
                self.position['usdt'] += round(grid.trade_amount * grid.price - fee, 8)
                profit = round(profit - fee, 8)
                
                # Grid-Reservierung aktualisieren
                self.grids[grid.price].coin_reserved = max(0, self.grids[grid.price].coin_reserved - grid.trade_amount)
            else:  # Kauf
                # Verfügbares USDT prüfen
                required_usdt = round(grid.trade_amount * grid.price * (1 + self.fee_rate), 8)
                if self.position['usdt'] < required_usdt:
                    return
                
                # Kauf ausführen
                fee = round(grid.trade_amount * grid.price * self.fee_rate, 8)
                self.position['usdt'] -= required_usdt
                self.position['coin'] += grid.trade_amount
                self.coin_inventory.append((grid.trade_amount, grid.price, timestamp))

            # Trade protokollieren
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
            raise RuntimeError(f"Trade-Fehler bei {grid.price}: {str(e)}")

def simulate_grid_bot(df: pd.DataFrame,
                     total_investment: float,
                     lower_price: float,
                     upper_price: float,
                     num_grids: int = 20,
                     grid_mode: str = 'geometric',
                     fee_rate: float = 0.001) -> Dict:
    """
    Simuliert Grid-Bot Strategie mit:
    - FIFO Gewinnberechnung
    - Konsistenten Trade-Mengen
    - Präziser Gebührenberechnung
    """
    try:
        initial_price = float(df.iloc[0]['close'])
        bot = GridBot(total_investment, lower_price, upper_price, num_grids, grid_mode, fee_rate, initial_price)
        
        for _, candle in df.iterrows():
            bot.process_candle(candle)
        
        final_price = float(df.iloc[-1]['close'])
        final_value = round(bot.position['usdt'] + bot.position['coin'] * final_price, 8)
        
        # Gesamtgewinn berechnen (inkl. unrealisiert)
        total_profit = final_value - total_investment
        total_fees = round(sum(t['fee'] for t in bot.trade_log), 8)
        
        return {
            'initial_investment': total_investment,
            'final_value': final_value,
            'profit_usdt': total_profit,
            'profit_pct': round((total_profit / total_investment) * 100, 4),
            'fees_paid': total_fees,
            'num_trades': len(bot.trade_log),
            'trade_log': bot.trade_log,
            'grid_lines': bot.grid_lines,
            'final_position': dict(bot.position),
            'initial_coin': bot.initial_coin,
            'reserved_coin': round(sum(g.coin_reserved for g in bot.grids.values()), 8),
            'initial_price': initial_price,
            'final_price': final_price,
            'price_change_pct': round(((final_price - initial_price) / initial_price) * 100, 4),
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