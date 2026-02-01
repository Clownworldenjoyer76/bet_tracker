#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import defaultdict

# Setup directories
INPUT_CLEAN_DIR = Path("docs/win/clean")
INPUT_NORM_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/cleaned")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_norm_data(league, date_str):
    """Loads betting data from docs/win/manual/normalized/."""
    # Handle NCAAB underscore format vs others
    search_date = date_str.replace("-", "_") if league == "ncaab" else date_str
    pattern = f"norm_dk_{league}_totals_{search_date}.csv"
    norm_files = list(INPUT_NORM_DIR.glob(pattern))
    
    data = {}
    if not norm_files:
        return data

    with open(norm_files[0], mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gid = row.get("game_id")
            side = (row.get("side") or "").upper()
            if gid not in data:
                data[gid] = {"over": {}, "under": {}, "total": row.get("total", "")}
            
            if side == "OVER":
                data[gid]["over"] = row
            elif side == "UNDER":
                data[gid]["under"] = row
    return data

def process_league(league):
    files = sorted(INPUT_CLEAN_DIR.glob(f"win_prob__clean_{league}_*.csv"))
    
    for file_path in files:
        # FIX: Extract date correctly regardless of dash or underscore
        # This takes everything after the league name
        date_part = file_path.stem.split(f"clean_{league}_")[-1]
        
        norm_data = load_norm_data(league, date_part)
        
        games = defaultdict(list)
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gid = row.get("game_id")
                if gid:
                    games[gid].append(row)

        output_rows = []
        for gid, rows in games.items():
            team_rows = [r for r in rows if r["team"] != "DRAW"]
            if len(team_rows) < 2:
                continue

            away = team_rows[0] 
            home = team_rows[1] 
            
            p_key = "points" if league in ["nba", "ncaab"] else "goals"
            
            dk = norm_data.get(gid, {"over": {}, "under": {}, "total": ""})

            output_rows.append({
                "game_id": gid,
                "date": away.get("date"),
                "time": away.get("time"),
                "away_team": away.get("team"),
                "home_team": home.get("team"),
                "away_points": away.get(p_key),
                "home_points": home.get(p_key),
                "total_points": away.get(f"total_{p_key}", ""),
                "away_win_probability": away.get("win_probability"),
                "home__win_probability": home.get("win_probability"),
                "total": dk["total"],
                "over_total_odds": dk["over"].get("odds", ""),
                "under_total_odds": dk["under"].get("odds", ""),
                "over_handle_pct": dk["over"].get("handle_pct", ""),
                "under_handle_pct": dk["under"].get("handle_pct", ""),
                "over_bets_pct": dk["over"].get("bets_pct", ""),
                "under_bets_pct": dk["under"].get("bets_pct", ""),
                "league": league
            })

        if output_rows:
            # Force output to YYYY_mm_DD to keep NCAAB style or YYYY-mm-DD for others
            final_date = date_part.replace("-", "_") if league == "ncaab" else date_part
            out_name = f"clean_{league}_{final_date}.csv"
            out_path = OUTPUT_DIR / out_name
            
            headers = [
                "game_id", "date", "time", "away_team", "home_team",
                "away_points", "home_points", "total_points",
                "away_win_probability", "home__win_probability",
                "total", "over_total_odds", "under_total_odds",
                "over_handle_pct", "under_handle_pct", "over_bets_pct",
                "under_bets_pct", "league"
            ]

            with open(out_path, "w", newline="", encoding="utf-8") as out_f:
                writer = csv.DictWriter(out_f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(output_rows)
            print(f"Created: {out_path}")

def main():
    for league in ["nba", "ncaab", "nhl", "soc"]:
        process_league(league)

if __name__ == "__main__":
    main()
