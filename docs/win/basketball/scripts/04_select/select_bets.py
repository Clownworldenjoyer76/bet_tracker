#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    for csv_file in INPUT_DIR.glob("*.csv"):
        df = pd.read_csv(csv_file)
        fname = csv_file.name.lower()
        league = "NBA" if "nba" in fname else "NCAAB"
        results = []

        for _, row in df.iterrows():
            # --- TOTALS ---
            if "total" in fname:
                for side in ["over", "under"]:
                    edge = row.get(f"{side}_edge_decimal", 0)
                    line = pd.to_numeric(row.get("total"), errors='coerce')
                    diff = abs(pd.to_numeric(row.get("total_diff"), errors='coerce'))
                    
                    if league == "NBA":
                        if edge >= 0.12:
                            results.append(row)
                    
                    elif league == "NCAAB":
                        # Apply Custom NCAAB Totals Over Logic
                        if side == "over":
                            if line < 150:
                                if edge >= 0.40 and diff >= 4:
                                    results.append(row)
                            elif line > 150:
                                if diff >= 2:
                                    results.append(row)
                        # Keep original logic for NCAAB Under
                        else:
                            if edge >= 0.08:
                                results.append(row)

            # --- SPREADS ---
            elif "spread" in fname:
                for side in ["home", "away"]:
                    edge = row.get(f"{side}_edge_decimal", 0)
                    line = abs(float(row.get(f"{side}_spread", 0)))
                    if league == "NBA" and edge >= 0.06 and line <= 10.5:
                        results.append(row)
                    elif league == "NCAAB" and edge >= 0.07 and line <= 12.5:
                        results.append(row)

            # --- MONEYLINE ---
            elif "moneyline" in fname:
                for side in ["home", "away"]:
                    edge, prob = row.get(f"{side}_edge_decimal", 0), row.get(f"{side}_prob", 0)
                    odds = pd.to_numeric(row.get(f"{side}_juice_odds"), errors='coerce')
                    if league == "NBA":
                        if odds <= 100 and edge >= 0.05 and prob >= 0.58: results.append(row)
                        elif odds > 100 and edge >= 0.05 and prob >= 0.42: results.append(row)
                    elif league == "NCAAB":
                        if edge >= 0.06 and prob >= 0.60:
                            results.append(row)

        if results:
            pd.DataFrame(results).drop_duplicates().to_csv(OUTPUT_DIR / csv_file.name, index=False)

if __name__ == "__main__":
    main()
