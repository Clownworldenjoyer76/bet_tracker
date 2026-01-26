# scripts/zodds_bands.py

from pathlib import Path
import pandas as pd

DATA_DIR = Path("bets/historic")

ODDS_BINS = [
    (-10000, -300, "<= -300"),
    (-299, -200, "-299 to -200"),
    (-199, -150, "-199 to -150"),
    (-149, -110, "-149 to -110"),
    (-109, -101, "-109 to -101"),
    (100, 149, "+100 to +149"),
    (150, 199, "+150 to +199"),
    (200, 299, "+200 to +299"),
    (300, 10000, ">= +300"),
]


def odds_band(odds: float) -> str | None:
    if pd.isna(odds):
        return None
    for low, high, label in ODDS_BINS:
        if low <= odds <= high:
            return label
    return None


def process_file(path: Path):
    df = pd.read_csv(path)

    required = {
        "home_close_ml",
        "away_close_ml",
        "home_final",
        "away_final",
    }

    if not required.issubset(df.columns):
        print(f"[SKIP] {path.name} missing required columns")
        return

    rows = []

    for side in ("home", "away"):
        odds_col = f"{side}_close_ml"
        score_col = f"{side}_final"
        opp_col = "away_final" if side == "home" else "home_final"

        tmp = df[[odds_col, score_col, opp_col]].copy()
        tmp["win"] = tmp[score_col] > tmp[opp_col]
        tmp["odds"] = tmp[odds_col]
        tmp["band"] = tmp["odds"].apply(odds_band)

        rows.append(tmp[["band", "win"]])

    bets = pd.concat(rows)
    bets = bets.dropna(subset=["band"])

    summary = (
        bets.groupby("band")
        .agg(
            bets=("win", "count"),
            wins=("win", "sum"),
        )
        .reset_index()
    )

    summary["win_pct"] = (summary["wins"] / summary["bets"]).round(4)

    out_path = path.with_name(path.stem + "_ml_bands.csv")
    summary.to_csv(out_path, index=False)

    print(f"[OK] wrote {out_path} ({len(summary)} bands)")


def main():
    for path in DATA_DIR.glob("*_data.csv"):
        process_file(path)


if __name__ == "__main__":
    main()
