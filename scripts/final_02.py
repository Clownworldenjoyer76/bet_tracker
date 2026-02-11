import pandas as pd
import glob
from pathlib import Path

FINAL_BASE = Path("docs/win/final/step_1")
MANUAL_BASE = Path("docs/win/manual/normalized")

COVERAGE_THRESHOLD = 0.80

FILES_PROCESSED = 0
TOTAL_ROWS = 0
TOTAL_FILLED = 0

def update_files(final_glob, manual_glob, mappings):
    global FILES_PROCESSED, TOTAL_ROWS, TOTAL_FILLED

    manual_files = glob.glob(str(manual_glob))
    if not manual_files:
        raise RuntimeError(f"No manual files found for {manual_glob}")

    manual = pd.concat([pd.read_csv(f) for f in manual_files])
    manual["game_id"] = manual["game_id"].astype(str).str.strip()
    manual = manual.drop_duplicates("game_id").set_index("game_id")

    for f in glob.glob(str(final_glob)):
        df = pd.read_csv(f)
        FILES_PROCESSED += 1

        if "game_id" not in df.columns:
            raise RuntimeError(f"{f} missing game_id")

        df["game_id"] = df["game_id"].astype(str).str.strip()
        rows = len(df)
        TOTAL_ROWS += rows

        filled = 0
        for out_col, src_col in mappings.items():
            df[out_col] = df["game_id"].map(manual[src_col])
            filled += df[out_col].notna().sum()

        TOTAL_FILLED += filled
        df.to_csv(f, index=False)

        print(f"Updated {f} | rows={rows} | filled={filled}")

def run():
    update_files(
        FINAL_BASE / "nba/ml/*.csv",
        MANUAL_BASE / "dk_nba_moneyline_*.csv",
        {"dk_away_odds": "away_odds", "dk_home_odds": "home_odds"},
    )

    coverage = TOTAL_FILLED / TOTAL_ROWS if TOTAL_ROWS else 0

    print("\n=== FINAL_02 SUMMARY ===")
    print(f"Files processed: {FILES_PROCESSED}")
    print(f"Total rows: {TOTAL_ROWS}")
    print(f"Coverage: {coverage:.2%}")

    if FILES_PROCESSED == 0:
        raise RuntimeError("final_02: 0 files processed")

    if coverage < COVERAGE_THRESHOLD:
        raise RuntimeError(f"Manual coverage below threshold: {coverage:.2%}")

if __name__ == "__main__":
    run()
