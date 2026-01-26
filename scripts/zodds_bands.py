from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("bets/historic")

ODDS_BANDS = [
    (-10000, -301),
    (-300, -201),
    (-200, -151),
    (-150, -101),
    (-100, -1),
    (100, 149),
    (150, 199),
    (200, 299),
    (300, 10000),
]


def odds_to_band(odds: float) -> str:
    for low, high in ODDS_BANDS:
        if low <= odds <= high:
            return f"{low} to {high}"
    return "unknown"


def process_file(path: Path):
    df = pd.read_csv(path)

    # detect required columns
    required = {
        "home_score",
        "away_score",
        "home_close_ml",
        "away_close_ml",
    }

    if not required.issubset(df.columns):
        print(f"[SKIP] {path.name}: missing required columns")
        return

    # force numeric scores (THIS FIXES YOUR ERROR)
    for col in ["home_score", "away_score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["home_score", "away_score"])

    records = []

    # home side
    home = df[["home_close_ml", "home_score", "away_score"]].copy()
    home["odds"] = pd.to_numeric(home["home_close_ml"], errors="coerce")
    home["win"] = home["home_score"] > home["away_score"]

    # away side
    away = df[["away_close_ml", "away_score", "home_score"]].copy()
    away["odds"] = pd.to_numeric(away["away_close_ml"], errors="coerce")
    away["win"] = away["away_score"] > away["home_score"]

    all_sides = pd.concat(
        [
            home[["odds", "win"]],
            away[["odds", "win"]],
        ],
        ignore_index=True,
    )

    all_sides = all_sides.dropna(subset=["odds"])

    all_sides["band"] = all_sides["odds"].apply(odds_to_band)

    summary = (
        all_sides.groupby("band", dropna=True)
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
    files = DATA_DIR.glob("*_data.csv")

    for path in files:
        try:
            process_file(path)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}")


if __name__ == "__main__":
    main()
