import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
BASE_OUT = Path("bets/historic/ncaab_old/location")

OUT_DIRS = {
    "neutral": BASE_OUT / "neutral",
    "away": BASE_OUT / "away",
    "home": BASE_OUT / "home",
}

for d in OUT_DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

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
    return abs(ml) / (abs(ml) + 100) if ml < 0 else 100 / (ml + 100)

def bucketize(p):
    for lo, hi, label in BUCKETS:
        if lo <= p < hi:
            return label
    return None

def parse_ml(val):
    try:
        v = str(val).strip()
        if v in ("", "NL", "-"):
            return None
        return float(v)
    except Exception:
        return None

def main():
    rows = {"neutral": [], "away": [], "home": []}

    for path in IN_DIR.glob("*.csv"):
        df = pd.read_csv(path, dtype=str)

        for _, r in df.iterrows():
            neutral = str(r["neutral_location"]).upper() == "YES"
            away_final = float(r["away_final"])
            home_final = float(r["home_final"])

            away_ml = parse_ml(r["away_ml"])
            if away_ml is not None:
                venue = "neutral" if neutral else "away"
                rows[venue].append({
                    "prob_bucket": bucketize(implied_prob(away_ml)),
                    "win": int(away_final > home_final)
                })

            home_ml = parse_ml(r["home_ml"])
            if home_ml is not None:
                venue = "neutral" if neutral else "home"
                rows[venue].append({
                    "prob_bucket": bucketize(implied_prob(home_ml)),
                    "win": int(home_final > away_final)
                })

    for venue, data in rows.items():
        out = (
            pd.DataFrame(data)
            .groupby("prob_bucket")
            .agg(bets=("win", "count"), wins=("win", "sum"))
            .reset_index()
            .sort_values("prob_bucket")
        )
        out.to_csv(OUT_DIRS[venue] / "ml_prob_buckets.csv", index=False)

if __name__ == "__main__":
    main()
