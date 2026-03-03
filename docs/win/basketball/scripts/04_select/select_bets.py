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

                line = pd.to_numeric(row.get("total"), errors="coerce")
                proj = pd.to_numeric(row.get("total_projected_points"), errors="coerce")
                diff = abs(proj - line) if pd.notna(proj) and pd.notna(line) else 0

                for side in ["over", "under"]:

                    edge = row.get(f"{side}_edge_decimal", 0)
                    edge = float(edge) if pd.notna(edge) else 0

                    if league == "NBA":
                        if edge >= 0.14:
                            new_row = row.copy()
                            new_row["market_type"] = "total"
                            new_row["bet_side"] = side
                            new_row["line"] = line
                            results.append(new_row)

                    elif league == "NCAAB":

                        if side == "over":
                            if line < 150:
                                if edge >= 0.40 and diff >= 4:
                                    new_row = row.copy()
                                    new_row["market_type"] = "total"
                                    new_row["bet_side"] = side
                                    new_row["line"] = line
                                    results.append(new_row)
                            elif line > 150:
                                if diff >= 2:
                                    new_row = row.copy()
                                    new_row["market_type"] = "total"
                                    new_row["bet_side"] = side
                                    new_row["line"] = line
                                    results.append(new_row)

                        else:  # under
                            if edge >= 0.08:
                                new_row = row.copy()
                                new_row["market_type"] = "total"
                                new_row["bet_side"] = side
                                new_row["line"] = line
                                results.append(new_row)

            # =========================
            # SPREADS
            # =========================
            elif "spread" in fname:

                for side in ["home", "away"]:

                    edge = row.get(f"{side}_edge_decimal", 0)
                    spread = row.get(f"{side}_spread", 0)

                    edge = float(edge) if pd.notna(edge) else 0
                    spread_val = float(row.get(f"{side}_spread")) if pd.notna(row.get(f"{side}_spread")) else 0
                    spread_abs = abs(spread_val)

                    if league == "NBA":
                        if edge >= 0.08 and spread_abs <= 10.5:
                            new_row = row.copy()
                            new_row["market_type"] = "spread"
                            new_row["bet_side"] = side
                            new_row["line"] = spread_val
                            results.append(new_row)

                    elif league == "NCAAB":
                        if edge >= 0.07 and spread_abs <= 12.5:
                            new_row = row.copy()
                            new_row["market_type"] = "spread"
                            new_row["bet_side"] = side
                            new_row["line"] = spread_val
                            results.append(new_row)

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

                    if league == "NBA":

                        if odds < 0:
                            if edge >= 0.05 and prob >= 0.58:
                                new_row = row.copy()
                                new_row["market_type"] = "moneyline"
                                new_row["bet_side"] = side
                                new_row["line"] = 0
                                results.append(new_row)

                        else:
                            if edge >= 0.05 and prob >= 0.42:
                                new_row = row.copy()
                                new_row["market_type"] = "moneyline"
                                new_row["bet_side"] = side
                                new_row["line"] = 0
                                results.append(new_row)

                    elif league == "NCAAB":
                        if edge >= 0.06 and prob >= 0.60:
                            new_row = row.copy()
                            new_row["market_type"] = "moneyline"
                            new_row["bet_side"] = side
                            new_row["line"] = 0
                            results.append(new_row)

        if results:
            pd.DataFrame(results).drop_duplicates().to_csv(
                OUTPUT_DIR / csv_file.name,
                index=False
            )

if __name__ == "__main__":
    main()
