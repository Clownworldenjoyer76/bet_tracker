#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
import glob
from datetime import datetime

# =========================
# PATHS
# =========================

INPUT_DIR = Path("bets/soccer")
OUTPUT_DIR = Path("bets/soccer/calibration")
OUTPUT_FILE = OUTPUT_DIR / "soccer_calibration_master.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def extract_season_from_filename(filename: str):
    # Example: E0_2021.csv or E0-2021.csv
    digits = "".join([c for c in filename if c.isdigit()])
    return digits if digits else ""

def compute_implied_probs(row):
    try:
        pH_raw = 1 / row["AvgH"]
        pD_raw = 1 / row["AvgD"]
        pA_raw = 1 / row["AvgA"]

        overround = pH_raw + pD_raw + pA_raw

        pH_fair = pH_raw / overround
        pD_fair = pD_raw / overround
        pA_fair = pA_raw / overround

        return pH_raw, pD_raw, pA_raw, overround, pH_fair, pD_fair, pA_fair
    except:
        return None

# =========================
# MAIN
# =========================

def main():
    all_files = glob.glob(str(INPUT_DIR / "*.csv"))
    master_rows = []

    for file_path in all_files:
        filename = Path(file_path).name

        # Only process E0-style files
        if "E0" not in filename:
            continue

        print(f"Processing {filename}")

        df = pd.read_csv(file_path)

        required_cols = ["Date", "HomeTeam", "AwayTeam", "FTR", "AvgH", "AvgD", "AvgA"]
        if not all(col in df.columns for col in required_cols):
            print(f"Skipping {filename} - missing required columns")
            continue

        season = extract_season_from_filename(filename)

        for _, row in df.iterrows():

            if pd.isna(row["AvgH"]) or pd.isna(row["AvgD"]) or pd.isna(row["AvgA"]):
                continue

            probs = compute_implied_probs(row)
            if probs is None:
                continue

            pH_raw, pD_raw, pA_raw, overround, pH_fair, pD_fair, pA_fair = probs

            date = row["Date"]
            home = row["HomeTeam"]
            away = row["AwayTeam"]
            result = row["FTR"]

            markets = [
                ("1x2_home", row["AvgH"], pH_raw, pH_fair, 1 if result == "H" else 0),
                ("1x2_draw", row["AvgD"], pD_raw, pD_fair, 1 if result == "D" else 0),
                ("1x2_away", row["AvgA"], pA_raw, pA_fair, 1 if result == "A" else 0),
            ]

            for market_name, odds, raw_prob, fair_prob, win in markets:
                master_rows.append({
                    "date": date,
                    "season": season,
                    "league": "EPL",
                    "home_team": home,
                    "away_team": away,
                    "market": market_name,
                    "decimal_odds": odds,
                    "implied_prob_raw": raw_prob,
                    "overround": overround,
                    "implied_prob_fair": fair_prob,
                    "result": win
                })

    master_df = pd.DataFrame(master_rows)

    if master_df.empty:
        print("No valid data found.")
        return

    master_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {OUTPUT_FILE} ({len(master_df)} rows)")


if __name__ == "__main__":
    main()
