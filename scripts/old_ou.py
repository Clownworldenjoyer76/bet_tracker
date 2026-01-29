import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/Over_Under")
OUT_DIR.mkdir(parents=True, exist_ok=True)

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

        margin = actual - line

        if margin > 0:
            outcome = "OVER"
        elif margin < 0:
            outcome = "UNDER"
        else:
            outcome = "PUSH"

        rows.append({
            "over_under": line,
            "margin": margin,
            "outcome": outcome
        })

    d = pd.DataFrame(rows)

    out = (
        d.groupby("over_under")
        .agg(
            bets=("outcome", "count"),
            overs=("outcome", lambda x: (x == "OVER").sum()),
            unders=("outcome", lambda x: (x == "UNDER").sum()),
            pushes=("outcome", lambda x: (x == "PUSH").sum()),
            avg_margin=("margin", "mean"),
            median_margin=("margin", "median"),
            avg_over_margin=("margin", lambda x: x[x > 0].mean()),
            avg_under_margin=("margin", lambda x: x[x < 0].mean()),
        )
        .reset_index()
        .sort_values("over_under")
    )

    out_path = OUT_DIR / path.name.replace(".csv", "_ou_exact_totals.csv")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("*.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
