#####scripts/raw_1.py


import os
import pandas as pd
import glob
from datetime import datetime
import re

INPUT_DIR = "docs/win/dump/csvs/"
OUTPUT_DIR = "docs/win/dump/csvs/cleaned/"
MAP_PATH = "mappings/team_map.csv"

NEED_MAP_DIR = "mappings/need_map"
DUMP_NO_MAP_PATH = os.path.join(NEED_MAP_DIR, "dump_no_map.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(NEED_MAP_DIR, exist_ok=True)

################################### TEAM NORMALIZATION ###################################

def norm(s: str) -> str:
    if pd.isna(s):
        return s
    s = str(s).replace("\u00A0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def norm_league(s: str) -> str:
    return norm(s).lower()


def load_team_map() -> dict:
    df = pd.read_csv(MAP_PATH, dtype=str)

    df["league"] = df["league"].apply(norm_league)
    df["dk_team"] = df["dk_team"].apply(norm)
    df["canonical_team"] = df["canonical_team"].apply(norm)

    team_map: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        lg = row["league"]
        dk = row["dk_team"]
        can = row["canonical_team"]
        if pd.isna(lg) or pd.isna(dk) or pd.isna(can):
            continue
        team_map.setdefault(lg, {})[dk] = can

    return team_map


def canonicalize_team(raw: str, league_map: dict) -> tuple[str, bool]:
    """
    Deterministically map a dump team name to canonical_team.

    Strategy (in order):
    1. Exact match
    2. Strip mascot (school-only, first 2 words)
    3. First token only (e.g. Louisiana, Sam)
    """
    if raw in league_map:
        return league_map[raw], True

    parts = raw.split()
    if len(parts) >= 2:
        school_only = " ".join(parts[:2])
        if school_only in league_map:
            return league_map[school_only], True

    if parts and parts[0] in league_map:
        return league_map[parts[0]], True

    return raw, False

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
    team_map = load_team_map()
    files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))

    unmapped_rows = []

    for file_path in files:
        if "cleaned" in file_path:
            continue

        filename = os.path.basename(file_path)
        raw_league = filename.split("_")[0].lower()
        league = f"{raw_league}_ml"

        df = pd.read_csv(file_path)
        processed_data = []

        league_map = team_map.get(raw_league, {})

        for index, row in df.iterrows():
            time_parts = str(row["Time"]).split("\n")
            team_parts = str(row["Teams"]).split("\n")
            win_parts = str(row["Win"]).replace("%", "").split("\n")

            # Date
            raw_date = time_parts[0].strip()
            try:
                dt_obj = datetime.strptime(raw_date, "%m/%d/%Y")
                f_date = dt_obj.strftime("%Y_%m_%d")
            except Exception:
                f_date = raw_date

            g_time = time_parts[1].strip() if len(time_parts) > 1 else ""

            away_raw = team_parts[0].split("(")[0].strip()
            home_raw = team_parts[1].split("(")[0].strip()

            away_norm = norm(away_raw)
            home_norm = norm(home_raw)

            away_team, ok = canonicalize_team(away_norm, league_map)
            if not ok:
                unmapped_rows.append({
                    "league": raw_league,
                    "team": away_norm,
                    "file": filename,
                })

            home_team, ok = canonicalize_team(home_norm, league_map)
            if not ok:
                unmapped_rows.append({
                    "league": raw_league,
                    "team": home_norm,
                    "file": filename,
                })

            # Win probabilities
            p_away_pct = float(win_parts[0])
            p_home_pct = float(win_parts[1])
            p_away_dec = round(p_away_pct / 100, 4)
            p_home_dec = round(p_home_pct / 100, 4)

            entry = {
                "date": f_date,
                "time": g_time,
                "away_team": away_team,
                "home_team": home_team,
                "away_team_moneyline_win_prob": p_away_dec,
                "home_team_moneyline_win_prob": p_home_dec,
                "league": league,
                "game_id": f"{league}_{f_date}_{index}",
            }

            if raw_league in ("nba", "ncaab"):
                score_parts = str(row["Points"]).split("\n")
                entry["away_team_projected_points"] = float(score_parts[0])
                entry["home_team_projected_points"] = float(score_parts[1])
                entry["game_projected_points"] = row.get("Total\nPoints", 0)
            else:  # NHL
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
            clean_league = league.replace("_ml", "")
            out_filename = f"{clean_league}_{d_val}.csv"
            d_grp.to_csv(os.path.join(OUTPUT_DIR, out_filename), index=False)

    # Write dump-side unmapped alerts
    if unmapped_rows:
        new_df = pd.DataFrame(unmapped_rows).drop_duplicates()

        if os.path.exists(DUMP_NO_MAP_PATH):
            old_df = pd.read_csv(DUMP_NO_MAP_PATH, dtype=str)
            new_df = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates()

        new_df.to_csv(DUMP_NO_MAP_PATH, index=False)


if __name__ == "__main__":
    process_files()
