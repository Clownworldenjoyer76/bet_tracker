#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
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

OUT_DIR = Path("docs/win/football/cfl/data_dump/proof/game_analysis_v2")

TEAM_ORDER = ["BC", "CGY", "EDM", "HAM", "MTL", "OTT", "SSK", "TOR", "WPG", "CFL"]
TEAM_RE = re.compile(r"^(BC|CGY|EDM|HAM|MTL|OTT|SSK|TOR|WPG|CFL)\b")

DUMP_ID_RE = re.compile(
    r"^(?P<season>\d{4})_week_(?P<week>\d{2})_(?P<report_slug>.+)_(?P<timestamp>\d{8}_\d{6})$"
)

BASE_COLUMNS = ["dump_id", "season", "week", "report_type", "team"]

SOURCE_COLUMNS = [
    "source_txt_path",
    "source_pdf_path",
    "pdf_pages",
    "row_parse_status",
]


@dataclass(frozen=True)
class TableSpec:
    filename: str
    start_marker: str
    end_marker: str
    value_columns: list[str]
    mode: str = "default"


def parse_dump_id() -> dict[str, str]:
    match = DUMP_ID_RE.match(DUMP_ID)

    if not match:
        raise ValueError(f"Bad dump_id format: {DUMP_ID}")

    return {
        "season": match.group("season"),
        "week": str(int(match.group("week"))),
        "report_type": match.group("report_slug").replace("_", " ").upper(),
    }


def count_pdf_pages() -> str:
    data = PDF_PATH.read_bytes()
    return str(len(re.findall(rb"/Type\s*/Page(?!s)\b", data)))


def parse_games_played(text: str) -> str:
    match = re.search(r"GMS PLAYED:\s*(\d+)", text)
    return match.group(1) if match else ""


def read_text() -> str:
    if not TXT_PATH.exists():
        raise FileNotFoundError(f"Missing TXT file: {TXT_PATH}")

    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Missing PDF file: {PDF_PATH}")

    return TXT_PATH.read_text(encoding="utf-8", errors="replace")


def extract_section_lines(text: str, start_marker: str, end_marker: str) -> list[str]:
    lines = text.splitlines()

    start_idx = None
    end_idx = None

    for idx, line in enumerate(lines):
        if start_marker in line:
            start_idx = idx
            break

    if start_idx is None:
        raise ValueError(f"Missing section start: {start_marker}")

    for idx in range(start_idx + 1, len(lines)):
        if end_marker in lines[idx]:
            end_idx = idx
            break

    if end_idx is None:
        raise ValueError(f"Missing section end after {start_marker}: {end_marker}")

    return lines[start_idx:end_idx]


def collect_team_blocks(section_lines: list[str]) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_team: str | None = None
    current_lines: list[str] = []

    for raw_line in section_lines:
        line = raw_line.strip()

        if not line:
            continue

        match = TEAM_RE.match(line)

        if match:
            team = match.group(1)

            if current_team is not None and team != current_team and current_team not in blocks:
                blocks[current_team] = " ".join(current_lines)

            if current_team is None or team != current_team:
                current_team = team
                current_lines = [line]
            else:
                current_lines.append(line)

            continue

        if current_team is not None:
            current_lines.append(line)

    if current_team is not None and current_team not in blocks:
        blocks[current_team] = " ".join(current_lines)

    return blocks


def strip_team_tokens(text: str) -> str:
    return re.sub(r"\b(BC|CGY|EDM|HAM|MTL|OTT|SSK|TOR|WPG|CFL)\b", " ", text)


