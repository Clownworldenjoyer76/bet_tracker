import pandas as pd
from pathlib import Path

RAW_DIR = Path("bets/historic/ncaab_old")
OUT_DIR = RAW_DIR / "stage_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VH_MAP = {"H": "Home", "V": "Away", "N": "Neutral"}

def clean_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)

    df["date"] = df["Date"].astype(str).str.strip()

    # ROT as int (safe because CSV)
    df["Rot_int"] = pd.to_numeric(df["Rot"], errors="coerce").astype("Int64")
    # Pair rotation (odd-even pairing)
    df["pair_rot"] = df["Rot_int"].where(df["Rot_int"] % 2 == 1, df["Rot_int"] - 1)

    # CRITICAL: pair key must include date because rotation numbers repeat daily
    df["pair_key"] = df["date"] + "_" + df["pair_rot"].astype(str)

    # VH mapping
    vh = df["VH"].astype(str).str.upper().str.strip()
    df["VH_out"] = vh.map(VH_MAP).fillna("Neutral")

    # Build game_id per pair_key using the two teams (sorted by Rot)
    game_id_map = {}
    for pk, g in df.groupby("pair_key", dropna=False):
        if len(g) < 2:
            continue
        r = g.sort_values("Rot_int")
        team1 = r.iloc[0]["Team"]
        team2 = r.iloc[1]["Team"]
        gid = f"{r.iloc[0]['date']}_{team1}_{team2}"
        for idx in r.index:
            game_id_map[idx] = gid

    df["game_id"] = df.index.map(game_id_map)

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
        "2H": df["2H"],
    })

    return out

def main():
    for f in RAW_DIR.glob("ncaa-basketball-*.csv"):
        cleaned = clean_file(f)
        cleaned.to_csv(OUT_DIR / f"{f.stem}_stage1.csv", index=False)

if __name__ == "__main__":
    main()
