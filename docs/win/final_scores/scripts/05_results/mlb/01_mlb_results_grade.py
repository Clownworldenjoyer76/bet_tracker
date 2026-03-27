# docs/win/final_scores/scripts/05_results/mlb/01_mlb_results_grade.py
#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

SELECT_DIR = Path("docs/win/baseball/04_select")

SCORE_DIR = Path("docs/win/final_scores/results/mlb/final_scores")
OUTPUT_DIR = Path("docs/win/final_scores/results/mlb/graded")

ERROR_DIR = Path("docs/win/final_scores/errors")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def determine_outcome(row):
    market = str(row["market_type"]).lower()
    side = str(row["bet_side"]).lower()

    away = float(row["final_away_score"])
    home = float(row["final_home_score"])

    if market == "moneyline":
        if away == home:
            return "Push"
        return "Win" if (home > away and side == "home") or (away > home and side == "away") else "Loss"

    if market == "run_line":
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

    has_decimal = "home_edge_decimal_moneyline" in df.columns
    has_standard = "home_ml_edge" in df.columns

    def pick_edge(row):
        market = row["market_type"]
        side = row["bet_side"]

        if market == "moneyline":
            if has_decimal:
                if side == "home":
                    return row["home_edge_decimal_moneyline"]
                elif side == "away":
                    return row["away_edge_decimal_moneyline"]

            if has_standard:
                if side == "home":
                    return row["home_ml_edge"]
                elif side == "away":
                    return row["away_ml_edge"]

        if market == "run_line":
            if "home_edge_decimal_run_line" in row.index:
                if side == "home":
                    return row["home_edge_decimal_run_line"]
                elif side == "away":
                    return row["away_edge_decimal_run_line"]

            if "home_rl_edge" in row.index:
                if side == "home":
                    return row["home_rl_edge"]
                elif side == "away":
                    return row["away_rl_edge"]

        if market == "total":
            if "over_edge_decimal_total" in row.index:
                if side == "over":
                    return row["over_edge_decimal_total"]
                elif side == "under":
                    return row["under_edge_decimal_total"]

            if "over_edge" in row.index:
                if side == "over":
                    return row["over_edge"]
                elif side == "under":
                    return row["under_edge"]

        return None

    df["selected_edge"] = df.apply(pick_edge, axis=1)

    return df


def grade_league():
    files = list(SELECT_DIR.glob("*MLB*.csv"))
    all_results = []

    for file in files:
        df = pd.read_csv(file)

        for date, sub in df.groupby("game_date"):
            score_file = SCORE_DIR / f"{date}_final_scores_MLB.csv"

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
        final.to_csv(OUTPUT_DIR / "MLB_final.csv", index=False)


def main():
    grade_league()
    print("MLB grading complete.")


if __name__ == "__main__":
    main()
