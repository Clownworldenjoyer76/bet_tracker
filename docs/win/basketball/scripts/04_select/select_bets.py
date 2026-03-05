#!/usr/bin/env python3
# docs/win/basketball/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime

# =========================
# LOGGER UTILITY
# =========================

def audit(log_path, stage, status, msg="", df=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a") as f:
        f.write(f"\n[{ts}] [{stage}] {status}\n")
        if msg:
            f.write(f"  MSG: {msg}\n")
        if df is not None and isinstance(df, pd.DataFrame):
            f.write(f"  STATS: {len(df)} rows | {len(df.columns)} cols\n")
            f.write(f"  SAMPLE:\n{df.head(3).to_string(index=False)}\n")
        f.write("-" * 40 + "\n")


# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/03_edges")
OUTPUT_DIR = Path("docs/win/basketball/04_select")
ERROR_DIR = Path("docs/win/basketball/errors/04_select")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = ERROR_DIR / "select_bets_audit.txt"


# =========================
# MAIN
# =========================

def main():

    all_candidates = []

    for csv_file in INPUT_DIR.glob("*.csv"):

        df = pd.read_csv(csv_file)
        fname = csv_file.name.lower()
        league = "NBA" if "nba" in fname else "NCAAB"

        for _, row in df.iterrows():

            game_key = (
                row.get("game_date"),
                row.get("away_team"),
                row.get("home_team")
            )

            # =========================
            # TOTAL FILE
            # =========================

            if "total" in fname:

                line = pd.to_numeric(row.get("total"), errors="coerce")
                proj = pd.to_numeric(row.get("total_projected_points"), errors="coerce")
                diff = abs(proj - line) if pd.notna(proj) and pd.notna(line) else 0

                edges = {
                    "over": float(row.get("over_edge_decimal", 0) or 0),
                    "under": float(row.get("under_edge_decimal", 0) or 0)
                }

                for side, edge in edges.items():

                    odds = float(row.get(f"total_{side}_juice_odds", 0) or 0)
                    if odds <= -300:
                        continue

                    # =========================
                    # NCAAB TOTAL
                    # =========================

                    if league == "NCAAB":

                        if edge > 0.30:
                            continue

                        if edge < 0.10:
                            continue

                        if side == "under" and pd.notna(line) and line < 140:
                            continue

                        if side == "over":
                            if line < 150 and not (edge >= 0.02 and diff >= 4):
                                continue
                            if line >= 150 and not (edge > 0.001 and diff >= 2):
                                continue

                    # =========================
                    # NBA TOTAL
                    # =========================

                    if league == "NBA":

                        edge_required = 0.07

                        if pd.notna(line) and line <= 205 and side == "over":
                            edge_required -= 0.02

                        if pd.notna(line) and line <= 205 and side == "under":
                            continue

                        if pd.notna(line) and line > 245:
                            continue

                        if diff < 3:
                            continue

                        if edge > 0.35:
                            continue

                        if edge < edge_required:
                            continue

                    new_row = row.copy()
                    new_row["market_type"] = "total"
                    new_row["bet_side"] = side
                    new_row["line"] = line
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key

                    all_candidates.append(new_row)

            # =========================
            # SPREAD FILE
            # =========================

            elif "spread" in fname:

                for side in ["home", "away"]:

                    edge = float(row.get(f"{side}_edge_decimal", 0) or 0)
                    spread = float(row.get(f"{side}_spread", 0) or 0)

                    odds = float(row.get(f"{side}_spread_juice_odds", 0) or 0)
                    if odds <= -300:
                        continue

                    # =========================
                    # NCAAB SPREAD
                    # =========================

                    if league == "NCAAB":

                        if edge > 0.30:
                            continue

                        if edge < 0.10:
                            continue

                        if side == "away" and edge < 0.10:
                            continue

                        if abs(spread) > 20:
                            continue

                    # =========================
                    # NBA SPREAD
                    # =========================

                    if league == "NBA":

                        if edge < 0.06:
                            continue

                        if abs(spread) > 15:
                            continue

                    new_row = row.copy()
                    new_row["market_type"] = "spread"
                    new_row["bet_side"] = side
                    new_row["line"] = spread
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key

                    all_candidates.append(new_row)

            # =========================
            # MONEYLINE FILE
            # =========================

            elif "moneyline" in fname:

                for side in ["home", "away"]:

                    edge = float(row.get(f"{side}_edge_decimal", 0) or 0)
                    prob = float(row.get(f"{side}_prob", 0) or 0)
                    odds = float(row.get(f"{side}_juice_odds", 0) or 0)

                    if odds <= -300:
                        continue

                    # =========================
                    # NCAAB MONEYLINE
                    # =========================

                    if league == "NCAAB":

                        if edge > 0.30:
                            continue

                        if edge < 0.10:
                            continue

                        if side == "home" and (-180 <= odds <= -150):
                            continue

                        if prob < 0.60:
                            continue

                    # =========================
                    # NBA MONEYLINE
                    # =========================

                    if league == "NBA":

                        if edge < 0.06:
                            continue

                    new_row = row.copy()
                    new_row["market_type"] = "moneyline"
                    new_row["bet_side"] = side
                    new_row["line"] = odds
                    new_row["candidate_edge"] = edge
                    new_row["game_key"] = game_key

                    all_candidates.append(new_row)

    # =========================
    # POST FILTER RULES
    # =========================

    df = pd.DataFrame(all_candidates)

    final_rows = []

    for game, g in df.groupby("game_key"):

        totals = g[g.market_type == "total"]
        sides = g[g.market_type.isin(["spread", "moneyline"])]

        chosen_total = None
        chosen_side = None

        if not totals.empty:
            chosen_total = totals.sort_values("candidate_edge", ascending=False).iloc[0]

        if not sides.empty:
            chosen_side = sides.sort_values("candidate_edge", ascending=False).iloc[0]

        if chosen_total is not None:
            final_rows.append(chosen_total)

        if chosen_side is not None:
            final_rows.append(chosen_side)

    res_df = pd.DataFrame(final_rows).drop_duplicates()

    if not res_df.empty:
        res_df.drop(columns=["candidate_edge", "game_key"], errors="ignore").to_csv(
            OUTPUT_DIR / "selected_bets.csv",
            index=False
        )

        audit(LOG_FILE, "SELECTION", "SUCCESS", msg=f"Selected {len(res_df)} bets", df=res_df)

    else:
        audit(LOG_FILE, "SELECTION", "INFO", msg="No bets selected")


if __name__ == "__main__":
    main()
