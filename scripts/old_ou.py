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

def parse_float(val):
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
            line = parse_float(r["over_under"])
            actual = parse_float(r["actual_total"])

            if line is None or actual is None:
                continue

            neutral = str(r["neutral_location"]).upper() == "YES"
            venue = "neutral" if neutral else "home"  # totals are venue-based, not side-based

            margin = actual - line
            outcome = "PUSH" if margin == 0 else ("OVER" if margin > 0 else "UNDER")

            rows[venue].append({
                "over_under": line,
                "margin": margin,
                "outcome": outcome
            })

    for venue, data in rows.items():
        d = pd.DataFrame(data)

        out = (
            d.groupby("over_under")
            .agg(
                bets=("outcome", "count"),
                overs=("outcome", lambda x: (x == "OVER").sum()),
                unders=("outcome", lambda x: (x == "UNDER").sum()),
                pushes=("outcome", lambda x: (x == "PUSH").sum()),
                avg_margin=("margin", "mean"),
                median_margin=("margin", "median"),
            )
            .reset_index()
            .sort_values("over_under")
        )

        out.to_csv(OUT_DIRS[venue] / "exact_ou.csv", index=False)

if __name__ == "__main__":
    main()
