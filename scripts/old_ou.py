import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/Over_Under")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# total-size buckets (you can adjust later if you want)
TOTAL_BUCKETS = [
    (0, 120, "<120"),
    (120, 130, "120–130"),
    (130, 140, "130–140"),
    (140, 150, "140–150"),
    (150, 160, "150–160"),
    (160, 1000, "≥160"),
]

def bucketize_total(total):
    for lo, hi, label in TOTAL_BUCKETS:
        if lo <= total < hi:
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
        line = parse_float(r["over_under"])
        actual = parse_float(r["actual_total"])

        if line is None or actual is None:
            continue

        bucket = bucketize_total(line)
        if bucket is None:
            continue

        # outcome
        if actual > line:
            outcome = "OVER"
        elif actual < line:
            outcome = "UNDER"
        else:
            outcome = "PUSH"

        rows.append({
            "total_bucket": bucket,
            "outcome": outcome
        })

    out = (
        pd.DataFrame(rows)
        .groupby("total_bucket")
        .agg(
            bets=("outcome", "count"),
            overs=("outcome", lambda x: (x == "OVER").sum()),
            unders=("outcome", lambda x: (x == "UNDER").sum()),
            pushes=("outcome", lambda x: (x == "PUSH").sum()),
        )
        .reset_index()
        .sort_values("total_bucket")
    )

    out_path = OUT_DIR / path.name.replace(".csv", "_ou_buckets.csv")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("*.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
