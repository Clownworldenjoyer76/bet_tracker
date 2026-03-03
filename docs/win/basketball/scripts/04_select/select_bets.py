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

            # =========================
            # TOTALS
            # =========================
            if "total" in fname:

                for side in ["over", "under"]:

                    edge = row.get(f"{side}_edge_decimal", 0)
                    edge = float(edge) if pd.notna(edge) else 0

                    if league == "NBA":
                        if edge >= 0.12:
                            results.append(row)

                    elif league == "NCAAB":
                        if side == "over":
                            if edge >= 0.12:
                                results.append(row)
                        else:
                            if edge >= 0.08:
                                results.append(row)

            # =========================
            # SPREADS
            # =========================
            elif "spread" in fname:

                for side in ["home", "away"]:

                    edge = row.get(f"{side}_edge_decimal", 0)
                    spread = row.get(f"{side}_spread", 0)

                    edge = float(edge) if pd.notna(edge) else 0
                    spread = abs(float(spread)) if pd.notna(spread) else 0

                    if league == "NBA":
                        if edge >= 0.06 and spread <= 10.5:
                            results.append(row)

                    elif league == "NCAAB":
                        if edge >= 0.07 and spread <= 12.5:
                            results.append(row)

            # =========================
            # MONEYLINE
            # =========================
            elif "moneyline" in fname:

                for side in ["home", "away"]:

                    edge = row.get(f"{side}_edge_decimal", 0)
                    prob = row.get(f"{side}_prob", 0)
                    odds = row.get(f"{side}_juice_odds", None)

                    edge = float(edge) if pd.notna(edge) else 0
                    prob = float(prob) if pd.notna(prob) else 0
                    odds = float(odds) if pd.notna(odds) else None

                    if odds is None:
                        continue

                    # Correct favorite/dog logic
                    if league == "NBA":

                        if odds < 0:  # favorite
                            if edge >= 0.05 and prob >= 0.58:
                                results.append(row)

                        else:  # underdog
                            if edge >= 0.05 and prob >= 0.42:
                                results.append(row)

                    elif league == "NCAAB":

                        if edge >= 0.06 and prob >= 0.60:
                            results.append(row)

        if results:
            pd.DataFrame(results).drop_duplicates().to_csv(
                OUTPUT_DIR / csv_file.name,
                index=False
            )

if __name__ == "__main__":
    main()
