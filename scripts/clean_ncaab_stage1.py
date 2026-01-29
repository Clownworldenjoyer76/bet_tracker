import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/stage_3")
OUT_DIR.mkdir(parents=True, exist_ok=True)

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
    ml = float(ml)
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

    rows = []

    for _, r in df.iterrows():
        # away side
        if r["away_ml"] not in ("", "NL"):
            ml = float(r["away_ml"])
            p = implied_prob(ml)
            bucket = bucketize(p)
            win = int(float(r["away_final"]) > float(r["home_final"]))
            rows.append({"prob_bucket": bucket, "win": win})

        # home side
        if r["home_ml"] not in ("", "NL"):
            ml = float(r["home_ml"])
            p = implied_prob(ml)
            bucket = bucketize(p)
            win = int(float(r["home_final"]) > float(r["away_final"]))
            rows.append({"prob_bucket": bucket, "win": win})

    out = (
        pd.DataFrame(rows)
        .groupby("prob_bucket", dropna=True)
        .agg(bets=("win", "count"), wins=("win", "sum"))
        .reset_index()
        .sort_values("prob_bucket")
    )

    out_path = OUT_DIR / path.name.replace(".csv", "_prob_buckets.csv")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("*.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
