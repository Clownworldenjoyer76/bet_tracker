import pandas as pd
from pathlib import Path

CLEAN_DIR = Path("docs/win/clean")
EDGE_DIR = Path("docs/win/edge")
EDGE_DIR.mkdir(parents=True, exist_ok=True)

def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds >= 2:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

def implied_prob_from_decimal(decimal_odds: float) -> float:
    return 1 / decimal_odds

for csv_path in CLEAN_DIR.glob("win_prob__clean_soc_*"):
    df = pd.read_csv(csv_path)

    for side in ["home", "draw", "away"]:
        dec_col = f"{side}_odds_decimal"
        amer_col = f"{side}_odds_american"
        imp_col = f"{side}_prob_market"
        edge_col = f"{side}_edge"

        df[amer_col] = df[dec_col].apply(decimal_to_american)
        df[imp_col] = df[dec_col].apply(implied_prob_from_decimal)
        df[edge_col] = df[f"{side}_prob_model"] - df[imp_col]

    out_path = EDGE_DIR / csv_path.name.replace("clean", "edge")
    df.to_csv(out_path, index=False)

    print(f"Wrote {out_path}")
