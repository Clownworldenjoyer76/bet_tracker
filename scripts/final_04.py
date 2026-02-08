import pandas as pd
import glob
from pathlib import Path

BASE_IN = Path("docs/win/final/step_1")
BASE_OUT = Path("docs/win/final/step_2")

JOBS = [
    # ---------------- MONEYLINE ----------------
    (
        BASE_IN / "*/ml/juice_*_ml_*.csv",
        [
            "date",
            "time",
            "away_team",
            "home_team",
            "league",
            "game_id",
            "home_ml_juice_odds",
            "away_ml_juice_odds",
            "dk_away_odds",
            "dk_home_odds",
        ],
    ),

    # ---------------- SPREADS ----------------
    (
        BASE_IN / "*/spreads/juice_*_spreads_*.csv",
        [
            "date",
            "time",
            "away_team",
            "home_team",
            "league",
            "game_id",
            "away_spread_juice_odds",
            "home_spread_juice_odds",
            "dk_away_odds",
            "dk_home_odds",
        ],
    ),

    # ---------------- TOTALS ----------------
    (
        BASE_IN / "*/totals/juice_*_totals_*.csv",
        [
            "date",
            "time",
            "away_team",
            "home_team",
            "league",
            "game_id",
            "over_juice_odds",
            "under_juice_odds",
            "dk_over_odds",
            "dk_under_odds",
        ],
    ),
]


def run():
    wrote_any = False

    for pattern, cols in JOBS:
        files = glob.glob(str(pattern))

        for f in files:
            df = pd.read_csv(f)

            missing = [c for c in cols if c not in df.columns]
            if missing:
                print(f"Skipping {f} (missing {missing})")
                continue

            out_df = df[cols]

            # mirror directory structure under step_2
            rel_path = Path(f).relative_to(BASE_IN)
            out_path = BASE_OUT / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            out_df.to_csv(out_path, index=False)
            wrote_any = True
            print(f"Wrote {out_path}")

    if not wrote_any:
        print("WARNING: final_04.py wrote no files — check input paths")


if __name__ == "__main__":
    run()
