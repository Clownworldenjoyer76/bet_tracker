#!/usr/bin/env python3
# docs/win/hockey/scripts/03_edges/compute_edges.py

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, UTC
import traceback

INPUT_DIR = Path("docs/win/hockey/02_juice")
OUTPUT_DIR = Path("docs/win/hockey/03_edges")
ERROR_DIR = Path("docs/win/hockey/errors/03_edges")
ERROR_LOG = ERROR_DIR / "compute_edges.txt"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(UTC).isoformat()} | {msg}\n")


def validate_columns(df: pd.DataFrame, required_cols: list[str], file_path: Path) -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{file_path} missing required columns: {missing}")


def decimal_to_american(series: pd.Series) -> pd.Series:
    dec = pd.to_numeric(series, errors="coerce")
    american = pd.Series(index=dec.index, dtype="float64")

    pos = dec >= 2
    neg = (dec > 1) & (dec < 2)

    american[pos] = (dec[pos] - 1) * 100
    american[neg] = -100 / (dec[neg] - 1)

    return american.round(0)


def safe_edge_decimal(dk_decimal: pd.Series, prob: pd.Series) -> pd.Series:
    dk = pd.to_numeric(dk_decimal, errors="coerce")
    p = pd.to_numeric(prob, errors="coerce")

    out = pd.Series(np.nan, index=dk.index)
    valid = (dk > 1) & (p > 0) & (p < 1) & np.isfinite(dk) & np.isfinite(p)

    out[valid] = p[valid] * dk[valid] - 1
    return out


def safe_edge_pct(dk_decimal: pd.Series, prob: pd.Series) -> pd.Series:
    dk = pd.to_numeric(dk_decimal, errors="coerce")
    p = pd.to_numeric(prob, errors="coerce")

    edge = pd.Series(np.nan, index=dk.index)
    valid = (dk > 1) & (p > 0) & (p < 1) & np.isfinite(dk) & np.isfinite(p)

    p_market = 1 / dk[valid]
    edge[valid] = p[valid] - p_market
    return edge


def atomic_write_csv(df: pd.DataFrame, output_path: Path) -> None:
    tmp = output_path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(output_path)


# =========================
# MONEYLINE
# =========================

def compute_moneyline_edges(df: pd.DataFrame, file_path: Path) -> pd.DataFrame:
    required = [
        "game_id",
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline",
        "home_normalized_prob_moneyline",
        "away_normalized_prob_moneyline",
        "home_prob",
        "away_prob",
    ]
    validate_columns(df, required, file_path)

    df["home_edge_decimal_moneyline"] = safe_edge_decimal(
        df["home_dk_decimal_moneyline"],
        df["home_normalized_prob_moneyline"],
    )
    df["away_edge_decimal_moneyline"] = safe_edge_decimal(
        df["away_dk_decimal_moneyline"],
        df["away_normalized_prob_moneyline"],
    )

    df["home_raw_edge_decimal_moneyline"] = safe_edge_decimal(
        df["home_dk_decimal_moneyline"],
        df["home_prob"],
    )
    df["away_raw_edge_decimal_moneyline"] = safe_edge_decimal(
        df["away_dk_decimal_moneyline"],
        df["away_prob"],
    )

    df["home_edge_pct_moneyline"] = safe_edge_pct(
        df["home_dk_decimal_moneyline"],
        df["home_normalized_prob_moneyline"],
    )
    df["away_edge_pct_moneyline"] = safe_edge_pct(
        df["away_dk_decimal_moneyline"],
        df["away_normalized_prob_moneyline"],
    )

    return df


# =========================
# PUCK LINE
# =========================

