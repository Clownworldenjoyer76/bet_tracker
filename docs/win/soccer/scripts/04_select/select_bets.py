#!/usr/bin/env python3
# docs/win/soccer/scripts/04_select/select_bets.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback
import re

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
# CRITERIA CONFIG
# =========================
MIN_EDGE_PCT = 0.03
MIN_PROB = 0.20

DRAW_MIN_EDGE_PCT = 0.05
DRAW_MIN_PROB = 0.22
DRAW_DOMINANCE_MARGIN = 0.03

KELLY_FRACTION = 0.25

# =========================
# HELPERS
# =========================
def parse_match_time(time_str):
    if pd.isna(time_str):
        return None

    time_str = str(time_str).strip()

    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return datetime.strptime(time_str, fmt)
        except Exception:
            pass

    return None


def calculate_kelly(prob, odds, fraction=0.25):
    if pd.isna(prob) or pd.isna(odds):
        return 0

    if odds <= 1 or prob <= 0:
        return 0

    f_star = (odds * prob - 1) / (odds - 1)
    return max(0, f_star * fraction)


def get_result_prob(row, side):
    return row.get(f"{side}_prob")


def get_total_prob(row, side):
    if side == "over25":
        return row.get("over25_prob")

    if side == "under25":
        over_prob = row.get("over25_prob")

        if pd.isna(over_prob):
            return None

        return 1 - over_prob

    return None


def build_selection(row, market_name, take_bet, edge_pct, prob):

    odds_decimal = row.get(f"{take_bet}_dk_decimal")
    odds_american = row.get(f"{take_bet}_american")

    stake = calculate_kelly(prob, odds_decimal, KELLY_FRACTION)

    # =========================
    # NEW SAFETY FILTER
    # Reject bets with non-positive Kelly
    # =========================
    if stake <= 0:
        return None

    return {
        "league": row.get("league"),
        "market": market_name,
        "match_date": row.get("match_date"),
        "match_time": row.get("match_time"),
        "home_team": row.get("home_team"),
        "away_team": row.get("away_team"),
        "game_id": row.get("game_id"),
        "take_bet": take_bet,
        "odds_american": odds_american,
        "odds_decimal": odds_decimal,
        "edge_pct": edge_pct,
        "kelly_stake_pct": round(stake * 100, 2),
        "expected_goals": row.get("expected_total_goals", "")
    }


def select_best_result_side(row, columns):

    result_candidates = {}

    for side in ["home", "draw", "away"]:

        edge_col = f"{side}_edge_pct"
        prob_col = f"{side}_prob"

        if edge_col not in columns or prob_col not in columns:
            continue

        edge_val = row.get(edge_col)
        prob_val = row.get(prob_col)

        if pd.isna(edge_val) or pd.isna(prob_val):
            continue

        if edge_val >= MIN_EDGE_PCT and prob_val >= MIN_PROB:
            result_candidates[side] = edge_val

    if not result_candidates:
        return None

    best_side = max(result_candidates, key=result_candidates.get)
    best_edge = result_candidates[best_side]

    if best_side == "draw":

        all_edges = {
            side: row.get(f"{side}_edge_pct")
            for side in ["home", "draw", "away"]
        }

        sorted_vals = sorted(
            [v for v in all_edges.values() if not pd.isna(v)],
            reverse=True
        )

        second_best = sorted_vals[1] if len(sorted_vals) > 1 else -999

        draw_prob = row.get("draw_prob", 0)

        if (
            best_edge < DRAW_MIN_EDGE_PCT
            or pd.isna(draw_prob)
            or draw_prob < DRAW_MIN_PROB
            or (best_edge - second_best) < DRAW_DOMINANCE_MARGIN
        ):

            non_draw = {
                k: v for k, v in result_candidates.items() if k != "draw"
            }

            if not non_draw:
                return None

            best_side = max(non_draw, key=non_draw.get)
            best_edge = non_draw[best_side]

    prob = get_result_prob(row, best_side)

    if pd.isna(prob):
        return None

    return build_selection(
        row=row,
        market_name="result",
        take_bet=best_side,
        edge_pct=best_edge,
        prob=prob
    )


def select_best_total(row, columns):

    total_candidates = {}

    for side in ["over25", "under25"]:

        edge_col = f"{side}_edge_pct"

        if edge_col not in columns:
            continue

        edge_val = row.get(edge_col)
        prob_val = get_total_prob(row, side)

        if pd.isna(edge_val) or prob_val is None or pd.isna(prob_val):
            continue

        if edge_val >= MIN_EDGE_PCT and prob_val >= MIN_PROB:
            total_candidates[side] = edge_val

    if not total_candidates:
        return None

    best_total = max(total_candidates, key=total_candidates.get)
    best_edge = total_candidates[best_total]

    prob = get_total_prob(row, best_total)

    if prob is None or pd.isna(prob):
        return None

    return build_selection(
        row=row,
        market_name="total",
        take_bet=best_total,
        edge_pct=best_edge,
        prob=prob
    )


# =========================
# MAIN
# =========================
def main():

    with open(ERROR_LOG, "a") as log:

        log.write(f"=== SELECT BETS RUN: {datetime.utcnow().isoformat()}Z ===\n")

        try:

            input_files = sorted(INPUT_DIR.glob("soccer_*.csv"))

            if not input_files:
                log.write("No input files found.\n")
                return

            for input_path in input_files:

                df = pd.read_csv(input_path)
                columns = set(df.columns)

                selections = []

                for _, row in df.iterrows():

                    result_selection = select_best_result_side(row, columns)

                    if result_selection:
                        selections.append(result_selection)

                    total_selection = select_best_total(row, columns)

                    if total_selection:
                        selections.append(total_selection)

                output_path = OUTPUT_DIR / input_path.name

                if selections:

                    sel_df = pd.DataFrame(selections)

                    sel_df["_sort_time"] = sel_df["match_time"].apply(parse_match_time)

                    sel_df = sel_df.sort_values(
                        by=["match_date", "_sort_time", "home_team", "away_team", "market"],
                        na_position="last"
                    ).drop(columns=["_sort_time"])

                    sel_df.to_csv(output_path, index=False)

                    log.write(f"Wrote {len(selections)} plays to {output_path}\n")

                else:

                    log.write(f"No plays qualified for {input_path.name}\n")

        except Exception as e:

            log.write(f"\nCRITICAL ERROR: {str(e)}\n{traceback.format_exc()}\n")


        # =========================
        # CREATE REQUIRED RESULTS INPUT FILES
        # docs/win/soccer/04_select/{YYYY_MM_DD}*soccer*.csv
        # =========================
        try:

            date_groups = {}

            for csv_file in OUTPUT_DIR.glob("*.csv"):

                match = re.search(r"(\d{4}_\d{2}_\d{2})", csv_file.name)

                if not match:
                    continue

                date_str = match.group(1)

                date_groups.setdefault(date_str, []).append(csv_file)

            for date_str, files in date_groups.items():

                dfs = []

                for f in files:
                    try:
                        df = pd.read_csv(f)
                        if not df.empty:
                            dfs.append(df)
                    except Exception:
                        continue

                if not dfs:
                    continue

                combined = pd.concat(dfs, ignore_index=True)

                out_path = OUTPUT_DIR / f"{date_str}_soccer.csv"

                combined.to_csv(out_path, index=False)

                log.write(f"Created results input file {out_path}\n")

        except Exception as e:

            log.write(f"\nERROR BUILDING REQUIRED SOCCER RESULTS FILES: {str(e)}\n{traceback.format_exc()}\n")


if __name__ == "__main__":
    main()
