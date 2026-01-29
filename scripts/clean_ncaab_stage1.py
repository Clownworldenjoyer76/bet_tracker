import pandas as pd
from pathlib import Path
import re

IN_DIR = Path("bets/historic/ncaab_old/stage_1")
OUT_DIR = Path("bets/historic/ncaab_old/stage_2")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_season(filename: str) -> str:
    # first 4-digit year in filename
    m = re.search(r"(19|20)\d{2}", filename)
    if not m:
        raise ValueError(f"Cannot extract season from {filename}")
    return m.group()

def process_file(path: Path):
    season = extract_season(path.name)
    df = pd.read_csv(path, dtype=str)

    # moneyline to numeric for logic
    ml_num = pd.to_numeric(df["ML"], errors="coerce")

    favorite = []
    underdog = []

    for ml in ml_num:
        if pd.isna(ml):
            favorite.append("")
            underdog.append("")
        elif ml < 0:
            favorite.append("YES")
            underdog.append("")
        elif ml > 0:
            favorite.append("")
            underdog.append("YES")
        else:
            favorite.append("PUSH")
            underdog.append("PUSH")

    out = pd.DataFrame({
        "game_id": df["game_id"].astype(str) + "_" + season,
        "VH": df["VH"],
        "Team": df["Team"],
        "Final": df["Final"],
        "Close": df["Close"],
        "ML": df["ML"],
        "favorite": favorite,
        "underdog": underdog,
        "over_under": "",
        "spread": ""
    })

    out_path = OUT_DIR / path.name.replace("_stage1", "_stage2")
    out.to_csv(out_path, index=False)

def main():
    files = IN_DIR.glob("ncaa-basketball-*_stage1.csv")
    for f in files:
        process_file(f)

if __name__ == "__main__":
    main()
