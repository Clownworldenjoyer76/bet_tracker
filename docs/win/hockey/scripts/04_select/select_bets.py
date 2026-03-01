#!/usr/bin/env python3
# docs/win/hockey/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

INPUT_DIR = Path("docs/win/hockey/03_edges")
OUTPUT_DIR = Path("docs/win/hockey/04_select")
ERROR_DIR = Path("docs/win/hockey/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

ML_MIN_EDGE_PCT = 0.03
TOTAL_MIN_EDGE_PCT = 0.03

ML_MIN_PROB = 0.33
TOTAL_MIN_PROB = 0.45


def valid_edge(edge_pct, threshold):
    return pd.notna(edge_pct) and edge_pct >= threshold


def main():
    with open(ERROR_LOG, "w") as log:

        log.write("=== NHL SELECT BETS RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:

            moneyline_files = sorted(INPUT_DIR.glob("*_NHL_moneyline.csv"))
            puckline_files = sorted(INPUT_DIR.glob("*_NHL_puck_line.csv"))
            total_files = sorted(INPUT_DIR.glob("*_NHL_total.csv"))

            all_files = moneyline_files + puckline_files + total_files
            slates = {}

            for f in all_files:
                slate_key = f.name.replace("_NHL_moneyline.csv", "") \
                                  .replace("_NHL_puck_line.csv", "") \
                                  .replace("_NHL_total.csv", "")
                slates.setdefault(slate_key, []).append(f)

            for slate_key in slates.keys():

                final_rows = []

                ml_path = INPUT_DIR / f"{slate_key}_NHL_moneyline.csv"
                pl_path = INPUT_DIR / f"{slate_key}_NHL_puck_line.csv"
                total_path = INPUT_DIR / f"{slate_key}_NHL_total.csv"

                ml_df = pd.read_csv(ml_path) if ml_path.exists() else None
                pl_df = pd.read_csv(pl_path) if pl_path.exists() else None
                total_df = pd.read_csv(total_path) if total_path.exists() else None

                game_ids = set()

                if ml_df is not None:
                    game_ids.update(ml_df["game_id"].unique())
                if pl_df is not None:
                    game_ids.update(pl_df["game_id"].unique())
                if total_df is not None:
                    game_ids.update(total_df["game_id"].unique())

                for game_id in game_ids:

                    puck_selected = None
                    ml_selected = None
                    total_selected = None

                    # =====================
                    # PUCK LINE CHECK
                    # =====================
                    if pl_df is not None:
                        game_pl = pl_df[pl_df["game_id"] == game_id]

                        for _, row in game_pl.iterrows():
                            for side in ["home", "away"]:
                                puck_line = row.get(f"{side}_puck_line")
                                edge_pct = row.get(f"{side}_edge_pct")

                                if pd.isna(puck_line) or puck_line <= 0:
                                    continue
                                if pd.isna(edge_pct) or edge_pct <= 0:
                                    continue

                                puck_selected = {
                                    "game_id": game_id,
                                    "take_bet": f"{side}_puck_line",
                                    "take_bet_prob": row.get(f"{side}_juiced_prob_puck_line"),
                                    "take_bet_edge_decimal": row.get(f"{side}_edge_decimal"),
                                    "take_bet_edge_pct": edge_pct,
                                    "take_team": row.get(f"{side}_team"),
                                    "take_odds": row.get(f"{side}_juiced_american_puck_line"),
                                    "value": puck_line,
                                }
                                break
                            if puck_selected:
                                break

                    # =====================
                    # MONEYLINE CHECK
                    # =====================
                    if ml_df is not None:
                        game_ml = ml_df[ml_df["game_id"] == game_id]

                        for _, row in game_ml.iterrows():
                            for side in ["home", "away"]:
                                edge_pct = row.get(f"{side}_edge_pct")
                                prob = row.get(f"{side}_prob")

                                if not valid_edge(edge_pct, ML_MIN_EDGE_PCT):
                                    continue
                                if pd.isna(prob) or prob < ML_MIN_PROB:
                                    continue

                                ml_selected = {
                                    "game_id": game_id,
                                    "take_bet": f"{side}_moneyline",
                                    "take_bet_prob": prob,
                                    "take_bet_edge_decimal": row.get(f"{side}_edge_decimal"),
                                    "take_bet_edge_pct": edge_pct,
                                    "take_team": row.get(f"{side}_team"),
                                    "take_odds": row.get(f"{side}_juiced_american_moneyline"),
                                    "value": prob,
                                }
                                break
                            if ml_selected:
                                break

                    # =====================
                    # TOTAL CHECK
                    # =====================
                    if total_df is not None:
                        game_total = total_df[total_df["game_id"] == game_id]

                        for _, row in game_total.iterrows():
                            for side in ["over", "under"]:
                                edge_pct = row.get(f"{side}_edge_pct")
                                prob = row.get(f"juiced_total_{side}_prob")

                                if not valid_edge(edge_pct, TOTAL_MIN_EDGE_PCT):
                                    continue
                                if pd.isna(prob) or prob < TOTAL_MIN_PROB:
                                    continue

                                total_selected = {
                                    "game_id": game_id,
                                    "take_bet": f"{side}_total",
                                    "take_bet_prob": prob,
                                    "take_bet_edge_decimal": row.get(f"{side}_edge_decimal"),
                                    "take_bet_edge_pct": edge_pct,
                                    "take_team": side,
                                    "take_odds": row.get(f"juiced_total_{side}_american"),
                                    "value": row.get("total"),
                                }
                                break
                            if total_selected:
                                break

                    # =====================
                    # APPEND RESULTS (Independent)
                    # =====================
                    if puck_selected:
                        final_rows.append(puck_selected)

                    if ml_selected:
                        final_rows.append(ml_selected)

                    if total_selected:
                        final_rows.append(total_selected)

                out_df = pd.DataFrame(final_rows)
                output_path = OUTPUT_DIR / f"{slate_key}_NHL.csv"
                out_df.to_csv(output_path, index=False)

                log.write(f"Wrote {output_path} | rows={len(out_df)}\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())


if __name__ == "__main__":
    main()
