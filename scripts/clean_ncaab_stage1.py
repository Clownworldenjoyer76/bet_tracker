import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/stage_3")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def process_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    # normalize flags
    df["favorite"] = df["favorite"].str.upper().str.strip()
    df["underdog"] = df["underdog"].str.upper().str.strip()

    # initialize columns
    df["over_under"] = ""
    df["spread"] = ""

    # resolve per game_id
    for gid, g in df.groupby("game_id"):
        if len(g) != 2:
            continue

        # over/under from underdog row
        ou_row = g[g["underdog"] == "YES"]
        if len(ou_row) == 1:
            ou_value = ou_row.iloc[0]["Close"]
            df.loc[ou_row.index, "over_under"] = ou_value
            df.loc[g.index.difference(ou_row.index), "over_under"] = ou_value

        # spread from favorite row
        fav_row = g[g["favorite"] == "YES"]
        if len(fav_row) == 1:
            spread_val = fav_row.iloc[0]["Close"]
            spread_out = f"-{spread_val}"
            df.loc[fav_row.index, "spread"] = spread_out
            df.loc[g.index.difference(fav_row.index), "spread"] = spread_out

    out = df[
        [
            "game_id",
            "VH",
            "Team",
            "Final",
            "Close",
            "ML",
            "favorite",
            "underdog",
            "over_under",
            "spread",
        ]
    ]

    out_path = OUT_DIR / path.name.replace("_stage2", "_stage3")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("ncaa-basketball-*_stage2.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
