import pandas as pd
import glob
from pathlib import Path

STEP1 = Path("docs/win/final/step_1")
STEP2 = Path("docs/win/final/step_2")
STEP3 = Path("docs/win/final/step_3")


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def write_filtered(
    step2_pattern,
    step1_pattern,
    out_base,
    juice_dk_pairs,
    keep_cols,
    extra_merge_cols=None,
):
    step1_map = {}

    # load step_1 data if needed (for spreads / totals)
    if step1_pattern:
        for f in glob.glob(str(step1_pattern)):
            df = pd.read_csv(f)
            df["game_id"] = df["game_id"].astype(str)
            step1_map[Path(f).name] = df

    for f in glob.glob(str(step2_pattern)):
        df = pd.read_csv(f)
        df["game_id"] = df["game_id"].astype(str)

        # apply juice > dk condition
        mask = False
        for juice_col, dk_col in juice_dk_pairs:
            if juice_col in df.columns and dk_col in df.columns:
                mask = mask | (df[juice_col] > df[dk_col])

        df = df[mask].copy()
        if df.empty:
            continue

        # merge extra values from step_1 (spread / total)
        if extra_merge_cols:
            step1_file = Path(f).name
            if step1_file in step1_map:
                step1_df = step1_map[step1_file][
                    ["game_id"] + extra_merge_cols
                ]
                df = df.merge(step1_df, on="game_id", how="left")

        out_df = df[keep_cols]

        out_path = STEP3 / Path(f).relative_to(STEP2)
        ensure_dir(out_path.parent)
        out_df.to_csv(out_path, index=False)

        print(f"Wrote {out_path}")


def run():
    # ---------- ML ----------
    write_filtered(
        STEP2 / "*/ml/juice_*_ml_*.csv",
        None,
        STEP3,
        [
            ("deci_home_ml_juice_odds", "deci_dk_home_odds"),
            ("deci_away_ml_juice_odds", "deci_dk_away_odds"),
        ],
        [
            "date",
            "time",
            "away_team",
            "home_team",
            "league",
            "game_id",
            "deci_home_ml_juice_odds",
            "deci_away_ml_juice_odds",
            "deci_dk_away_odds",
            "deci_dk_home_odds",
        ],
    )

    # ---------- SPREADS ----------
    write_filtered(
        STEP2 / "*/spreads/juice_*_spreads_*.csv",
        STEP1 / "*/spreads/juice_*_spreads_*.csv",
        STEP3,
        [
            ("deci_away_spread_juice_odds", "deci_dk_away_odds"),
            ("deci_home_spread_juice_odds", "deci_dk_home_odds"),
        ],
        [
            "date",
            "time",
            "away_team",
            "home_team",
            "league",
            "game_id",
            "deci_away_spread_juice_odds",
            "deci_home_spread_juice_odds",
            "deci_dk_away_odds",
            "deci_dk_home_odds",
            "away_spread",
            "home_spread",
        ],
        extra_merge_cols=["away_spread", "home_spread"],
    )

    # ---------- TOTALS ----------
    write_filtered(
        STEP2 / "*/totals/juice_*_totals_*.csv",
        STEP1 / "*/totals/juice_*_totals_*.csv",
        STEP3,
        [
            ("deci_over_juice_odds", "deci_dk_over_odds"),
            ("deci_under_juice_odds", "deci_dk_under_odds"),
        ],
        [
            "date",
            "time",
            "away_team",
            "home_team",
            "league",
            "game_id",
            "deci_over_juice_odds",
            "deci_under_juice_odds",
            "deci_dk_over_odds",
            "deci_dk_under_odds",
            "total",
        ],
        extra_merge_cols=["total"],
    )


if __name__ == "__main__":
    run()
