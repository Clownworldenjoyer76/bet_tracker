#scripts/raw_clean.py

import os
import pandas as pd
import glob
from datetime import datetime

INPUT_DIR = "docs/win/dump/csvs/"
OUTPUT_DIR = "docs/win/dump/csvs/cleaned/"

os.makedirs(OUTPUT_DIR, exist_ok=True)

################################### ODDS HELPERS ###################################

def conv_american(dec):
    if dec <= 1.001:
        return 0
    if dec >= 2.0:
        return int((dec - 1) * 100)
    else:
        return int(-100 / (dec - 1))

################################### MAIN PROCESS ###################################

def process_files():
    files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))

    for file_path in files:
        if "cleaned" in file_path:
            continue

        filename = os.path.basename(file_path)
        raw_league = filename.split("_")[0].lower()
        league = f"{raw_league}_ml"

        df = pd.read_csv(file_path)
        processed_data = []

        for index, row in df.iterrows():
            time_parts = str(row["Time"]).split("\n")
            team_parts = str(row["Teams"]).split("\n")
            win_parts = str(row["Win"]).replace("%", "").split("\n")

            raw_date = time_parts[0].strip()
            try:
                dt_obj = datetime.strptime(raw_date, "%m/%d/%Y")
                f_date = dt_obj.strftime("%Y_%m_%d")
            except Exception:
                f_date = raw_date

            g_time = time_parts[1].strip() if len(time_parts) > 1 else ""

            away_team = team_parts[0].split("(")[0].strip()
            home_team = team_parts[1].split("(")[0].strip()

            p_away_pct = float(win_parts[0])
            p_home_pct = float(win_parts[1])

            entry = {
                "date": f_date,
                "time": g_time,
                "away_team": away_team,
                "home_team": home_team,
                "away_team_moneyline_win_prob": round(p_away_pct / 100, 4),
                "home_team_moneyline_win_prob": round(p_home_pct / 100, 4),
                "league": league,
                "game_id": f"{league}_{f_date}_{index}",
            }

            if raw_league in ("nba", "ncaab"):
                score_parts = str(row["Points"]).split("\n")
                entry["away_team_projected_points"] = float(score_parts[0])
                entry["home_team_projected_points"] = float(score_parts[1])
                entry["game_projected_points"] = row.get("Total\nPoints", 0)
            else:
                score_parts = str(row["Goals"]).split("\n")
                s_away = float(score_parts[0])
                s_home = float(score_parts[1])
                entry["away_team_projected_goals"] = s_away
                entry["home_team_projected_goals"] = s_home
                entry["game_projected_goals"] = round(s_away + s_home, 2)

            dec_away = round(100 / p_away_pct, 2)
            entry.update({
                "fair_decimal_odds": dec_away,
                "fair_american_odds": conv_american(dec_away),
                "acceptable_decimal_odds": dec_away,
                "acceptable_american_odds": conv_american(dec_away),
            })

            processed_data.append(entry)

        out_df = pd.DataFrame(processed_data)

        for d_val, d_grp in out_df.groupby("date"):
            out_filename = f"{raw_league}_{d_val}.csv"
            d_grp.to_csv(os.path.join(OUTPUT_DIR, out_filename), index=False)

if __name__ == "__main__":
    process_files()
