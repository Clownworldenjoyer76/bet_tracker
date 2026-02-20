#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/soccer/03_edges")
OUTPUT_DIR = Path("docs/win/soccer/04_select")
ERROR_DIR = Path("docs/win/soccer/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# CONFIG
# =========================

MIN_EDGE_PCT = 0.02      # require at least 2% edge
DRAW_PENALTY = 0.015     # penalize draw edges to reduce frequency

# =========================
# CORE
# =========================

def main():

    with open(ERROR_LOG, "w") as log:

        log.write("=== SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:

            input_files = sorted(INPUT_DIR.glob("soccer_*.csv"))

            if not input_files:
                log.write("No input files found.\n")
                return

            for input_path in input_files:

                df = pd.read_csv(input_path)

                required_cols = [
                    "game_id",
                    "home_prob", "draw_prob", "away_prob",
                    "home_edge_decimal", "draw_edge_decimal", "away_edge_decimal",
                    "home_edge_pct", "draw_edge_pct", "away_edge_pct"
                ]

                for col in required_cols:
                    if col not in df.columns:
                        raise ValueError(f"Missing column: {col}")

                selections = []

                for _, row in df.iterrows():

                    sides = ["home", "draw", "away"]

                    best_side = None
                    best_score = -999

                    for side in sides:

                        edge_pct = row[f"{side}_edge_pct"]
                        edge_dec = row[f"{side}_edge_decimal"]

                        if pd.isna(edge_pct) or pd.isna(edge_dec):
                            continue

                        if edge_pct < MIN_EDGE_PCT:
                            continue

                        score = edge_pct

                        # penalize draw
                        if side == "draw":
                            score -= DRAW_PENALTY

                        if score > best_score:
                            best_score = score
                            best_side = side

                    if best_side:

                        selections.append({
                            "game_id": row["game_id"],
                            "take_bet": best_side,
                            "take_bet_prob": row[f"{best_side}_prob"],
                            "take_bet_edge_decimal": row[f"{best_side}_edge_decimal"],
                            "take_bet_edge_pct": row[f"{best_side}_edge_pct"],
                        })

                sel_df = pd.DataFrame(selections)

                output_path = OUTPUT_DIR / input_path.name
                sel_df.to_csv(output_path, index=False)

                log.write(f"Wrote {output_path}\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()
