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
            away_final = parse_float(r.get("away_final"))
            home_final = parse_float(r.get("home_final"))
            away_spread = parse_float(r.get("away_spread"))
            home_spread = parse_float(r.get("home_spread"))

            if away_final is None or home_final is None:
                continue

            neutral = str(r.get("neutral_location", "")).upper() == "YES"

            # --- Away side (include ALL spreads, +/-) ---
            if away_spread is not None:
                ats_margin = (away_final + away_spread) - home_final
                outcome = (
                    "PUSH" if ats_margin == 0
                    else "COVER" if ats_margin > 0
                    else "NO_COVER"
                )
                venue = "neutral" if neutral else "away"
                rows[venue].append({
                    "spread": away_spread,
                    "outcome": outcome
                })

            # --- Home side (include ALL spreads, +/-) ---
            if home_spread is not None:
                ats_margin = (home_final + home_spread) - away_final
                outcome = (
                    "PUSH" if ats_margin == 0
                    else "COVER" if ats_margin > 0
                    else "NO_COVER"
                )
                venue = "neutral" if neutral else "home"
                rows[venue].append({
                    "spread": home_spread,
                    "outcome": outcome
                })

    # Write outputs
    for venue, data in rows.items():
        out_path = OUT_DIRS[venue] / "exact_spreads.csv"

        if not data:
            pd.DataFrame(
                columns=["spread", "bets", "covers", "no_covers", "pushes"]
            ).to_csv(out_path, index=False)
            continue

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

        out.to_csv(out_path, index=False)


if __name__ == "__main__":
    main()
