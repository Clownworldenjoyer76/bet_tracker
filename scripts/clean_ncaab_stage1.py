import pandas as pd
from pathlib import Path

IN_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR = Path("bets/historic/ncaab_old/stage_3")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def process_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    # drop rows with ML = NL
    df = df[df["ML"] != "NL"].copy()

    # numeric finals for math only
    df["Final_num"] = pd.to_numeric(df["Final"], errors="coerce")

    # init output columns as strings
    df["actual_total"] = ""
    df["actual_spread"] = ""

    for gid, g in df.groupby("game_id"):
        if len(g) != 2:
            continue

        idx = g.index

        # actual total
        total = g["Final_num"].sum()
        df.loc[idx, "actual_total"] = str(int(total))

        # actual spread = favorite - underdog
        fav = g[g["favorite"].str.upper() == "YES"]
        dog = g[g["underdog"].str.upper() == "YES"]

        if len(fav) == 1 and len(dog) == 1:
            spread = fav.iloc[0]["Final_num"] - dog.iloc[0]["Final_num"]
            df.loc[idx, "actual_spread"] = str(int(spread))

    out = df[
        [
            "game_id",
            "VH",
            "Team",
            "Final",
            "ML",
            "favorite",
            "underdog",
            "over_under",
            "actual_total",
            "actual_spread",
        ]
    ]

    out_path = OUT_DIR / path.name.replace("_stage2", "_stage3")
    out.to_csv(out_path, index=False)

def main():
    for f in IN_DIR.glob("ncaa-basketball-*_stage2.csv"):
        process_file(f)

if __name__ == "__main__":
    main()
