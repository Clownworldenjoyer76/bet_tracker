import pandas as pd
import glob
from pathlib import Path

FINAL_BASE = Path("docs/win/final/step_1")
MANUAL_BASE = Path("docs/win/manual/normalized")

# League-specific thresholds
THRESHOLDS = {
    "nba": 0.80,
    "ncaab": 0.50,  # allow expected drops
}

FILES_PROCESSED = 0
TOTAL_ROWS = 0


def load_lookup(pattern):
    files = glob.glob(str(pattern))
    if not files:
        raise RuntimeError(f"No manual files found for {pattern}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        if "game_id" not in df.columns:
            continue
        df["game_id"] = df["game_id"].astype(str).str.strip()
        dfs.append(df)

    if not dfs:
        raise RuntimeError(f"Manual files missing game_id for {pattern}")

    return (
        pd.concat(dfs, ignore_index=True)
        .drop_duplicates(subset="game_id", keep="last")
        .set_index("game_id")
    )


def update_files(final_glob, manual_glob, mappings, league_key):
    global FILES_PROCESSED, TOTAL_ROWS

    manual = load_lookup(manual_glob)

    league_rows = 0
    league_filled = 0

    for f in glob.glob(str(final_glob)):
        df = pd.read_csv(f)
        FILES_PROCESSED += 1

        if "game_id" not in df.columns:
            raise RuntimeError(f"{f} missing game_id")

        df["game_id"] = df["game_id"].astype(str).str.strip()

        rows = len(df)
        TOTAL_ROWS += rows
        league_rows += rows

        for out_col, src_col in mappings.items():
            if src_col not in manual.columns:
                raise RuntimeError(
                    f"Manual source column '{src_col}' missing in {manual_glob}"
                )
            df[out_col] = df["game_id"].map(manual[src_col])

        required_cols = list(mappings.keys())
        rows_fully_filled = df[required_cols].notna().all(axis=1).sum()
        league_filled += rows_fully_filled

        df.to_csv(f, index=False)

        print(
            f"Updated {f} | rows={rows} | fully_filled_rows={rows_fully_filled}"
        )

    if league_rows == 0:
        raise RuntimeError(f"{league_key}: 0 rows processed")

    coverage = league_filled / league_rows
    threshold = THRESHOLDS[league_key]

    print(
        f"{league_key.upper()} Coverage: {coverage:.2%} "
        f"(threshold {threshold:.0%})"
    )

    if coverage < threshold:
        raise RuntimeError(
            f"final_02: {league_key} coverage below threshold "
            f"({coverage:.2%} < {threshold:.0%})"
        )


def run():
    # ---------------- NBA MONEYLINE ----------------
    update_files(
        FINAL_BASE / "nba/ml/*.csv",
        MANUAL_BASE / "dk_nba_moneyline_*.csv",
        {"dk_away_odds": "away_odds", "dk_home_odds": "home_odds"},
        league_key="nba",
    )

    # ---------------- NBA SPREADS ----------------
    update_files(
        FINAL_BASE / "nba/spreads/*.csv",
        MANUAL_BASE / "dk_nba_spreads_*.csv",
        {"dk_away_odds": "away_odds", "dk_home_odds": "home_odds"},
        league_key="nba",
    )

    # ---------------- NBA TOTALS ----------------
    update_files(
        FINAL_BASE / "nba/totals/*.csv",
        MANUAL_BASE / "dk_nba_totals_*.csv",
        {"dk_over_odds": "over_odds", "dk_under_odds": "under_odds"},
        league_key="nba",
    )

    # ---------------- NCAAB MONEYLINE ----------------
    update_files(
        FINAL_BASE / "ncaab/ml/*.csv",
        MANUAL_BASE / "dk_ncaab_moneyline_*.csv",
        {"dk_away_odds": "away_odds", "dk_home_odds": "home_odds"},
        league_key="ncaab",
    )

    # ---------------- NCAAB SPREADS ----------------
    update_files(
        FINAL_BASE / "ncaab/spreads/*.csv",
        MANUAL_BASE / "dk_ncaab_spreads_*.csv",
        {"dk_away_odds": "away_odds", "dk_home_odds": "home_odds"},
        league_key="ncaab",
    )

    # ---------------- NCAAB TOTALS ----------------
    update_files(
        FINAL_BASE / "ncaab/totals/*.csv",
        MANUAL_BASE / "dk_ncaab_totals_*.csv",
        {"dk_over_odds": "over_odds", "dk_under_odds": "under_odds"},
        league_key="ncaab",
    )

    print("\n=== FINAL_02 SUMMARY ===")
    print(f"Files processed: {FILES_PROCESSED}")
    print(f"Total rows processed: {TOTAL_ROWS}")

    if FILES_PROCESSED == 0:
        raise RuntimeError("final_02: 0 files processed")

    if TOTAL_ROWS == 0:
        raise RuntimeError("final_02: 0 rows processed")


if __name__ == "__main__":
    run()
