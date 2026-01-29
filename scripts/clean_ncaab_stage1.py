import pandas as pd
from pathlib import Path

RAW_DIR = Path("bets/historic/ncaab_old")
OUT_DIR = RAW_DIR / "stage_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VH_MAP = {
    "H": "Home",
    "V": "Away",
    "N": "Neutral"
}

def make_game_id(date, team1, team2):
    return f"{date}_{team1}_{team2}"

def clean_file(path: Path):
    df = pd.read_csv(path, dtype=str)

    # keep original date as-is
    df["date"] = df["Date"]

    # normalize VH
    df["VH_out"] = df["VH"].map(VH_MAP).fillna("Neutral")

    # rotation-based pairing
    df["Rot"] = df["Rot"].astype(int)
    df["pair_key"] = df["Rot"].where(df["Rot"] % 2 == 1, df["Rot"] - 1)

    game_ids = {}

    for pk, g in df.groupby("pair_key"):
        if len(g) != 2:
            continue
        r = g.sort_values("Rot")
        date = r.iloc[0]["date"]
        team1 = r.iloc[0]["Team"]
        team2 = r.iloc[1]["Team"]
        gid = make_game_id(date, team1, team2)
        for idx in r.index:
            game_ids[idx] = gid

    df["game_id"] = df.index.map(game_ids)

    out = pd.DataFrame({
        "date": df["date"],
        "game_id": df["game_id"],
        "VH": df["VH_out"],
        "Team": df["Team"],
        "1st": df["1st"],
        "2nd": df["2nd"],
        "Final": df["Final"],
        "Open": df["Open"],
        "Close": df["Close"],
        "ML": df["ML"],
        "2H": df["2H"]
    })

    return out

def main():
    files = RAW_DIR.glob("ncaa-basketball-*.csv")
    for f in files:
        cleaned = clean_file(f)
        out_path = OUT_DIR / f"{f.stem}_stage1.csv"
        cleaned.to_csv(out_path, index=False)

if __name__ == "__main__":
    main()
