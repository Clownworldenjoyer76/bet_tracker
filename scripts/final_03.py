import pandas as pd
import glob
from pathlib import Path

FINAL_BASE = Path("docs/win/final/step_1")
MANUAL_BASE = Path("docs/win/manual/normalized")

COVERAGE_THRESHOLD = 0.80

FILES_PROCESSED = 0
TOTAL_ROWS = 0
TOTAL_FILLED = 0


def load_lookup(pattern, game_col="game_id"):
    dfs = []

    for f in glob.glob(str(pattern)):
        df = pd.read_csv(f)

        if game_col not in df.columns:
            continue

        df[game_col] = df[game_col].astype(str).str.strip()
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return (
        pd.concat(dfs, ignore_index=True)
        .drop_duplicates(subset=game_col, keep="last")
        .set_index(game_col)
    )


def update_files(final_glob, manual_glob, mappings):
    global FILES_PROCESSED, TOTAL_ROWS, TOTAL_FILLED

    manual = load_lookup(manual_glob)

    if manual.empty:
        raise RuntimeError(f"No manual data found for {manual_glob}")

    for f in glob.glob(str(final_glob)):
        df = pd.read_csv(f)
        FILES_PROCESSED += 1

        if "game_id" not in df.columns:
            raise RuntimeError(f"{f} missing game_id column")

        df["game_id"] = df["game_id"].astype(str).str.strip()

        rows = len(df)
        TOTAL_ROWS += rows

        for out_col, src_col in mappings.items():
            if src_col not in manual.columns:
                raise RuntimeError(
                    f"Manual source column '{src_col}' missing in {manual_glob}"
                )
            df[out_col] = df["game_id"].map(manual[src_col])

        required_cols = list(mappings.keys())
        rows_fully_filled = df[required_cols].notna().all(axis=1).sum()

        TOTAL_FILLED += rows_fully_filled

        df.to_csv(f, index=False)
        print(f"Updated {f} | rows={rows} | fully_filled_rows={rows_fully_filled}")


def run():
    update_files(
        FINAL_BASE / "nba/ml/juice_nba_ml_*.csv",
        MANUAL_BASE / "dk_nba_moneyline_*.csv",
        {
            "away_handle_pct": "away_handle_pct",
            "home_handle_pct": "home_handle_pct",
            "away_bets_pct": "away_bets_pct",
            "home_bets_pct": "home_bets_pct",
        },
    )

    update_files(
        FINAL_BASE / "ncaab/ml/juice_ncaab_ml_*.csv",
        MANUAL_BASE / "dk_ncaab_moneyline_*.csv",
        {
            "away_handle_pct": "away_handle_pct",
            "home_handle_pct": "home_handle_pct",
            "away_bets_pct": "away_bets_pct",
            "home_bets_pct": "home_bets_pct",
        },
    )

    coverage = TOTAL_FILLED / TOTAL_ROWS if TOTAL_ROWS else 0

    print("\n=== FINAL_03 SUMMARY ===")
    print(f"Files processed: {FILES_PROCESSED}")
    print(f"Total rows: {TOTAL_ROWS}")
    print(f"Fully filled rows: {TOTAL_FILLED}")
    print(f"Coverage: {coverage:.2%}")

    if FILES_PROCESSED == 0:
        raise RuntimeError("final_03: 0 files processed")

    if TOTAL_ROWS == 0:
        raise RuntimeError("final_03: 0 rows processed")

    if coverage < COVERAGE_THRESHOLD:
        raise RuntimeError(
            f"final_03: Manual coverage below threshold ({coverage:.2%})"
        )


if __name__ == "__main__":
    run()
