#!/usr/bin/env python3
"""
parse_cfl_dump.py

First-pass parser for pasted CFL report dumps.

Input:
    Raw text file already saved in repo by docs/cfl_data_dump.html

Outputs:
    docs/win/football/cfl/data_dump/json/{dump_id}.json
    docs/win/football/cfl/data_dump/summary/{dump_id}_summary.json
    docs/win/football/cfl/data_dump/csv/{dump_id}_lines.csv
    docs/win/football/cfl/data_dump/csv/{dump_id}_sections.csv
    docs/win/football/cfl/data_dump/csv/{dump_id}_section_rows.csv

Purpose:
    Preserve all raw report data while creating structured first-pass outputs.
    This does not assume every CFL report table has the same shape.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEAM_PREFIXES = [
    "BC",
    "CGY",
    "CALGARY",
    "EDM",
    "EDMONTON",
    "HAM",
    "HAMILTON",
    "MTL",
    "MONTRÉAL",
    "MONTREAL",
    "OTT",
    "OTTAWA",
    "SSK",
    "SASKATCHEWAN",
    "TOR",
    "TORONTO",
    "WPG",
    "WINNIPEG",
    "CFL",
]

SECTION_PATTERNS = [
    re.compile(r"^\s*\d+[A-Za-z]?\.\s+.+"),
    re.compile(r"^\s*\d{4}\s+CFL\s+.+", re.IGNORECASE),
    re.compile(r"^\s*CFL\s+\d{4}\s+.+", re.IGNORECASE),
    re.compile(r"^\s*CFL\s+INDIVIDUAL\s+LEADERS\b.*", re.IGNORECASE),
    re.compile(r"^\s*TEAM\s+STATISTICS\b.*", re.IGNORECASE),
    re.compile(r"^\s*OPPONENT\s+STATISTICS\b.*", re.IGNORECASE),
    re.compile(r"^\s*POSSESSIONS,\s+BIG\s+PLAYS.*", re.IGNORECASE),
    re.compile(r"^\s*TURNOVER\s+&\s+PENALTY.*", re.IGNORECASE),
    re.compile(r"^\s*CFL\s+SPECIAL\s+TEAMS\b.*", re.IGNORECASE),
    re.compile(r"^\s*BASE\s+PASSING\s+STATISTICS\b.*", re.IGNORECASE),
    re.compile(r"^\s*ADDITIONAL\s+PASSING\s+STATISTICS\b.*", re.IGNORECASE),
    re.compile(r"^\s*RUSHING\s+LEADERS\b.*", re.IGNORECASE),
    re.compile(r"^\s*RECEIVING\b.*", re.IGNORECASE),
    re.compile(r"^\s*FIELD\s+GOALS\s+&\s+CONVERTS\b.*", re.IGNORECASE),
    re.compile(r"^\s*PUNTS\s+&\s+KICKOFFS\b.*", re.IGNORECASE),
    re.compile(r"^\s*PUNT\s+RETURNS\b.*", re.IGNORECASE),
    re.compile(r"^\s*DEFENSIVE\s+RETURNS\b.*", re.IGNORECASE),
    re.compile(r"^\s*QB\s+SACKS\b.*", re.IGNORECASE),
    re.compile(r"^\s*DEFENSIVE\s+TACKLES\b.*", re.IGNORECASE),
    re.compile(r"^\s*SPECIAL\s+TEAMS\s+TACKLES\b.*", re.IGNORECASE),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--report-type", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--week", required=True)
    parser.add_argument("--through-game", default="")
    parser.add_argument("--report-date", default="")
    parser.add_argument("--raw-path", required=True)
    parser.add_argument("--dump-id", required=True)
    parser.add_argument(
        "--output-root",
        default="docs/win/football/cfl/data_dump",
    )

    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: str | int | None) -> int | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        return int(text)
    except ValueError:
        return None


def normalize_text(text: str) -> str:
    replacements = {
        "\r\n": "\n",
        "\r": "\n",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00a0": " ",
        "\ufeff": "",
    }

    out = text

    for old, new in replacements.items():
        out = out.replace(old, new)

    return out


def compact_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_report_type(text: str) -> str | None:
    upper = text.upper()

    if "GAME ANALYSIS REPORT" in upper:
        return "GAME ANALYSIS REPORT"

    if "CFL STATISTICS" in upper or "STATISTICS REPORT" in upper:
        return "CFL STATISTICS REPORT"

    return None


def detect_season(text: str) -> int | None:
    patterns = [
        r"\bCFL\s+(20\d{2})\b",
        r"\b(20\d{2})\s+CFL\b",
        r"\b(20\d{2})\s+CFL\s+STATISTICS\b",
        r"\bCFL-WIDE\s+IN\s+(20\d{2})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return safe_int(match.group(1))

    match = re.search(r"\b20\d{2}\b", text)

    if match:
        return safe_int(match.group(0))

    return None


def detect_week(text: str) -> int | None:
    patterns = [
        r"\bTHROUGH\s+CFL\s+WEEK\s*#:\s*(\d+)",
        r"\bTO\s+CFL\s+WEEK\s*#:\s*(\d+)",
        r"\bTO\s+WEEK\s*:\s*(\d+)",
        r"\bWK\s*#:\s*(\d+)",
        r"\bWEEK\s*#:\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return safe_int(match.group(1))

    return None


def detect_through_game(text: str) -> int | None:
    patterns = [
        r"\bTHROUGH\s+GM\s*#:\s*(\d+)",
        r"\bTO\s+GAME\s*#:\s*(\d+)",
        r"\bTO\s+GM\s*#:\s*(\d+)",
        r"\bGAME\s*#:\s*(\d+)",
        r"\bGM\s*#:\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return safe_int(match.group(1))

    return None


def detect_report_date(text: str) -> str | None:
    month_map = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "sept": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }

    pattern = re.compile(
        r"\b("
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
        r")[a-z]*\s+(\d{1,2})/(\d{2,4})\b",
        flags=re.IGNORECASE,
    )

    matches = list(pattern.finditer(text))

    if not matches:
        return None

    match = matches[-1]
    month_raw = match.group(1).lower()
    day = int(match.group(2))
    year_raw = match.group(3)

    if len(year_raw) == 2:
        year = int("20" + year_raw)
    else:
        year = int(year_raw)

    month = month_map.get(month_raw[:3])

    if not month:
        return None

    return f"{year:04d}-{month}-{day:02d}"


def is_section_heading(line: str) -> bool:
    clean = compact_spaces(line)

    if len(clean) < 5:
        return False

    for pattern in SECTION_PATTERNS:
        if pattern.match(clean):
            return True

    return False


def split_sections(lines: list[str]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for idx, line in enumerate(lines, start=1):
        if is_section_heading(line):
            if current is not None:
                current["end_line"] = idx - 1
                current["line_count"] = (
                    current["end_line"] - current["start_line"] + 1
                )
                sections.append(current)

            current = {
                "section_index": len(sections) + 1,
                "title": compact_spaces(line),
                "start_line": idx,
                "end_line": idx,
                "line_count": 1,
                "lines": [],
            }

        if current is None:
            current = {
                "section_index": 1,
                "title": "document_start",
                "start_line": idx,
                "end_line": idx,
                "line_count": 1,
                "lines": [],
            }

        current["lines"].append(
            {
                "line_no": idx,
                "text": line,
            }
        )

    if current is not None:
        current["end_line"] = len(lines)
        current["line_count"] = (
            current["end_line"] - current["start_line"] + 1
        )
        sections.append(current)

    return sections


def tokenize_line(line: str) -> list[str]:
    clean = compact_spaces(line)

    if not clean:
        return []

    return clean.split(" ")


def count_numbers(line: str) -> int:
    return len(
        re.findall(
            r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?",
            line,
        )
    )


def starts_with_team(line: str) -> bool:
    clean = compact_spaces(line)
    upper = clean.upper()

    for prefix in TEAM_PREFIXES:
        if upper == prefix:
            return True

        if upper.startswith(prefix + " "):
            return True

        if upper.startswith(prefix + "-"):
            return True

    return False


def looks_like_player_line(line: str) -> bool:
    clean = compact_spaces(line)

    if not clean:
        return False

    if re.match(r"^[A-ZÀ-ÖØ-Þ.'\- ]+,\s+[A-ZÀ-ÖØ-Þ.'\- ]+\s+", clean):
        return True

    if re.match(r"^[A-ZÀ-ÖØ-Þ.'\-]+\s+[A-ZÀ-ÖØ-Þ.'\-]+\s+[A-Z]{2,3}\s+", clean):
        return True

    return False


def classify_row(line: str) -> str | None:
    clean = compact_spaces(line)

    if not clean:
        return None

    if starts_with_team(clean):
        return "team"

    if looks_like_player_line(clean):
        return "player"

    if count_numbers(clean) >= 3:
        return "numeric"

    return None


def build_section_rows(
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for section in sections:
        section_rows = []

        for item in section["lines"]:
            line = item["text"]
            row_type = classify_row(line)

            if row_type is None:
                continue

            row = {
                "section_index": section["section_index"],
                "section_title": section["title"],
                "line_no": item["line_no"],
                "row_type": row_type,
                "raw_line": compact_spaces(line),
                "tokens": tokenize_line(line),
                "number_count": count_numbers(line),
            }

            section_rows.append(row)
            rows.append(row)

        section["rows"] = section_rows
        section["row_count"] = len(section_rows)

    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_lines_csv(
    path: Path,
    dump_id: str,
    lines: list[str],
    sections: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    section_by_line: dict[int, dict[str, Any]] = {}

    for section in sections:
        for line_no in range(section["start_line"], section["end_line"] + 1):
            section_by_line[line_no] = section

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dump_id",
                "line_no",
                "section_index",
                "section_title",
                "text",
            ],
        )
        writer.writeheader()

        for idx, line in enumerate(lines, start=1):
            section = section_by_line.get(idx, {})

            writer.writerow(
                {
                    "dump_id": dump_id,
                    "line_no": idx,
                    "section_index": section.get("section_index", ""),
                    "section_title": section.get("title", ""),
                    "text": line,
                }
            )


def write_sections_csv(
    path: Path,
    dump_id: str,
    sections: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dump_id",
                "section_index",
                "title",
                "start_line",
                "end_line",
                "line_count",
                "row_count",
            ],
        )
        writer.writeheader()

        for section in sections:
            writer.writerow(
                {
                    "dump_id": dump_id,
                    "section_index": section["section_index"],
                    "title": section["title"],
                    "start_line": section["start_line"],
                    "end_line": section["end_line"],
                    "line_count": section["line_count"],
                    "row_count": section.get("row_count", 0),
                }
            )


def write_section_rows_csv(
    path: Path,
    dump_id: str,
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dump_id",
                "section_index",
                "section_title",
                "line_no",
                "row_type",
                "number_count",
                "raw_line",
                "tokens_json",
            ],
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "dump_id": dump_id,
                    "section_index": row["section_index"],
                    "section_title": row["section_title"],
                    "line_no": row["line_no"],
                    "row_type": row["row_type"],
                    "number_count": row["number_count"],
                    "raw_line": row["raw_line"],
                    "tokens_json": json.dumps(
                        row["tokens"],
                        ensure_ascii=False,
                    ),
                }
            )


def main() -> int:
    args = parse_args()

    raw_path = Path(args.raw_path)
    output_root = Path(args.output_root)
    dump_id = args.dump_id.strip()

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw path does not exist: {raw_path}")

    raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
    text = normalize_text(raw_text)
    lines = text.split("\n")

    manual_season = safe_int(args.season)
    manual_week = safe_int(args.week)
    manual_through_game = safe_int(args.through_game)

    detected_report_type = detect_report_type(text)
    detected_season = detect_season(text)
    detected_week = detect_week(text)
    detected_through_game = detect_through_game(text)
    detected_report_date = detect_report_date(text)

    sections = split_sections(lines)
    section_rows = build_section_rows(sections)

    row_type_counts = Counter(row["row_type"] for row in section_rows)

    manual_report_type = args.report_type.strip()
    manual_report_date = args.report_date.strip()

    metadata = {
        "dump_id": dump_id,
        "created_at_utc": utc_now_iso(),
        "manual": {
            "report_type": manual_report_type,
            "season": manual_season,
            "week": manual_week,
            "through_game": manual_through_game,
            "report_date": manual_report_date,
            "raw_path": str(raw_path),
        },
        "detected": {
            "report_type": detected_report_type,
            "season": detected_season,
            "week": detected_week,
            "through_game": detected_through_game,
            "report_date": detected_report_date,
        },
        "matches": {
            "report_type_match": (
                detected_report_type == manual_report_type
                if detected_report_type
                else None
            ),
            "season_match": (
                detected_season == manual_season
                if detected_season and manual_season
                else None
            ),
            "week_match": (
                detected_week == manual_week
                if detected_week and manual_week
                else None
            ),
            "through_game_match": (
                detected_through_game == manual_through_game
                if detected_through_game and manual_through_game
                else None
            ),
        },
    }

    files = {
        "raw": str(raw_path),
        "json": str(output_root / "json" / f"{dump_id}.json"),
        "summary": str(output_root / "summary" / f"{dump_id}_summary.json"),
        "lines_csv": str(output_root / "csv" / f"{dump_id}_lines.csv"),
        "sections_csv": str(output_root / "csv" / f"{dump_id}_sections.csv"),
        "section_rows_csv": str(
            output_root / "csv" / f"{dump_id}_section_rows.csv"
        ),
    }

    full_json = {
        "metadata": metadata,
        "files": files,
        "line_count": len(lines),
        "section_count": len(sections),
        "section_row_count": len(section_rows),
        "row_type_counts": dict(row_type_counts),
        "lines": [
            {
                "line_no": idx,
                "text": line,
            }
            for idx, line in enumerate(lines, start=1)
        ],
        "sections": sections,
    }

    summary_json = {
        "metadata": metadata,
        "files": files,
        "line_count": len(lines),
        "section_count": len(sections),
        "section_row_count": len(section_rows),
        "row_type_counts": dict(row_type_counts),
        "sections": [
            {
                "section_index": section["section_index"],
                "title": section["title"],
                "start_line": section["start_line"],
                "end_line": section["end_line"],
                "line_count": section["line_count"],
                "row_count": section.get("row_count", 0),
            }
            for section in sections
        ],
    }

    write_json(output_root / "json" / f"{dump_id}.json", full_json)
    write_json(output_root / "summary" / f"{dump_id}_summary.json", summary_json)

    write_lines_csv(
        output_root / "csv" / f"{dump_id}_lines.csv",
        dump_id,
        lines,
        sections,
    )

    write_sections_csv(
        output_root / "csv" / f"{dump_id}_sections.csv",
        dump_id,
        sections,
    )

    write_section_rows_csv(
        output_root / "csv" / f"{dump_id}_section_rows.csv",
        dump_id,
        section_rows,
    )

    print(json.dumps(summary_json, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
