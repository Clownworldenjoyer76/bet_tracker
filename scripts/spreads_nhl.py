#!/usr/bin/env python3
"""
nhl_spreads_pipeline.py

Consolidates:
- nhl_spreads_01.py
- nhl_spreads_02.py
- nhl_spreads_03.py
- nhl_spreads_04.py
- nhl_spreads_05.py
- nhl_spreads_06.py

Goal:
Run the exact same pipeline end-to-end while preserving your formats and logic.

Default behavior:
- Creates spreads files from edge_nhl_totals_*.csv
- Enriches spreads from final_nhl_*.csv
- Adds goals columns
- Computes fair puck line odds (+1.5 underdog)
- Computes venue-adjusted acceptable odds (+1.5 underdog)
- Computes spread_win_prob for +1.5
"""

import csv
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# -------------------------
# Directories (match your scripts)
# -------------------------
ROOT = Path(".")
NHL_DIR = ROOT / "docs" / "win" / "nhl"
SPREADS_DIR = NHL_DIR / "spreads"
FINAL_DIR = ROOT / "docs" / "win" / "final"

SPREADS_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------
# Step 01 config (from nhl_spreads_01.py)
# -------------------------
EDGE_INPUT_DIR = NHL_DIR
EDGE_PATTERN = "edge_nhl_totals_*.csv"

REQUIRED_COLUMNS_01 = [
    "game_id",
    "date",
    "time",
    "team_1",
    "team_2",
    "market_total",
    "side",
    "model_probability",
]

HEADER_MAP_01 = {
    "team_1": "away_team",
    "team_2": "home_team",
    "model_probability": "ou_prob",
}

EXTRA_HEADERS_01 = [
    "away_win_prob",
    "home_win_prob",
    "away_amer_odds",
    "home_amer_odds",
    "away_deci_odds",
    "home_deci_odds",
    "underdog",
    "puck_line",
    "puck_line_fair_deci",
    "puck_line_fair_amer",
    "puck_line_acceptable_deci",
    "puck_line_acceptable_amer",
    "puck_line_juiced_deci",
    "puck_line_juiced_amer",
    "league",
]

# -------------------------
# Step 02 config (from nhl_spreads_02.py)
# -------------------------
REQUIRED_FINAL_COLUMNS_02 = [
    "game_id",
    "team",
    "opponent",
    "win_probability",
    "personally_acceptable_american_odds",
    "personally_acceptable_decimal_odds",
]

# -------------------------
# Step 04 config (from nhl_spreads_04.py)
# -------------------------
MAX_GOALS_04 = 15  # safe Poisson cutoff for NHL scoring

# ============================================================
# Shared helpers
# ============================================================

def extract_date_yyyymmdd_from_filename(filename: str) -> str:
    m = re.search(r"(\d{4}_\d{2}_\d{2})", filename)
    if not m:
        raise ValueError(f"Could not extract date from filename: {filename}")
    return m.group(1)

def extract_date_from_edge_filename(filename: str) -> str:
    # expects edge_nhl_totals_YYYY_MM_DD*.csv
    return extract_date_yyyymmdd_from_filename(filename)

