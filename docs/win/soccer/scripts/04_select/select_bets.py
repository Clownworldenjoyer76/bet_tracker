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
# CRITERIA CONFIG (unchanged, but no longer used for filtering)
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
        return None if pd.isna(over_prob) else 1 - over_prob

    if side == "over35":
        return row.get("over35_prob")

    if side == "under35":
        over_prob = row.get("over35_prob")
        return None if pd.isna(over_prob) else 1 - over_prob

    return None


def get_btts_prob(row, side):

    if side == "btts_yes":
        return row.get("btts_prob")

    if side == "btts_no":
        prob = row.get("btts_prob")
        return None if pd.isna(prob) else 1 - prob

    return None


# =========================
# BUILD SELECTION
# =========================
def build_selection(row, market_name, take_bet, edge_pct, prob):

    odds_decimal = row.get(f"{take_bet}_dk_decimal")
    odds_american = row.get(f"dk_{take_bet}_american")

    stake = calculate_kelly(prob, odds_decimal, KELLY_FRACTION)

    return {
        "league": "Soccer",
        "market": row.get("market"),
        "game_date": row.get("match_date"),
        "match_time": row.get("match_time"),
        "home_team": row.get("home_team"),
        "away_team": row.get("away_team"),
        "game_id": row.get("game_id"),
        "market_type": market_name,
        "take_bet": take_bet,
        "odds_american": odds_american,
        "odds_decimal": odds_decimal,
        "edge_pct": edge_pct,
        "kelly_stake_pct": round(stake * 100, 2),
        "expected_goals": row.get("expected_total_goals", "")
    }


# =========================
# RESULT (ALWAYS PICK BEST)
# =========================
def select_best_result_side(row, columns):

    candidates = {}

    for side in ["home", "draw", "away"]:

        edge = row.get(f"{side}_edge_pct")

        if pd.isna(edge):
            continue

        candidates[side] = edge

    if not candidates:
        return None

    best = max(candidates, key=candidates.get)

    prob = get_result_prob(row, best)

    return build_selection(row, "result", best, candidates[best], prob)


# =========================
# TOTAL (ALWAYS PICK BEST)
# =========================
def select_best_total(row, columns):

    candidates = {}

    for side in ["over25", "under25", "over35", "under35"]:

        edge = row.get(f"{side}_edge_pct")
        prob = get_total_prob(row, side)

        if pd.isna(edge) or prob is None:
            continue

        candidates[side] = edge

    if not candidates:
        return None

    best = max(candidates, key=candidates.get)
    prob = get_total_prob(row, best)

    return build_selection(row, "total", best, candidates[best], prob)


# =========================
# BTTS (ALWAYS PICK BEST)
# =========================
def select_best_btts(row, columns):

    candidates = {}

    for side in ["btts_yes", "btts_no"]:

        edge = row.get(f"{side}_edge_pct")
        prob = get_btts_prob(row, side)

        if pd.isna(edge) or prob is None:
            continue

        candidates[side] = edge

    if not candidates:
        return None

    best = max(candidates, key=candidates.get)
    prob = get_btts_prob(row, best)

    return build_selection(row, "btts", best, candidates[best], prob)


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

                    r = select_best_result_side(row, columns)
                    if r:
                        selections.append(r)

                    t = select_best_total(row, columns)
                    if t:
                        selections.append(t)

                    b = select_best_btts(row, columns)
                    if b:
                        selections.append(b)

                if not selections:
                    log.write(f"No plays for {input_path.name}\n")
                    continue

                sel_df = pd.DataFrame(selections)

                sel_df["_sort_time"] = sel_df["match_time"].apply(parse_match_time)

                sel_df = sel_df.sort_values(
                    by=["game_date", "_sort_time", "home_team", "away_team", "market_type"],
                    na_position="last"
                ).drop(columns=["_sort_time"])

                output_path = OUTPUT_DIR / input_path.name

                sel_df.to_csv(output_path, index=False)

                log.write(f"Wrote {len(sel_df)} rows to {output_path}\n")

        except Exception as e:

            log.write(f"\nCRITICAL ERROR: {str(e)}\n{traceback.format_exc()}\n")


        # =========================
        # DAILY COMBINED
        # =========================
        try:

            date_groups = {}

            for csv_file in OUTPUT_DIR.glob("soccer_*.csv"):

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
                    except:
                        continue

                if not dfs:
                    continue

                combined = pd.concat(dfs, ignore_index=True)

                combined = combined.drop_duplicates(
                    subset=["game_date", "home_team", "away_team", "market_type"]
                )

                out_path = OUTPUT_DIR / f"{date_str}_soccer.csv"

                combined.to_csv(out_path, index=False)

                log.write(f"Created {out_path}\n")

        except Exception as e:

            log.write(f"\nERROR BUILDING DAILY: {str(e)}\n{traceback.format_exc()}\n")


if __name__ == "__main__":
    main()
