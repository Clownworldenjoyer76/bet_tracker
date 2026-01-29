import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/ML")
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

def process_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    rows = []

    for _, r in df.iterrows():
        away_final = float(r["away_final"])
        home_final = float(r["home_final"])

        # away side
        away_ml = parse_ml(r["away_ml"])
        if away_ml is not None:
            p = implied_prob(away_ml)
            prob_pct = int(round(p * 100))
            win = int(away_final > home_final)
            rows.append({"prob_pct": prob_pct, "win": win})

        # home side
        home_ml = parse_ml(r["home_ml"])
        if home_ml is not None:
            p = implied_prob(home_ml)
            prob_pct = int(round(p * 100))
            win = int(home_final > away_final)
            rows.append({"prob_pct": prob_pct, "win": win})

    out = (
        pd.DataFrame(rows)
        .groupby("prob_pct", dropna=True)
        .agg(bets=("win", "count"), wins=("win", "sum"))
        .reset_index()
        .sort_values("prob_pct")
    )

    out["actual_win_pct"] = out["wins"] / out["bets"]

    out_path = OUT_DIR / path.name.replace(".csv", "_ml_exact_probs.csv")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("*.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
