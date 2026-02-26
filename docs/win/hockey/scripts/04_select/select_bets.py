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

MIN_EDGE_PCT = 0.03
ML_MIN_PROB = 0.33
TOTAL_MIN_PROB = 0.45


def valid_edge(edge_pct):
    return pd.notna(edge_pct) and edge_pct >= MIN_EDGE_PCT


def main():
    with open(ERROR_LOG, "w") as log:

        log.write("=== NHL SELECT BETS RUN (STRICT) ===\n")
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

                selections = {}

                ml_df = None
                pl_df = None
                total_df = None

                ml_path = INPUT_DIR / f"{slate_key}_NHL_moneyline.csv"
                if ml_path.exists():
                    ml_df = pd.read_csv(ml_path)

                pl_path = INPUT_DIR / f"{slate_key}_NHL_puck_line.csv"
                if pl_path.exists():
                    pl_df = pd.read_csv(pl_path)

                total_path = INPUT_DIR / f"{slate_key}_NHL_total.csv"
                if total_path.exists():
                    total_df = pd.read_csv(total_path)

                # =========================
                # MONEYLINE
                # =========================
                if ml_df is not None:
                    for _, row in ml_df.iterrows():
                        game_id = row["game_id"]

                        for side in ["home", "away"]:
                            edge_pct = row.get(f"{side}_edge_pct")
                            edge_dec = row.get(f"{side}_edge_decimal")
                            prob = row.get(f"{side}_prob")

                            if not valid_edge(edge_pct):
                                continue
                            if pd.isna(prob) or prob < ML_MIN_PROB:
                                continue

                            sel = {
                                "game_id": game_id,
                                "take_bet": f"{side}_moneyline",
                                "take_bet_prob": prob,
                                "take_bet_edge_decimal": edge_dec,
                                "take_bet_edge_pct": edge_pct,
                                "take_team": row.get(f"{side}_team"),
                                "take_odds": row.get(f"{side}_juiced_american_moneyline"),
                                "value": row.get(f"{side}_prob"),
                            }

                            selections.setdefault(game_id, {})["ml"] = sel

                # =========================
                # PUCK LINE
                # =========================
                if pl_df is not None:
                    for _, row in pl_df.iterrows():
                        game_id = row["game_id"]

                        for side in ["home", "away"]:
                            puck_line = row.get(f"{side}_puck_line")
                            edge_pct = row.get(f"{side}_edge_pct")
                            edge_dec = row.get(f"{side}_edge_decimal")

                            if pd.isna(puck_line) or puck_line <= 0:
                                continue
                            if not valid_edge(edge_pct):
                                continue

                            sel = {
                                "game_id": game_id,
                                "take_bet": f"{side}_puck_line",
                                "take_bet_prob": row.get(f"{side}_prob"),
                                "take_bet_edge_decimal": edge_dec,
                                "take_bet_edge_pct": edge_pct,
                                "take_team": row.get(f"{side}_team"),
                                "take_odds": row.get(f"{side}_juiced_american_puck_line"),
                                "value": row.get(f"{side}_puck_line"),
                            }

                            selections.setdefault(game_id, {})["pl"] = sel

                # =========================
                # TOTALS
                # =========================
                if total_df is not None:
                    for _, row in total_df.iterrows():
                        game_id = row["game_id"]

                        for side in ["over", "under"]:
                            edge_pct = row.get(f"{side}_edge_pct")
                            edge_dec = row.get(f"{side}_edge_decimal")
                            prob = row.get(f"juiced_total_{side}_prob")

                            if not valid_edge(edge_pct):
                                continue
                            if pd.isna(prob) or prob < TOTAL_MIN_PROB:
                                continue

                            sel = {
                                "game_id": game_id,
                                "take_bet": f"{side}_total",
                                "take_bet_prob": prob,
                                "take_bet_edge_decimal": edge_dec,
                                "take_bet_edge_pct": edge_pct,
                                "take_team": side,
                                "take_odds": row.get(f"juiced_total_{side}_american"),
                                "value": row.get("total"),
                            }

                            selections.setdefault(game_id, {})["total"] = sel

                # =========================
                # FINAL OUTPUT
                # =========================
                final_rows = []

                for game_id, markets in selections.items():

                    ml_pl_choice = None

                    if "pl" in markets:
                        ml_pl_choice = markets["pl"]
                    elif "ml" in markets:
                        ml_pl_choice = markets["ml"]

                    if ml_pl_choice:
                        final_rows.append(ml_pl_choice)

                    if "total" in markets:
                        final_rows.append(markets["total"])

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
