"""
Transform all_predictions.csv into sport-specific prediction and final score files.

Usage:
    python transform_predictions.py --input all_predictions.csv

Output structure:
    docs/win/basketball/00_intake/predictions/basketball_NBA_{date}.csv
    docs/win/basketball/00_intake/predictions/basketball_NCAAB_{date}.csv
    docs/win/hockey/00_intake/predictions/hockey_{date}.csv
    docs/win/final_scores/results/nba/final_scores/{date}_final_scores_NBA.csv
    docs/win/final_scores/results/ncaab/final_scores/{date}_final_scores_NCAAB.csv
    docs/win/final_scores/results/nhl/final_scores/{date}_final_scores_NHL.csv

Notes:
    - team1 = away team, team2 = home team (always)
    - Files are split by game_date
    - Soccer leagues are skipped
    - NHL final scores look up dk lines from docs/win/hockey/00_intake/sportsbook/hockey_{date}.csv
"""

import os
import argparse
import pandas as pd
from datetime import datetime


def parse_date(date_str: str) -> str:
    """Convert 'MM/DD/YYYY HH:MM AM/PM' to 'YYYY_MM_DD'."""
    try:
        dt = datetime.strptime(date_str.strip(), "%m/%d/%Y %I:%M %p")
        return dt.strftime("%Y_%m_%d")
    except ValueError:
        return date_str.strip().replace("/", "_").replace(" ", "_")


def parse_time(date_str: str) -> str:
    """Extract 'HH:MM AM/PM' from date_time string."""
    parts = date_str.strip().split(" ")
    if len(parts) >= 2:
        return " ".join(parts[1:])
    return ""


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def save(df: pd.DataFrame, path: str):
    ensure_dir(path)
    df.to_csv(path, index=False)
    print(f"  Saved {len(df)} rows -> {path}")


def process_basketball_predictions(df: pd.DataFrame, market: str, league_label: str):
    """NBA or NCAAB upcoming games -> basketball predictions files."""
    # Filter: no scores
    mask = df["score1"].isna() | (df["score1"].astype(str).str.strip() == "")
    upcoming = df[mask].copy()

    if upcoming.empty:
        print(f"  No upcoming {market} games found.")
        return

    for date_val, group in upcoming.groupby("game_date"):
        rows = []
        for _, row in group.iterrows():
            try:
                home_prob = float(str(row["team2_win_pct"]).replace("%", "")) / 100
                away_prob = float(str(row["team1_win_pct"]).replace("%", "")) / 100
            except (ValueError, TypeError):
                home_prob = away_prob = ""

            try:
                away_proj = float(row["proj_score_1"])
                home_proj = float(row["proj_score_2"])
                total_proj = round(away_proj + home_proj, 1)
            except (ValueError, TypeError):
                away_proj = home_proj = total_proj = ""

            rows.append({
                "league":                  "Basketball",
                "market":                  market,
                "game_date":               date_val,
                "game_time":               row["game_time"],
                "home_team":               row["team2"],
                "away_team":               row["team1"],
                "home_prob":               f"{home_prob:.6f}" if home_prob != "" else "",
                "away_prob":               f"{away_prob:.6f}" if away_prob != "" else "",
                "away_projected_points":   away_proj,
                "home_projected_points":   home_proj,
                "total_projected_points":  total_proj,
            })

        out = pd.DataFrame(rows)
        path = f"docs/win/basketball/00_intake/predictions/basketball_{market}_{date_val}.csv"
        save(out, path)


def process_basketball_final_scores(df: pd.DataFrame, market: str, league_label: str, folder: str):
    """NBA or NCAAB completed games -> final score files."""
    mask = df["score1"].notna() & (df["score1"].astype(str).str.strip() != "")
    completed = df[mask].copy()

    if completed.empty:
        print(f"  No completed {market} games found.")
        return

    for date_val, group in completed.groupby("game_date"):
        rows = []
        for _, row in group.iterrows():
            try:
                away_score = int(float(row["score1"]))
                home_score = int(float(row["score2"]))
                total      = away_score + home_score
                away_spread = away_score - home_score
                home_spread = home_score - away_score
            except (ValueError, TypeError):
                away_score = home_score = total = away_spread = home_spread = ""

            rows.append({
                "game_date":       date_val,
                "league":          "Basketball",
                "market":          market,
                "away_team":       row["team1"],
                "home_team":       row["team2"],
                "away_score":      away_score,
                "home_score":      home_score,
                "total":           total,
                "away_spread":     away_spread,
                "home_spread":     home_spread,
                "away_puck_line":  "",
                "home_puck_line":  "",
            })

        out = pd.DataFrame(rows)
        path = f"docs/win/final_scores/results/{folder}/final_scores/{date_val}_final_scores_{market}.csv"
        save(out, path)


