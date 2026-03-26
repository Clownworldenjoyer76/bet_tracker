"""
Transform NHL raw JSON into prediction and final score files.

Matches basketball structure exactly (:contentReference[oaicite:1]{index=1})
"""

import os
import re
import json
import argparse
import pandas as pd
from datetime import datetime


def parse_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str.strip(), "%m/%d/%Y %I:%M %p")
        return dt.strftime("%Y_%m_%d")
    except ValueError:
        return date_str.strip().replace("/", "_").replace(" ", "_")


def parse_time(date_str: str) -> str:
    parts = date_str.strip().split(" ")
    if len(parts) >= 2:
        return " ".join(parts[1:])
    return ""


def strip_record(name: str) -> str:
    return re.sub(r"\s*\(\d+[-–]\d+[-–]?\d*\)\s*$", "", str(name)).strip()


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def save(df: pd.DataFrame, path: str):
    ensure_dir(path)
    df.to_csv(path, index=False)
    print(f"  Saved {len(df)} rows -> {path}")


def load_json(path: str) -> list:
    if not path or not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def games_to_df(games: list) -> pd.DataFrame:
    df = pd.DataFrame(games)
    if df.empty:
        return df

    df["game_date"] = df["date_time"].apply(parse_date)
    df["game_time"] = df["date_time"].apply(parse_time)
    df["team1"] = df["team1"].apply(strip_record)
    df["team2"] = df["team2"].apply(strip_record)

    return df


# -------------------------
# PREDICTIONS
# -------------------------
def process_predictions(df: pd.DataFrame):
    mask = df["score1"].isna() | (df["score1"].astype(str).str.strip() == "")
    upcoming = df[mask].copy()

    if upcoming.empty:
        print("  No upcoming NHL games found.")
        return

    for date_val, group in upcoming.groupby("game_date"):
        rows = []

        for _, row in group.iterrows():
            try:
                home_prob = float(str(row["team2_win_pct"]).replace("%", "")) / 100
                away_prob = float(str(row["team1_win_pct"]).replace("%", "")) / 100
            except:
                home_prob = away_prob = ""

            try:
                away_proj = float(row["proj_score_1"])
                home_proj = float(row["proj_score_2"])
                total_proj = round(away_proj + home_proj, 2)
            except:
                away_proj = home_proj = total_proj = ""

            rows.append({
                "league":                "Hockey",
                "market":                "NHL",
                "game_date":             date_val,
                "game_time":             row["game_time"],
                "home_team":             row["team2"],
                "away_team":             row["team1"],
                "home_prob":             f"{home_prob:.6f}" if home_prob != "" else "",
                "away_prob":             f"{away_prob:.6f}" if away_prob != "" else "",
                "away_projected_goals":  away_proj,
                "home_projected_goals":  home_proj,
                "total_projected_goals": total_proj,
            })

        out = pd.DataFrame(rows)
        path = f"docs/win/hockey/00_intake/predictions/hockey_{date_val}.csv"
        save(out, path)


# -------------------------
# FINAL SCORES + DK
# -------------------------
def load_sportsbook(date_val: str):
    path = f"docs/win/hockey/00_intake/sportsbook/hockey_{date_val}.csv"
    if not os.path.exists(path):
        print(f"  WARNING: sportsbook missing: {path}")
        return None
    return pd.read_csv(path)


def get_dk_values(sb, home_team, away_team):
    if sb is None:
        return {}

    match = sb[
        (sb["home_team"].str.strip() == home_team.strip()) &
        (sb["away_team"].str.strip() == away_team.strip())
    ]

    if match.empty:
        return {}

    row = match.iloc[0]

    return {
        "dk_away_puck_line": row.get("away_puck_line", ""),
        "dk_home_puck_line": row.get("home_puck_line", ""),
        "dk_total":          row.get("total", ""),
    }


def process_final_scores(df: pd.DataFrame):
    mask = df["score1"].notna() & (df["score1"].astype(str).str.strip() != "")
    completed = df[mask].copy()

    if completed.empty:
        print("  No completed NHL games found.")
        return

    for date_val, group in completed.groupby("game_date"):
        sb = load_sportsbook(date_val)
        rows = []

        for _, row in group.iterrows():
            try:
                away_score = int(float(row["score1"]))
                home_score = int(float(row["score2"]))
                total      = away_score + home_score

                away_pl = away_score - home_score
                home_pl = home_score - away_score
            except:
                away_score = home_score = total = away_pl = home_pl = ""

            dk = get_dk_values(sb, row["team2"], row["team1"])

            rows.append({
                "game_date":         date_val,
                "league":            "Hockey",
                "market":            "NHL",
                "away_team":         row["team1"],
                "home_team":         row["team2"],
                "away_score":        away_score,
                "home_score":        home_score,
                "total":             total,
                "away_spread":       "",
                "home_spread":       "",
                "away_puck_line":    away_pl,
                "home_puck_line":    home_pl,
                "dk_away_puck_line": dk.get("dk_away_puck_line", ""),
                "dk_home_puck_line": dk.get("dk_home_puck_line", ""),
                "dk_total":          dk.get("dk_total", ""),
            })

        out = pd.DataFrame(rows)
        path = f"docs/win/final_scores/results/nhl/final_scores/{date_val}_final_scores_NHL.csv"
        save(out, path)


# -------------------------
# MAIN
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nhl", required=True, help="Path to NHL raw JSON file")
    args = parser.parse_args()

    print(f"\nProcessing NHL: {args.nhl}")

    games = load_json(args.nhl)
    df = games_to_df(games)

    if not df.empty:
        process_predictions(df)
        process_final_scores(df)

    print("\nDone.")


if __name__ == "__main__":
    main()
