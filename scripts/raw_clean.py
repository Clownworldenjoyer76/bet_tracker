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
# MAIN PROCESS
###################################

def process_files():
    files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))

    all_games_master_rows = []

    for file_path in files:
        if "cleaned" in file_path:
            continue

        filename = os.path.basename(file_path)
        raw_league = filename.split("_")[0].lower()
        league = raw_league

        df = pd.read_csv(file_path)
        processed_data = []

        for index, row in df.iterrows():
            # ---------- DATE ----------
            time_parts = str(row.get("Time", "")).split("\n")
            raw_date = time_parts[0].strip()

            try:
                dt_obj = datetime.strptime(raw_date, "%m/%d/%Y")
                f_date = dt_obj.strftime("%Y_%m_%d")
            except Exception:
                continue  # date is mandatory for games master

            # ---------- TEAMS ----------
            team_parts = str(row.get("Teams", "")).split("\n")
            if len(team_parts) < 2:
                continue

            away_team = team_parts[0].split("(")[0].strip()
            home_team = team_parts[1].split("(")[0].strip()

            game_id = f"{league}_{f_date}_{index}"

            # ---------- ALWAYS ADD TO GAMES MASTER ----------
            all_games_master_rows.append({
                "date": f_date,
                "league": league,
                "game_id": game_id,
                "away_team": away_team,
                "home_team": home_team,
            })

            # ---------- WIN PROBABILITIES ----------
            win_parts = str(row.get("Win", "")).replace("%", "").split("\n")
            try:
                p_away_pct = float(win_parts[0])
                p_home_pct = float(win_parts[1])
            except Exception:
                continue

            entry = {
                "date": f_date,
                "league": league,
                "game_id": game_id,
                "away_team": away_team,
                "home_team": home_team,
                "away_team_moneyline_win_prob": round(p_away_pct / 100, 4),
                "home_team_moneyline_win_prob": round(p_home_pct / 100, 4),
            }

            # ---------- PROJECTIONS ----------
            if raw_league in ("nba", "ncaab"):
                score_parts = str(row.get("Points", "")).split("\n")
                if len(score_parts) < 2:
                    continue
                entry["away_team_projected_points"] = float(score_parts[0])
                entry["home_team_projected_points"] = float(score_parts[1])
                entry["game_projected_points"] = round(
                    entry["away_team_projected_points"] +
                    entry["home_team_projected_points"], 2
                )
            else:
                score_parts = str(row.get("Goals", "")).split("\n")
                if len(score_parts) < 2:
                    continue
                entry["away_team_projected_goals"] = float(score_parts[0])
                entry["home_team_projected_goals"] = float(score_parts[1])
                entry["game_projected_goals"] = round(
                    entry["away_team_projected_goals"] +
                    entry["home_team_projected_goals"], 2
                )

            dec_away = round(100 / p_away_pct, 4)
            entry["fair_decimal_odds"] = dec_away
            entry["fair_american_odds"] = conv_american(dec_away)
            entry["acceptable_decimal_odds"] = dec_away
            entry["acceptable_american_odds"] = conv_american(dec_away)

            processed_data.append(entry)

        if processed_data:
            out_df = pd.DataFrame(processed_data)
            for d_val, d_grp in out_df.groupby("date"):
                out_path = os.path.join(OUTPUT_DIR, f"{league}_{d_val}.csv")
                d_grp.to_csv(out_path, index=False)
                print(f"Saved: {out_path}")

    # ---------- WRITE ONE FILE PER DATE (ALL LEAGUES) ----------
    if not all_games_master_rows:
        raise RuntimeError("No games written to games_master — aborting")

    gm_df = pd.DataFrame(all_games_master_rows).drop_duplicates()

    for d_val, d_grp in gm_df.groupby("date"):
        gm_path = os.path.join(GAMES_MASTER_DIR, f"games_{d_val}.csv")
        d_grp.to_csv(gm_path, index=False)
        print(f"Saved games master: {gm_path}")

if __name__ == "__main__":
    process_files()