def load_sportsbook(date_val: str) -> pd.DataFrame | None:
    """Load the DK sportsbook file for a given date, return None if missing."""
    path = f"docs/win/hockey/00_intake/sportsbook/hockey_{date_val}.csv"
    if not os.path.exists(path):
        print(f"  WARNING: sportsbook file not found: {path}")
        return None
    return pd.read_csv(path)


def get_dk_values(sb: pd.DataFrame, home_team: str, away_team: str) -> dict:
    """Look up dk puck line / total values from sportsbook by home+away team match."""
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


def process_hockey_predictions(df: pd.DataFrame):
    """NHL upcoming games -> hockey predictions files."""
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
            except (ValueError, TypeError):
                home_prob = away_prob = ""

            try:
                away_proj = float(row["proj_score_1"])
                home_proj = float(row["proj_score_2"])
                total_proj = round(away_proj + home_proj, 2)
            except (ValueError, TypeError):
                away_proj = home_proj = total_proj = ""

            rows.append({
                "league":                "hockey",
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


def process_hockey_final_scores(df: pd.DataFrame):
    """NHL completed games -> final score files, with dk lookup."""
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
                away_pl    = away_score - home_score
                home_pl    = home_score - away_score
            except (ValueError, TypeError):
                away_score = home_score = total = away_pl = home_pl = ""

            dk = get_dk_values(sb, str(row["team2"]), str(row["team1"]))

            rows.append({
                "game_date":        date_val,
                "league":           "Hockey",
                "market":           "NHL",
                "away_team":        row["team1"],
                "home_team":        row["team2"],
                "away_score":       away_score,
                "home_score":       home_score,
                "total":            total,
                "away_spread":      "",
                "home_spread":      "",
                "away_puck_line":   away_pl,
                "home_puck_line":   home_pl,
                "dk_away_puck_line": dk.get("dk_away_puck_line", ""),
                "dk_home_puck_line": dk.get("dk_home_puck_line", ""),
                "dk_total":          dk.get("dk_total", ""),
            })

        out = pd.DataFrame(rows)
        path = f"docs/win/final_scores/results/nhl/final_scores/{date_val}_final_scores_NHL.csv"
        save(out, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="all_predictions.csv", help="Path to all_predictions.csv")
    args = parser.parse_args()

    print(f"Reading {args.input}...")
    df = pd.read_csv(args.input)

    # Parse date and time from date_time column
    df["game_date"] = df["date_time"].apply(parse_date)
    df["game_time"] = df["date_time"].apply(parse_time)

    # Normalize team names (strip record info like "(44-28)")
    import re
    def strip_record(name: str) -> str:
        return re.sub(r"\s*\(\d+[-–]\d+[-–]?\d*\)\s*$", "", str(name)).strip()

    df["team1"] = df["team1"].apply(strip_record)
    df["team2"] = df["team2"].apply(strip_record)

    # Process each sport
    for sport, group in df.groupby("sport"):
        print(f"\nProcessing {sport}...")

        if sport == "NBA":
            process_basketball_predictions(group, "NBA", "Basketball")
            process_basketball_final_scores(group, "NBA", "Basketball", "nba")

        elif sport == "NCAA":
            process_basketball_predictions(group, "NCAAB", "Basketball")
            process_basketball_final_scores(group, "NCAAB", "Basketball", "ncaab")

        elif sport == "NHL":
            process_hockey_predictions(group)
            process_hockey_final_scores(group)

        else:
            print(f"  Skipping {sport}")

    print("\nDone.")


if __name__ == "__main__":
    main()