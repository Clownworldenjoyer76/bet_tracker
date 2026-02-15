# scripts/spreads_ncaab.py

import pandas as pd
import glob
from pathlib import Path
from scipy.stats import norm
from datetime import datetime

CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/ncaab/spreads")
ERROR_DIR = Path("docs/win/errors/06_spreads")
ERROR_LOG = ERROR_DIR / "spreads_ncaab_errors.txt"

EDGE = 0.05
NCAAB_STD_DEV = 15

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)


def log(msg):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def log_error(msg):
    log(f"{datetime.utcnow().isoformat()} | ERROR | {msg}")


def to_american(dec):
    if pd.isna(dec) or dec <= 1:
        return ""
    if dec >= 2:
        return f"+{int((dec - 1) * 100)}"
    return f"-{int(100 / (dec - 1))}"


def clamp_probability(p):
    return min(max(p, 0.05), 0.95)


def process_spreads():
    ERROR_LOG.write_text("", encoding="utf-8")

    log("=== NCAAB SPREADS RUN START ===")
    log(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    log(f"CLEANED_DIR exists: {CLEANED_DIR.exists()}")
    log(f"NORMALIZED_DIR exists: {NORMALIZED_DIR.exists()}")
    log(f"OUTPUT_DIR exists: {OUTPUT_DIR.exists()}")

    projection_files = glob.glob(str(CLEANED_DIR / "ncaab_*.csv"))
    log(f"Projection files found: {len(projection_files)}")

    if not projection_files:
        log_error("No NCAAB projection files found")
        log("=== RUN END ===")
        return

    total_files_processed = 0
    total_rows_written = 0
    total_merge_rows = 0

    for proj_path in projection_files:
        log(f"Processing projection file: {proj_path}")

        try:
            date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
            dk_path = NORMALIZED_DIR / f"dk_ncaab_spreads_{date_suffix}.csv"

            log(f"Expected DK file: {dk_path}")
            log(f"DK exists: {dk_path.exists()}")

            if not dk_path.exists():
                log_error(f"Missing DK file: {dk_path}")
                continue

            df_proj = pd.read_csv(proj_path)
            df_dk = pd.read_csv(dk_path)

            log(f"Projection rows: {len(df_proj)}")
            log(f"DK rows: {len(df_dk)}")

            dk_required_cols = [
                "game_id", "league", "date", "time",
                "away_team", "home_team",
                "away_spread", "home_spread",
                "away_handle_pct", "home_handle_pct",
                "away_bets_pct", "home_bets_pct",
            ]

            missing_cols = [c for c in dk_required_cols if c not in df_dk.columns]
            if missing_cols:
                log_error(f"Missing DK columns: {missing_cols}")
                continue

            df_dk_subset = df_dk[dk_required_cols]

            df_proj = df_proj[
                [
                    "game_id",
                    "away_team_projected_points",
                    "home_team_projected_points",
                    "game_projected_points",
                ]
            ]

            merged = pd.merge(df_dk_subset, df_proj, on="game_id", how="inner")

            log(f"Merged rows: {len(merged)}")

            if merged.empty:
                log_error(f"No merge rows for {proj_path}")
                continue

            total_merge_rows += len(merged)

            merged["proj_home_margin"] = (
                merged["home_team_projected_points"]
                - merged["away_team_projected_points"]
            )

            merged["home_spread_probability"] = merged.apply(
                lambda x: 1 - norm.cdf(
                    -x["home_spread"],
                    x["proj_home_margin"],
                    NCAAB_STD_DEV,
                ),
                axis=1,
            )

            merged["home_spread_probability"] = merged[
                "home_spread_probability"
            ].apply(clamp_probability)

            merged["away_spread_probability"] = 1 - merged["home_spread_probability"]

            merged["home_spread_acceptable_decimal_odds"] = (
                (1 / merged["home_spread_probability"]) * (1 + EDGE)
            )
            merged["away_spread_acceptable_decimal_odds"] = (
                (1 / merged["away_spread_probability"]) * (1 + EDGE)
            )

            merged["home_spread_acceptable_american_odds"] = merged[
                "home_spread_acceptable_decimal_odds"
            ].apply(to_american)

            merged["away_spread_acceptable_american_odds"] = merged[
                "away_spread_acceptable_decimal_odds"
            ].apply(to_american)

            cols = [
                "game_id", "league", "date", "time",
                "away_team", "home_team",
                "away_team_projected_points", "home_team_projected_points",
                "game_projected_points",
                "away_spread", "home_spread",
                "away_handle_pct", "home_handle_pct",
                "away_bets_pct", "home_bets_pct",
                "away_spread_probability", "home_spread_probability",
                "away_spread_acceptable_decimal_odds", "away_spread_acceptable_american_odds",
                "home_spread_acceptable_decimal_odds", "home_spread_acceptable_american_odds",
            ]

            output_path = OUTPUT_DIR / f"spreads_ncaab_{date_suffix}.csv"
            merged[cols].to_csv(output_path, index=False)

            log(f"Wrote file: {output_path}")
            total_files_processed += 1
            total_rows_written += len(merged)

        except Exception as e:
            log_error(f"{proj_path} failed: {e}")

    log("=== SUMMARY ===")
    log(f"Files processed: {total_files_processed}")
    log(f"Total merged rows: {total_merge_rows}")
    log(f"Total rows written: {total_rows_written}")
    log("=== RUN END ===")


if __name__ == "__main__":
    process_spreads()
