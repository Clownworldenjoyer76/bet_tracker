import pandas as pd
import glob
from pathlib import Path

FINAL_BASE = Path("docs/win/final/step_1")
MANUAL_BASE = Path("docs/win/manual/normalized")

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

    return pd.concat(dfs, ignore_index=True).drop_duplicates(
        subset=game_col, keep="last"
    )


def update_files(
    final_glob,
    manual_glob,
    mappings,
):
    manual = load_lookup(manual_glob)
    if manual.empty:
        print(f"No manual data for {manual_glob}")
        return

    manual = manual.set_index("game_id")

    for f in glob.glob(str(final_glob)):
        df = pd.read_csv(f)

        if "game_id" not in df.columns:
            print(f"Skipping {f} (no game_id)")
            continue

        df["game_id"] = df["game_id"].astype(str).str.strip()

        filled = 0
        for out_col, src_col in mappings.items():
            df[out_col] = df["game_id"].map(manual[src_col])
            filled += df[out_col].notna().sum()

        df.to_csv(f, index=False)
        print(f"Updated {f} | values filled: {filled}")


def run():
    # ---------- MONEYLINE ----------
    update_files(
        FINAL_BASE / "nba/ml/juice_nba_ml_*.csv",
        MANUAL_BASE / "dk_nba_moneyline_*.csv",
        {
            "dk_away_odds": "away_odds",
            "dk_home_odds": "home_odds",
        },
    )

    update_files(
        FINAL_BASE / "ncaab/ml/juice_ncaab_ml_*.csv",
        MANUAL_BASE / "dk_ncaab_moneyline_*.csv",
        {
            "dk_away_odds": "away_odds",
            "dk_home_odds": "home_odds",
        },
    )

    # ---------- SPREADS ----------
    update_files(
        FINAL_BASE / "nba/spreads/juice_nba_spreads_*.csv",
        MANUAL_BASE / "dk_nba_spreads_*.csv",
        {
            "dk_away_odds": "away_odds",
            "dk_home_odds": "home_odds",
        },
    )

    update_files(
        FINAL_BASE / "ncaab/spreads/juice_ncaab_spreads_*.csv",
        MANUAL_BASE / "dk_ncaab_spreads_*.csv",
        {
            "dk_away_odds": "away_odds",
            "dk_home_odds": "home_odds",
        },
    )

    # ---------- TOTALS ----------
    update_files(
        FINAL_BASE / "nba/totals/juice_nba_totals_*.csv",
        MANUAL_BASE / "dk_nba_totals_*.csv",
        {
            "dk_over_odds": "over_odds",
            "dk_under_odds": "under_odds",
        },
    )

    update_files(
        FINAL_BASE / "ncaab/totals/juice_ncaab_totals_*.csv",
        MANUAL_BASE / "dk_ncaab_totals_*.csv",
        {
            "dk_over_odds": "over_odds",
            "dk_under_odds": "under_odds",
        },
    )


if __name__ == "__main__":
    run()
