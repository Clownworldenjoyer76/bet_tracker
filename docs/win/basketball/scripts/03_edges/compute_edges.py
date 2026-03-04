#!/usr/bin/env python3
# docs/win/basketball/scripts/03_edges/compute_edges.py

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


def edge_decimal(dk: pd.Series, juice_decimal: pd.Series) -> pd.Series:
    dk = pd.to_numeric(dk, errors="coerce")
    j = pd.to_numeric(juice_decimal, errors="coerce")
    return dk - j


# =========================
# NBA EDGE (UPDATED)
# =========================

def edge_decimal_nba(dk: pd.Series, juice_decimal: pd.Series) -> pd.Series:
    dk = pd.to_numeric(dk, errors="coerce")
    j = pd.to_numeric(juice_decimal, errors="coerce")
    out = dk - j
    return out.where((dk > 0) & (j > 0))


def edge_pct_nba(dk: pd.Series, juice_decimal: pd.Series) -> pd.Series:
    dk = pd.to_numeric(dk, errors="coerce")
    j = pd.to_numeric(juice_decimal, errors="coerce")
    out = (dk - j) / j
    return out.where(j > 0)


def edge_pct(dk: pd.Series, juice_decimal: pd.Series) -> pd.Series:
    dk = pd.to_numeric(dk, errors="coerce")
    j = pd.to_numeric(juice_decimal, errors="coerce")
    out = (dk - j) / j
    return out.where(j > 0)


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

def compute_moneyline_edges(df: pd.DataFrame, league: str) -> pd.DataFrame:
    required = [
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline",
        "home_juice_decimal_moneyline",
        "away_juice_decimal_moneyline",
    ]
    validate_columns(df, required)

    if league == "NBA":
        edge_fn = edge_decimal_nba
        pct_fn = edge_pct_nba
    else:
        edge_fn = edge_decimal
        pct_fn = edge_pct

    df["home_edge_decimal"] = edge_fn(df["home_dk_decimal_moneyline"], df["home_juice_decimal_moneyline"])
    df["home_edge_pct"] = pct_fn(df["home_dk_decimal_moneyline"], df["home_juice_decimal_moneyline"])
    df["home_play"] = df["home_edge_decimal"] > 0

    df["away_edge_decimal"] = edge_fn(df["away_dk_decimal_moneyline"], df["away_juice_decimal_moneyline"])
    df["away_edge_pct"] = pct_fn(df["away_dk_decimal_moneyline"], df["away_juice_decimal_moneyline"])
    df["away_play"] = df["away_edge_decimal"] > 0

    return df


def compute_spread_edges(df: pd.DataFrame, league: str) -> pd.DataFrame:
    required = [
        "home_dk_spread_decimal",
        "away_dk_spread_decimal",
        "home_spread_juice_decimal",
        "away_spread_juice_decimal",
    ]
    validate_columns(df, required)

    if league == "NBA":
        edge_fn = edge_decimal_nba
        pct_fn = edge_pct_nba
    else:
        edge_fn = edge_decimal
        pct_fn = edge_pct

    df["home_edge_decimal"] = edge_fn(df["home_dk_spread_decimal"], df["home_spread_juice_decimal"])
    df["home_edge_pct"] = pct_fn(df["home_dk_spread_decimal"], df["home_spread_juice_decimal"])
    df["home_play"] = df["home_edge_decimal"] > 0

    df["away_edge_decimal"] = edge_fn(df["away_dk_spread_decimal"], df["away_spread_juice_decimal"])
    df["away_edge_pct"] = pct_fn(df["away_dk_spread_decimal"], df["away_spread_juice_decimal"])
    df["away_play"] = df["away_edge_decimal"] > 0

    return df


