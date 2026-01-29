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

def implied_prob(ml):
    return abs(ml) / (abs(ml) + 100) if ml < 0 else 100 / (ml + 100)

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
                    "prob_dec": round(implied_prob(away_ml), 3),
                    "win": int(away_final > home_final)
                })

            home_ml = parse_ml(r["home_ml"])
            if home_ml is not None:
                venue = "neutral" if neutral else "home"
                rows[venue].append({
                    "prob_dec": round(implied_prob(home_ml), 3),
                    "win": int(home_final > away_final)
                })

    for venue, data in rows.items():
        out = (
            pd.DataFrame(data)
            .groupby("prob_dec")
            .agg(bets=("win", "count"), wins=("win", "sum"))
            .reset_index()
            .sort_values("prob_dec")
        )
        out["actual_win_pct"] = out["wins"] / out["bets"]
        out.to_csv(OUT_DIRS[venue] / "ml_exact_probs.csv", index=False)

if __name__ == "__main__":
    main()
