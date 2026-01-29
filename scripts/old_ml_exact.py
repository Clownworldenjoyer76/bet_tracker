import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/tally")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def implied_prob(ml: float) -> float:
    if ml < 0:
        return abs(ml) / (abs(ml) + 100)
    return 100 / (ml + 100)

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
                p = round(implied_prob(away_ml), 3)
                rows.append({"prob_dec": p, "win": int(away_final > home_final)})

            home_ml = parse_ml(r["home_ml"])
            if home_ml is not None:
                p = round(implied_prob(home_ml), 3)
                rows.append({"prob_dec": p, "win": int(home_final > away_final)})

    out = (
        pd.DataFrame(rows)
        .groupby("prob_dec")
        .agg(bets=("win", "count"), wins=("win", "sum"))
        .reset_index()
        .sort_values("prob_dec")
    )

    out["actual_win_pct"] = out["wins"] / out["bets"]

    out.to_csv(OUT_DIR / "exact_ml_prob_tally.csv", index=False)

if __name__ == "__main__":
    main()
