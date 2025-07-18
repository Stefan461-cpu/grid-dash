# main.py – Debug-Test für GridBot
# Version: 1.1 – 2025-07-17 22:45

import pandas as pd
from services.bot import simulate_grid_bot

# Debug-Hinweis aktivieren
import pprint
from datetime import datetime

def main():
    print(f"[{datetime.now()}] Starte GridBot-Debuglauf\n")

    # Pfad zur Testdaten-Datei
    csv_path = "testdata.csv"

    # Parameter
    total_investment = 1000
    lower_price = 100000
    upper_price = 120000
    num_grids = 20
    grid_mode = "geometric"  # oder "arithmetic"
#    grid_mode = "arithmetic"  # oder "arithmetic"
    fee_rate = 0.001

    # Daten laden
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    print(f"[{datetime.now()}] Eingelesene Kerzen: {len(df)}")
    print(df.head())

    # Simulation starten
    result = simulate_grid_bot(
        df=df,
        total_investment=total_investment,
        lower_price=lower_price,
        upper_price=upper_price,
        num_grids=num_grids,
        grid_mode=grid_mode,
        fee_rate=fee_rate
    )

    # Resultate anzeigen
    print("\nFinale Position:", result["final_position"])
    print("Profit (USDT):", result["profit_usdt"])
    print("Trades insgesamt:", len(result["trade_log"]))
    for trade in result["trade_log"]:
        pprint.pprint(trade)

if __name__ == "__main__":
    main()
