# main.py – Debug-Test für GridBot
# Version: 1.0 – 2025-07-17 22:25

import pandas as pd
from services.bot import simulate_grid_bot

# Pfad zur Testdaten-Datei
csv_path = "testdata.csv"  # z. B. Kerzen mit Spalten: timestamp, open, high, low, close

# Parameter
total_investment = 1000
lower_price = 100000
upper_price = 120000
num_grids = 20
grid_mode = "geometric"  # oder "arithmetic"
fee_rate = 0.001

# Daten laden
df = pd.read_csv(csv_path)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Simulation starten
results = simulate_grid_bot(df, total_investment, lower_price, upper_price,
                            num_grids, grid_mode, fee_rate)

# Ergebnisse anzeigen
print("Finale Position:", results['final_position'])
print("Profit (USDT):", results['profit_usdt'])
print("Trades insgesamt:", results['num_trades'])

# Optional: Details ausgeben
for trade in results['trade_log'][-5:]:
    print(trade)