def compute_puck_line_edges(df: pd.DataFrame, file_path: Path) -> pd.DataFrame:
    required = [
        "game_id",
        "home_dk_puck_line_decimal",
        "away_dk_puck_line_decimal",
        "home_normalized_prob_puck_line",
        "away_normalized_prob_puck_line",
        "home_prob_puck_line",
        "away_prob_puck_line",
    ]
    validate_columns(df, required, file_path)

    # Juiced edge: post-juice normalized probability vs DK price
    df["home_edge_decimal_puck_line"] = safe_edge_decimal(
        df["home_dk_puck_line_decimal"],
        df["home_normalized_prob_puck_line"],
    )
    df["away_edge_decimal_puck_line"] = safe_edge_decimal(
        df["away_dk_puck_line_decimal"],
        df["away_normalized_prob_puck_line"],
    )

    # Raw edge: unmodified model probability vs DK price
    df["home_raw_edge_decimal_puck_line"] = safe_edge_decimal(
        df["home_dk_puck_line_decimal"],
        df["home_prob_puck_line"],
    )
    df["away_raw_edge_decimal_puck_line"] = safe_edge_decimal(
        df["away_dk_puck_line_decimal"],
        df["away_prob_puck_line"],
    )

    return df


# =========================
# TOTAL
# =========================

def compute_total_edges(df: pd.DataFrame, file_path: Path) -> pd.DataFrame:
    required = [
        "game_id",
        "dk_total_over_decimal",
        "dk_total_under_decimal",
        "over_normalized_prob_total",
        "under_normalized_prob_total",
        "fair_total_over_decimal",
        "fair_total_under_decimal",
    ]
    validate_columns(df, required, file_path)

    df["over_prob"] = 1 / pd.to_numeric(df["fair_total_over_decimal"], errors="coerce")
    df["under_prob"] = 1 / pd.to_numeric(df["fair_total_under_decimal"], errors="coerce")

    df["over_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_over_decimal"],
        df["over_normalized_prob_total"],
    )
    df["under_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_under_decimal"],
        df["under_normalized_prob_total"],
    )

    df["over_raw_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_over_decimal"],
        df["over_prob"],
    )
    df["under_raw_edge_decimal_total"] = safe_edge_decimal(
        df["dk_total_under_decimal"],
        df["under_prob"],
    )

    return df


# =========================
# DRIVER
# =========================

def process_pattern(pattern, compute_fn, label, summary):
    input_files = sorted(INPUT_DIR.glob(pattern))
    if not input_files:
        log(f"[WARN] No input files found for pattern: {pattern}")
        return

    for input_path in input_files:
        # FIX: wrap per-file processing in try/except so one bad file does not
        # kill all remaining files in the batch.
        try:
            df = pd.read_csv(input_path)
            out_df = compute_fn(df, input_path)

            output_path = OUTPUT_DIR / input_path.name
            atomic_write_csv(out_df, output_path)

            summary["files_processed"] += 1
            summary["rows_processed"] += len(out_df)
            summary[f"{label}_files"] += 1

            log(f"[INFO] WROTE: {output_path} rows={len(out_df)}")

        except Exception as e:
            log(f"[ERROR] SKIPPED: {input_path} reason={e}")
            log(traceback.format_exc())


def main():
    with open(ERROR_LOG, "w", encoding="utf-8") as f:
        f.write("=== NHL COMPUTE EDGES RUN ===\n")
        f.write(f"{datetime.now(UTC).isoformat()}\n\n")

    summary = {
        "files_processed": 0,
        "rows_processed": 0,
        "moneyline_files": 0,
        "puck_line_files": 0,
        "total_files": 0,
    }

    try:
        process_pattern("*_NHL_moneyline.csv", compute_moneyline_edges, "moneyline", summary)
        process_pattern("*_NHL_puck_line.csv", compute_puck_line_edges, "puck_line", summary)
        process_pattern("*_NHL_total.csv", compute_total_edges, "total", summary)

        log("=== SUMMARY ===")
        log(f"[SUMMARY] Files processed: {summary['files_processed']}")
        log(f"[SUMMARY] Rows processed:  {summary['rows_processed']}")
        log(f"[SUMMARY] Moneyline files: {summary['moneyline_files']}")
        log(f"[SUMMARY] Puck line files: {summary['puck_line_files']}")
        log(f"[SUMMARY] Total files:     {summary['total_files']}")

    except Exception as e:
        log("[ERROR] Fatal error in main")
        log(str(e))
        log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()