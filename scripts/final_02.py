import pandas as pd
import glob
from pathlib import Path

FINAL_BASE = Path("docs/win/final/step_1")
MANUAL_BASE = Path("docs/win/manual/normalized")

TARGETS = [
    (
        "nba",
        FINAL_BASE / "nba/ml",
        MANUAL_BASE / "dk_nba_moneyline_*.csv",
    ),
    (
        "ncaab",
        FINAL_BASE / "ncaab/ml",
        MANUAL_BASE / "dk_ncaab_moneyline_*.csv",
    ),
]

HANDLE_COLS = [
    "away_handle_pct",
    "home_handle_pct",
    "away_bets_pct",
    "home_bets_pct",
]

def load_manual_map(pattern):
    """
    Load all DK manual files into a single lookup DataFrame keyed by game_id.
    Last file wins if duplicates exist.
    """
    dfs = []
    for f in glob.glob(str(pattern)):
        df = pd.read_csv(f)

        missing = ["game_id", *HANDLE_COLS]
        missing = [c for c in missing if c not in df.columns]
        if missing:
            print(f"Skipping manual file {f} (missing {missing})")
            continue

        dfs.append(df[["game_id", *HANDLE_COLS]])

    if not dfs:
        return pd.DataFrame(columns=["game_id", *HANDLE_COLS])

    out = pd.concat(dfs, ignore_index=True)
    return out.drop_duplicates(subset="game_id", keep="last")


def run():
    for league, final_dir, manual_pattern in TARGETS:
        manual_df = load_manual_map(manual_pattern)

        if manual_df.empty:
            print(f"No manual data found for {league}, skipping")
            continue

        manual_df = manual_df.set_index("game_id")

        for f in glob.glob(str(final_dir / "juice_*.csv")):
            df = pd.read_csv(f)

            if "game_id" not in df.columns:
                print(f"Skipping {f} (no game_id)")
                continue

            # Add columns if missing
            for col in HANDLE_COLS:
                if col not in df.columns:
                    df[col] = pd.NA

            # Map values by game_id
            df = df.set_index("game_id")
            for col in HANDLE_COLS:
                if col in manual_df.columns:
                    df[col] = df[col].combine_first(manual_df[col])

            df = df.reset_index()

            df.to_csv(f, index=False)
            print(f"Updated {f}")


if __name__ == "__main__":
    run()
