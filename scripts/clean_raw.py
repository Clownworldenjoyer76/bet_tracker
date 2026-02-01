#!/usr/bin/env python3

import csv
import re
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from openpyxl import load_workbook

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).parent.parent
INPUT_RAW_DIR = BASE_DIR / "docs/win/dump"
INPUT_NORM_DIR = BASE_DIR / "docs/win/manual/normalized"
FINAL_OUTPUT_DIR = BASE_DIR / "docs/win/cleaned"
FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Helper for team cleaning
def strip_team(name):
    if not name: return ""
    s = re.sub(r"\([^)]*\)", "", str(name))
    s = re.sub(r"\s+\d+\s*-\s*\d+\s*$", "", s)
    return s.strip()

def pct_to_decimal(value):
    if not value: return ""
    s = str(value).strip()
    return str(float(s[:-1]) / 100) if s.endswith("%") else s

# ============================================================
# EXTRACTION LOGIC
# ============================================================

def get_raw_rows(league):
    """Reads Excel files and returns list of dicts with basic cleanup."""
    files = sorted(INPUT_RAW_DIR.glob(f"{league}_*.xlsx"))
    all_extracted = []

    for path in files:
        wb = load_workbook(path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))[1:] # Skip header
        
        for row in rows:
            if not row or not any(row): continue
            
            # Basic shared parsing
            dt_lines = str(row[0]).splitlines() if row[0] else []
            date = dt_lines[0] if len(dt_lines) > 0 else ""
            time = dt_lines[1] if len(dt_lines) > 1 else ""
            
            teams = str(row[1]).splitlines() if row[1] else []
            team_a = strip_team(teams[0]) if len(teams) > 0 else ""
            team_b = strip_team(teams[1]) if len(teams) > 1 else ""
            
            wins = str(row[2]).splitlines() if row[2] else []
            win_a = pct_to_decimal(wins[0]) if len(wins) > 0 else ""
            win_b = pct_to_decimal(wins[1]) if len(wins) > 1 else ""

            # League specific mapping
            data = {"date": date, "time": time, "team_a": team_a, "team_b": team_b, 
                    "win_a": win_a, "win_b": win_b, "league": league}

            if league == "soc":
                data.update({"draw": pct_to_decimal(row[3]), "goals_a": str(row[4]).splitlines()[0] if row[4] else "", 
                             "goals_b": str(row[4]).splitlines()[1] if row[4] and len(str(row[4]).splitlines())>1 else "",
                             "total": row[5] or ""})
            elif league == "nhl":
                data.update({"goals_a": str(row[3]).splitlines()[0] if row[3] else "", 
                             "goals_b": str(row[3]).splitlines()[1] if row[3] and len(str(row[3]).splitlines())>1 else "",
                             "total": row[4] or ""})
            else: # NBA / NCAAB
                data.update({"pts_a": str(row[3]).splitlines()[0] if row[3] else "", 
                             "pts_b": str(row[3]).splitlines()[1] if row[3] and len(str(row[3]).splitlines())>1 else "",
                             "total": row[4] or ""})
            
            all_extracted.append(data)
    return all_extracted

# ============================================================
# PROCESSING & MERGING
# ============================================================

def process_league_unified(league):
    raw_data = get_raw_rows(league)
    if not raw_data: return

    # Load DK Manual Data
    # Assume file date comes from the first record's date
    first_date = ""
    for r in raw_data:
        if r['date']:
            first_date = datetime.strptime(r['date'], "%m/%d/%Y").strftime("%Y-%m-%d")
            break
    
    dk_file = INPUT_NORM_DIR / f"norm_dk_{league}_totals_{first_date.replace('-','_')}.csv"
    dk_map = {}
    if dk_file.exists():
        with open(dk_file, 'r') as f:
            for row in csv.DictReader(f):
                gid = row["game_id"]
                if gid not in dk_map: dk_map[gid] = {"total": row.get("total", ""), "over": {}, "under": {}}
                dk_map[gid][row["side"].lower()] = row

    # Group into Final Format
    final_rows = []
    for i, entry in enumerate(raw_data):
        # Generate a Game ID (simplified pairing since we have team_a and team_b in one row now)
        date_str = datetime.strptime(entry['date'], "%m/%d/%Y").strftime("%Y_%m_%d")
        gid = f"{league}_{date_str}_game_{i+1}"
        
        p_key_a = entry.get("pts_a") or entry.get("goals_a") or ""
        p_key_b = entry.get("pts_b") or entry.get("goals_b") or ""
        dk = dk_map.get(gid, {"total": "", "over": {}, "under": {}}) # Note: GID matching logic depends on your DK CSVs

        final_rows.append({
            "game_id": gid, "date": entry["date"], "time": entry["time"],
            "away_team": entry["team_a"], "home_team": entry["team_b"],
            "away_points": p_key_a, "home_points": p_key_b,
            "total_points": entry["total"], "away_win_probability": entry["win_a"],
            "home__win_probability": entry["win_b"], "total": dk["total"],
            "over_total_odds": dk["over"].get("odds", ""), "under_total_odds": dk["under"].get("odds", ""),
            "over_handle_pct": dk["over"].get("handle_pct", ""), "under_handle_pct": dk["under"].get("handle_pct", ""),
            "over_bets_pct": dk["over"].get("bets_pct", ""), "under_bets_pct": dk["under"].get("bets_pct", ""),
            "league": league
        })

    if final_rows:
        out_path = FINAL_OUTPUT_DIR / f"clean_{league}_{first_date}.csv"
        headers = list(final_rows[0].keys())
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(final_rows)
        print(f"Saved: {out_path.name}")

def main():
    for league in ["nba", "ncaab", "nhl", "soc"]:
        process_league_unified(league)

if __name__ == "__main__":
    main()
