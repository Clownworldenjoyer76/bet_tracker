# scripts/raw_clean.py

import os
import pandas as pd
import glob
from datetime import datetime

INPUT_DIR = "docs/win/dump/csvs/"
OUTPUT_DIR = "docs/win/dump/csvs/cleaned/"
GAMES_MASTER_DIR = "docs/win/games_master/"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GAMES_MASTER_DIR, exist_ok=True)

###################################
# ODDS HELPERS
###################################

def conv_american(dec):
    if dec <= 1.001:
        return 0
    if dec >= 2.0:
        return int((dec - 1) * 100)
    return int(-100 / (dec - 1))

###################################
# GAMES MASTER CREATION
###################################

def write_games_master(out_df):
    required_cols = ["date", "league", "game_id", "away_team", "home_team"]

    gm_df = out_df[required_cols].drop_duplicates()

    for d_val, d_grp in gm_df.groupby("date"):
        gm_filename = f"games_{d_val}.csv"
        gm_path = os.path.join(GAMES_MASTER_DIR, gm_filename)
        d_grp.to_csv(gm_path, index=False)
        print(f"Saved games master: {gm_path}")

###################################
# MAIN PROCESS
###################################

def process_files():
    files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))

    for file_path in files:
        if "cleaned" in file_path:
            continue

        filename = os.path.basename(file_path)

        # league inferred from filename prefix (nba, ncaab, nhl)
        raw_league = filename.split("_")[0].lower()
        league = raw_league  # explicitly no _ml suffix anywhere

        df = pd.read_csv(file_path)
        processed_data = []

        for index, row in df.iterrows():
            # ---------- TIME / DATE ----------
            time_parts = str(row.get("Time", "")).split("\n")
            raw_date = time_parts[0].strip()

            try:
                dt_obj = datetime.strptime(raw_date, "%m/%d/%Y")
                f_date = dt_obj.strftime("%Y_%m_%d")
            except Exception:
                f_date = raw_date.replace("/", "_")

            g_time = time_parts[1].strip() if len(time_parts) > 1 else ""

            # ---------- TEAMS ----------
            team_parts = str(row.get("Teams", "")).split("\n")
            away_team = team_parts[0].split("(")[0].strip() if len(team_parts) > 0 else ""
            home_team = team_parts[1].split("(")[0].strip() if len(team_parts) > 1 else ""

            # ---------- WIN PROBABILITIES ----------
            win_parts = str(row.get("Win", "")).replace("%", "").split("\n")
            try:
                p_away_pct = float(win_parts[0])
                p_home_pct = float(win_parts[1])
            except Exception:
                continue

            entry = {
                "date": f_date,
                "time": g_time,
                "league": league,
                "game_id": f"{league}_{f_date}_{index}",
                "away_team": away_team,
                "home_team": home_team,
                "away_team_moneyline_win_prob": round(p_away_pct / 100, 4),
                "home_team_moneyline_win_prob": round(p_home_pct / 100, 4),
            }

            # ---------- PROJECTIONS ----------
            if raw_league in ("nba", "ncaab"):
                score_parts = str(row.get("Points", "")).split("\n")
                try:
                    away_pts = float(score_parts[0])
                    home_pts = float(score_parts[1])
                except Exception:
                    continue

                entry["away_team_projected_points"] = away_pts
                entry["home_team_projected_points"] = home_pts
                entry["game_projected_points"] = round(away_pts + home_pts, 2)

            else:  # NHL
                score_parts = str(row.get("Goals", "")).split("\n")
                try:
                    away_goals = float(score_parts[0])
                    home_goals = float(score_parts[1])
                except Exception:
                    continue

                entry["away_team_projected_goals"] = away_goals
                entry["home_team_projected_goals"] = home_goals
                entry["game_projected_goals"] = round(away_goals + home_goals, 2)

            # ---------- FAIR / ACCEPTABLE ODDS ----------
            dec_away = round(100 / p_away_pct, 4)

            entry.update({
                "fair_decimal_odds": dec_away,
                "fair_american_odds": conv_american(dec_away),
                "acceptable_decimal_odds": dec_away,
                "acceptable_american_odds": conv_american(dec_away),
            })

            processed_data.append(entry)

        if not processed_data:
            continue

        out_df = pd.DataFrame(processed_data)

        # ---------- WRITE PER-DATE FILES ----------
        for d_val, d_grp in out_df.groupby("date"):
            out_filename = f"{league}_{d_val}.csv"
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            d_grp.to_csv(out_path, index=False)
            print(f"Saved: {out_path}")

        # ---------- WRITE GAMES MASTER ----------
        write_games_master(out_df)

if __name__ == "__main__":
    process_files()
