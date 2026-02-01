#!/usr/bin/env python3

import csv
import re
import os
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).parent.parent
INPUT_RAW_DIR = BASE_DIR / "docs/win/dump"
INPUT_NORM_DIR = BASE_DIR / "docs/win/manual/normalized"
FINAL_OUTPUT_DIR = BASE_DIR / "docs/win/cleaned"
FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def strip_team(name):
    if not name: return ""
    s = re.sub(r"\([^)]*\)", "", str(name))
    s = re.sub(r"\s+\d+\s*-\s*\d+\s*$", "", s)
    return s.strip()

def pct_to_decimal(value):
    if not value: return ""
    s = str(value).strip()
    return str(float(s[:-1]) / 100) if s.endswith("%") else s

def get_raw_rows(league):
    files = sorted(INPUT_RAW_DIR.glob(f"{league}_*.xlsx"))
    all_extracted = []
    for path in files:
        wb = load_workbook(path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))[1:] 
        for row in rows:
            if not row or not any(row): continue
            dt_lines = str(row[0]).splitlines() if row[0] else []
            teams = str(row[1]).splitlines() if row[1] else []
            wins = str(row[2]).splitlines() if row[2] else []
            data = {
                "date": dt_lines[0] if dt_lines else "",
                "time": dt_lines[1] if len(dt_lines) > 1 else "",
                "team_a": strip_team(teams[0]) if teams else "",
                "team_b": strip_team(teams[1]) if len(teams) > 1 else "",
                "win_a": pct_to_decimal(wins[0]) if wins else "",
                "win_b": pct_to_decimal(wins[1]) if len(wins) > 1 else "",
                "league": league
            }
            if league == "soc":
                data.update({"goals_a": str(row[4]).splitlines()[0] if row[4] else "", 
                             "goals_b": str(row[4]).splitlines()[1] if row[4] and len(str(row[4]).splitlines())>1 else "",
                             "total_pts": row[5] or ""})
            elif league == "nhl":
                data.update({"goals_a": str(row[3]).splitlines()[0] if row[3] else "", 
                             "goals_b": str(row[3]).splitlines()[1] if row[3] and len(str(row[3]).splitlines())>1 else "",
                             "total_pts": row[4] or ""})
            else:
                data.update({"pts_a": str(row[3]).splitlines()[0] if row[3] else "", 
                             "pts_b": str(row[3]).splitlines()[1] if row[3] and len(str(row[3]).splitlines())>1 else "",
                             "total_pts": row[4] or ""})
            all_extracted.append(data)
    return all_extracted

def process_league_unified(league):
    raw_data = get_raw_rows(league)
    if not raw_data: return

    search_date = ""
    for r in raw_data:
        if r['date']:
            for fmt in ("%m/%d/%Y", "%m/%d/%y"):
                try:
                    search_date = datetime.strptime(r['date'], fmt).strftime("%Y_%m_%d")
                    break
                except: continue
            if search_date: break
    if not search_date: return

    dk_file = INPUT_NORM_DIR / f"norm_dk_{league}_totals_{search_date}.csv"
    dk_map = {}
    if dk_file.exists():
        with open(dk_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gid = row.get("game_id")
                if not gid: continue
                if gid not in dk_map:
                    dk_map[gid] = {"total": "", "OVER": {}, "UNDER": {}}
                
                side = str(row.get("side") or "").strip().upper()
                if side in ["OVER", "UNDER"]:
                    dk_map[gid][side] = row
                    # Capture the total from the row itself
                    dk_map[gid]["total"] = row.get("total", "")

    final_rows = []
    for i, entry in enumerate(raw_data):
        gid = f"{league}_{search_date}_game_{i+1}"
        dk = dk_map.get(gid, {"total": "", "OVER": {}, "UNDER": {}})

        final_rows.append({
            "game_id": gid, "date": entry["date"], "time": entry["time"],
            "away_team": entry["team_a"], "home_team": entry["team_b"],
            "away_points": entry.get("pts_a") or entry.get("goals_a") or "",
            "home_points": entry.get("pts_b") or entry.get("goals_b") or "",
            "total_points": entry.get("total_pts", ""),
            "away_win_probability": entry["win_a"],
            "home__win_probability": entry["win_b"],
            "total": dk["total"],
            "over_total_odds": dk["OVER"].get("odds", ""),
            "under_total_odds": dk["UNDER"].get("odds", ""),
            "over_handle_pct": dk["OVER"].get("handle_pct", ""),
            "under_handle_pct": dk["UNDER"].get("handle_pct", ""),
            "over_bets_pct": dk["OVER"].get("bets_pct", ""),
            "under_bets_pct": dk["UNDER"].get("bets_pct", ""),
            "league": league
        })

    if final_rows:
        out_date = search_date.replace("_", "-")
        out_path = FINAL_OUTPUT_DIR / f"clean_{league}_{out_date}.csv"
        headers = ["game_id", "date", "time", "away_team", "home_team", "away_points", "home_points", "total_points", "away_win_probability", "home__win_probability", "total", "over_total_odds", "under_total_odds", "over_handle_pct", "under_handle_pct", "over_bets_pct", "under_bets_pct", "league"]
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(final_rows)

def main():
    for lg in ["nba", "ncaab", "nhl", "soc"]:
        process_league_unified(lg)

if __name__ == "__main__":
    main()
