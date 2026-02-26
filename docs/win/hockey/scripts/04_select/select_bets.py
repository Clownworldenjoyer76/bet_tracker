#!/usr/bin/env python3
# docs/win/hockey/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/hockey/03_edges")
OUTPUT_DIR = Path("docs/win/hockey/04_select")
ERROR_DIR = Path("docs/win/hockey/errors/04_select")
ERROR_LOG = ERROR_DIR / "select_bets.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# RULES
# =========================

MIN_EDGE_PCT = 0.03

ML_MIN_PROB = 0.33
TOTAL_MIN_PROB = 0.45

# =========================
# HELPERS
# =========================

def valid_edge(edge_pct):
    return pd.notna(edge_pct) and edge_pct >= MIN_EDGE_PCT


def select_side(row, side, market_type, min_prob, prob_column=None):
    edge_pct = row.get(f"{side}_edge_pct")
    edge_dec = row.get(f"{side}_edge_decimal")

    if prob_column:
        model_prob = row.get(prob_column)
    else:
        model_prob = row.get(f"{side}_prob")

    if not valid_edge(edge_pct):
        return None

    if pd.isna(model_prob) or model_prob < min_prob:
        return None

    return {
        "game_id": row["game_id"],
        "take_bet": f"{side}_{market_type}",
        "take_bet_prob": model_prob,
        "take_bet_edge_decimal": edge_dec,
        "take_bet_edge_pct": edge_pct,
    }


def select_puck_side(row, side):
    """
    Only allow +1.5 puck lines.
    No probability floor (Option A).
    """
    puck_line = row.get(f"{side}_puck_line")

    if pd.isna(puck_line) or puck_line <= 0:
        return None

    edge_pct = row.get(f"{side}_edge_pct")
    edge_dec = row.get(f"{side}_edge_decimal")
    model_prob = row.get(f"{side}_prob")

    if not valid_edge(edge_pct):
        return None

    return {
        "game_id": row["game_id"],
        "take_bet": f"{side}_puck_line",
        "take_bet_prob": model_prob,
        "take_bet_edge_decimal": edge_dec,
        "take_bet_edge_pct": edge_pct,
    }


# =========================
# MAIN
# =========================

def main():
    with open(ERROR_LOG, "w") as log:

        log.write("=== NHL SELECT BETS RUN (STRICT) ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        try:

            moneyline_files = sorted(INPUT_DIR.glob("*_NHL_moneyline.csv"))
            puckline_files = sorted(INPUT_DIR.glob("*_NHL_puck_line.csv"))
            total_files = sorted(INPUT_DIR.glob("*_NHL_total.csv"))

            if not (moneyline_files or puckline_files or total_files):
                log.write("No input files found.\n")
                return

            all_files = moneyline_files + puckline_files + total_files
            slates = {}

            for f in all_files:
                slate_key = f.name.replace("_NHL_moneyline.csv", "") \
                                  .replace("_NHL_puck_line.csv", "") \
                                  .replace("_NHL_total.csv", "")
                slates.setdefault(slate_key, []).append(f)

            for slate_key in slates.keys():

                selections = {}

                # ---- MONEYLINE ----
                ml_path = INPUT_DIR / f"{slate_key}_NHL_moneyline.csv"
                if ml_path.exists():
                    df = pd.read_csv(ml_path)

                    for _, row in df.iterrows():
                        game_id = row["game_id"]

                        home_sel = select_side(row, "home", "moneyline", ML_MIN_PROB)
                        away_sel = select_side(row, "away", "moneyline", ML_MIN_PROB)

                        best_ml = None
                        if home_sel and away_sel:
                            best_ml = max([home_sel, away_sel],
                                          key=lambda x: x["take_bet_edge_pct"])
                        elif home_sel:
                            best_ml = home_sel
                        elif away_sel:
                            best_ml = away_sel

                        if best_ml:
                            selections.setdefault(game_id, {})["ml"] = best_ml

                # ---- PUCK LINE ----
                pl_path = INPUT_DIR / f"{slate_key}_NHL_puck_line.csv"
                if pl_path.exists():
                    df = pd.read_csv(pl_path)

                    for _, row in df.iterrows():
                        game_id = row["game_id"]

                        home_sel = select_puck_side(row, "home")
                        away_sel = select_puck_side(row, "away")

                        best_pl = None
                        if home_sel and away_sel:
                            best_pl = max([home_sel, away_sel],
                                          key=lambda x: x["take_bet_edge_pct"])
                        elif home_sel:
                            best_pl = home_sel
                        elif away_sel:
                            best_pl = away_sel

                        if best_pl:
                            selections.setdefault(game_id, {})["pl"] = best_pl

                # ---- TOTALS ----
                total_path = INPUT_DIR / f"{slate_key}_NHL_total.csv"
                if total_path.exists():
                    df = pd.read_csv(total_path)

                    for _, row in df.iterrows():
                        game_id = row["game_id"]

                        over_sel = select_side(
                            row,
                            "over",
                            "total",
                            TOTAL_MIN_PROB,
                            prob_column="juiced_total_over_prob"
                        )

                        under_sel = select_side(
                            row,
                            "under",
                            "total",
                            TOTAL_MIN_PROB,
                            prob_column="juiced_total_under_prob"
                        )

                        best_total = None
                        if over_sel and under_sel:
                            best_total = max([over_sel, under_sel],
                                             key=lambda x: x["take_bet_edge_pct"])
                        elif over_sel:
                            best_total = over_sel
                        elif under_sel:
                            best_total = under_sel

                        if best_total:
                            selections.setdefault(game_id, {})["total"] = best_total

                # ---- FINAL DECISION PER GAME ----
                final_rows = []

                for game_id, markets in selections.items():

                    # PRIORITY: +1.5 puck line beats moneyline
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
