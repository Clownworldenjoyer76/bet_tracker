#!/usr/bin/env python3
# docs/win/final_scores/scripts/00_parsing/espn.py

import sys
import re
import csv
from pathlib import Path
from datetime import datetime
import traceback

OUT_DIR = Path("docs/win/final_scores")
ERR_DIR = OUT_DIR / "errors"
MAP_DIR = OUT_DIR / "team_maps"

OUT_DIR.mkdir(parents=True, exist_ok=True)
ERR_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = [
    "game_date",
    "league",
    "market",
    "away_team",
    "home_team",
    "away_score",
    "home_score",
    "total",
    "away_spread",
    "home_spread",
    "away_puck_line",
    "home_puck_line",
]


def normalize_market(market: str) -> str:
    m = (market or "").strip().upper()
    if m in {"NBA", "NCAAB", "NCAAM"}:
        return "NCAAB" if m in {"NCAAB", "NCAAM"} else "NBA"
    if m == "NHL":
        return "NHL"
    raise ValueError("market must be one of: NBA, NCAAB, NHL")


def league_from_market(market: str) -> str:
    return "Basketball" if market in {"NBA", "NCAAB"} else "Hockey"


def get_map_path(market: str) -> Path:
    if market == "NBA":
        return MAP_DIR / "team_map_nba.csv"
    if market == "NCAAB":
        return MAP_DIR / "team_map_ncaab.csv"
    if market == "NHL":
        return MAP_DIR / "team_map_nhl.csv"
    raise ValueError("Invalid market")


def load_team_map(market: str) -> dict:
    path = get_map_path(market)

    if not path.exists():
        raise FileNotFoundError(f"Team map not found: {path}")

    team_map = {}

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "team_name" not in reader.fieldnames or "abbreviation" not in reader.fieldnames:
            raise ValueError(f"Invalid headers in {path}. Required: team_name,abbreviation")

        for row in reader:
            team = row["team_name"].strip()
            abbr = row["abbreviation"].strip()
            if team:
                team_map[team] = abbr

    return team_map


def parse_game_date(lines):
    for line in lines[:20]:
        s = line.strip()
        if not s:
            continue
        try:
            dt = datetime.strptime(s, "%A, %B %d, %Y")
            return dt.strftime("%Y_%m_%d")
        except Exception:
            continue
    raise ValueError("Could not parse game date.")


def next_non_empty(lines, start_idx):
    i = start_idx
    while i < len(lines):
        s = lines[i].strip()
        if s:
            return i, s
        i += 1
    return len(lines), ""


def prev_non_empty(lines, start_idx):
    i = start_idx
    while i >= 0:
        s = lines[i].strip()
        if s:
            return i, s
        i -= 1
    return -1, ""


def is_at_line(s):
    return s.strip() == "@"


def looks_like_result_line(s):
    return "," in s and len(re.findall(r"\d+", s)) >= 2


def extract_pairs(result_line):
    return re.findall(r"([A-Z]+)\s+(\d+)", result_line)


def map_scores(result_line, away_team, home_team, team_map):
    pairs = extract_pairs(result_line)
    if len(pairs) < 2:
        raise ValueError(f"Invalid result line: {result_line}")

    score_map = {abbr: int(score) for abbr, score in pairs}

    if away_team not in team_map:
        raise ValueError(f"Team not found in map: {away_team}")

    if home_team not in team_map:
        raise ValueError(f"Team not found in map: {home_team}")

    away_abbrev = team_map[away_team]
    home_abbrev = team_map[home_team]

    if away_abbrev not in score_map or home_abbrev not in score_map:
        raise ValueError(
            f"Abbreviation mismatch: {result_line} | "
            f"Away={away_team}({away_abbrev}) "
            f"Home={home_team}({home_abbrev})"
        )

    return score_map[away_abbrev], score_map[home_abbrev]


def parse_games(lines, game_date, market, team_map):
    rows = []
    is_basketball = market in {"NBA", "NCAAB"}
    is_hockey = market == "NHL"

    for i, raw in enumerate(lines):
        if not is_at_line(raw.strip()):
            continue

        _, away_team = prev_non_empty(lines, i - 1)
        _, home_team = next_non_empty(lines, i + 1)

        if not away_team or not home_team:
            continue

        j, _ = next_non_empty(lines, i + 2)

        result_line = ""
        for k in range(j, min(len(lines), j + 20)):
            if looks_like_result_line(lines[k].strip()):
                result_line = lines[k].strip()
                break

        if not result_line:
            continue

        away_score, home_score = map_scores(
            result_line,
            away_team,
            home_team,
            team_map
        )

        total = away_score + home_score
        margin = home_score - away_score

        away_spread = ""
        home_spread = ""
        away_puck_line = ""
        home_puck_line = ""

        if is_basketball:
            away_spread = str(margin)
            home_spread = str(-margin)

        if is_hockey:
            away_puck_line = str(margin)
            home_puck_line = str(-margin)

        rows.append({
            "game_date": game_date,
            "league": league_from_market(market),
            "market": market,
            "away_team": away_team,
            "home_team": home_team,
            "away_score": str(away_score),
            "home_score": str(home_score),
            "total": str(total),
            "away_spread": away_spread,
            "home_spread": home_spread,
            "away_puck_line": away_puck_line,
            "home_puck_line": home_puck_line,
        })

    return rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    if len(sys.argv) != 3:
        print("Usage: espn.py <market: NBA|NCAAB|NHL> <input_text_file>")
        return 2

    market = normalize_market(sys.argv[1])
    input_path = Path(sys.argv[2])
    err_path = ERR_DIR / f"espn_{market}.txt"

    try:
        lines = input_path.read_text(encoding="utf-8", errors="replace").splitlines()
        game_date = parse_game_date(lines)

        team_map = load_team_map(market)

        rows = parse_games(lines, game_date, market, team_map)

        out_path = OUT_DIR / f"{game_date}_final_scores_{market}.csv"
        write_csv(out_path, rows)

        print(f"Wrote {out_path} | rows={len(rows)}")
        return 0

    except Exception as e:
        with err_path.open("w", encoding="utf-8") as f:
            f.write(str(e) + "\n\n")
            f.write(traceback.format_exc())
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
