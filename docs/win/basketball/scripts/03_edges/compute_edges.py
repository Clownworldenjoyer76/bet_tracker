#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
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
# MATH HELPERS
# =========================

def implied_prob(decimal_odds):
    return (1 / decimal_odds).where(decimal_odds > 1, 0)


def calculate_edge(model_decimal, book_decimal):

    model_decimal = pd.to_numeric(model_decimal, errors="coerce")
    book_decimal = pd.to_numeric(book_decimal, errors="coerce")

    model_p = implied_prob(model_decimal)
    book_p = implied_prob(book_decimal)

    return model_p - book_p


def validate_columns(df: pd.DataFrame, required_cols):

    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

# =========================
# HELPERS
# =========================

def extract_date_from_filename(filename):

    match = re.search(r"\d{4}_\d{2}_\d{2}", filename)

    if not match:
        raise ValueError(f"No date found in filename: {filename}")

    return match.group(0)

# =========================
# EDGE COMPUTATION
# =========================

def compute_moneyline_edges(df, league, date):

    # ---------- NBA ----------
    if league == "NBA":

        edge_file = OUTPUT_DIR / f"{date}_basketball_NBA_moneyline.csv"

        if not edge_file.exists():
            raise FileNotFoundError(f"Missing edge file: {edge_file}")

        edge_df = pd.read_csv(edge_file)

        required = ["game_id", "home_edge_decimal", "away_edge_decimal"]
        validate_columns(edge_df, required)

        df = df.merge(edge_df[required], on="game_id", how="left")

        df["home_ml_edge_decimal"] = df["home_edge_decimal"]
        df["away_ml_edge_decimal"] = df["away_edge_decimal"]

        return df

    # ---------- NCAAB ----------
    required = [
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline",
        "home_juice_decimal_moneyline",
        "away_juice_decimal_moneyline",
    ]

    validate_columns(df, required)

    df["home_ml_edge_decimal"] = calculate_edge(
        df["home_dk_decimal_moneyline"],
        df["home_juice_decimal_moneyline"]
    )

    df["away_ml_edge_decimal"] = calculate_edge(
        df["away_dk_decimal_moneyline"],
        df["away_juice_decimal_moneyline"]
    )

    return df


def compute_spread_edges(df, league, date):

    # ---------- NBA ----------
    if league == "NBA":

        edge_file = OUTPUT_DIR / f"{date}_basketball_NBA_spread.csv"

        if not edge_file.exists():
            raise FileNotFoundError(f"Missing edge file: {edge_file}")

        edge_df = pd.read_csv(edge_file)

        required = ["game_id", "home_edge_decimal", "away_edge_decimal"]
        validate_columns(edge_df, required)

        df = df.merge(edge_df[required], on="game_id", how="left")

        df["home_spread_edge_decimal"] = df["home_edge_decimal"]
        df["away_spread_edge_decimal"] = df["away_edge_decimal"]

        return df

    # ---------- NCAAB ----------
    required = [
        "home_dk_spread_decimal",
        "away_dk_spread_decimal",
        "home_spread_juice_decimal",
        "away_spread_juice_decimal",
    ]

    validate_columns(df, required)

    df["home_spread_edge_decimal"] = calculate_edge(
        df["home_dk_spread_decimal"],
        df["home_spread_juice_decimal"]
    )

    df["away_spread_edge_decimal"] = calculate_edge(
        df["away_dk_spread_decimal"],
        df["away_spread_juice_decimal"]
    )

    return df


def compute_total_edges(df, league):

    required = [
        "dk_total_over_decimal",
        "dk_total_under_decimal",
        "total_over_juice_decimal",
        "total_under_juice_decimal",
    ]

    validate_columns(df, required)

    df["over_edge_decimal"] = calculate_edge(
        df["dk_total_over_decimal"],
        df["total_over_juice_decimal"]
    )

    df["under_edge_decimal"] = calculate_edge(
        df["dk_total_under_decimal"],
        df["total_under_juice_decimal"]
    )

    return df

# =========================
# SYSTEM HELPERS
# =========================

def atomic_write_csv(df, output_path):

    tmp = output_path.with_suffix(".tmp")

    df.to_csv(tmp, index=False)

    tmp.replace(output_path)


def process_market_files(files, compute_fn, league, market):

    if not files:
        audit(ERROR_LOG, f"{league}_{market.upper()}", "SKIPPED", "No files found.")
        return

    for f in files:

        try:

            df = pd.read_csv(f)

            date = extract_date_from_filename(f.name)

            if market in ("moneyline", "spread"):
                df = compute_fn(df, league, date)
            else:
                df = compute_fn(df, league)

            df = df.drop(columns=["home_play", "away_play"], errors="ignore")

            output_path = OUTPUT_DIR / f"{date}_basketball_{league}_{market}.csv"

            atomic_write_csv(df, output_path)

            audit(
                ERROR_LOG,
                f"{league}_{market.upper()}",
                "SUCCESS",
                f"File: {f.name}",
                df=df
            )

        except Exception:

            audit(
                ERROR_LOG,
                f"{league}_{market.upper()}",
                "FAILED",
                msg=traceback.format_exc()
            )

# =========================
# LEAGUE PROCESSING
# =========================

def process_league(league):

    process_market_files(
        sorted(INPUT_DIR.glob(f"*_{league}_moneyline.csv")),
        compute_moneyline_edges,
        league,
        "moneyline"
    )

    process_market_files(
        sorted(INPUT_DIR.glob(f"*_{league}_spread.csv")),
        compute_spread_edges,
        league,
        "spread"
    )

    process_market_files(
        sorted(INPUT_DIR.glob(f"*_{league}_total.csv")),
        compute_total_edges,
        league,
        "total"
    )

# =========================
# MAIN
# =========================

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