def read_csv_dict(path: Path) -> Tuple[List[dict], List[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    return rows, fieldnames

def write_csv_dict(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def deci_to_american(deci: float) -> int:
    if deci >= 2.0:
        return int(round(100 * (deci - 1)))
    else:
        return int(round(-100 / (deci - 1)))

# ============================================================
# STEP 01: Create nhl_spreads_YYYY_MM_DD.csv from edge_nhl_totals_*.csv
# (logic preserved from nhl_spreads_01.py)
# ============================================================

def step01_create_spreads_from_edge() -> List[Path]:
    edge_files = sorted(EDGE_INPUT_DIR.glob(EDGE_PATTERN))
    if not edge_files:
        print("No input files found for step01.", file=sys.stderr)
        return []

    created: List[Path] = []

    for path in edge_files:
        date_str = extract_date_from_edge_filename(path.name)
        output_path = SPREADS_DIR / f"nhl_spreads_{date_str}.csv"

        with path.open(newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)

            missing = [c for c in REQUIRED_COLUMNS_01 if c not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"{path.name} missing required columns: {missing}")

            output_headers = [HEADER_MAP_01.get(col, col) for col in REQUIRED_COLUMNS_01] + EXTRA_HEADERS_01

            with output_path.open("w", newline="", encoding="utf-8") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=output_headers)
                writer.writeheader()

                for row in reader:
                    out_row = {}
                    for col in REQUIRED_COLUMNS_01:
                        out_col = HEADER_MAP_01.get(col, col)
                        out_row[out_col] = row[col]
                    writer.writerow(out_row)

        print(f"Created: {output_path}")
        created.append(output_path)

    return created

# ============================================================
# STEP 02: Populate spreads using final_nhl_*.csv
# (logic preserved from nhl_spreads_02.py)
# ============================================================

def load_final_rows_02(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_FINAL_COLUMNS_02 if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path.name} missing required columns: {missing}")
        return list(reader)

def step02_enrich_spreads_from_final(spread_paths: Optional[List[Path]] = None) -> None:
    files = spread_paths if spread_paths is not None else sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))
    if not files:
        print("No nhl_spreads files found for step02.", file=sys.stderr)
        return

    for spread_path in files:
        date_str = extract_date_yyyymmdd_from_filename(spread_path.name)
        final_path = FINAL_DIR / f"final_nhl_{date_str}.csv"

        if not final_path.exists():
            print(f"Missing final file for {spread_path.name}", file=sys.stderr)
            continue

        final_rows = load_final_rows_02(final_path)

        spread_rows, headers = read_csv_dict(spread_path)

        for srow in spread_rows:
            away = next(
                (r for r in final_rows
                 if r["game_id"] == srow.get("game_id")
                 and r["team"] == srow.get("away_team")),
                None
            )

            home = next(
                (r for r in final_rows
                 if r["game_id"] == srow.get("game_id")
                 and r["team"] == srow.get("home_team")),
                None
            )

            if not away or not home:
                continue

            srow["away_win_prob"] = away["win_probability"]
            srow["home_win_prob"] = home["win_probability"]

            srow["away_amer_odds"] = away["personally_acceptable_american_odds"]
            srow["home_amer_odds"] = home["personally_acceptable_american_odds"]

            srow["away_deci_odds"] = away["personally_acceptable_decimal_odds"]
            srow["home_deci_odds"] = home["personally_acceptable_decimal_odds"]

            if float(away["win_probability"]) < float(home["win_probability"]):
                srow["underdog"] = srow.get("away_team")
            else:
                srow["underdog"] = srow.get("home_team")

            srow["puck_line"] = "+1.5"
            srow["puck_line_fair_deci"] = ""
            srow["puck_line_fair_amer"] = ""
            srow["puck_line_acceptable_deci"] = ""
            srow["puck_line_acceptable_amer"] = ""
            srow["puck_line_juiced_deci"] = ""
            srow["puck_line_juiced_amer"] = ""
            srow["league"] = "nhl_spread"

        write_csv_dict(spread_path, spread_rows, headers)
        print(f"Updated: {spread_path}")

# ============================================================
# STEP 03: Add home_goals / away_goals from final_nhl_*.csv
# (logic preserved from nhl_spreads_03.py)
# ============================================================

def load_final_goals_03() -> Dict[str, Dict[str, str]]:
    data: Dict[str, Dict[str, str]] = {}

    for path in FINAL_DIR.glob("final_nhl_*.csv"):
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                game_id = row.get("game_id")
                team = row.get("team")
                goals = row.get("goals")

                if not game_id or not team:
                    continue

                data.setdefault(game_id, {})[team] = goals

    return data

def step03_add_goals_columns(spread_paths: Optional[List[Path]] = None) -> None:
    final_goals = load_final_goals_03()
    files = spread_paths if spread_paths is not None else list(SPREADS_DIR.glob("nhl_spreads_*.csv"))

    for path in files:
        rows, fieldnames = read_csv_dict(path)

        if "home_goals" not in fieldnames:
            fieldnames.append("home_goals")
        if "away_goals" not in fieldnames:
            fieldnames.append("away_goals")

        for row in rows:
            game_id = row.get("game_id")
            home_team = row.get("home_team")
            away_team = row.get("away_team")

            if not game_id or game_id not in final_goals:
                continue

            goals_map = final_goals[game_id]

            if away_team in goals_map:
                row["away_goals"] = goals_map[away_team]
            if home_team in goals_map:
                row["home_goals"] = goals_map[home_team]

        write_csv_dict(path, rows, fieldnames)

# ============================================================
# STEP 04: Compute FAIR puck line odds for UNDERDOG +1.5
# (logic preserved from nhl_spreads_04.py)
# ============================================================

def fair_prob_underdog_plus_1_5(lam_u: float, lam_f: float) -> float:
    prob = 0.0
    for u in range(MAX_GOALS_04 + 1):
        pu = poisson_pmf(u, lam_u)
        for f in range(MAX_GOALS_04 + 1):
            if u - f >= -1:
                prob += pu * poisson_pmf(f, lam_f)
    return prob

def load_goal_map_04(final_path: Path) -> Dict[Tuple[str, str], float]:
    with final_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {(r["game_id"], r["team"]): float(r["goals"]) for r in reader}

