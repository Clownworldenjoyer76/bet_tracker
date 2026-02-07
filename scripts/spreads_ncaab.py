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
OUTPUT_DIR = Path("docs/win/ncaab/spreads")

EDGE = 0.05
NCAAB_STD_DEV = 11

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def to_american(decimal_odds):
    if pd.isna(decimal_odds) or decimal_odds <= 1:
        return ""
    if decimal_odds >= 2:
        return f"+{int((decimal_odds - 1) * 100)}"
    return f"-{int(100 / (decimal_odds - 1))}"

def process_spreads():
    projection_files = glob.glob(str(CLEANED_DIR / "ncaab_*.csv"))

    for proj_path in projection_files:
        date_suffix = "_".join(Path(proj_path).stem.split("_")[1:])
        dk_path = NORMALIZED_DIR / f"dk_ncaab_spreads_{date_suffix}.csv"

        if not dk_path.exists():
            continue

        df_proj = pd.read_csv(proj_path)
        df_dk = pd.read_csv(dk_path)

        df_proj = df_proj.drop(
            columns=["date", "time", "away_team", "home_team"],
            errors="ignore"
        )

        merged = pd.merge(df_proj, df_dk, on="game_id", how="inner")
        if merged.empty:
            continue

        merged["proj_home_margin"] = (
            merged["home_team_projected_points"]
            - merged["away_team_projected_points"]
        )

        merged["home_spread_probability"] = merged.apply(
            lambda x: 1 - norm.cdf(
                -x["home_spread"], x["proj_home_margin"], NCAAB_STD_DEV
            ),
            axis=1
        )
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
            "away_odds", "home_odds",
            "away_spread_probability", "home_spread_probability",
            "away_spread_acceptable_decimal_odds", "away_spread_acceptable_american_odds",
            "home_spread_acceptable_decimal_odds", "home_spread_acceptable_american_odds",
        ]

        merged[cols].to_csv(
            OUTPUT_DIR / f"spreads_ncaab_{date_suffix}.csv",
            index=False
        )

if __name__ == "__main__":
    process_spreads()
