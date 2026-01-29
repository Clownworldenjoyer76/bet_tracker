import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/tally")
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

def implied_prob(ml: float) -> float:
    if ml < 0:
        return abs(ml) / (abs(ml) + 100)
    return 100 / (ml + 100)

def bucketize(p: float):
    for lo, hi, label in BUCKETS:
        if lo <= p < hi:
            return label
    return None

def parse_ml(val):
    if val is None:
        return None
    val = str(val).strip()
    if val in ("", "NL", "-"):
        return None
    try:
        return float(val)
    except ValueError:
        return None

def main():
    rows = []

    for path in IN_DIR.glob("*.csv"):
        df = pd.read_csv(path, dtype=str)

        for _, r in df.iterrows():
            away_final = float(r["away_final"])
            home_final = float(r["home_final"])

            away_ml = parse_ml(r["away_ml"])
            if away_ml is not None:
                rows.append({
                    "prob_bucket": bucketize(implied_prob(away_ml)),
                    "win": int(away_final > home_final)
                })

            home_ml = parse_ml(r["home_ml"])
            if home_ml is not None:
                rows.append({
                    "prob_bucket": bucketize(implied_prob(home_ml)),
                    "win": int(home_final > away_final)
                })

    out = (
        pd.DataFrame(rows)
        .groupby("prob_bucket")
        .agg(bets=("win", "count"), wins=("win", "sum"))
        .reset_index()
        .sort_values("prob_bucket")
    )

    out.to_csv(OUT_DIR / "ml_prob_bucket_tally.csv", index=False)

if __name__ == "__main__":
    main()
