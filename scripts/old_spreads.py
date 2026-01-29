import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/tally")
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

def main():
    rows = []

    for path in IN_DIR.glob("*.csv"):
        df = pd.read_csv(path, dtype=str)

        for _, r in df.iterrows():
            away_final = parse_float(r["away_final"])
            home_final = parse_float(r["home_final"])
            away_spread = parse_float(r["away_spread"])
            home_spread = parse_float(r["home_spread"])

            if away_final is None or home_final is None:
                continue

            if away_spread is not None and away_spread < 0:
                spread = away_spread
                ats_margin = (away_final + spread) - home_final
            elif home_spread is not None and home_spread < 0:
                spread = home_spread
                ats_margin = (home_final + spread) - away_final
            else:
                continue

            if ats_margin > 0:
                outcome = "COVER"
            elif ats_margin < 0:
                outcome = "NO_COVER"
            else:
                outcome = "PUSH"

            rows.append({"spread": spread, "outcome": outcome})

    out = (
        pd.DataFrame(rows)
        .groupby("spread")
        .agg(
            bets=("outcome", "count"),
            covers=("outcome", lambda x: (x == "COVER").sum()),
            no_covers=("outcome", lambda x: (x == "NO_COVER").sum()),
            pushes=("outcome", lambda x: (x == "PUSH").sum()),
        )
        .reset_index()
        .sort_values("spread")
    )

    out.to_csv(OUT_DIR / "exact_spreads_tally.csv", index=False)

if __name__ == "__main__":
    main()