def compute_total_edges(df: pd.DataFrame, league: str) -> pd.DataFrame:
    required = [
        "dk_total_over_decimal",
        "dk_total_under_decimal",
        "total_over_juice_decimal",
        "total_under_juice_decimal",
    ]
    validate_columns(df, required)

    if league == "NBA":
        edge_fn = edge_decimal_nba
        pct_fn = edge_pct_nba
    else:
        edge_fn = edge_decimal
        pct_fn = edge_pct

    df["over_edge_decimal"] = edge_fn(df["dk_total_over_decimal"], df["total_over_juice_decimal"])
    df["over_edge_pct"] = pct_fn(df["dk_total_over_decimal"], df["total_over_juice_decimal"])
    df["over_play"] = df["over_edge_decimal"] > 0

    df["under_edge_decimal"] = edge_fn(df["dk_total_under_decimal"], df["total_under_juice_decimal"])
    df["under_edge_pct"] = pct_fn(df["dk_total_under_decimal"], df["total_under_juice_decimal"])
    df["under_play"] = df["under_edge_decimal"] > 0

    return df

# =========================
# PROCESSING
# =========================

def process_market_files(files, compute_fn, league: str, market: str, log):
    log.write(f"\n--- Market Segment: {market.upper()} ---\n")
    if not files:
        log.write("  STATUS: No files found matching pattern.\n")
        return

    for f in files:
        try:
            df = pd.read_csv(f)
            df = compute_fn(df, league)
            date = extract_date_from_filename(f.name)

            # --- EXTENSIVE DATA AUDIT ---
            total_rows = len(df)
            play_cols = [c for c in df.columns if "_play" in c]
            edge_cols = [c for c in df.columns if "_edge_pct" in c]
            
            total_plays = df[play_cols].sum().sum()
            avg_edge = df[edge_cols].mean().mean()
            null_count = df[edge_cols].isna().sum().sum()

            output_name = f"{date}_basketball_{league}_{market}.csv"
            output_path = OUTPUT_DIR / output_name
            atomic_write_csv(df, output_path)

            log.write(f"  FILE: {f.name}\n")
            log.write(f"    [Metrics] Rows: {total_rows} | Total Plays: {int(total_plays)} | Avg Edge: {avg_edge:.2%} | Nulls: {null_count}\n")
            log.write(f"    [Output]  Saved to -> {output_name}\n")
            log.write(f"    [Sample Data Preview]\n")
            # Log first 2 rows of pertinent columns
            preview = df.head(2).to_string(index=False, justify='left')
            log.write(f"{'      ' + preview.replace(chr(10), chr(10) + '      ')}\n\n")

        except Exception as e:
            log.write(f"  !!! FAILED FILE: {f.name} !!!\n")
            log.write(f"    Reason: {str(e)}\n")
            log.write(f"    Trace: {traceback.format_exc().splitlines()[-1]}\n\n")


def process_league(league: str, log):
    log.write(f"\n{'#'*60}\n")
    log.write(f"### LEAGUE AUDIT: {league}\n")
    log.write(f"{'#'*60}\n")
    
    process_market_files(sorted(INPUT_DIR.glob(f"*_{league}_moneyline.csv")), compute_moneyline_edges, league, "moneyline", log)
    process_market_files(sorted(INPUT_DIR.glob(f"*_{league}_spread.csv")), compute_spread_edges, league, "spread", log)
    process_market_files(sorted(INPUT_DIR.glob(f"*_{league}_total.csv")), compute_total_edges, league, "total", log)


def main():
    with open(ERROR_LOG, "w") as log:
        log.write("============================================================\n")
        log.write("         BASKETBALL EDGES: EXHAUSTIVE SYSTEM AUDIT\n")
        log.write("============================================================\n")
        log.write(f"Run Initiated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Source:        {INPUT_DIR.resolve()}\n")
        log.write(f"Destination:   {OUTPUT_DIR.resolve()}\n")
        
        try:
            process_league("NBA", log)
            process_league("NCAAB", log)
            log.write("\n============================================================\n")
            log.write("SYSTEM STATUS: SUCCESSFUL COMPLETION\n")
        except Exception as e:
            log.write("\n!!! CRITICAL PIPELINE FAILURE !!!\n")
            log.write(traceback.format_exc())
        finally:
            log.write(f"Run Concluded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write("============================================================\n")


if __name__ == "__main__":
    main()
