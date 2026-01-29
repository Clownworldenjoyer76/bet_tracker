import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/Spreads")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# spread-magnitude buckets (absolute value)
SPREAD_BUCKETS = [
    (0.0, 3.0, "0–3"),
    (3.0, 7.0, "3–7"),
    (7.0, 12.0, "7–12"),
    (12.0, 20.0, "12–20"),
    (20.0, 200.0, "≥20"),
]

def bucketize_spread(mag: float):
    for lo, hi, label in SPREAD_BUCKETS:
        if lo <= mag < hi:
            return label
    return None

def parse_float(val):
    if val is None:
        return None
    val = str(val).strip()
    if val in ("", "NL", "-"):
        return None
    try:
        return float(val)
    except ValueError:
        return None

def process_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    rows = []

    for _, r in df.iterrows():
        away_final = parse_float(r["away_final"])
        home_final = parse_float(r["home_final"])
        away_spread = parse_float(r["away_spread"])
        home_spread = parse_float(r["home_spread"])

        if away_final is None or home_final is None:
            continue

        # Away ATS bet
        if away_spread is not None:
            mag = abs(away_spread)
            bucket = bucketize_spread(mag)
            if bucket is not None:
                ats_margin = (away_final + away_spread) - home_final
                if ats_margin > 0:
                    outcome = "COVER"
                elif ats_margin < 0:
                    outcome = "NO_COVER"
                else:
                    outcome = "PUSH"
                rows.append({"spread_bucket": bucket, "outcome": outcome})

        # Home ATS bet
        if home_spread is not None:
            mag = abs(home_spread)
            bucket = bucketize_spread(mag)
            if bucket is not None:
                ats_margin = (home_final + home_spread) - away_final
                if ats_margin > 0:
                    outcome = "COVER"
                elif ats_margin < 0:
                    outcome = "NO_COVER"
                else:
                    outcome = "PUSH"
                rows.append({"spread_bucket": bucket, "outcome": outcome})

    out = (
        pd.DataFrame(rows)
        .groupby("spread_bucket")
        .agg(
            bets=("outcome", "count"),
            covers=("outcome", lambda x: (x == "COVER").sum()),
            no_covers=("outcome", lambda x: (x == "NO_COVER").sum()),
            pushes=("outcome", lambda x: (x == "PUSH").sum()),
        )
        .reset_index()
        .sort_values("spread_bucket")
    )

    out_path = OUT_DIR / path.name.replace(".csv", "_spread_buckets.csv")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("*.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
