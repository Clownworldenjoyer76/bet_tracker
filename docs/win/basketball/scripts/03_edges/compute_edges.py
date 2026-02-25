# docs/win/basketball/scripts/03_edges/compute_edges.py

#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback
import re

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/basketball/02_juice")
OUTPUT_DIR = Path("docs/win/basketball/03_edges")
ERROR_DIR = Path("docs/win/basketball/errors/03_edges")
ERROR_LOG = ERROR_DIR / "compute_edges.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def validate_columns(df: pd.DataFrame, required_cols: list[str]) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

def safe_edge_pct(dk: pd.Series, juiced: pd.Series) -> pd.Series:
    dk_num = pd.to_numeric(dk, errors="coerce")
    j_num = pd.to_numeric(juiced, errors="coerce")
    out = (dk_num / j_num) - 1
    out = out.where(j_num > 0)
    return out

def safe_edge_decimal(dk: pd.Series, juiced: pd.Series) -> pd.Series:
    dk_num = pd.to_numeric(dk, errors="coerce")
    j_num = pd.to_numeric(juiced, errors="coerce")
    return dk_num - j_num

def atomic_write_csv(df: pd.DataFrame, output_path: Path) -> None:
    tmp = output_path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(output_path)

def extract_date_from_filename(filename: str) -> str:
    match = re.search(r"\d{4}_\d{2}_\d{2}", filename)
    if not match:
        raise ValueError(f"No date found in filename: {filename}")
    return match.group(0)

# =========================
# EDGE COMPUTATION
# =========================

def compute_moneyline_edges(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "game_id",
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline",
        "home_juice_odds",
        "away_juice_odds",
    ]
    validate_columns(df, required)

    df["home_edge_decimal"] = safe_edge_decimal(
        df["home_dk_decimal_moneyline"], df["home_juice_odds"]
    )
    df["home_edge_pct"] = safe_edge_pct(
        df["home_dk_decimal_moneyline"], df["home_juice_odds"]
    )
    df["home_play"] = df["home_edge_decimal"] > 0

    df["away_edge_decimal"] = safe_edge_decimal(
        df["away_dk_decimal_moneyline"], df["away_juice_odds"]
    )
    df["away_edge_pct"] = safe_edge_pct(
        df["away_dk_decimal_moneyline"], df["away_juice_odds"]
    )
    df["away_play"] = df["away_edge_decimal"] > 0

    return df

def compute_spread_edges(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "game_id",
        "home_dk_spread_decimal",
        "away_dk_spread_decimal",
        "home_spread_juice_odds",
        "away_spread_juice_odds",
    ]
    validate_columns(df, required)

    df["home_edge_decimal"] = safe_edge_decimal(
        df["home_dk_spread_decimal"], df["home_spread_juice_odds"]
    )
    df["home_edge_pct"] = safe_edge_pct(
        df["home_dk_spread_decimal"], df["home_spread_juice_odds"]
    )
    df["home_play"] = df["home_edge_decimal"] > 0

    df["away_edge_decimal"] = safe_edge_decimal(
        df["away_dk_spread_decimal"], df["away_spread_juice_odds"]
    )
    df["away_edge_pct"] = safe_edge_pct(
        df["away_dk_spread_decimal"], df["away_spread_juice_odds"]
    )
    df["away_play"] = df["away_edge_decimal"] > 0

    return df

def compute_total_edges(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "game_id",
        "dk_total_over_decimal",
        "dk_total_under_decimal",
        "total_over_juice_odds",
        "total_under_juice_odds",
    ]
    validate_columns(df, required)

    df["over_edge_decimal"] = safe_edge_decimal(
        df["dk_total_over_decimal"], df["total_over_juice_odds"]
    )
    df["over_edge_pct"] = safe_edge_pct(
        df["dk_total_over_decimal"], df["total_over_juice_odds"]
    )
    df["over_play"] = df["over_edge_decimal"] > 0

    df["under_edge_decimal"] = safe_edge_decimal(
        df["dk_total_under_decimal"], df["total_under_juice_odds"]
    )
    df["under_edge_pct"] = safe_edge_pct(
        df["dk_total_under_decimal"], df["total_under_juice_odds"]
    )
    df["under_play"] = df["under_edge_decimal"] > 0

    return df

# =========================
# MAIN
# =========================

def process_league(league: str):
    moneyline_files = sorted(INPUT_DIR.glob(f"*_{league}_moneyline.csv"))
    spread_files = sorted(INPUT_DIR.glob(f"*_{league}_spread.csv"))
    total_files = sorted(INPUT_DIR.glob(f"*_{league}_total.csv"))

    all_frames = []

    for f in moneyline_files:
        df = pd.read_csv(f)
        df = compute_moneyline_edges(df)
        all_frames.append(df)

    for f in spread_files:
        df = pd.read_csv(f)
        df = compute_spread_edges(df)
        all_frames.append(df)

    for f in total_files:
        df = pd.read_csv(f)
        df = compute_total_edges(df)
        all_frames.append(df)

    if not all_frames:
        return

    combined = pd.concat(all_frames, ignore_index=True)

    date = extract_date_from_filename(all_frames[0]["game_id"].iloc[0])
    if league == "NBA":
        output_name = f"basketball_NBA_{date}.csv"
    else:
        output_name = f"NCAAB_{date}.csv"

    output_path = OUTPUT_DIR / output_name
    atomic_write_csv(combined, output_path)

def main():
    with open(ERROR_LOG, "w") as log:
        log.write("=== BASKETBALL COMPUTE EDGES RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")
        try:
            process_league("NBA")
            process_league("NCAAB")
        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())

if __name__ == "__main__":
    main()
