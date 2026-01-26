from pathlib import Path
import pandas as pd

DATA_DIR = Path("bets/historic")

ODDS_BANDS = [
    (-10000, -1000),
    (-999, -600),
    (-599, -500),
    (-499, -400),
    (-399, -350),
    (-349, -325),
    (-324, -300),
    (-299, -290),
    (-289, -280),
    (-279, -270),
    (-269, -260),
    (-259, -250),
    (-249, -240),
    (-239, -230),
    (-229, -220),
    (-219, -210),
    (-209, -200),
    (-199, -190),
    (-189, -180),
    (-179, -170),
    (-169, -160),
    (-159, -150),
    (-149, -140),
    (-139, -130),
    (-129, -120),
    (-119, -110),
    (-109, -100),
    (-99, -90),
    (-89, -80),
    (-79, -70),
    (-69, -60),
    (-59, -50),
    (-49, -40),
    (-39, -30),
    (-29, -20),
    (-19, -10),
    (-9, 0),
    (1, 9),
    (10, 19),
    (20, 29),
    (30, 39),
    (40, 49),
    (50, 59),
    (60, 69),
    (70, 79),
    (80, 89),
    (90, 99),
    (100, 109),
    (110, 119),
    (120, 129),
    (130, 139),
    (140, 149),
    (150, 159),
    (160, 169),
    (170, 179),
    (180, 189),
    (190, 199),
    (200, 209),
    (210, 219),
    (220, 229),
    (230, 239),
    (240, 249),
    (250, 259),
    (260, 269),
    (270, 279),
    (280, 289),
    (290, 299),
    (300, 324),
    (325, 349),
    (350, 399),
    (400, 449),
    (450, 499),
    (500, 599),
    (600, 999),
    (1000, 10000),
]


def odds_to_band(odds: float) -> str:
    for low, high in ODDS_BANDS:
        if low <= odds <= high:
            return f"{low} to {high}"
    return "unknown"


def calc_profit(odds: float, win: bool) -> float:
    if not win:
        return -1.0
    if odds < 0:
        return 100.0 / abs(odds)
    return odds / 100.0


def process_file(path: Path):
    df = pd.read_csv(path)

    required = {"close_ml", "win"}
    if not required.issubset(df.columns):
        print(f"[SKIP] {path.name}: missing required columns")
        return

    df["close_ml"] = pd.to_numeric(df["close_ml"], errors="coerce")
    df = df.dropna(subset=["close_ml"])

    df["band"] = df["close_ml"].apply(odds_to_band)
    df["side"] = df["close_ml"].apply(
        lambda x: "favorite" if x < 0 else "underdog"
    )

    df["profit"] = df.apply(
        lambda r: calc_profit(r["close_ml"], r["win"]),
        axis=1,
    )

    summary = (
        df.groupby(["band", "side"], dropna=True)
        .agg(
            bets=("win", "count"),
            wins=("win", "sum"),
            profit=("profit", "sum"),
        )
        .reset_index()
    )

    summary["win_pct"] = (summary["wins"] / summary["bets"]).round(4)
    summary["roi"] = (summary["profit"] / summary["bets"]).round(4)

    out_path = path.with_name(
        path.stem.replace("_normalized", "") + "_ml_bands.csv"
    )
    summary.to_csv(out_path, index=False)

    print(f"[OK] wrote {out_path} ({len(summary)} rows)")


def main():
    files = list(DATA_DIR.glob("*_normalized.csv"))

    if not files:
        print("[WARN] no normalized files found")
        return

    for path in files:
        try:
            process_file(path)
        except Exception as e:
            print(f"[ERROR] {path.name}: {e}")


if __name__ == "__main__":
    main()
