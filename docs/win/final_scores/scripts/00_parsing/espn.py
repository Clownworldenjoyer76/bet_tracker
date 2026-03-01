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
    if market in {"NBA", "NCAAB"}:
        return "Basketball"
    if market == "NHL":
        return "Hockey"
    return ""


def parse_game_date(lines: list[str]) -> str:
    # Expect: "Tuesday, February 24, 2026"
    for line in lines[:20]:
        s = line.strip()
        if not s:
            continue
        try:
            dt = datetime.strptime(s, "%A, %B %d, %Y")
            return dt.strftime("%Y_%m_%d")
        except Exception:
            continue
    raise ValueError("Could not find/parse game date line like 'Tuesday, February 24, 2026'")


def next_non_empty(lines: list[str], start_idx: int) -> tuple[int, str]:
    i = start_idx
    while i < len(lines):
        s = lines[i].strip()
        if s:
            return i, s
        i += 1
    return len(lines), ""


def prev_non_empty(lines: list[str], start_idx: int) -> tuple[int, str]:
    i = start_idx
    while i >= 0:
        s = lines[i].strip()
        if s:
            return i, s
        i -= 1
    return -1, ""


def is_at_line(s: str) -> bool:
    return s.strip() == "@"


def looks_like_result_line(s: str) -> bool:
    # Must contain comma and at least two integers
    if "," not in s:
        return False
    nums = re.findall(r"\d+", s)
    return len(nums) >= 2


def parse_scores_from_result_line(s: str) -> tuple[int, int]:
    nums = re.findall(r"\d+", s)
    if len(nums) < 2:
        raise ValueError(f"Could not parse two scores from result line: {s}")
    away_score = int(nums[0])
    home_score = int(nums[1])
    return away_score, home_score


def parse_games(lines: list[str], game_date: str, market: str) -> list[dict]:
    rows = []
    is_basketball = market in {"NBA", "NCAAB"}
    is_hockey = market == "NHL"

    for i, raw in enumerate(lines):
        s = raw.strip()
        if not is_at_line(s):
            continue

        _, away_team = prev_non_empty(lines, i - 1)
        _, home_team = next_non_empty(lines, i + 1)

        if not away_team or not home_team:
            continue

        # Find the next result line after home team
        j, candidate = next_non_empty(lines, i + 2)
        # Some pages have extra tokens before result; scan forward a bit
        scan_limit = min(len(lines), j + 20)
        result_line = ""
        k = j
        while k < scan_limit:
            cand = lines[k].strip()
            if looks_like_result_line(cand):
                result_line = cand
                break
            k += 1

        if not result_line:
            continue

        away_score, home_score = parse_scores_from_result_line(result_line)
        total = away_score + home_score

        away_spread = ""
        home_spread = ""
        away_puck_line = ""
        home_puck_line = ""

        if is_basketball:
            away_spread = str(away_score - home_score)
            home_spread = str(home_score - away_score)

        if is_hockey:
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

    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in HEADERS})


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: espn.py <market: NBA|NCAAB|NHL> <input_text_file>")
        return 2

    market = normalize_market(sys.argv[1])
    input_path = Path(sys.argv[2])

    err_path = ERR_DIR / f"espn_{market}.txt"

    try:
        raw = input_path.read_text(encoding="utf-8", errors="replace")
        lines = raw.splitlines()

        game_date = parse_game_date(lines)
        rows = parse_games(lines, game_date, market)

        out_path = OUT_DIR / f"{game_date}_final_scores_{market}.csv"
        write_csv(out_path, rows)

        # Minimal stdout for workflow logs
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
