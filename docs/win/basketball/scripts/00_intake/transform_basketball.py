# docs/win/basketball/scripts/00_intake/transform_basketball.py

import os
import re
import json
import argparse
import traceback
import pandas as pd
from pathlib import Path
from datetime import datetime

ERROR_DIR = Path("docs/win/basketball/errors/00_intake")
ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = ERROR_DIR / "transform_basketball.txt"

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== transform_basketball RUN {datetime.now().isoformat()} ===\n")

def log(msg: str) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {msg}\n")


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


def save(df: pd.DataFrame, path: str, files_written: list):
    ensure_dir(path)
    df.to_csv(path, index=False)
    files_written.append((path, len(df)))
    log(f"WROTE {path} ({len(df)} rows)")
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
    df["team1"]     = df["team1"].apply(strip_record)
    df["team2"]     = df["team2"].apply(strip_record)
    return df


def process_predictions(df: pd.DataFrame, market: str, files_written: list):
    mask     = df["score1"].isna() | (df["score1"].astype(str).str.strip() == "")
    upcoming = df[mask].copy()

    if upcoming.empty:
        log(f"No upcoming {market} games found.")
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
                away_proj  = float(row["proj_score_1"])
                home_proj  = float(row["proj_score_2"])
                total_proj = round(away_proj + home_proj, 1)
            except (ValueError, TypeError):
                away_proj = home_proj = total_proj = ""

            rows.append({
                "league":                 "Basketball",
                "market":                 market,
                "game_date":              date_val,
                "game_time":              row["game_time"],
                "home_team":              row["team2"],
                "away_team":              row["team1"],
                "home_prob":              f"{home_prob:.6f}" if home_prob != "" else "",
                "away_prob":              f"{away_prob:.6f}" if away_prob != "" else "",
                "away_projected_points":  away_proj,
                "home_projected_points":  home_proj,
                "total_projected_points": total_proj,
            })

        out  = pd.DataFrame(rows)
        path = f"docs/win/basketball/00_intake/predictions/basketball_{market}_{date_val}.csv"
        save(out, path, files_written)


def process_final_scores(df: pd.DataFrame, market: str, folder: str, files_written: list):
    mask      = df["score1"].notna() & (df["score1"].astype(str).str.strip() != "")
    completed = df[mask].copy()

    if completed.empty:
        log(f"No completed {market} games found.")
        return

    for date_val, group in completed.groupby("game_date"):
        rows = []
        for _, row in group.iterrows():
            try:
                away_score  = int(float(row["score1"]))
                home_score  = int(float(row["score2"]))
                total       = away_score + home_score
                away_spread = away_score - home_score
                home_spread = home_score - away_score
            except (ValueError, TypeError):
                away_score = home_score = total = away_spread = home_spread = ""

            rows.append({
                "game_date":      date_val,
                "league":         "Basketball",
                "market":         market,
                "away_team":      row["team1"],
                "home_team":      row["team2"],
                "away_score":     away_score,
                "home_score":     home_score,
                "total":          total,
                "away_spread":    away_spread,
                "home_spread":    home_spread,
                "away_puck_line": "",
                "home_puck_line": "",
            })

        out = pd.DataFrame(rows)

        path = f"docs/win/final_scores/results/{folder}/final_scores/{date_val}_final_scores_{market}.csv"
        save(out, path, files_written)

        if market == "MLB":
        baseball_path = f"docs/win/baseball/05_final_scores/results/final_scores/{date_val}_final_scores_{market}.csv"
        save(out, baseball_path, files_written)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nba",   default=None)
    parser.add_argument("--ncaab", default=None)
    args = parser.parse_args()

    files_written = []

    try:
        if args.nba:
            log(f"Processing NBA: {args.nba}")
            games = load_json(args.nba)
            log(f"NBA games loaded: {len(games)}")
            df = games_to_df(games)
            if not df.empty:
                process_predictions(df, "NBA", files_written)
                process_final_scores(df, "NBA", "nba", files_written)
            else:
                log("NBA: no data to process.")

        if args.ncaab:
            log(f"Processing NCAAB: {args.ncaab}")
            games = load_json(args.ncaab)
            log(f"NCAAB games loaded: {len(games)}")
            df = games_to_df(games)
            if not df.empty:
                process_predictions(df, "NCAAB", files_written)
                process_final_scores(df, "NCAAB", "ncaab", files_written)
            else:
                log("NCAAB: no data to process.")

        log("--- SUMMARY ---")
        log(f"Files written: {len(files_written)}")
        for path, count in files_written:
            log(f"  FILE: {path} ({count} rows)")
        log("STATUS: SUCCESS")

    except Exception as e:
        log(f"FATAL ERROR: {e}\n{traceback.format_exc()}")
        log("STATUS: FAILED")
        raise

    print("\nDone.")


if __name__ == "__main__":
    main()
