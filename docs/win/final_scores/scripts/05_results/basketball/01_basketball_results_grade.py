# docs/win/final_scores/scripts/05_results/basketball/01_basketball_results_grade.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

BASE = Path("docs/win/basketball")
SELECT_DIR = BASE / "04_select/daily_slate"

NBA_SCORE_DIR = Path("docs/win/final_scores/results/nba/final_scores")
NCAAB_SCORE_DIR = Path("docs/win/final_scores/results/ncaab/final_scores")

NBA_OUTPUT = Path("docs/win/final_scores/results/nba/graded")
NCAAB_OUTPUT = Path("docs/win/final_scores/results/ncaab/graded")

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def determine_outcome(row):
    market = str(row["market_type"]).lower()
    side = str(row["bet_side"]).lower()

    away = float(row["away_score"])
    home = float(row["home_score"])

    if market == "moneyline":
        if away == home:
            return "Push"
        return "Win" if (home > away and side == "home") or (away > home and side == "away") else "Loss"

    if market == "spread":
        line = float(row["line"])
        diff = (home + line - away) if side == "home" else (away + line - home)

        if abs(diff) < 1e-9:
            return "Push"
        return "Win" if diff > 0 else "Loss"

    if market == "total":
        total = away + home
        line = float(row["line"])

        if abs(total - line) < 1e-9:
            return "Push"

        return "Win" if (total > line and side == "over") or (total < line and side == "under") else "Loss"

    return "Unknown"


def clean_merge_columns(df):
    for col in list(df.columns):
        if col.endswith("_x"):
            df[col[:-2]] = df[col]
        elif col.endswith("_y"):
            base = col[:-2]
            if base not in df.columns:
                df[base] = df[col]

    df = df.drop(columns=[c for c in df.columns if c.endswith("_x") or c.endswith("_y")], errors="ignore")
    return df


def rebuild_selected_edge(df):

    # detect which system exists
    has_decimal = "home_ml_edge_decimal" in df.columns
    has_standard = "home_ml_edge" in df.columns

    def pick_edge(row):

        market = row["market_type"]
        side = row["bet_side"]

        # ========================
        # MONEYLINE
        # ========================
        if market == "moneyline":

            if has_decimal:
                if side == "home":
                    return row["home_ml_edge_decimal"]
                elif side == "away":
                    return row["away_ml_edge_decimal"]

            if has_standard:
                if side == "home":
                    return row["home_ml_edge"]
                elif side == "away":
                    return row["away_ml_edge"]

        # ========================
        # SPREAD
        # ========================
        if market == "spread":

            if has_decimal:
                if side == "home":
                    return row["home_spread_edge_decimal"]
                elif side == "away":
                    return row["away_spread_edge_decimal"]

            if has_standard:
                if side == "home":
                    return row["home_spread_edge"]
                elif side == "away":
                    return row["away_spread_edge"]

        # ========================
        # TOTAL
        # ========================
        if market == "total":

            if has_decimal:
                if side == "over":
                    return row["over_edge_decimal"]
                elif side == "under":
                    return row["under_edge_decimal"]

            if has_standard:
                if side == "over":
                    return row["over_edge"]
                elif side == "under":
                    return row["under_edge"]

        return None

    df["selected_edge"] = df.apply(pick_edge, axis=1)

    return df


def grade_league(league):

    score_dir = NBA_SCORE_DIR if league == "NBA" else NCAAB_SCORE_DIR
    output_dir = NBA_OUTPUT if league == "NBA" else NCAAB_OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)

    if league == "NBA":
        files = list(SELECT_DIR.glob("*nba*.csv"))
    else:
        files = list(SELECT_DIR.glob("*ncaab*.csv"))

    all_results = []

    for file in files:
        df = pd.read_csv(file)

        for date, sub in df.groupby("game_date"):

            score_file = score_dir / f"{date}_final_scores_{league}.csv"

            if not score_file.exists():
                continue

            scores = pd.read_csv(score_file)

            merged = pd.merge(
                sub,
                scores,
                on=["away_team", "home_team", "game_date"],
                how="inner"
            )

            merged = clean_merge_columns(merged)
            merged = rebuild_selected_edge(merged)

            merged["bet_result"] = merged.apply(determine_outcome, axis=1)

            all_results.append(merged)

    if all_results:
        final = pd.concat(all_results, ignore_index=True)
        final.to_csv(output_dir / f"{league}_final.csv", index=False)


def main():
    grade_league("NBA")
    grade_league("NCAAB")
    print("Grading complete.")


if __name__ == "__main__":
    main()
