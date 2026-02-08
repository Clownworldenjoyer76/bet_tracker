import pandas as pd
import glob
from pathlib import Path

BASE_IN = Path("docs/win/final/step_2")
BASE_OUT = Path("docs/win/final/step_3")
BASE_OUT.mkdir(parents=True, exist_ok=True)

OUT_FILE = BASE_OUT / "final_edges.csv"


def load_and_filter(pattern, conditions, market):
    rows = []

    for f in glob.glob(str(pattern)):
        df = pd.read_csv(f)

        for juice_col, dk_col in conditions:
            if juice_col not in df.columns or dk_col not in df.columns:
                continue

            mask = df[juice_col] > df[dk_col]
            if mask.any():
                hit = df[mask].copy()
                hit["edge_market"] = market
                hit["edge_type"] = f"{juice_col} > {dk_col}"
                hit["source_file"] = Path(f).name
                rows.append(hit)

    if rows:
        return pd.concat(rows, ignore_index=True)

    return pd.DataFrame()


def run():
    outputs = []

    # ---------- MONEYLINE ----------
    outputs.append(
        load_and_filter(
            BASE_IN / "*/ml/juice_*_ml_*.csv",
            [
                ("deci_home_ml_juice_odds", "deci_dk_home_odds"),
                ("deci_away_ml_juice_odds", "deci_dk_away_odds"),
            ],
            "ml",
        )
    )

    # ---------- SPREADS ----------
    outputs.append(
        load_and_filter(
            BASE_IN / "*/spreads/juice_*_spreads_*.csv",
            [
                ("deci_away_spread_juice_odds", "deci_dk_away_odds"),
                ("deci_home_spread_juice_odds", "deci_dk_home_odds"),
            ],
            "spreads",
        )
    )

    # ---------- TOTALS ----------
    outputs.append(
        load_and_filter(
            BASE_IN / "*/totals/juice_*_totals_*.csv",
            [
                ("deci_over_juice_odds", "deci_dk_over_odds"),
                ("deci_under_juice_odds", "deci_dk_under_odds"),
            ],
            "totals",
        )
    )

    final = pd.concat(
        [df for df in outputs if not df.empty],
        ignore_index=True,
    )

    if final.empty:
        print("No edges found — final_edges.csv not written")
        return

    final.to_csv(OUT_FILE, index=False)
    print(f"Wrote {OUT_FILE} | rows: {len(final)}")


if __name__ == "__main__":
    run()