def clean_block(block: str, mode: str) -> str:
    out = block
    stops: list[str] = []

    if mode == "big_play":
        stops = ["Notes:", "1. Offence", "2. Returns", "K/O returns"]

    elif mode == "coaches":
        stops = [
            "Def. Pass",
            "Reception",
            "Roughing",
            "Fumble?",
            "No DPI",
            "No Yards?",
            "All Others",
            "BY TYPE",
        ]

    elif mode == "field_goals":
        out = re.sub(r"\s+[-+]?\d+(?:\.\d+)?\s+yds.*$", "", out)
        out = re.sub(r"\s+[-+]?\d+(?:\.\d+)?\s+PerG.*$", "", out)
        out = re.sub(r"\s+4th Quarter.*$", "", out)
        out = re.sub(r"\s+FG Atts.*$", "", out)
        out = re.sub(r"\s+Made\s+\d+.*$", "", out)
        out = re.sub(r"\s+%\s+100%.*$", "", out)
        out = re.sub(r"\s+Atts\s+\d+.*$", "", out)

    elif mode == "penalties":
        stops = ["PER GAME", "IN 2022", "IN 2021"]

    elif mode == "red_zone":
        stops = ["CFL RED ZONE FREQUENCY", "RED ZONE LEGEND:"]

    else:
        stops = ["Notes:"]

    for stop in stops:
        pos = out.find(stop)
        if pos != -1:
            out = out[:pos]

    return out


def parse_numeric_values(text: str) -> list[str]:
    text = strip_team_tokens(text)

    tokens = re.findall(
        r"#DIV/0!|###|T\d+|\([-+]?\d+(?:,\d{3})*(?:\.\d+)?\)|[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?",
        text,
    )

    values: list[str] = []

    for token in tokens:
        if token == "#DIV/0!":
            values.append("0")
        elif token == "###":
            values.append("")
        elif token.startswith("T") and token[1:].isdigit():
            values.append(token[1:])
        else:
            values.append(token.strip("()").replace(",", "").replace("%", ""))

    return values


def all_zero_or_blank(values: list[str]) -> bool:
    if not values:
        return False

    for value in values:
        if value == "":
            continue

        try:
            if float(value) != 0:
                return False
        except ValueError:
            return False

    return True


def zero_row(count: int) -> list[str]:
    return ["0"] * count


def normalize_for_spec(
    values: list[str],
    team: str,
    spec: TableSpec,
    games_played: str,
) -> tuple[list[str], str]:
    expected_count = len(spec.value_columns)
    mode = spec.mode

    if team != "CFL" and values and values[0] == "0" and len(values) < expected_count:
        return zero_row(expected_count), "OK_ZERO_GP"

    if mode == "coaches" and values and values[0] == "0":
        return zero_row(expected_count), "OK"

    if mode == "field_goals" and len(values) == expected_count - 1:
        if len(values) > 7 and values[5] == "0" and values[6] == "0":
            values = values[:7] + ["0"] + values[7:]
            return values[:expected_count], "OK"

        if (
            len(values) > 12
            and values[8] == "0"
            and values[9] == "0"
            and values[10] == "0"
            and values[11] == "0"
        ):
            values = values[:12] + ["0"] + values[12:]
            return values[:expected_count], "OK"

    if mode == "passing_base" and len(values) == expected_count - 1:
        if len(values) > 4 and values[4] == "0":
            values = values[:13] + [""] + values[13:]
            return values[:expected_count], "OK"

    if mode == "opponent_passing_base" and len(values) == expected_count - 1:
        if len(values) > 4 and values[4] == "0":
            values = values[:13] + [""] + values[13:]
            return values[:expected_count], "OK"

        if team == "CFL":
            values = values[:17] + [""] + values[17:]
            return values[:expected_count], "OK_AGGREGATE"

    if mode == "net_offence" and team == "CFL" and len(values) == 15:
        values = [
            values[0],
            values[1],
            values[2],
            values[3],
            values[4],
            values[5],
            "",
            values[6],
            values[7],
            "",
            values[8],
            values[9],
            values[10],
            values[11],
            values[12],
            values[13],
            values[14],
        ]
        return values, "OK_AGGREGATE"

    if mode == "penalties" and team == "CFL":
        if values and values[0] in {"2023", "2024", "2025", "2026"}:
            values = [games_played] + values[1:]
            return (values + [""] * expected_count)[:expected_count], "OK_AGGREGATE"

    if mode == "kick_returns" and team == "CFL" and len(values) == 23:
        values = values[:7] + [""] + values[7:13] + [""] + values[13:]
        return values, "OK_AGGREGATE"

    if team == "CFL" and len(values) < expected_count:
        return (values + [""] * expected_count)[:expected_count], "OK_AGGREGATE"

    if len(values) >= expected_count:
        return values[:expected_count], "OK"

    if all_zero_or_blank(values):
        if team == "CFL":
            return zero_row(expected_count), "OK_AGGREGATE"

        return zero_row(expected_count), "OK_ZERO_GP"

    return (values + [""] * expected_count)[:expected_count], (
        f"NEEDS_REVIEW_{len(values)}_OF_{expected_count}"
    )


