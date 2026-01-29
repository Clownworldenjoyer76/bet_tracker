import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/stage_3")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# probability buckets
BUCKETS = [
    (0.00, 0.30, "p < 0.30"),
    (0.30, 0.35, "0.30–0.35"),
    (0.35, 0.40, "0.35–0.40"),
    (0.40, 0.45, "0.40–0.45"),
    (0.45, 0.50, "0.45–0.50"),
    (0.50, 0.55, "0.50–0.55"),
    (0.55, 0.60, "0.55–0.60"),
    (0.60, 0.65, "0.60–0.65"),
    (0.65, 0.70, "0.65–0.70"),
    (0.70, 1.01, "≥ 0.70"),
]

def implied_prob(ml):
    if ml < 0:
        return abs(ml) / (abs(ml) + 100)
    return 100 / (ml + 100)

def bucketize(p):
    for lo, hi, label in BUCKETS:
        if lo <= p < hi:
            return label
    return None

def process_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    # numeric fields
    df["ML_num"] = pd.to_numeric(df["ML"], errors="coerce")
    df["actual_spread_num"] = pd.to_numeric(df["actual_spread"], errors="coerce")

    # drop unusable rows
    df = df.dropna(subset=["ML_num", "actual_spread_num"])

    # implied probability
    df["implied_prob"] = df["ML_num"].apply(implied_prob)

    # bucket
    df["prob_bucket"] = df["implied_prob"].apply(bucketize)

    # outcome (win = 1, loss = 0)
    def outcome(row):
        if row["favorite"].upper() == "YES" and row["actual_spread_num"] > 0:
            return 1
        if row["underdog"].upper() == "YES" and row["actual_spread_num"] < 0:
            return 1
        return 0

    df["win"] = df.apply(outcome, axis=1)

    # aggregate
    summary = (
        df.groupby("prob_bucket", dropna=True)
        .agg(
            bets=("win", "count"),
            wins=("win", "sum"),
        )
        .reset_index()
        .sort_values("prob_bucket")
    )

    out_path = OUT_DIR / path.name.replace("_stage2", "_stage3")
    summary.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("ncaa-basketball-*_stage2.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
