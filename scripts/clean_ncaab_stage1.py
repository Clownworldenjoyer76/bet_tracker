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

def infer_year(mmdd: int, season_start: int) -> int:
    return season_start if mmdd // 100 >= 11 else season_start + 1

def clean_file(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")

    season_start = extract_season_start_year(path.name)

    # ---- Dates ----
    df["mmdd"] = pd.to_numeric(df["Date"], errors="coerce")
    df = df.dropna(subset=["mmdd"])
    df["mmdd"] = df["mmdd"].astype(int)

    df["year"] = df["mmdd"].apply(lambda x: infer_year(x, season_start))
    df["month"] = df["mmdd"] // 100
    df["day"] = df["mmdd"] % 100
    df["game_date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=df["day"]),
        errors="coerce"
    )
    df = df.dropna(subset=["game_date"])

    # ---- Rotation / Game Key ----
    df["rotation"] = pd.to_numeric(df["Rot"], errors="coerce")
    df = df.dropna(subset=["rotation"])
    df["rotation"] = df["rotation"].astype(int)
    df["game_key"] = df["rotation"].where(df["rotation"] % 2 == 1, df["rotation"] - 1)

    # ---- VH Handling ----
    vh = df["VH"].astype(str).str.upper().str.strip()
    df["is_home"] = (vh == "H").astype(int)
    df["is_away"] = (vh == "V").astype(int)
    df["is_neutral"] = (~vh.isin(["H", "V"])).astype(int)

    # ---- Scores ----
    df["team_score"] = pd.to_numeric(df["Final"], errors="coerce")
    df = df.dropna(subset=["team_score"])
    df["team_score"] = df["team_score"].astype(int)

    # Must have exactly 2 rows per game
    valid_games = df.groupby("game_key")["team_score"].count()
    valid_games = valid_games[valid_games == 2].index
    df = df[df["game_key"].isin(valid_games)]

    # Opponent score
    opp = (
        df[["game_key", "team_score"]]
        .groupby("game_key")
        .transform(lambda x: x.iloc[::-1].values)
    )
    df["opp_score"] = opp["team_score"]
    df["margin"] = df["team_score"] - df["opp_score"]
    df["win_flag"] = (df["margin"] > 0).astype(int)

    # ---- Odds: coerce to numeric safely ----
    def coerce_odds(s):
        s = s.astype(str).str.upper().str.strip()
        s = s.replace({"PK": "0", "PICK": "0", "": pd.NA, "NAN": pd.NA})
        return pd.to_numeric(s, errors="coerce")

    df["Open_num"] = coerce_odds(df["Open"])
    df["Close_num"] = coerce_odds(df["Close"])

    df["open_spread"] = pd.NA
    df["close_spread"] = pd.NA
    df["open_total"] = pd.NA
    df["close_total"] = pd.NA

    for gk, g in df.groupby("game_key"):
        if len(g) != 2:
            continue

        r1, r2 = g.index.tolist()
        o1, o2 = g.loc[r1, "Open_num"], g.loc[r2, "Open_num"]

        # If either is missing, skip odds assignment for this game
        if pd.isna(o1) or pd.isna(o2):
            continue

        # Totals are large; spreads are small
        if abs(o1) > 50:
            total_row, spread_row = r1, r2
        else:
            spread_row, total_row = r1, r2

        df.loc[g.index, "open_total"] = g.loc[total_row, "Open_num"]
        df.loc[g.index, "close_total"] = g.loc[total_row, "Close_num"]
        df.loc[g.index, "open_spread"] = g.loc[spread_row, "Open_num"]
        df.loc[g.index, "close_spread"] = g.loc[spread_row, "Close_num"]

    out_cols = [
        "game_date", "rotation", "game_key",
        "Team", "is_home", "is_away", "is_neutral",
        "team_score", "opp_score", "margin", "win_flag",
        "open_spread", "close_spread",
        "open_total", "close_total",
        "ML"
    ]

    return df[out_cols].sort_values(
        ["game_date", "game_key", "is_home"],
        ascending=[True, True, False]
    )

def main():
    files = sorted(RAW_DIR.glob("ncaa-basketball-*.xlsx"))
    if not files:
        raise RuntimeError("No XLSX files found")

    for f in files:
        cleaned = clean_file(f)
        cleaned.to_csv(OUT_DIR / f"{f.stem}_stage1.csv", index=False)

if __name__ == "__main__":
    main()
