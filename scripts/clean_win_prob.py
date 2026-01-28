#!/usr/bin/env python3

import csv
import re
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook

# ============================================================
# Paths
# ============================================================

INPUT_DIR = Path("docs/win/dump")
OUTPUT_DIR = Path("docs/win/clean")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Shared helpers
# ============================================================

def load_rows(path):
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    return list(ws.iter_rows(values_only=True))[1:]


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def split_datetime(cell):
    if not cell:
        return "", ""
    lines = str(cell).splitlines()
    return (
        lines[0] if len(lines) > 0 else "",
        lines[1] if len(lines) > 1 else "",
    )


def strip_team(name):
    if not name:
        return ""
    s = str(name)
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\s+\d+\s*-\s*\d+\s*$", "", s)
    return s.strip()


def pct_to_decimal(value):
    if not value:
        return ""
    s = str(value).strip()
    return str(float(s[:-1]) / 100) if s.endswith("%") else s


def round_prob(value):
    try:
        return f"{round(float(value), 2):.2f}"
    except Exception:
        return ""


def extract_teams(cell):
    lines = str(cell).splitlines() if cell else []
    return (
        strip_team(lines[0]) if len(lines) > 0 else "",
        strip_team(lines[1]) if len(lines) > 1 else "",
    )


def extract_split(cell):
    lines = str(cell).splitlines() if cell else []
    return (
        lines[0] if len(lines) > 0 else "",
        lines[1] if len(lines) > 1 else "",
    )

# ============================================================
# Soccer
# ============================================================

SOCCER_HEADERS = [
    "date", "time", "team", "opponent",
    "goals", "total_goals",
    "win_probability", "draw_probability",
    "best_ou", "bet_type", "league"
]

def parse_best_ou_soccer(value):
    m = re.search(r"(\d+)", str(value)) if value else None
    return f"{m.group(1)}.5" if m else ""


def run_soccer():
    for path in sorted(INPUT_DIR.glob("soc_*.xlsx")):
        rows = load_rows(path)
        output = []

        for row in rows:
            if not row or (not row[1] and not row[2] and not row[4]):
                continue

            date, time = split_datetime(row[0])
            team_a, team_b = extract_teams(row[1])
            win_a, win_b = extract_split(row[2])
            draw = pct_to_decimal(row[3])
            goals_a, goals_b = extract_split(row[4])
            total_goals = row[5] or ""
            best_ou = parse_best_ou_soccer(row[6])

            output += [
                [date, time, team_a, team_b, goals_a, total_goals,
                 pct_to_decimal(win_a), draw, best_ou, "win", "soc"],
                [date, time, team_b, team_a, goals_b, total_goals,
                 pct_to_decimal(win_b), draw, best_ou, "win", "soc"],
                [date, time, "DRAW", f"{team_a} vs {team_b}", "",
                 total_goals, "", draw, best_ou, "draw", "soc"],
            ]

        if not output:
            continue

        file_date = datetime.strptime(
            rows[0][0].splitlines()[0], "%m/%d/%Y"
        ).strftime("%Y-%m-%d")

        write_csv(
            OUTPUT_DIR / f"win_prob__clean_soc_{file_date}.csv",
            SOCCER_HEADERS,
            output
        )

# ============================================================
# NHL
# ============================================================

NHL_HEADERS = [
    "date", "time", "team", "opponent",
    "goals", "total_goals",
    "win_probability", "best_ou", "league"
]

def parse_best_ou_nhl(value):
    nums = re.findall(r"\d+\.?\d*", str(value).lower()) if value else []
    return f"{int(float(nums[0]))}.5" if nums else ""


def run_nhl():
    for path in sorted(INPUT_DIR.glob("nhl_*.xlsx")):
        rows = load_rows(path)
        output = []
        file_date = ""

        for row in rows:
            if not any(row):
                continue

            date, time = split_datetime(row[0])
            if date and not file_date:
                file_date = datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")

            team_a, team_b = extract_teams(row[1])
            win_a, win_b = extract_split(row[2])
            goals_a, goals_b = extract_split(row[3])
            total_goals = row[4] or ""
            best_ou = parse_best_ou_nhl(row[5])

            output += [
                [date, time, team_a, team_b, goals_a,
                 total_goals, pct_to_decimal(win_a), best_ou, "nhl"],
                [date, time, team_b, team_a, goals_b,
                 total_goals, pct_to_decimal(win_b), best_ou, "nhl"],
            ]

        if output:
            write_csv(
                OUTPUT_DIR / f"win_prob__clean_nhl_{file_date}.csv",
                NHL_HEADERS,
                output
            )

# ============================================================
# NBA
# ============================================================

NBA_HEADERS = [
    "date", "time", "team", "opponent",
    "points", "total_points",
    "win_probability", "best_ou", "league"
]

def parse_best_ou_nba(raw):
    if not raw:
        return ""
    s = str(raw).lower().replace("½", ".5")
    if not (s.startswith("o") or s.startswith("u")):
        return ""
    s = s[1:].split("-")[0]
    return f"{int(float(s))}.5"


def run_nba():
    for path in sorted(INPUT_DIR.glob("nba_*.xlsx")):
        rows = load_rows(path)
        output = []
        file_date = ""

        for row in rows:
            if not row or not row[0] or not row[1]:
                continue

            date, time = split_datetime(row[0])
            if not file_date:
                file_date = datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")

            team_a, team_b = extract_teams(row[1])
            win_a, win_b = extract_split(row[2])
            pts_a, pts_b = extract_split(row[3])
            total = row[4] or ""
            best_ou = parse_best_ou_nba(row[5])

            output += [
                [date, time, team_a, team_b, pts_a, total,
                 pct_to_decimal(win_a), best_ou, "nba"],
                [date, time, team_b, team_a, pts_b, total,
                 pct_to_decimal(win_b), best_ou, "nba"],
            ]

        if output:
            write_csv(
                OUTPUT_DIR / f"win_prob__clean_nba_{file_date}.csv",
                NBA_HEADERS,
                output
            )

# ============================================================
# NCAAB
# ============================================================

NCAAB_HEADERS = NBA_HEADERS

def parse_best_ou_ncaab(value):
    nums = re.findall(r"\d+", str(value)) if value else []
    return f"{nums[0]}.5" if nums else ""


def run_ncaab():
    for path in sorted(INPUT_DIR.glob("ncaab_*.xlsx")):
        rows = load_rows(path)
        output = []
        file_date = ""

        for row in rows:
            if not row or not row[0] or not row[1]:
                continue

            date, time = split_datetime(row[0])
            if not file_date:
                file_date = datetime.strptime(date, "%m/%d/%Y").strftime("%Y_%m_%d")

            team_a, team_b = extract_teams(row[1])
            win_a, win_b = extract_split(row[2])
            pts_a, pts_b = extract_split(row[3])
            total = row[4] or ""
            best_ou = parse_best_ou_ncaab(row[5])

            output += [
                [date, time, team_a, team_b, pts_a, total,
                 round_prob(pct_to_decimal(win_a)), best_ou, "ncaab"],
                [date, time, team_b, team_a, pts_b, total,
                 round_prob(pct_to_decimal(win_b)), best_ou, "ncaab"],
            ]

        if output:
            write_csv(
                OUTPUT_DIR / f"win_prob__clean_ncaab_{file_date}.csv",
                NCAAB_HEADERS,
                output
            )

# ============================================================
# Main
# ============================================================

def main():
    run_soccer()
    run_nhl()
    run_nba()
    run_ncaab()


if __name__ == "__main__":
    main()
