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
        teams = g["Team"].tolist()

        # neutral location
        neutral_location = "YES" if all(v == "Neutral" for v in vh_vals) else "NO"

        # determine away/home
        if neutral_location == "NO":
            away_row = g[g["VH"] == "Away"].iloc[0]
            home_row = g[g["VH"] == "Home"].iloc[0]
        else:
            away_row = g.iloc[0]
            home_row = g.iloc[1]

        # safety check
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
