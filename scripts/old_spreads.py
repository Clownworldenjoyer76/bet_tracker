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
            away_final = parse_float(r["away_final"])
            home_final = parse_float(r["home_final"])
            away_spread = parse_float(r["away_spread"])
            home_spread = parse_float(r["home_spread"])

            if away_final is None or home_final is None:
                continue

            neutral = str(r["neutral_location"]).upper() == "YES"

            if away_spread is not None and away_spread < 0:
                spread = away_spread
                ats_margin = (away_final + spread) - home_final
                venue = "neutral" if neutral else "away"
            elif home_spread is not None and home_spread < 0:
                spread = home_spread
                ats_margin = (home_final + spread) - away_final
                venue = "neutral" if neutral else "home"
            else:
                continue

            outcome = "PUSH" if ats_margin == 0 else ("COVER" if ats_margin > 0 else "NO_COVER")

            rows[venue].append({"spread": spread, "outcome": outcome})

    for venue, data in rows.items():
        out = (
            pd.DataFrame(data)
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

        out.to_csv(OUT_DIRS[venue] / "exact_spreads.csv", index=False)

if __name__ == "__main__":
    main()
