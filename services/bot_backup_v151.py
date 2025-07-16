# bot.py - Version 15.1 (Strict State Machine with Fixed Imports)
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Set, List

# Helper function must be defined OUTSIDE the class
def calculate_grid_lines(lower_price: float, upper_price: float, 
                        num_grids: int, grid_mode: str) -> List[float]:
    """
    Calculate grid lines (arithmetic or geometric) as a standalone function.
    Called by both StrictGridBot and app.py.
    """
    if grid_mode == "arithmetic":
        return np.linspace(lower_price, upper_price, num_grids + 1).tolist()
    ratio = (upper_price / lower_price) ** (1 / num_grids)
    return [lower_price * (ratio ** i) for i in range(num_grids + 1)]

@dataclass
class GridState:
    price: float
    side: str  # 'buy' or 'sell'
    state: str = 'inactive'  # 'inactive'|'active'|'cooldown'
    cooldown: int = 0
    trade_count: int = 0
    coin_reserved: float = 0.0  # 👈 Neu hinzugefügt

class StrictGridBot:
    def __init__(self, 
                 total_investment: float, 
                 lower_price: float,
                 upper_price: float,
                 num_grids: int,
                 grid_mode: str,
                 fee_rate: float):
        """
        Initialisiert den Grid-Bot mit strenger Typvalidierung
        
        Args:
            total_investment: Gesamt-USDT (muss > 0)
            lower_price: Untere Preisgrenze (muss < upper_price)
            upper_price: Obere Preisgrenze
            num_grids: Anzahl Grid-Levels (mind. 2)
            grid_mode: 'arithmetic' oder 'geometric'
            fee_rate: Gebühr (0.0001 für 0.01%)
        """
        # Typvalidierung
        assert isinstance(num_grids, int) and num_grids >= 2, "num_grids muss Integer ≥ 2 sein"
        assert grid_mode in ('arithmetic', 'geometric'), "Nur 'arithmetic' oder 'geometric' erlaubt"
        assert 0 <= fee_rate < 0.1, "fee_rate muss zwischen 0 und 0.1 liegen"

        self.grid_lines = self._calculate_grid_lines(lower_price, upper_price, num_grids, grid_mode)
        self.fee_rate = float(fee_rate)
        self.position = {'usdt': float(total_investment), 'coin': 0.0}
        self.trade_log = []
        self.trade_history: Set[float] = set()
        self.min_price_gap = float(upper_price) * 0.0015
        self._init_grids(float(total_investment))

    def _calculate_grid_lines(self, lower: float, upper: float, num: int, mode: str) -> List[float]:
        """Berechnet Grid-Levels"""
        if mode == "arithmetic":
            return np.linspace(lower, upper, num + 1).tolist()
        ratio = (upper / lower) ** (1 / num)
        return [lower * (ratio ** i) for i in range(num + 1)]

    def _init_grids(self, total_investment: float):
        """Korrigierte Grid-Initialisierung"""
        self.grids: Dict[float, GridState] = {}
        grid_usdt = total_investment * 0.98 / len(self.grid_lines)
        
        # Sortierte Grid-Lines für korrekte Zuordnung
        sorted_grids = sorted(self.grid_lines)
        mid_index = len(sorted_grids) // 2
        
        for i, price in enumerate(sorted_grids):
            # Alles unterhalb des mittleren Grids ist BUY, darüber SELL
            side = 'buy' if i < mid_index else 'sell'
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
        current_price = candle['close']
        if not (self.grid_lines[0] <= current_price <= self.grid_lines[-1]):
            return  # Keine Aktion außerhalb des Grid-Bereichs
        self._update_grid_states(current_price)

        for price, grid in self.grids.items():
            if self._should_execute(grid, current_price):
                self._execute_trade(grid, candle)

    def _update_grid_states(self, current_price: float):
        """Aktiviere nur relevante Grids"""
        active_threshold = 2  # Anzahl aktiver Grids
        
        # Deaktiviere alle Grids
        for grid in self.grids.values():
            grid.state = 'inactive'
        
        # Finde die nächsten Grids in beide Richtungen
        eligible_grids = []
        for price, grid in self.grids.items():
            if grid.cooldown == 0 and price not in self.trade_history:
                distance = abs(price - current_price)
                eligible_grids.append((distance, grid))
        
        # Aktiviere die nächstgelegenen Grids
        for _, grid in sorted(eligible_grids, key=lambda x: x[0])[:active_threshold]:
            grid.state = 'active'

    # def _update_grid_states(self, current_price: float):
    #     """Aktiviert/Deaktiviert Grids basierend auf Preis"""
    #     # Deaktiviere alle Grids >5% vom aktuellen Preis
    #     for grid in self.grids.values():
    #         if abs(grid.price - current_price)/current_price > 0.05:
    #             grid.state = 'inactive'
        
    #     # Aktiviere die 2 nächstgelegenen Grids
    #     active_grids = sorted(
    #         (g for g in self.grids.values() 
    #          if g.cooldown == 0 and g.price not in self.trade_history),
    #         key=lambda g: abs(g.price - current_price)
    #     )[:2]
        
    #     for grid in active_grids:
    #         grid.state = 'active'

    # def _should_execute(self, grid: GridState, current_price: float) -> bool:
    #     """Prüft Handelsbedingungen"""
    #     if grid.state != 'active' or grid.price in self.trade_history:
    #         return False
            
    #     price_diff = abs(grid.price - current_price) / current_price
    #     min_diff = 0.0005  # Mindest 0.05% Bewegung
        
    #     if grid.side == 'sell':
    #         return (current_price >= grid.price * 1.0015 and 
    #                 price_diff > min_diff and
    #                 all(abs(grid.price - p) > self.min_price_gap 
    #                     for p in self.trade_history))
    #     else:
    #         return (current_price <= grid.price * 0.9985 and
    #                 price_diff > min_diff and
    #                 all(abs(grid.price - p) > self.min_price_gap 
    #                     for p in self.trade_history))

    def _should_execute(self, grid: GridState, current_price: float) -> bool:
        """Strikte Preisvergleichslogik"""
        if grid.state != 'active' or grid.price in self.trade_history:
            return False
            
        # Strikte Richtungsüberprüfung
        if grid.side == 'sell':
            return current_price > grid.price  # Nur wenn Preis ÜBER Grid
        else:
            return current_price < grid.price  # Nur wenn Preis UNTER Grid
        
    def _execute_trade(self, grid: GridState, candle: pd.Series):
        """Führt Trade aus und aktualisiert Zustand"""
        if grid.side == 'sell':
            # Sell-Logik
            trade_amount = min(grid.coin_reserved, self.position['coin'])
            trade_value = trade_amount * grid.price
            fee = trade_value * self.fee_rate
            
            self.position['coin'] -= trade_amount
            self.position['usdt'] += trade_value - fee
            grid.coin_reserved -= trade_amount
        else:
            # Buy-Logik
            max_usdt = self.position['usdt'] * 0.1  # Max 10% des USDT pro Trade
            trade_amount = min(
                max_usdt / (grid.price * (1 + self.fee_rate)),
                self.position['usdt'] / grid.price
            )
            fee = trade_amount * grid.price * self.fee_rate
            
            self.position['usdt'] -= trade_amount * grid.price + fee
            self.position['coin'] += trade_amount
            grid.coin_reserved += trade_amount

        # Trade protokollieren
        self.trade_log.append({
            'timestamp': candle['timestamp'],
            'type': grid.side.upper(),
            'price': grid.price,
            'amount': trade_amount,
            'fee': fee,
            'profit': (grid.price - self._get_cost_basis()) * trade_amount - fee if grid.side == 'sell' else 0,
            'inventory_slots': len([g for g in self.grids.values() if g.coin_reserved > 0])
        })
        
        # Post-Trade Updates
        self.trade_history.add(grid.price)
        grid.state = 'cooldown'
        grid.cooldown = 3
        grid.trade_count += 1

    def _get_cost_basis(self) -> float:
        """Durchschnittliche Kaufkosten der Coins"""
        buy_trades = [t for t in self.trade_log if t['type'] == 'BUY']
        if not buy_trades:
            return 0.0
        total_cost = sum(t['price'] * t['amount'] for t in buy_trades)
        total_amount = sum(t['amount'] for t in buy_trades)
        return total_cost / total_amount if total_amount > 0 else 0.0
    
# Wrapper function must be at MODULE LEVEL (not in the class)
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
        'bot_version': 'StrictGridBot v15.1'
    }