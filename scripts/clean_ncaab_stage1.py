import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_3")
OUT_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def process_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    rows = []

    for gid, g in df.groupby("game_id"):
        if len(g) != 2:
            continue

        g = g.reset_index(drop=True)

        vh_vals = g["VH"].tolist()
        neutral_location = "YES" if all(v == "Neutral" for v in vh_vals) else "NO"

        away_row = None
        home_row = None

        if neutral_location == "NO":
            away_matches = g[g["VH"] == "Away"]
            home_matches = g[g["VH"] == "Home"]

            if len(away_matches) > 0:
                away_row = away_matches.iloc[0]
            if len(home_matches) > 0:
                home_row = home_matches.iloc[0]

        # fallback logic (neutral or partial labeling)
        if away_row is None or home_row is None:
            away_row = g.iloc[0]
            home_row = g.iloc[1]

        # safety: never same team
        if away_row["Team"] == home_row["Team"]:
            continue

        rows.append({
            "game_id": gid,
            "neutral_location": neutral_location,
            "away_team": away_row["Team"],
            "home_team": home_row["Team"],
            "away_final": away_row["Final"],
            "home_final": home_row["Final"],
            "away_ml": away_row["ML"],
            "home_ml": home_row["ML"],
            "over_under": away_row["over_under"],
            "actual_total": away_row["actual_total"],
            "away_spread": away_row["spread"],
            "home_spread": home_row["spread"],
        })

    out_df = pd.DataFrame(rows)
    out_path = OUT_DIR / path.name.replace("_stage3", "_stage2")
    out_df.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("ncaa-basketball-*_stage3.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
