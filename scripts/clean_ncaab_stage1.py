import pandas as pd
import re
from pathlib import Path

RAW_DIR = Path("bets/historic/ncaab_old")
OUT_DIR = RAW_DIR / "stage_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLS = {
    "Date", "Rot", "VH", "Team",
    "1st", "2nd", "Final",
    "Open", "Close", "ML"
}

def extract_season_start_year(filename: str) -> int:
    m = re.search(r"(19|20)\d{2}", filename)
    if not m:
        raise ValueError(f"{filename}: cannot infer season year")
    return int(m.group())

def clean_file(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")

    season_start = extract_season_start_year(path.name)

    # Date is irrelevant: assign season start year only
    df["season_year"] = season_start

    df["rotation"] = df["Rot"].astype(int)
    df["game_key"] = df["rotation"].where(
        df["rotation"] % 2 == 1,
        df["rotation"] - 1
    )

    df["is_home"] = (df["VH"] == "H").astype(int)
    df["is_away"] = (df["VH"] == "V").astype(int)
    df["is_neutral"] = (df["VH"] == "N").astype(int)

    df["team_score"] = df["Final"].astype(int)

    opp = (
        df[["game_key", "team_score"]]
        .groupby("game_key")
        .transform(lambda x: x.iloc[::-1].values)
    )
    df["opp_score"] = opp["team_score"]

    df["margin"] = df["team_score"] - df["opp_score"]
    df["win_flag"] = (df["margin"] > 0).astype(int)

    df["open_spread"] = pd.NA
    df["close_spread"] = pd.NA
    df["open_total"] = pd.NA
    df["close_total"] = pd.NA

    for gk, g in df.groupby("game_key"):
        if len(g) != 2:
            continue

        rows = g.index.tolist()

        # identify total vs spread by magnitude
        if abs(g.loc[rows[0], "Open"]) > 50:
            total_row, spread_row = rows[0], rows[1]
        else:
            spread_row, total_row = rows[0], rows[1]

        df.loc[rows, "open_total"] = g.loc[total_row, "Open"]
        df.loc[rows, "close_total"] = g.loc[total_row, "Close"]
        df.loc[rows, "open_spread"] = g.loc[spread_row, "Open"]
        df.loc[rows, "close_spread"] = g.loc[spread_row, "Close"]

    out_cols = [
        "season_year", "rotation", "game_key",
        "Team", "is_home", "is_away", "is_neutral",
        "team_score", "opp_score", "margin", "win_flag",
        "open_spread", "close_spread",
        "open_total", "close_total",
        "ML"
    ]

    return df[out_cols].sort_values(
        ["season_year", "game_key", "is_home"],
        ascending=[True, True, False]
    )

def main():
    files = sorted(RAW_DIR.glob("ncaa-basketball-*.xlsx"))
    if not files:
        raise RuntimeError("No XLSX files found")

    for f in files:
        clean = clean_file(f)
        clean.to_csv(OUT_DIR / f"{f.stem}_stage1.csv", index=False)

if __name__ == "__main__":
    main()
