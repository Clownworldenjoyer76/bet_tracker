#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback
import re
import sys

# --- DYNAMIC PATH SETUP ---
SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.append(SCRIPTS_DIR)

from utils.logger import audit

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
# MATH HELPERS (PROBABILITY BASED)
# =========================

def implied_prob(decimal_odds):
    """Converts decimal odds to implied probability (0.0 to 1.0)."""
    # Use 0 if odds are 1 or less to avoid infinity/errors
    return (1 / decimal_odds).where(decimal_odds > 1, 0)

def calculate_edge(model_decimal, book_decimal):
    """
    Calculates edge as the difference in win probability.
    Positive result means your model sees more value than the bookie.
    """
    model_decimal = pd.to_numeric(model_decimal, errors="coerce")
    book_decimal = pd.to_numeric(book_decimal, errors="coerce")
    
    model_p = implied_prob(model_decimal)
    book_p = implied_prob(book_decimal)
    
    # Edge = Your Prob - Bookie Prob
    return model_p - book_p

def validate_columns(df: pd.DataFrame, required_cols: list[str]) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

# =========================
# EDGE COMPUTATION
# =========================

def compute_moneyline_edges(df: pd.DataFrame, league: str) -> pd.DataFrame:
    required = [
        "home_dk_decimal_moneyline", "away_dk_decimal_moneyline",
        "home_juice_decimal_moneyline", "away_juice_decimal_moneyline",
    ]
    validate_columns(df, required)

    # Home Edge
    df["home_edge_decimal"] = calculate_edge(df["home_dk_decimal_moneyline"], df["home_juice_decimal_moneyline"])
    df["home_play"] = df["home_edge_decimal"] > 0

    # Away Edge
    df["away_edge_decimal"] = calculate_edge(df["away_dk_decimal_moneyline"], df["away_juice_decimal_moneyline"])
    df["away_play"] = df["away_edge_decimal"] > 0

    return df

def compute_spread_edges(df: pd.DataFrame, league: str) -> pd.DataFrame:
    required = [
        "home_dk_spread_decimal", "away_dk_spread_decimal",
        "home_spread_juice_decimal", "away_spread_juice_decimal",
    ]
    validate_columns(df, required)

    df["home_edge_decimal"] = calculate_edge(df["home_dk_spread_decimal"], df["home_spread_juice_decimal"])
    df["home_play"] = df["home_edge_decimal"] > 0

    df["away_edge_decimal"] = calculate_edge(df["away_dk_spread_decimal"], df["away_spread_juice_decimal"])
    df["away_play"] = df["away_edge_decimal"] > 0

    return df

def compute_total_edges(df: pd.DataFrame, league: str) -> pd.DataFrame:
    required = [
        "dk_total_over_decimal", "dk_total_under_decimal",
        "total_over_juice_decimal", "total_under_juice_decimal",
    ]
    validate_columns(df, required)

    df["over_edge_decimal"] = calculate_edge(df["dk_total_over_decimal"], df["total_over_juice_decimal"])
    df["over_play"] = df["over_edge_decimal"] > 0

    df["under_edge_decimal"] = calculate_edge(df["dk_total_under_decimal"], df["total_under_juice_decimal"])
    df["under_play"] = df["under_edge_decimal"] > 0

    return df

# =========================
# SYSTEM HELPERS
# =========================

def atomic_write_csv(df: pd.DataFrame, output_path: Path) -> None:
    tmp = output_path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(output_path)

def extract_date_from_filename(filename: str) -> str:
    match = re.search(r"\d{4}_\d{2}_\d{2}", filename)
    if not match:
        raise ValueError(f"No date found in filename: {filename}")
    return match.group(0)

def process_market_files(files, compute_fn, league: str, market: str):
    if not files:
        audit(ERROR_LOG, f"{league}_{market.upper()}", "SKIPPED", "No files found.")
        return

    for f in files:
        try:
            df = pd.read_csv(f)
            df = compute_fn(df, league)
            date = extract_date_from_filename(f.name)
            output_path = OUTPUT_DIR / f"{date}_basketball_{league}_{market}.csv"
            atomic_write_csv(df, output_path)
            audit(ERROR_LOG, f"{league}_{market.upper()}", "SUCCESS", f"File: {f.name}", df=df)
        except Exception:
            audit(ERROR_LOG, f"{league}_{market.upper()}", "FAILED", msg=traceback.format_exc())

def process_league(league: str):
    process_market_files(sorted(INPUT_DIR.glob(f"*_{league}_moneyline.csv")), compute_moneyline_edges, league, "moneyline")
    process_market_files(sorted(INPUT_DIR.glob(f"*_{league}_spread.csv")), compute_spread_edges, league, "spread")
    process_market_files(sorted(INPUT_DIR.glob(f"*_{league}_total.csv")), compute_total_edges, league, "total")

def main():
    audit(ERROR_LOG, "SYSTEM", "STARTING RUN")
    try:
        process_league("NBA")
        process_league("NCAAB")
        audit(ERROR_LOG, "SYSTEM", "SUCCESSFUL COMPLETION")
    except Exception:
        audit(ERROR_LOG, "SYSTEM", "CRITICAL FAILURE", msg=traceback.format_exc())

if __name__ == "__main__":
    main()
