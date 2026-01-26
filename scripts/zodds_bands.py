from pathlib import Path
import pandas as pd

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

    required = {"close_ml", "win"}
    if not required.issubset(df.columns):
        print(f"[SKIP] {path.name}: missing required columns")
        return

    # force numeric odds
    df["close_ml"] = pd.to_numeric(df["close_ml"], errors="coerce")
    df = df.dropna(subset=["close_ml"])

    df["band"] = df["close_ml"].apply(odds_to_band)

    summary = (
        df.groupby("band")
        .agg(
            bets=("win", "count"),
            wins=("win", "sum"),
        )
        .reset_index()
    )

    summary["win_pct"] = (summary["wins"] / summary["bets"]).round(4)

    out_path = path.with_name(path.stem.replace("_normalized", "") + "_ml_bands.csv")
    summary.to_csv(out_path, index=False)

    print(f"[OK] wrote {out_path} ({len(summary)} bands)")


def main():
    files = DATA_DIR.glob("*_normalized.csv")

    if not any(files):
        print("[WARN] no normalized files found")
        return

    for path in DATA_DIR.glob("*_normalized.csv"):
        try:
            process_file(path)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}")


if __name__ == "__main__":
    main()