def step04_compute_fair_puckline(spread_paths: Optional[List[Path]] = None) -> None:
    files = spread_paths if spread_paths is not None else sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))
    if not files:
        print("No nhl_spreads files found for step04.", file=sys.stderr)
        return

    for spread_path in files:
        date_str = extract_date_yyyymmdd_from_filename(spread_path.name)
        final_path = FINAL_DIR / f"final_nhl_{date_str}.csv"
        if not final_path.exists():
            raise FileNotFoundError(f"Missing final file: {final_path}")

        goal_map = load_goal_map_04(final_path)
        rows, headers = read_csv_dict(spread_path)

        for row in rows:
            gid = row.get("game_id", "")
            away = row.get("away_team", "")
            home = row.get("home_team", "")
            underdog = row.get("underdog", "")

            try:
                away_goals = goal_map[(gid, away)]
                home_goals = goal_map[(gid, home)]
            except KeyError:
                continue  # strict join failure — do not fabricate

            if underdog == away:
                lam_u, lam_f = away_goals, home_goals
            else:
                lam_u, lam_f = home_goals, away_goals

            p = fair_prob_underdog_plus_1_5(lam_u, lam_f)
            fair_deci = 1.0 / p
            fair_amer = deci_to_american(fair_deci)

            row["puck_line_fair_deci"] = f"{fair_deci:.6f}"
            row["puck_line_fair_amer"] = str(fair_amer)

        write_csv_dict(spread_path, rows, headers)
        print(f"Updated fair puck line odds: {spread_path.name}")

# ============================================================
# STEP 05: Apply venue-adjusted juice to FAIR puck line odds
# (logic preserved from nhl_spreads_05.py)
# ============================================================

def step05_apply_venue_juice(spread_paths: Optional[List[Path]] = None) -> None:
    files = spread_paths if spread_paths is not None else sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))
    if not files:
        print("No nhl_spreads files found for step05.", file=sys.stderr)
        return

    for path in files:
        rows, headers = read_csv_dict(path)

        for row in rows:
            if not row.get("puck_line_fair_deci"):
                continue

            try:
                fair_deci = float(row["puck_line_fair_deci"])
            except ValueError:
                continue

            underdog = row.get("underdog")
            home_team = row.get("home_team")
            away_team = row.get("away_team")

            if not underdog or not home_team or not away_team:
                continue

            if underdog == home_team:
                juice = 0.05
            elif underdog == away_team:
                juice = 0.06
            else:
                continue

            p_fair = 1.0 / fair_deci
            p_juiced = p_fair * (1.0 + juice)

            if p_juiced >= 1.0:
                continue

            acceptable_deci = 1.0 / p_juiced
            acceptable_amer = deci_to_american(acceptable_deci)

            row["puck_line_acceptable_deci"] = f"{acceptable_deci:.6f}"
            row["puck_line_acceptable_amer"] = str(acceptable_amer)

        write_csv_dict(path, rows, headers)
        print(f"Updated acceptable puck line odds: {path.name}")

# ============================================================
# STEP 06: Add spread_win_prob for +1.5
# (logic preserved from nhl_spreads_06.py)
# ============================================================

def prob_lose_by_one(lam_dog: float, lam_fav: float, max_goals: int = 12) -> float:
    p = 0.0
    for k in range(max_goals + 1):
        p += poisson_pmf(k, lam_dog) * poisson_pmf(k + 1, lam_fav)
    return p

def compute_plus_one_five_prob(dog_win_prob: float, lam_dog: float, lam_fav: float) -> float:
    p_lose_1 = prob_lose_by_one(lam_dog, lam_fav)
    return min(dog_win_prob + p_lose_1, 0.9999)

def step06_add_spread_win_prob_latest_only() -> None:
    # This step (per your script) edits only the latest nhl_spreads_*.csv file.
    files = sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))
    if not files:
        raise FileNotFoundError("No nhl_spreads_*.csv files found")

    path = files[-1]
    rows, fieldnames = read_csv_dict(path)

    if "spread_win_prob" not in fieldnames:
        fieldnames.append("spread_win_prob")

    out_rows: List[dict] = []

    for r in rows:
        try:
            away_win = float(r["away_win_prob"])
            home_win = float(r["home_win_prob"])
            away_goals = float(r["away_goals"])
            home_goals = float(r["home_goals"])
            underdog = r.get("underdog", "")
            away = r["away_team"]
            home = r["home_team"]
        except Exception:
            r["spread_win_prob"] = ""
            out_rows.append(r)
            continue

        if underdog == away:
            p = compute_plus_one_five_prob(
                dog_win_prob=away_win,
                lam_dog=away_goals,
                lam_fav=home_goals
            )
        elif underdog == home:
            p = compute_plus_one_five_prob(
                dog_win_prob=home_win,
                lam_dog=home_goals,
                lam_fav=away_goals
            )
        else:
            p = ""

        r["spread_win_prob"] = f"{p:.4f}" if p != "" else ""
        out_rows.append(r)

    write_csv_dict(path, out_rows, fieldnames)
    print(f"Updated {path} with spread_win_prob")

# ============================================================
# MAIN
# ============================================================

def main():
    created = step01_create_spreads_from_edge()
    # If step01 created files, operate on those; otherwise operate on existing spreads files.
    target_files = created if created else sorted(SPREADS_DIR.glob("nhl_spreads_*.csv"))

    step02_enrich_spreads_from_final(target_files)
    step03_add_goals_columns(target_files)
    step04_compute_fair_puckline(target_files)
    step05_apply_venue_juice(target_files)

    # Keep step06 behavior: only updates the latest spreads file.
    step06_add_spread_win_prob_latest_only()

if __name__ == "__main__":
    main()
