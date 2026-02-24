# docs/win/hockey/scripts/03_edges/compute_edges.py

#!/usr/bin/env python3
# docs/win/hockey/scripts/03_edges/compute_edges.py

import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# =========================
# PATHS
# =========================

INPUT_DIR = Path("docs/win/hockey/02_juice")
OUTPUT_DIR = Path("docs/win/hockey/03_edges")
ERROR_DIR = Path("docs/win/hockey/errors/03_edges")
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
    """
    edge_pct = (dk / juiced) - 1
    Returns NaN when dk/juiced invalid (NaN, juiced<=0).
    """
    dk_num = pd.to_numeric(dk, errors="coerce")
    j_num = pd.to_numeric(juiced, errors="coerce")
    out = (dk_num / j_num) - 1
    out = out.where(j_num > 0)
    return out

def safe_edge_decimal(dk: pd.Series, juiced: pd.Series) -> pd.Series:
    dk_num = pd.to_numeric(dk, errors="coerce")
    j_num = pd.to_numeric(juiced, errors="coerce")
    return dk_num - j_num

def upsert_dedup_by_game_id(new_df: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    """
    If output exists, append then dedupe by game_id (keep last).
    Always returns the final combined df.
    """
    if output_path.exists():
        existing = pd.read_csv(output_path)
        combined = pd.concat([existing, new_df], ignore_index=True)
        if "game_id" in combined.columns:
            combined = combined.drop_duplicates(subset=["game_id"], keep="last")
        return combined
    return new_df

def atomic_write_csv(df: pd.DataFrame, output_path: Path) -> None:
    tmp = output_path.with_suffix(".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(output_path)

# =========================
# CORE COMPUTE
# =========================

def compute_moneyline_edges(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "game_id",
        "home_dk_decimal_moneyline",
        "away_dk_decimal_moneyline",
        "home_juiced_decimal_moneyline",
        "away_juiced_decimal_moneyline",
    ]
    validate_columns(df, required)

    df["home_edge_decimal"] = safe_edge_decimal(df["home_dk_decimal_moneyline"], df["home_juiced_decimal_moneyline"])
    df["home_edge_pct"] = safe_edge_pct(df["home_dk_decimal_moneyline"], df["home_juiced_decimal_moneyline"])
    df["home_play"] = df["home_edge_decimal"] > 0

    df["away_edge_decimal"] = safe_edge_decimal(df["away_dk_decimal_moneyline"], df["away_juiced_decimal_moneyline"])
    df["away_edge_pct"] = safe_edge_pct(df["away_dk_decimal_moneyline"], df["away_juiced_decimal_moneyline"])
    df["away_play"] = df["away_edge_decimal"] > 0

    df = df.drop_duplicates(subset=["game_id"], keep="last")
    return df

def compute_puck_line_edges(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "game_id",
        "home_dk_puck_line_decimal",
        "away_dk_puck_line_decimal",
        "home_juiced_decimal_puck_line",
        "away_juiced_decimal_puck_line",
    ]
    validate_columns(df, required)

    df["home_edge_decimal"] = safe_edge_decimal(df["home_dk_puck_line_decimal"], df["home_juiced_decimal_puck_line"])
    df["home_edge_pct"] = safe_edge_pct(df["home_dk_puck_line_decimal"], df["home_juiced_decimal_puck_line"])
    df["home_play"] = df["home_edge_decimal"] > 0

    df["away_edge_decimal"] = safe_edge_decimal(df["away_dk_puck_line_decimal"], df["away_juiced_decimal_puck_line"])
    df["away_edge_pct"] = safe_edge_pct(df["away_dk_puck_line_decimal"], df["away_juiced_decimal_puck_line"])
    df["away_play"] = df["away_edge_decimal"] > 0

    df = df.drop_duplicates(subset=["game_id"], keep="last")
    return df

def compute_total_edges(df: pd.DataFrame) -> pd.DataFrame:
    required = [
        "game_id",
        "dk_total_over_decimal",
        "dk_total_under_decimal",
        "juiced_total_over_decimal",
        "juiced_total_under_decimal",
    ]
    validate_columns(df, required)

    df["over_edge_decimal"] = safe_edge_decimal(df["dk_total_over_decimal"], df["juiced_total_over_decimal"])
    df["over_edge_pct"] = safe_edge_pct(df["dk_total_over_decimal"], df["juiced_total_over_decimal"])
    df["over_play"] = df["over_edge_decimal"] > 0

    df["under_edge_decimal"] = safe_edge_decimal(df["dk_total_under_decimal"], df["juiced_total_under_decimal"])
    df["under_edge_pct"] = safe_edge_pct(df["dk_total_under_decimal"], df["juiced_total_under_decimal"])
    df["under_play"] = df["under_edge_decimal"] > 0

    df = df.drop_duplicates(subset=["game_id"], keep="last")
    return df

def process_pattern(log, pattern: str, compute_fn, label: str, summary: dict) -> None:
    input_files = sorted(INPUT_DIR.glob(pattern))
    if not input_files:
        log.write(f"No input files found for pattern: {pattern}\n")
        return

    for input_path in input_files:
        df = pd.read_csv(input_path)

        # compute edges
        out_df = compute_fn(df)

        output_path = OUTPUT_DIR / input_path.name
        final_df = upsert_dedup_by_game_id(out_df, output_path)
        atomic_write_csv(final_df, output_path)

        log.write(f"Wrote {output_path} | rows={len(final_df)}\n")
        summary["files_processed"] += 1
        summary["rows_processed"] += len(out_df)
        summary[f"{label}_files"] += 1

def main() -> None:
    with open(ERROR_LOG, "w") as log:
        log.write("=== NHL COMPUTE EDGES RUN ===\n")
        log.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")

        summary = {
            "files_processed": 0,
            "rows_processed": 0,
            "moneyline_files": 0,
            "puck_line_files": 0,
            "total_files": 0,
        }

        try:
            process_pattern(
                log=log,
                pattern="*_NHL_moneyline.csv",
                compute_fn=compute_moneyline_edges,
                label="moneyline",
                summary=summary,
            )
            process_pattern(
                log=log,
                pattern="*_NHL_puck_line.csv",
                compute_fn=compute_puck_line_edges,
                label="puck_line",
                summary=summary,
            )
            process_pattern(
                log=log,
                pattern="*_NHL_total.csv",
                compute_fn=compute_total_edges,
                label="total",
                summary=summary,
            )

            log.write("\n=== SUMMARY ===\n")
            log.write(f"Files processed: {summary['files_processed']}\n")
            log.write(f"Rows processed (this run, pre-upsert): {summary['rows_processed']}\n")
            log.write(f"Moneyline files: {summary['moneyline_files']}\n")
            log.write(f"Puck line files: {summary['puck_line_files']}\n")
            log.write(f"Total files: {summary['total_files']}\n")

        except Exception as e:
            log.write("\n=== ERROR ===\n")
            log.write(str(e) + "\n\n")
            log.write(traceback.format_exc())

if __name__ == "__main__":
    main()