def base_row(team: str, metadata: dict[str, str], pdf_pages: str, status: str) -> dict[str, str]:
    return {
        "dump_id": DUMP_ID,
        "season": metadata["season"],
        "week": metadata["week"],
        "report_type": metadata["report_type"],
        "team": team,
        "source_txt_path": str(TXT_PATH),
        "source_pdf_path": str(PDF_PATH),
        "pdf_pages": pdf_pages,
        "row_parse_status": status,
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def audit_entry(filename: str, rows: list[dict[str, str]]) -> dict[str, str]:
    statuses = [row.get("row_parse_status", "") for row in rows]

    return {
        "file_name": filename,
        "rows_written": str(len(rows)),
        "ok_rows": str(sum(status == "OK" for status in statuses)),
        "zero_gp_rows": str(sum(status == "OK_ZERO_GP" for status in statuses)),
        "aggregate_rows": str(sum(status == "OK_AGGREGATE" for status in statuses)),
        "needs_review_rows": str(sum(status.startswith("NEEDS_REVIEW") for status in statuses)),
        "missing_rows": str(sum(status == "MISSING_ROW" for status in statuses)),
        "status": (
            "OK"
            if all(status in {"OK", "OK_ZERO_GP", "OK_AGGREGATE"} for status in statuses)
            else "NEEDS_REVIEW"
        ),
    }


def write_generic_table(
    text: str,
    spec: TableSpec,
    metadata: dict[str, str],
    pdf_pages: str,
    games_played: str,
) -> dict[str, str]:
    rows: list[dict[str, str]] = []

    try:
        section_lines = extract_section_lines(text, spec.start_marker, spec.end_marker)
        blocks = collect_team_blocks(section_lines)
        missing_status = ""
    except Exception as exc:
        blocks = {}
        missing_status = f"MISSING_SECTION: {exc}"

    for team in TEAM_ORDER:
        block = blocks.get(team, "")

        if not block:
            values = [""] * len(spec.value_columns)
            status = missing_status or "MISSING_ROW"
        else:
            raw_values = parse_numeric_values(clean_block(block, spec.mode))
            values, status = normalize_for_spec(raw_values, team, spec, games_played)

        row = base_row(team, metadata, pdf_pages, status)

        for column, value in zip(spec.value_columns, values):
            row[column] = value

        rows.append(row)

    write_csv(OUT_DIR / spec.filename, BASE_COLUMNS + spec.value_columns + SOURCE_COLUMNS, rows)

    return audit_entry(spec.filename, rows)


def parse_top_block(block: str, expected_count: int) -> tuple[str, list[str], str]:
    match = re.search(r"\b\d{1,2}:\d{2}\b", block)
    top_value = match.group(0) if match else ""

    cleaned = block.replace(top_value, " ", 1) if top_value else block
    values = parse_numeric_values(cleaned)

    if len(values) >= expected_count:
        return top_value, values[:expected_count], "OK"

    if all_zero_or_blank(values):
        return top_value, zero_row(expected_count), "OK_ZERO_GP"

    return top_value, (values + [""] * expected_count)[:expected_count], (
        f"NEEDS_REVIEW_{len(values)}_OF_{expected_count}"
    )


def write_time_of_possession_table(
    text: str,
    metadata: dict[str, str],
    pdf_pages: str,
) -> dict[str, str]:
    value_columns = [
        "time_of_possession",
        "team_possessions",
        "team_field_position_yards",
        "team_avg_start_yard_line",
        "team_start_yard_line_rank",
        "opponent_end_start_count",
        "opponent_end_start_td",
        "start_yard_line_gap",
        "opponent_possessions",
        "opponent_field_position_yards",
        "opponent_avg_start_yard_line",
    ]

    numeric_columns = value_columns[1:]
    rows: list[dict[str, str]] = []

    try:
        section_lines = extract_section_lines(
            text,
            "4c. TIME OF POSSESSION & FIELD POSITION",
            "5. BIG PLAY ANALYSIS",
        )
        blocks = collect_team_blocks(section_lines)
        missing_status = ""
    except Exception as exc:
        blocks = {}
        missing_status = f"MISSING_SECTION: {exc}"

    for team in TEAM_ORDER:
        block = blocks.get(team, "")

        if not block:
            top_value = ""
            values = [""] * len(numeric_columns)
            status = missing_status or "MISSING_ROW"
        else:
            top_value, values, status = parse_top_block(block, len(numeric_columns))

        row = base_row(team, metadata, pdf_pages, status)
        row["time_of_possession"] = top_value

        for column, value in zip(numeric_columns, values):
            row[column] = value

        rows.append(row)

    filename = "time_of_possession_field_position.csv"

    write_csv(
        OUT_DIR / filename,
        BASE_COLUMNS + value_columns + SOURCE_COLUMNS,
        rows,
    )

    return audit_entry(filename, rows)


def write_first_down_tables(
    text: str,
    metadata: dict[str, str],
    pdf_pages: str,
) -> list[dict[str, str]]:
    offence_columns = [
        "team_first_down_plays",
        "team_first_down_avg_yards",
        "team_first_down_rank",
        "opponent_first_down_plays",
        "opponent_first_down_avg_yards",
        "opponent_first_down_rank",
    ]

    made_columns = [
        "first_down_call_rush",
        "first_down_call_pass_plus",
        "first_down_call_total",
        "team_first_downs_rush",
        "team_first_downs_pass",
        "team_first_downs_penalty",
        "team_first_downs_total",
        "opponent_first_downs_rush",
        "opponent_first_downs_pass",
        "opponent_first_downs_penalty",
    ]

    offence_rows: list[dict[str, str]] = []
    made_rows: list[dict[str, str]] = []

    try:
        section_lines = extract_section_lines(
            text,
            "8c. NET OFFENCE - ON 1ST DOWN",
            "9 RUSHING ANALYSIS",
        )
        blocks = collect_team_blocks(section_lines)
        missing_status = ""
    except Exception as exc:
        blocks = {}
        missing_status = f"MISSING_SECTION: {exc}"

    for team in TEAM_ORDER:
        block = blocks.get(team, "")

        if not block:
            values = [""] * 16
            status = missing_status or "MISSING_ROW"

        else:
            values = parse_numeric_values(clean_block(block, "default"))

            if team != "CFL" and values and values[0] == "0":
                values = zero_row(16)
                status = "OK_ZERO_GP"

            elif team == "CFL" and len(values) >= 14:
                call_total = (
                    str(int(float(values[4])) + int(float(values[5])))
                    if values[4] and values[5]
                    else ""
                )

                offence_values = [
                    values[0],
                    values[1],
                    "",
                    values[2],
                    values[3],
                    "",
                ]

                made_values = [
                    values[4],
                    values[5],
                    call_total,
                    values[7],
                    values[8],
                    values[9],
                    values[6],
                    values[11],
                    values[12],
                    values[13],
                ]

                status = "OK_AGGREGATE"

                offence_row = base_row(team, metadata, pdf_pages, status)
                made_row = base_row(team, metadata, pdf_pages, status)

                for column, value in zip(offence_columns, offence_values):
                    offence_row[column] = value

                for column, value in zip(made_columns, made_values):
                    made_row[column] = value

                offence_rows.append(offence_row)
                made_rows.append(made_row)
                continue

            elif len(values) >= 16:
                values = values[:16]
                status = "OK"

            else:
                original_len = len(values)
                values = (values + [""] * 16)[:16]
                status = f"NEEDS_REVIEW_{original_len}_OF_16"

        offence_row = base_row(team, metadata, pdf_pages, status)
        made_row = base_row(team, metadata, pdf_pages, status)

        for column, value in zip(offence_columns, values[:6]):
            offence_row[column] = value

        for column, value in zip(made_columns, values[6:16]):
            made_row[column] = value

        offence_rows.append(offence_row)
        made_rows.append(made_row)

    write_csv(
        OUT_DIR / "first_down_offence.csv",
        BASE_COLUMNS + offence_columns + SOURCE_COLUMNS,
        offence_rows,
    )

    write_csv(
        OUT_DIR / "first_downs_made.csv",
        BASE_COLUMNS + made_columns + SOURCE_COLUMNS,
        made_rows,
    )

    return [
        audit_entry("first_down_offence.csv", offence_rows),
        audit_entry("first_downs_made.csv", made_rows),
    ]


def make_specs() -> list[TableSpec]:
    touchdown_columns = [
        "td",
        "convert_1",
        "convert_2",
        "field_goals",
        "singles",
        "special_teams_td",
        "rush_td",
        "pass_td",
        "interception_return_td",
        "fumble_return_td",
        "punt_return_td",
        "kickoff_return_td",
        "missed_fg_return_td",
        "team_td",
        "q1_points",
        "q2_points",
        "q3_points",
        "q4_points",
        "ot_points",
    ]

    possession_columns = [
        "possessions",
        "td_drives",
        "fg_drives",
        "missed_fg_drives",
        "turnover_drives",
        "punt_drives",
        "other_drives",
        "own_1_20_drives",
        "own_1_20_td",
        "own_21_40_drives",
        "own_21_40_td",
        "own_41_54_drives",
        "own_41_54_td",
        "opp_55_41_drives",
        "opp_55_41_td",
        "opp_40_21_drives",
        "opp_40_21_td",
        "opp_20_1_drives",
        "opp_20_1_td",
        "two_and_outs",
        "two_and_out_pct",
    ]

    passing_depth_columns = [
        "depth_0_9_att",
        "depth_0_9_comp",
        "depth_0_9_comp_pct",
        "depth_0_9_yards",
        "depth_0_9_int",
        "depth_0_9_td",
        "depth_0_9_efficiency",
        "depth_10_19_att",
        "depth_10_19_comp",
        "depth_10_19_comp_pct",
        "depth_10_19_yards",
        "depth_10_19_int",
        "depth_10_19_td",
        "depth_10_19_efficiency",
        "depth_20_plus_att",
        "depth_20_plus_comp",
        "depth_20_plus_comp_pct",
        "depth_20_plus_yards",
        "depth_20_plus_int",
        "depth_20_plus_td",
        "depth_20_plus_efficiency",
    ]

    return [
        TableSpec(
            "team_scoring_breakdown.csv",
            "SCORING BREAKDOWN Home/Away",
            "TEAM SCORING TEAM TOUCHDOWNS",
            [
                "gp",
                "points_for",
                "points_for_avg",
                "points_against",
                "points_against_avg",
                "point_diff",
                "home_points",
                "away_points",
                "offensive_team_points",
                "offensive_team_avg",
                "offensive_opponent_points",
                "offensive_opponent_avg",
            ],
        ),
        TableSpec(
            "team_touchdowns_points_by_quarter.csv",
            "TEAM SCORING TEAM TOUCHDOWNS",
            "OPPONENT SCORING OPPONENT TOUCHDOWNS",
            touchdown_columns,
        ),
        TableSpec(
            "opponent_touchdowns_points_by_quarter.csv",
            "OPPONENT SCORING OPPONENT TOUCHDOWNS",
            "3. TURNOVER ANALYSIS",
            touchdown_columns,
        ),
        TableSpec(
            "turnover_analysis.csv",
            "3. TURNOVER ANALYSIS",
            "4a. POSSESSION ANALYSIS",
            [
                "turnover_ratio",
                "rank",
                "giveaways_fumble",
                "giveaways_interception",
                "giveaways_downs",
                "giveaways_total",
                "giveaway_points_allowed",
                "takeaway_offence",
                "takeaway_return",
                "takeaways_fumble",
                "takeaways_interception",
                "takeaways_downs",
                "takeaways_total",
                "takeaway_points",
            ],
        ),
        TableSpec(
            "team_possessions.csv",
            "4a. POSSESSION ANALYSIS",
            "4b. OPPONENT POSSESSION ANALYSIS",
            possession_columns,
        ),
        TableSpec(
            "opponent_possessions.csv",
            "4b. OPPONENT POSSESSION ANALYSIS",
            "4c. TIME OF POSSESSION",
            possession_columns,
        ),
        TableSpec(
            "big_play_analysis.csv",
            "5. BIG PLAY ANALYSIS",
            "6. RED ZONE RESULTS",
            [
                "team_big_plays_total",
                "team_big_play_rank",
                "team_rush_20_plus",
                "team_pass_30_plus",
                "team_punt_return_big_plays",
                "team_kickoff_return_big_plays",
                "team_fg_miss_return_big_plays",
                "opponent_big_plays_total",
                "opponent_rush_20_plus",
                "opponent_pass_30_plus",
                "opponent_punt_return_big_plays",
                "opponent_kickoff_return_big_plays",
                "opponent_fg_miss_return_big_plays",
                "big_play_diff",
            ],
            "big_play",
        ),
        TableSpec(
            "red_zone_results.csv",
            "6. RED ZONE RESULTS",
            "7. CFL COACHES' CHALLENGES",
            [
                "team_red_zone_att",
                "team_red_zone_td",
                "team_red_zone_td_pct",
                "team_red_zone_rank",
                "team_red_zone_fg",
                "team_red_zone_turnover",
                "team_red_zone_other",
                "team_red_zone_points",
                "team_red_zone_points_pct",
                "opponent_red_zone_att",
                "opponent_red_zone_td",
                "opponent_red_zone_td_pct",
                "opponent_red_zone_rank",
                "opponent_red_zone_fg",
                "opponent_red_zone_turnover",
                "opponent_red_zone_other",
                "opponent_red_zone_points",
            ],
            "red_zone",
        ),
        TableSpec(
            "coaches_challenges.csv",
            "7. CFL COACHES' CHALLENGES",
            "8a. TEAM NET OFFENCE",
            [
                "challenges",
                "challenges_won",
                "challenge_pct",
                "offence_challenges",
                "offence_challenges_won",
                "defence_challenges",
                "defence_challenges_won",
                "penalty_challenges",
                "no_penalty_challenges",
                "pass_challenges",
                "fumble_challenges",
                "spot_challenges",
            ],
            "coaches",
        ),
        TableSpec(
            "team_net_offence.csv",
            "8a. TEAM NET OFFENCE",
            "8b. OPPONENT NET OFFENCE",
            [
                "gp",
                "net_yards",
                "pass_yards",
                "rush_yards",
                "team_losses",
                "yards_per_game",
                "yards_per_game_rank",
                "plays",
                "yards_per_play",
                "yards_per_play_rank",
                "pass_attempts",
                "sacks_allowed",
                "rush_attempts",
                "other_team_losses",
                "rush_call_pct",
                "pass_plus_call_pct",
                "other_call_pct",
            ],
            "net_offence",
        ),
        TableSpec(
            "opponent_net_offence.csv",
            "8b. OPPONENT NET OFFENCE",
            "8c. NET OFFENCE - ON 1ST DOWN",
            [
                "gp",
                "opponent_net_yards",
                "opponent_pass_yards",
                "opponent_rush_yards",
                "opponent_team_losses",
                "opponent_yards_per_game",
                "opponent_yards_per_game_rank",
                "opponent_plays",
                "opponent_yards_per_play",
                "opponent_yards_per_play_rank",
                "opponent_pass_attempts",
                "opponent_sacks_allowed",
                "opponent_rush_attempts",
                "opponent_other_team_losses",
                "opponent_rush_call_pct",
                "opponent_pass_plus_call_pct",
                "opponent_other_call_pct",
            ],
            "net_offence",
        ),
        TableSpec(
            "rushing_analysis.csv",
            "9 RUSHING ANALYSIS",
            "10a. PASSING ANALYSIS",
            [
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
            ],
        ),
        TableSpec(
            "passing_base.csv",
            "2023 TEAM PASSING DATA",
            "ATTEMPTS 0-9 YDS DEPTH DOWNFIELD",
            [
                "pass_attempts",
                "pass_completions",
                "completion_pct",
                "pass_yards",
                "interceptions",
                "pass_td",
                "longest_pass",
                "passes_30_plus",
                "second_down_conversion_receptions",
                "pass_efficiency",
                "interception_pct",
                "yards_per_attempt",
                "yac_yards",
                "td_int_ratio",
                "pass_yards_per_game",
                "average_depth",
                "sacks_allowed",
                "sack_pct",
                "qb_escape_runs",
                "dropbacks",
            ],
            "passing_base",
        ),
        TableSpec(
            "passing_depth.csv",
            "ATTEMPTS 0-9 YDS DEPTH DOWNFIELD",
            "10b. PASSING ANALYSIS - BY OPPONENTS",
            passing_depth_columns,
        ),
        TableSpec(
            "opponent_passing_base.csv",
            "OPPONENT PASSING DATA",
            "OPPT ATTS 0-9 YDS DEPTH DOWNFIELD",
            [
                "opponent_pass_attempts",
                "opponent_pass_completions",
                "opponent_completion_pct",
                "opponent_pass_yards",
                "opponent_interceptions",
                "opponent_pass_td",
                "opponent_longest_pass",
                "opponent_passes_30_plus",
                "opponent_second_down_conversion_receptions",
                "opponent_pass_efficiency",
                "opponent_interception_pct",
                "opponent_yards_per_attempt",
                "opponent_yac_yards",
                "opponent_td_int_ratio",
                "opponent_average_depth",
                "opponent_games",
                "opponent_dropbacks",
                "opponent_sack_pct",
                "opponent_sacks_allowed",
                "opponent_qb_escape_runs",
            ],
            "opponent_passing_base",
        ),
        TableSpec(
            "opponent_passing_depth.csv",
            "OPPT ATTS 0-9 YDS DEPTH DOWNFIELD",
            "11. 2ND DOWN CONVERSIONS",
            passing_depth_columns,
        ),
        TableSpec(
            "second_down_conversions.csv",
            "11. 2ND DOWN CONVERSIONS",
            "12. 3RD & SHORT RESULTS",
            [
                "all_att",
                "all_made",
                "all_pct",
                "rank",
                "one_to_three_att",
                "one_to_three_made",
                "one_to_three_pct",
                "four_to_six_att",
                "four_to_six_made",
                "four_to_six_pct",
                "seven_plus_att",
                "seven_plus_made",
                "seven_plus_pct",
                "yards_to_go_total",
                "yards_to_go_avg",
                "yards_to_go_rank",
            ],
        ),
        TableSpec(
            "third_short_results.csv",
            "12. 3RD & SHORT RESULTS",
            "13a. PENALTIES",
            [
                "third_short_att",
                "third_short_made",
                "third_short_fail",
                "opponent_third_short_att",
                "opponent_third_short_made",
                "opponent_third_short_fail",
            ],
        ),
        TableSpec(
            "penalties_team_report.csv",
            "13b. PENALTIES - TEAM REPORTS",
            "14. SPECIAL TEAMS",
            [
                "gp",
                "penalties_all",
                "penalties_avg",
                "penalties_accepted",
                "penalties_declined",
                "penalty_yards",
                "offence_penalties",
                "defence_penalties",
                "special_teams_penalties",
                "punt_cover_penalties",
                "kickoff_cover_penalties",
                "punt_return_penalties",
                "kickoff_return_penalties",
            ],
            "penalties",
        ),
        TableSpec(
            "special_teams_field_goals.csv",
            "A) FIELD GOALS",
            "FIELD GOAL MISS RESULTS",
            [
                "fg_attempts",
                "fg_made",
                "fg_pct",
                "fg_long",
                "fg_singles",
                "fg_under_40_attempts",
                "fg_under_40_made",
                "fg_under_40_pct",
                "fg_40_plus_attempts",
                "fg_40_plus_made",
                "fg_40_plus_pct",
                "fg_50_plus_attempts",
                "fg_50_plus_made",
                "fg_made_yards",
                "fg_made_avg_yards",
                "fg_all_attempt_yards",
                "fg_all_attempt_avg_yards",
            ],
            "field_goals",
        ),
        TableSpec(
            "special_teams_converts.csv",
            "C) CONVERTS",
            "D) SPECIAL TEAMS - FAKE KICK PLAYS",
            [
                "convert_1_attempts",
                "convert_1_made",
                "convert_1_pct",
                "convert_1_missed",
                "convert_2_attempts",
                "convert_2_made",
                "convert_2_pct",
                "convert_2_rush",
                "convert_2_pass",
            ],
        ),
        TableSpec(
            "special_teams_kick_returns.csv",
            "E) KICK RETURN TEAMS",
            "OPPONENT PUNT RETURNS",
            [
                "punt_return_no",
                "punt_return_yards",
                "punt_return_avg",
                "punt_return_long",
                "punt_return_td",
                "punt_return_30_plus",
                "punt_return_10_plus",
                "punt_return_rank",
                "kickoff_return_no",
                "kickoff_return_yards",
                "kickoff_return_avg",
                "kickoff_return_long",
                "kickoff_return_td",
                "kickoff_return_40_plus",
                "kickoff_return_rank",
                "fg_miss_return_no",
                "fg_miss_return_yards",
                "fg_miss_return_long",
                "fg_miss_return_td",
                "fg_miss_return_30_plus",
                "kick_return_big_plays",
                "punt_return_td_total",
                "kickoff_return_td_total",
                "fg_miss_return_td_total",
                "kick_return_td_total",
            ],
            "kick_returns",
        ),
        TableSpec(
            "special_teams_punts.csv",
            "G) PUNT COVER",
            "H) KICKOFF COVER",
            [
                "punt_no",
                "punt_yards",
                "punt_avg",
                "punt_long",
                "punt_singles",
                "punt_inside_10",
                "opponent_punt_return_no",
                "opponent_punt_return_yards",
                "opponent_punt_return_avg",
                "opponent_punt_return_long",
                "opponent_punt_return_td",
                "opponent_punt_return_30_plus",
                "net_punt_avg",
                "net_punt_yards",
                "net_punt_rank",
                "single_adjustment",
                "cover_penalty_adjustment",
                "return_penalty_adjustment",
                "field_position_yards",
                "field_position_avg",
            ],
        ),
        TableSpec(
            "special_teams_kickoffs.csv",
            "H) KICKOFF COVER",
            "I) SPECIAL TEAMS COVER PENALTIES",
            [
                "kickoff_no",
                "kickoff_yards",
                "kickoff_avg",
                "kickoff_long",
                "kickoff_singles",
                "own_team_recoveries",
                "opponent_kickoff_return_no",
                "opponent_kickoff_return_yards",
                "opponent_kickoff_return_avg",
                "opponent_kickoff_return_long",
                "opponent_kickoff_return_td",
                "opponent_kickoff_return_40_plus",
                "regular_kickoff_no",
                "regular_kickoff_yards",
                "regular_kickoff_avg",
                "regular_kickoff_rank",
                "post_kickoff_possessions",
                "post_kickoff_yards",
                "post_kickoff_avg_start_yard_line",
                "post_kickoff_rank",
            ],
        ),
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    text = read_text()
    metadata = parse_dump_id()
    pdf_pages = count_pdf_pages()
    games_played = parse_games_played(text)

    audit_rows: list[dict[str, str]] = []

    for spec in make_specs():
        audit_rows.append(write_generic_table(text, spec, metadata, pdf_pages, games_played))

    audit_rows.append(write_time_of_possession_table(text, metadata, pdf_pages))
    audit_rows.extend(write_first_down_tables(text, metadata, pdf_pages))

    write_csv(
        OUT_DIR / "_parse_audit.csv",
        [
            "file_name",
            "rows_written",
            "ok_rows",
            "zero_gp_rows",
            "aggregate_rows",
            "needs_review_rows",
            "missing_rows",
            "status",
        ],
        audit_rows,
    )

    print(f"proof_dir={OUT_DIR}")
    print(f"proof_files_written={len(audit_rows)}")


if __name__ == "__main__":
    main()
