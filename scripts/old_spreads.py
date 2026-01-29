import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/tally")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_float(val):
    try:
        v = str(val).strip()
        if v in ("", "NL", "-"):
            return None
        return float(v)
    except Exception:
        return None


def main():
    rows = []

    for path in IN_DIR.glob("*.csv"):
        df = pd.read_csv(path, dtype=str)

        for _, r in df.iterrows():
            away_final = parse_float(r.get("away_final"))
            home_final = parse_float(r.get("home_final"))
            away_spread = parse_float(r.get("away_spread"))
            home_spread = parse_float(r.get("home_spread"))

            if away_final is None or home_final is None:
                continue

            # --- Away side (ALL spreads) ---
            if away_spread is not None:
                ats_margin = (away_final + away_spread) - home_final
                outcome = (
                    "PUSH" if ats_margin == 0
                    else "COVER" if ats_margin > 0
                    else "NO_COVER"
                )
                rows.append({
                    "spread": away_spread,
                    "outcome": outcome
                })

            # --- Home side (ALL spreads) ---
            if home_spread is not None:
                ats_margin = (home_final + home_spread) - away_final
                outcome = (
                    "PUSH" if ats_margin == 0
                    else "COVER" if ats_margin > 0
                    else "NO_COVER"
                )
                rows.append({
                    "spread": home_spread,
                    "outcome": outcome
                })

    if not rows:
        pd.DataFrame(
            columns=["spread", "bets", "covers", "no_covers", "pushes"]
        ).to_csv(OUT_DIR / "exact_spreads.csv", index=False)
        return

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

    out.to_csv(OUT_DIR / "exact_spreads.csv", index=False)


if __name__ == "__main__":
    main()
