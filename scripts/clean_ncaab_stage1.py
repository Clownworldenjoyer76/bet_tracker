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

def clean_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)

    # date passthrough
    df["date"] = df["Date"].astype(str).str.strip()

    # rotation handling
    df["Rot_int"] = pd.to_numeric(df["Rot"], errors="coerce").astype("Int64")
    df["pair_rot"] = df["Rot_int"].where(
        df["Rot_int"] % 2 == 1,
        df["Rot_int"] - 1
    )

    # stable game_id = date + rotation pair
    df["game_id"] = df["date"] + "_" + df["pair_rot"].astype(str)

    # VH mapping
    vh = df["VH"].astype(str).str.upper().str.strip()
    df["VH_out"] = vh.map(VH_MAP).fillna("Neutral")

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
        out_path = OUT_DIR / f"{f.stem}_stage1.csv"
        cleaned.to_csv(out_path, index=False)

if __name__ == "__main__":
    main()
