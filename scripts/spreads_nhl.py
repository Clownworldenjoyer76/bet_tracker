import pandas as pd
import glob
import numpy as np
from pathlib import Path
from scipy.stats import norm

# =========================
# CONSTANTS
# =========================

CLEANED_DIR = Path("docs/win/dump/csvs/cleaned")
NORMALIZED_DIR = Path("docs/win/manual/normalized")
OUTPUT_DIR = Path("docs/win/nhl/spreads")

EDGE = 0.05
NHL_STD_DEV = 2.0  # NHL goal margin std dev

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1:
        return ""
    if decimal_odds >= 2:
        return f"+{int((decimal_odds - 1) * 100)}"
    return f"-{int(100 / (decimal_odds - 1))}"

# =========================
# CORE
# =========================

def process_spreads():
    projection_files = glob.glob(str(CLEANED_DIR / "nhl_*.csv"))

    for proj_path in projection_files:
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_path = NORMALIZED_DIR / f"dk_nhl_spreads_{date_suffix}.csv"

        # ✅ NHL DK spreads not available yet → safe skip
        if not dk_path.exists():
            print(f"No NHL DK spreads for {date_suffix}, skipping.")
            continue

        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_path)

        # Drop identity columns from projections
        df_proj = df_proj.drop(
            columns=["date", "time", "away_team", "home_team"],
            errors="ignore"
        )

        merged = pd.merge(df_proj, df_dk, on="game_id", how="inner")
        if merged.empty:
            continue

        # Projected home goal margin
        merged["proj_home_margin"] = (
            merged["home_team_projected_goals"]
            - merged["away_team_projected_goals"]
        )

        # Probabilities to cover puck line
        merged["home_spread_probability"] = merged.apply(
            lambda x: 1 - norm.cdf(
                -x["home_spread"], x["proj_home_margin"], NHL_STD_DEV
            ),
            axis=1
        )
        merged["away_spread_probability"] = 1 - merged["home_spread_probability"]

        # Acceptable odds
        merged["home_spread_acceptable_decimal_odds"] = (
            (1 / merged["home_spread_probability"]) * (1 + EDGE)
        )
        merged["away_spread_acceptable_decimal_odds"] = (
            (1 / merged["away_spread_probability"]) * (1 + EDGE)
        )

        merged["home_spread_acceptable_american_odds"] = (
            merged["home_spread_acceptable_decimal_odds"].apply(to_american)
        )
        merged["away_spread_acceptable_american_odds"] = (
            merged["away_spread_acceptable_decimal_odds"].apply(to_american)
        )

        cols = [
            "game_id", "league", "date", "time",
            "away_team", "home_team",
            "away_team_projected_goals", "home_team_projected_goals",
            "game_projected_goals",
            "away_spread", "home_spread",
            "away_handle_pct", "home_handle_pct",
            "away_bets_pct", "home_bets_pct",
            "away_odds", "home_odds",
            "away_spread_probability", "home_spread_probability",
            "away_spread_acceptable_decimal_odds", "away_spread_acceptable_american_odds",
            "home_spread_acceptable_decimal_odds", "home_spread_acceptable_american_odds",
        ]

        merged[cols].to_csv(
            OUTPUT_DIR / f"spreads_nhl_{date_suffix}.csv",
            index=False
        )

if __name__ == "__main__":
    process_spreads()
