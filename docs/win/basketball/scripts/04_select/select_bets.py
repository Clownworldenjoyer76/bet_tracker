# docs/win/basketball/scripts/04_select/select_bets.py
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

                if league == "NBA":

                    edges = {
                        "over": float(row.get("over_edge_decimal",0)),
                        "under": float(row.get("under_edge_decimal",0))
                    }

                    side = max(edges, key=edges.get)
                    edge = edges[side]

                    edge_required = 0.16

                    if line <= 205 and side == "over":
                        edge_required -= 0.04

                    if line <= 205 and side == "under":
                        continue

                    if line > 245:
                        continue

                    if edge >= edge_required:
                        new_row = row.copy()
                        new_row["market_type"] = "total"
                        new_row["bet_side"] = side
                        new_row["line"] = line
                        results.append(new_row)

                elif league == "NCAAB":

                    for side in ["over", "under"]:

                        edge = row.get(f"{side}_edge_decimal", 0)
                        edge = float(edge) if pd.notna(edge) else 0

                        if side == "over":
                            if line < 150:
                                if edge >= 0.50 and diff >= 4:
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

                        else:
                            if edge >= 0.10:
                                new_row = row.copy()
                                new_row["market_type"] = "total"
                                new_row["bet_side"] = side
                                new_row["line"] = line
                                results.append(new_row)

            # =========================
            # SPREADS
            # =========================
            elif "spread" in fname:

                if league == "NBA":

                    edges = {
                        "home": float(row.get("home_edge_decimal",0)),
                        "away": float(row.get("away_edge_decimal",0))
                    }

                    side = max(edges, key=edges.get)
                    edge = edges[side]

                    if edge >= 0.10:

                        spread_val = float(row.get(f"{side}_spread"))
                        spread_abs = abs(spread_val)
                        venue = side

                        if spread_abs > 15:
                            continue

                        if spread_val <= -7.5 and venue == "home":
                            continue

                        if spread_abs <= 10.5:
                            new_row = row.copy()
                            new_row["market_type"] = "spread"
                            new_row["bet_side"] = side
                            new_row["line"] = spread_val
                            results.append(new_row)

                elif league == "NCAAB":

                    for side in ["home", "away"]:

                        edge = row.get(f"{side}_edge_decimal", 0)
                        spread = row.get(f"{side}_spread", 0)

                        edge = float(edge) if pd.notna(edge) else 0
                        spread_val = float(row.get(f"{side}_spread")) if pd.notna(row.get(f"{side}_spread")) else 0
                        spread_abs = abs(spread_val)

                        if edge >= 0.07 and spread_abs <= 20:
                            new_row = row.copy()
                            new_row["market_type"] = "spread"
                            new_row["bet_side"] = side
                            new_row["line"] = spread_val
                            results.append(new_row)

            # =========================
            # MONEYLINE
            # =========================
            elif "moneyline" in fname:

                if league == "NBA":

                    edges = {
                        "home": float(row.get("home_edge_decimal",0)),
                        "away": float(row.get("away_edge_decimal",0))
                    }

                    side = max(edges, key=edges.get)
                    edge = edges[side]

                    odds = float(row.get(f"{side}_juice_odds",0))
                    venue = side
                    fav_ud = "favorite" if odds < 0 else "underdog"

                    if fav_ud == "favorite" and venue == "home" and -180 <= odds <= -150:
                        continue

                    if fav_ud == "favorite" and odds <= -500:
                        continue

                    if fav_ud == "underdog" and odds >= 350:
                        continue

                    if fav_ud == "favorite":
                        edge_required = 0.08
                    else:
                        edge_required = 0.07

                    if fav_ud == "favorite" and venue == "home":
                        edge_required = 0.10

                    if fav_ud == "underdog" and venue == "away" and 130 <= odds <= 170:
                        edge_required = 0.06

                    if venue == "home":
                        edge_required += 0.02

                    if edge < edge_required:
                        continue

                    new_row = row.copy()
                    new_row["market_type"] = "moneyline"
                    new_row["bet_side"] = side
                    new_row["line"] = 0
                    results.append(new_row)

                elif league == "NCAAB":

                    for side in ["home", "away"]:

                        edge = row.get(f"{side}_edge_decimal", 0)
                        prob = row.get(f"{side}_prob", 0)

                        edge = float(edge) if pd.notna(edge) else 0
                        prob = float(prob) if pd.notna(prob) else 0

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
