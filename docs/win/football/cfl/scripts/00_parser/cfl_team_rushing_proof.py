#!/usr/bin/env python3
"""
Proof parser for one CFL GAME ANALYSIS raw TXT/PDF pair.

Reads:
    docs/win/football/cfl/data_dump/raw_txt/2023_week_01_game_analysis_report_20260627_142918.txt
    docs/win/football/cfl/data_dump/raw_pdf/2023_week_01_game_analysis_report_20260627_142918.pdf

Writes:
    docs/win/football/cfl/data_dump/proof/team_rushing_proof.csv
"""

from __future__ import annotations

import csv
import re
from pathlib import Path


DUMP_ID = "2023_week_01_game_analysis_report_20260627_142918"

TXT_PATH = Path(
    "docs/win/football/cfl/data_dump/raw_txt/"
    "2023_week_01_game_analysis_report_20260627_142918.txt"
)

PDF_PATH = Path(
    "docs/win/football/cfl/data_dump/raw_pdf/"
    "2023_week_01_game_analysis_report_20260627_142918.pdf"
)

OUT_PATH = Path("docs/win/football/cfl/data_dump/proof/team_rushing_proof.csv")


TEAM_ORDER = [
    "BC",
    "CGY",
    "EDM",
    "HAM",
    "MTL",
    "OTT",
    "SSK",
    "TOR",
    "WPG",
    "CFL",
]


OUTPUT_COLUMNS = [
    "dump_id",
    "season",
    "week",
    "report_type",
    "team",

    "team_rush_atts",
    "team_rush_yards",
    "team_rush_avg",
    "team_rush_td",
    "team_rush_10_plus",
    "team_rush_20_plus",
    "team_rush_yards_per_game",

    "first_down_rush_atts",
    "first_down_rush_yards",
    "first_down_rush_avg",

    "qb_rush_atts",
    "qb_rush_yards",
    "qb_escape_runs",

    "opponent_rush_atts",
    "opponent_rush_yards",
    "opponent_rush_avg",
    "opponent_rush_td",
    "opponent_rush_10_plus",
    "opponent_rush_20_plus",

    "source_txt_path",
    "source_pdf_path",
    "pdf_pages",
    "row_parse_status",
]


VALUE_COLUMNS = [
    "team_rush_atts",
    "team_rush_yards",
    "team_rush_avg",
    "team_rush_td",
    "team_rush_10_plus",
    "team_rush_20_plus",
    "team_rush_yards_per_game",

    "first_down_rush_atts",
    "first_down_rush_yards",
    "first_down_rush_avg",

    "qb_rush_atts",
    "qb_rush_yards",
    "qb_escape_runs",

    "opponent_rush_atts",
    "opponent_rush_yards",
    "opponent_rush_avg",
    "opponent_rush_td",
    "opponent_rush_10_plus",
    "opponent_rush_20_plus",
]


DUMP_ID_RE = re.compile(
    r"^(?P<season>\d{4})_week_(?P<week>\d{2})_(?P<report_slug>.+)_(?P<timestamp>\d{8}_\d{6})$"
)


def parse_dump_id(dump_id: str) -> dict[str, str]:
    match = DUMP_ID_RE.match(dump_id)

    if not match:
        raise ValueError(f"Bad dump_id format: {dump_id}")

    return {
        "season": match.group("season"),
        "week": str(int(match.group("week"))),
        "report_type": match.group("report_slug").replace("_", " ").upper(),
    }


def count_pdf_pages(pdf_path: Path) -> str:
    data = pdf_path.read_bytes()
    matches = re.findall(rb"/Type\s*/Page(?!s)\b", data)
    return str(len(matches))


def extract_rushing_section(text: str) -> list[str]:
    lines = text.splitlines()

    start_index = None
    end_index = None

    for idx, line in enumerate(lines):
        if "RUSHING ANALYSIS" in line:
            start_index = idx
            break

    if start_index is None:
        raise ValueError("Could not find RUSHING ANALYSIS section")

    for idx in range(start_index + 1, len(lines)):
        if "10a. PASSING ANALYSIS" in lines[idx]:
            end_index = idx
            break

    if end_index is None:
        raise ValueError("Could not find end of RUSHING ANALYSIS section")

    return lines[start_index:end_index]


def first_team_line(section_lines: list[str], team: str) -> str:
    pattern = re.compile(rf"^{re.escape(team)}\s+")

    for line in section_lines:
        cleaned = line.strip()

        if pattern.match(cleaned):
            return cleaned

    raise ValueError(f"Could not find rushing row for team: {team}")


def numeric_values_from_team_line(line: str, expected_count: int = 19) -> tuple[list[str], str]:
    parts = line.split(maxsplit=1)

    if len(parts) != 2:
        return [], "BAD_ROW"

    values_text = parts[1]

    values = re.findall(r"[-+]?\d+(?:\.\d+)?", values_text)

    if len(values) >= expected_count:
        return values[:expected_count], "OK"

    padded = values + [""] * (expected_count - len(values))
    return padded, f"SHORT_ROW_{len(values)}_OF_{expected_count}"


def build_rows() -> list[dict[str, str]]:
    if not TXT_PATH.exists():
        raise FileNotFoundError(f"Missing TXT file: {TXT_PATH}")

    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Missing PDF file: {PDF_PATH}")

    metadata = parse_dump_id(DUMP_ID)
    pdf_pages = count_pdf_pages(PDF_PATH)

    text = TXT_PATH.read_text(encoding="utf-8", errors="replace")
    rushing_section = extract_rushing_section(text)

    rows: list[dict[str, str]] = []

    for team in TEAM_ORDER:
        line = first_team_line(rushing_section, team)
        values, row_status = numeric_values_from_team_line(line)

        row = {
            "dump_id": DUMP_ID,
            "season": metadata["season"],
            "week": metadata["week"],
            "report_type": metadata["report_type"],
            "team": team,
            "source_txt_path": str(TXT_PATH),
            "source_pdf_path": str(PDF_PATH),
            "pdf_pages": pdf_pages,
            "row_parse_status": row_status,
        }

        for column, value in zip(VALUE_COLUMNS, values):
            row[column] = value

        rows.append(row)

    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = build_rows()
    write_csv(rows)

    print(f"proof_output={OUT_PATH}")
    print(f"rows={len(rows)}")


if __name__ == "__main__":
    main()
