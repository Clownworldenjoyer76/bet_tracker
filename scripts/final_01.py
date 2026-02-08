import pandas as pd
import glob
from pathlib import Path

BASE_IN = Path("docs/win/juice")
BASE_OUT = Path("docs/win/final/step_1")

JOBS = [
    # ---------------- NBA ----------------
    (
        "nba/ml",
        [
            "date", "time", "away_team", "home_team",
            "away_team_moneyline_win_prob", "home_team_moneyline_win_prob",
            "league", "game_id",
            "away_team_projected_points", "home_team_projected_points",
            "game_projected_points",
            "home_ml_juice_odds", "away_ml_juice_odds",
        ],
    ),
    (
        "nba/spreads",
        [
            "game_id", "league", "date", "time", "away_team", "home_team",
            "away_team_projected_points", "home_team_projected_points",
            "game_projected_points",
            "away_spread", "home_spread",
            "away_handle_pct", "home_handle_pct",
            "away_bets_pct", "home_bets_pct",
            "away_spread_probability", "home_spread_probability",
            "away_spread_juice_odds", "home_spread_juice_odds",
        ],
    ),
    (
        "nba/totals",
        [
            "game_id", "league", "date", "time", "away_team", "home_team",
            "away_team_projected_points", "home_team_projected_points",
            "away_handle_pct", "home_handle_pct",
            "away_bets_pct", "home_bets_pct",
            "game_projected_points",
            "total",
            "over_probability", "under_probability",
            "over_juice_odds", "under_juice_odds",
        ],
    ),

    # ---------------- NCAAB ----------------
    (
        "ncaab/ml",
        [
            "date", "time", "away_team", "home_team",
            "away_team_moneyline_win_prob", "home_team_moneyline_win_prob",
            "league", "game_id",
            "away_team_projected_points", "home_team_projected_points",
            "game_projected_points",
            "home_ml_juice_odds", "away_ml_juice_odds",
        ],
    ),
    (
        "ncaab/spreads",
        [
            "game_id", "league", "date", "time", "away_team", "home_team",
            "away_team_projected_points", "home_team_projected_points",
            "game_projected_points",
            "away_spread", "home_spread",
            "away_handle_pct", "home_handle_pct",
            "away_bets_pct", "home_bets_pct",
            "away_odds", "home_odds",
            "away_spread_probability", "home_spread_probability",
            "away_spread_juice_odds", "home_spread_juice_odds",
        ],
    ),
    (
        "ncaab/totals",
        [
            "game_id", "league", "date", "time", "away_team", "home_team",
            "away_team_projected_points", "home_team_projected_points",
            "away_handle_pct", "home_handle_pct",
            "away_bets_pct", "home_bets_pct",
            "game_projected_points",
            "total",
            "over_probability", "under_probability",
            "over_juice_odds", "under_juice_odds",
        ],
    ),
]

def run():
    for subdir, cols in JOBS:
        in_dir = BASE_IN / subdir
        out_dir = BASE_OUT / subdir
        out_dir.mkdir(parents=True, exist_ok=True)

        for f in glob.glob(str(in_dir / "*.csv")):
            df = pd.read_csv(f)

            missing = [c for c in cols if c not in df.columns]
            if missing:
                print(f"Skipping {f} (missing columns: {missing})")
                continue

            out_df = df[cols]
            out_path = out_dir / Path(f).name
            out_df.to_csv(out_path, index=False)

            print(f"Wrote {out_path}")

if __name__ == "__main__":
    run()
