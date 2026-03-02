#!/usr/bin/env python3
# docs/win/final_scores/scripts/00_parsing/scores.py

import sys
import re
import csv
from pathlib import Path
from datetime import datetime
import traceback

OUT_DIR = Path("docs/win/final_scores")
ERR_DIR = OUT_DIR / "errors"

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


# =========================
# MARKET / LEAGUE
# =========================

def normalize_market(market: str) -> str:
    m = (market or "").strip().upper()
    if m in {"NBA", "NCAAB", "NCAAM"}:
        return "NCAAB" if m in {"NCAAB", "NCAAM"} else "NBA"
    if m == "NHL":
        return "NHL"
    raise ValueError("market must be one of: NBA, NCAAB, NHL")


def league_from_market(market: str) -> str:
    return "Basketball" if market in {"NBA", "NCAAB"} else "Hockey"


# =========================
# PARSING HELPERS
# =========================

DATE_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4}$")
TIME_REGEX = re.compile(r"^\d{2}:\d{2}\s*(AM|PM)$")


def is_date_line(s: str) -> bool:
    return bool(DATE_REGEX.match(s.strip()))


def is_time_prefix_line(s: str) -> bool:
    parts = s.split("\t")
    if not parts:
        return False
    return bool(TIME_REGEX.match(parts[0].strip()))


def parse_date_to_output_format(date_str: str) -> str:
    dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
    return dt.strftime("%Y_%m_%d")


def extract_away_team(line: str) -> str:
    parts = line.split("\t")
    if len(parts) > 1:
        return parts[1].strip()
    return re.sub(r"^\d{2}:\d{2}\s*(AM|PM)\s*", "", line).strip()


def extract_home_team(line: str) -> str:
    return line.split("\t")[0].strip()


def first_field_is_integer(line: str) -> bool:
    if not line.strip():
        return False
    first = line.split("\t")[0].strip()
    return first.isdigit()


def extract_first_integer(line: str) -> int:
    return int(line.split("\t")[0].strip())


# =========================
# CORE PARSER
# =========================

def parse_games(lines, market):
    rows = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Start of new game block
        if is_date_line(line):
            game_date = parse_date_to_output_format(line)

            # Next line: time + away team
            i += 1
            if i >= len(lines):
                break

            away_line = lines[i].strip()
            if not is_time_prefix_line(away_line):
                continue

            away_team = extract_away_team(away_line)

            # Next line: home team
            i += 1
            if i >= len(lines):
                break

            home_line = lines[i].strip()
            home_team = extract_home_team(home_line)

            # Find away_score and home_score
            scores = []
            j = i + 1

            while j < len(lines) and len(scores) < 2:
                candidate = lines[j].strip()
                if first_field_is_integer(candidate):
                    scores.append(extract_first_integer(candidate))
                j += 1

            if len(scores) != 2:
                i += 1
                continue

            away_score = scores[0]
            home_score = scores[1]

            total = away_score + home_score

            away_spread = ""
            home_spread = ""
            away_puck_line = ""
            home_puck_line = ""

            if market in {"NBA", "NCAAB"}:
                away_spread = str(away_score - home_score)
                home_spread = str(home_score - away_score)

            if market == "NHL":
                away_puck_line = str(away_score - home_score)
                home_puck_line = str(home_score - away_score)

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

            i = j
            continue

        i += 1

    if not rows:
        raise ValueError("No games parsed from input.")

    return rows


# =========================
# CSV WRITER
# =========================

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


# =========================
# MAIN
# =========================

def main():
    if len(sys.argv) != 3:
        print("Usage: scores.py <market: NBA|NCAAB|NHL> <input_text_file>")
        return 2

    market = normalize_market(sys.argv[1])
    input_path = Path(sys.argv[2])
    err_path = ERR_DIR / f"scores_{market}.txt"

    try:
        lines = input_path.read_text(encoding="utf-8", errors="replace").splitlines()

        rows = parse_games(lines, market)

        game_date = rows[0]["game_date"]
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
